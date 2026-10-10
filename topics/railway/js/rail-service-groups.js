/* Railway 07: selectable service corridors across DB infrastructure route IDs.
   Example: RE4 uses 6107 and 6179 around Berlin. This ONLY aggregates
   observed stop counts for the detail card. Observed red/orange/green strokes
   retain their source-level grades; missing stop records never gain values. */
(()=>{
'use strict';
const {actualBounds}=window.Railway07Geometry;
const GEO_WORLD=131072,MAX_KM=18;
const kmPerPixel=y=>40075/GEO_WORLD/Math.cosh(Math.PI-2*Math.PI*y/GEO_WORLD);
function dominantLabel(group){
 const weights=new Map();
 for(const {leg} of group.members){
  for(const row of leg.label_hints||[]){
   if(!Array.isArray(row)||typeof row[0]!=='string')continue;
   const n=Number(row[1]);
   if(!(n>0))continue;
   weights.set(row[0],(weights.get(row[0])||0)+n);
  }
 }
 const arr=[...weights.entries()].sort((a,b)=>b[1]-a[1]);
 if(!arr.length||arr[0][1]<100)return null;
 const total=arr.reduce((n,r)=>n+r[1],0);
 return arr[0][1]/total>=.6?arr[0][0]:null;
}
function endpoint(group,side){
 const valid=group.members.filter(m=>{
  const r=m.leg.km_range;return Array.isArray(r)&&r.length===2&&r.every(Number.isFinite);
 });
 if(!valid.length)return [];
 const extreme=side==='low'
  ?Math.min(...valid.flatMap(m=>m.leg.km_range))
  :Math.max(...valid.flatMap(m=>m.leg.km_range));
 const out=[];
 for(const m of valid){
  const k=side==='low'?Math.min(...m.leg.km_range):Math.max(...m.leg.km_range);
  if(Math.abs(k-extreme)>.25)continue;
  for(const p of m.parts){
   const v=p.xy;out.push([v[0],v[1]],[v[v.length-2],v[v.length-1]]);
  }
  if(out.length>40)break;
 }
 return out;
}
function closestPair(a,b){
 let result=null,best=Infinity;
 for(const sideA of ['low','high'])for(const sideB of ['low','high']){
  const aa=endpoint(a,sideA),bb=endpoint(b,sideB);
  for(const x of aa)for(const y of bb){
   const d=Math.hypot(x[0]-y[0],x[1]-y[1]);
   if(d>=best)continue;
   best=d;result={a:x,b:y,sideA,sideB,
    straightKm:d*kmPerPixel((x[1]+y[1])/2)};
  }
 }
 return result;
}
function joinServiceCorridors(groups,graph,metric='both'){
 const labelGroups=new Map();
 groups.forEach((g,i)=>{
  const label=dominantLabel(g);
  if(!label)return;
  if(!labelGroups.has(label))labelGroups.set(label,[]);
  labelGroups.get(label).push(i);
 });
 const candidates=[];
 for(const [label,indices] of labelGroups){
  for(let i=0;i<indices.length;i++){
   const left=groups[indices[i]];
   for(let j=i+1;j<indices.length;j++){
    const right=groups[indices[j]];
    if(String(left.members[0].leg.route)===String(right.members[0].leg.route))continue;
    const link=closestPair(left,right);
    if(!link||link.straightKm>MAX_KM)continue;
    candidates.push({u:indices[i],v:indices[j],label,...link});
   }
  }
 }
 candidates.sort((a,b)=>a.straightKm-b.straightKm);
 const endpointKey=(id,side)=>id+':'+side;
 const byEnd=new Map();
 for(const c of candidates){
  for(const k of [endpointKey(c.u,c.sideA),endpointKey(c.v,c.sideB)]){
   if(!byEnd.has(k))byEnd.set(k,[]);
   byEnd.get(k).push(c);
  }
 }
 const parent=groups.map((_,i)=>i);
 const root=id=>{while(parent[id]!==id){parent[id]=parent[parent[id]];id=parent[id];}return id;};
 const used=new Set(),accepted=[];
 for(const c of candidates){
  const k1=endpointKey(c.u,c.sideA),k2=endpointKey(c.v,c.sideB);
  if(used.has(k1)||used.has(k2)||root(c.u)===root(c.v))continue;
  const dominant=k=>{
   const list=byEnd.get(k)||[];
   const alternate=list.find(row=>row!==c);
   return !alternate||alternate.straightKm>c.straightKm*1.3+1;
  };
  if(!dominant(k1)||!dominant(k2))continue;
  let path=null;
  if(c.straightKm>.3)
   path=graph.find(groups[c.u].members[0].leg.route,c.a,c.b,
    Math.min(25,c.straightKm*1.6+3));
  if(path&&path.km>c.straightKm*1.7+2)path=null;
  if(!path){
   // When topology of independently packed DB sections is incomplete,
   // preserve the original green underlay; a statistical association alone
   // does NOT authorize inventing a geometry path or painting a red gap.
   const aa=graph.nearest('__PHYSICAL_NETWORK__',c.a);
   const bb=graph.nearest('__PHYSICAL_NETWORK__',c.b);
   if(c.straightKm>12||!aa||!bb||aa.d>.3**2||bb.d>.3**2)continue;
   path={parts:[],km:c.straightKm,visualOnly:true};
  }
  parent[root(c.v)]=root(c.u);
  used.add(k1);used.add(k2);
  accepted.push({...c,path});
 }
 const clusters=new Map();
 groups.forEach((g,i)=>{
  const key=root(i);
  if(!clusters.has(key))clusters.set(key,[]);
  clusters.get(key).push(g);
 });
 const linkClusters=new Map();
 for(const c of accepted){
  const key=root(c.u);
  if(!linkClusters.has(key))linkClusters.set(key,[]);
  linkClusters.get(key).push(c);
 }
 const map=new Map(),corridors=[],servicePaths=[];
 for(const [id,gs] of clusters){
  if(gs.length===1){
   map.set(gs[0],gs[0]);corridors.push(gs[0]);continue;
  }
  const members=gs.flatMap(g=>g.members);
  const observed=members.flatMap(m=>m.parts);
  const ownBridges=gs.flatMap(g=>g.bridgeParts||[]);
  const joins=linkClusters.get(id)||[];
  const connectionParts=joins.flatMap(c=>c.path.parts);
  servicePaths.push(...connectionParts);
  const parts=[...observed,...ownBridges,...connectionParts];
  const nArrival=members.reduce((n,m)=>n+m.m.nArrival,0);
  const nPlanned=members.reduce((n,m)=>n+m.m.nPlanned,0);
  const lateCount=members.reduce((n,m)=>n+Number(m.leg.v11?.late6||0),0);
  const cancelCount=members.reduce((n,m)=>n+Number(m.leg.v11?.boundary_cancel||0),0);
  const late=nArrival?100*lateCount/nArrival:null;
  const cancel=nPlanned?100*cancelCount/nPlanned:null;
  const m={late,onTime:late===null?null:100-late,cancel,nArrival,nPlanned};
  const grade=window.Railway07Analysis.grade(m,metric);
  const joined={members,parts,bounds:actualBounds(parts),grade,m,
   serviceName:joins[0].label,serviceLinks:joins.length,
   gradeVariation:gs.some(g=>g.grade!==grade),
   bridgeParts:[...ownBridges,...connectionParts],
   bridges:gs.reduce((n,g)=>n+(g.bridges||0),0)+joins.length,
   schematicBridges:gs.reduce((n,g)=>n+(g.schematicBridges||0),0)+
    joins.filter(x=>x.path.visualOnly).length};
  for(const g of gs)map.set(g,joined);
  corridors.push(joined);
 }
 return {corridors,map,servicePaths,joined:accepted.length};
}
window.Railway07ServiceGroups=Object.freeze({dominantLabel,closestPair,joinServiceCorridors});
})();