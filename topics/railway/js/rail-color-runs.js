/* Railway 07 / interaction only.
 * A click selects the MAXIMAL contiguous stretch with ONE DISPLAYED colour
 * inside an existing city-to-city passenger corridor.  Green missing-data
 * geometry stays physical and selectable, but acquires no fictitious KPI.
 * All highlighted vertices lie on DB InfraGO geometry where verified.
 */
(()=>{
'use strict';
const {shape,actualBounds,segmentDist}=window.Railway07Geometry;
const {SpatialIndex}=window.Railway07Picker;
const {grade:gradeOf}=window.Railway07Analysis;
const RADIUS=.9;  // projection pixels at reference zoom 9, not kilometres
const SPACING=.85;
const sq=x=>x*x;
function indexItems(items){
 const indexes=[null,new SpatialIndex(),new SpatialIndex()];
 for(const item of items||[])
  if(item.grade===1||item.grade===2)indexes[item.grade].add(item);
 return indexes;
}
function color(point,indexes){
 // Rendering order is green underlay / orange / red. Red wins at overlaps.
 return indexes[2].nearest(point,RADIUS)?2:
   indexes[1].nearest(point,RADIUS)?1:0;
}
function samplePath(parts,indexes){
 const runs=[];let current=null,carry=null;
 function emit(){
  if(current&&current.coordinates.length>=4){
   const part=shape(current.coordinates);
   runs.push({grade:current.grade,parts:[part],bounds:actualBounds([part]),
    sampledPoints:current.coordinates.length/2});
  }
  current=null;
 }
 function add(grade,x,y){
  if(!current||current.grade!==grade){
   const previous=carry;
   emit();
   current={grade,coordinates:previous?[...previous,x,y]:[x,y]};
  }else{
   const p=current.coordinates;
   if(p[p.length-2]!==x||p[p.length-1]!==y)p.push(x,y);
  }
  carry=[x,y];
 }
 for(let k=0;k<parts.length;k++){
  const xy=parts[k].xy;
  // A DB source line part may be a new disconnected component: never draw
  // a fake connecting segment between the previous part and this one.
  if(k>0){
   const prev=parts[k-1].xy;
   if(Math.hypot(prev[prev.length-2]-xy[0],prev[prev.length-1]-xy[1])>1.2){
    emit();carry=null;
   }
  }
  for(let i=2;i<xy.length;i+=2){
   const ax=xy[i-2],ay=xy[i-1],bx=xy[i],by=xy[i+1];
   const length=Math.hypot(bx-ax,by-ay);
   const steps=Math.max(1,Math.ceil(length/SPACING));
   // Sample along ACTUAL existing DB vertices/edges, not a city chord.
   for(let n=i===2?0:1;n<=steps;n++){
    const t=n/steps,x=ax+(bx-ax)*t,y=ay+(by-ay)*t;
    add(color([x,y],indexes),x,y);
   }
  }
 }
 emit();
 // Suppress tiny false colour spikes from parallel tracks / points within a
 // station. Never bridge across a real long contrasting stretch.
 const length=r=>r.parts.reduce((sum,p)=>{
  const a=p.xy;for(let i=2;i<a.length;i+=2)
   sum+=Math.hypot(a[i]-a[i-2],a[i+1]-a[i-1]);return sum;
 },0);
 for(let i=1;i<runs.length-1;i++){
  if(length(runs[i])<1.15 && runs[i-1].grade===runs[i+1].grade){
   // Retain original verified vertices, absorb only a ~few-hundred-metre
   // discontinuity; segment at the existing track coordinates.
   runs[i].grade=runs[i-1].grade;
  }
 }
 const merged=[];
 for(const run of runs){
  const before=merged[merged.length-1];
  const prev=before?.parts[before.parts.length-1]?.xy;
  const first=run.parts[0].xy;
  const adjacent=prev&&Math.hypot(
   prev[prev.length-2]-first[0],prev[prev.length-1]-first[1])<1.2;
  if(before&&before.grade===run.grade&&adjacent){
   before.parts.push(...run.parts);before.bounds=actualBounds(before.parts);
   before.sampledPoints+=run.sampledPoints;
  }else merged.push(run);
 }
 return merged;
}
function closestOnParts(point,parts){
 let d=Infinity;
 for(const part of parts){
  if(point[0]<part.minX-4||point[0]>part.maxX+4||
     point[1]<part.minY-4||point[1]>part.maxY+4)continue;
  const a=part.xy;
  for(let i=2;i<a.length;i+=2)
   d=Math.min(d,segmentDist(...point,a[i-2],a[i-1],a[i],a[i+1]));
 }
 return d;
}
function samples(member){
 const out=[];
 for(const part of member.parts||[]){
  const a=part.xy;
  if(a.length<4)continue;
  const i=Math.floor((a.length/2-1)/2)*2;
  const j=Math.min(i+2,a.length-2);
  out.push([a[0],a[1]],
   [(a[i]+a[j])/2,(a[i+1]+a[j+1])/2],
   [a[a.length-2],a[a.length-1]]);
 }
 return out;
}
function aggregate(members){
 if(!members.length)return {
  m:{nArrival:0,nPlanned:0,late:null,cancel:null,onTime:null},
  noData:true
 };
 const nArrival=members.reduce((s,x)=>s+x.m.nArrival,0);
 const nPlanned=members.reduce((s,x)=>s+x.m.nPlanned,0);
 const l=members.reduce((s,x)=>s+Number(x.leg.v11?.late6||0),0);
 const c=members.reduce((s,x)=>s+Number(x.leg.v11?.boundary_cancel||0),0);
 const late=nArrival?100*l/nArrival:null;
 const cancel=nPlanned?100*c/nPlanned:null;
 return {m:{nArrival,nPlanned,late,cancel,onTime:late===null?null:100-late},
  noData:false};
}
function decorate(runs,observations,group=null){
 // Each directional observation contributes to ONE selected colour component,
 // so the displayed denominators never multiply when a track is sampled.
 const apportioned=new Map(runs.map(x=>[x,[]]));
 for(const item of observations||[]){
  const pts=samples(item);if(!pts.length)continue;
  let best=null,d=Infinity;
  for(const run of runs){
   // Use source endpoints and midpoint, not only the centre of a long stop
   // link, which may straddle the boundary of a physical colour component.
   // Opposite directions on the same track contribute to the same denominator.
   const q=Math.min(...pts.map(pt=>closestOnParts(pt,run.parts)));
   // At an exact colour boundary, a station edge's endpoint may touch the
   // previous risk component. Prefer its own observed tier at comparable
   // distance, but allow reverse-direction tiers on the same physical part.
   const rank=q+(run.grade===item.grade?0:2.1);
   if(rank<d){d=rank;best=run;}
  }
  if(best&&d<6)apportioned.get(best).push(item);
 }
 runs.forEach((run,i)=>{
  const members=apportioned.get(run);
  const {m,noData}=aggregate(members);
  Object.assign(run,{members,m,unobserved:noData,shadeRun:true,
   colorIndex:i,colorTotal:runs.length,
   route:group?.members?.[0]?.leg?.route||'',
   cityFrom:group?.cityFrom,cityTo:group?.cityTo,
   startStation:group?.startStation,endStation:group?.endStation,
   serviceName:group?.serviceName||'',observedEdges:members.length});
 });
 return runs;
}
function forCorridor(group,backbone){
 if(group._colorRuns)return group._colorRuns;
 const verified=backbone.full(group);
 if(!verified?.length){
  // Fallback still groups continuous SAME-GRADE observed station chains,
  // never replacing the official backbone with a drawn city-to-city chord.
  const members=group.members||[],byGrade=new Map();
  for(const member of members){
   if(!byGrade.has(member.grade))byGrade.set(member.grade,[]);
   byGrade.get(member.grade).push(member);
  }
  const runs=[];
  for(const [grade,items] of byGrade){
   // Separate disconnected station components even when identical colour.
   const remaining=new Set(items);
   while(remaining.size){
    const start=remaining.values().next().value;
    const chunk=[start];remaining.delete(start);
    const nodes=new Set([start.leg.from_station,start.leg.to_station]);
    let expand=true;
    while(expand){
     expand=false;
     for(const item of [...remaining]){
      if(nodes.has(item.leg.from_station)||nodes.has(item.leg.to_station)){
       chunk.push(item);remaining.delete(item);
       nodes.add(item.leg.from_station);nodes.add(item.leg.to_station);
       expand=true;
      }
     }
    }
    const parts=chunk.flatMap(x=>x.parts);
    runs.push({grade,parts,bounds:actualBounds(parts),members:chunk,
     m:aggregate(chunk).m,unobserved:false,shadeRun:true,
     route:group.members[0].leg.route,cityFrom:group.cityFrom,
     cityTo:group.cityTo,startStation:group.startStation,
     endStation:group.endStation,serviceName:group.serviceName,
     observedEdges:chunk.length});
   }
  }
  return group._colorRuns=runs;
 }
 const indexes=indexItems(group.members);
 const cuts=samplePath(verified,indexes);
 return group._colorRuns=decorate(cuts,group.members,group);
}
function forOfficial(official,rawRisk){
 const indexes=indexItems(rawRisk.filter(x=>x.grade>0));
 const cuts=samplePath(official.parts,indexes);
 // An arbitrary official track may run alongside a measured route.  Risk
 // locations determine the colour boundary only; they cannot supply
 // statistics to an unverified, possibly parallel no-data track.
 const runs=decorate(cuts,[],null);
 for(const r of runs)r.route=official.route;
 return runs;
}
function findRun(runs,point,preferred=null,maxDist=16){
 let best=null,d=Infinity;
 for(const run of runs){
  const dd=closestOnParts(point,run.parts);
  const score=dd+(preferred!==null&&run.grade!==preferred?Math.max(3,maxDist/3):0);
  if(score<d){d=score;best=run;}
 }
 return d<maxDist*maxDist?best:null;
}
window.Railway07ColorRuns=Object.freeze({
 samplePath,indexItems,forCorridor,forOfficial,findRun,aggregate
});
})();