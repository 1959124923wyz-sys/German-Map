/* Railway 07: conservative visual gap bridges over DB InfraGO official geometries.
   Official infrastructure is the ONLY drawable connector. No straight-line joins,
   no imputed delays, and no changes to the observation denominator. */
(()=>{
'use strict';
const {shape,actualBounds}=window.Railway07Geometry;
const STEP=.15,CELL=8,MAX_GAP=25,MAX_SNAP=1.15,GLOBAL='__PHYSICAL_NETWORK__';
const nodeKey=(x,y)=>Math.round(x/STEP)+','+Math.round(y/STEP);
const cellKey=(x,y)=>Math.floor(x/CELL)+','+Math.floor(y/CELL);
const kmPerPixel=(y)=>{
 const n=Math.PI-2*Math.PI*y/131072;
 return (40075/131072)/Math.cosh(n);
};
function length(points){
 let sum=0;
 for(let i=2;i<points.length;i+=2)
  sum+=Math.hypot(points[i]-points[i-2],points[i+1]-points[i-1])*kmPerPixel((points[i+1]+points[i-1])/2);
 return sum;
}
function closest(xy,x,y){
 let d=Infinity,index=-1,t=0,point=null;
 for(let i=2;i<xy.length;i+=2){
  const ax=xy[i-2],ay=xy[i-1],bx=xy[i],by=xy[i+1],dx=bx-ax,dy=by-ay;
  const q=dx*dx+dy*dy;
  const u=q?Math.max(0,Math.min(1,((x-ax)*dx+(y-ay)*dy)/q)):0;
  const px=ax+u*dx,py=ay+u*dy,dist=(x-px)**2+(y-py)**2;
  if(dist<d){d=dist;index=i;t=u;point=[px,py];}
 }
 return {d,index,t,point};
}
function partial(match,end){
 const a=match.edge.part.xy,i=match.index,pt=match.point;
 const out=[pt[0],pt[1]];
 if(end===0){
  out.push(a[i-2],a[i-1]);
  for(let j=i-4;j>=0;j-=2)out.push(a[j],a[j+1]);
 }else{
  out.push(a[i],a[i+1]);
  for(let j=i+2;j<a.length;j+=2)out.push(a[j],a[j+1]);
 }
 return shape(out);
}
function reversed(p){
 const a=p.xy,b=[];
 for(let i=a.length-2;i>=0;i-=2)b.push(a[i],a[i+1]);
 return shape(b);
}
class RouteGraph{
 constructor(){this.routes=new Map();this.allCells=new Map();this.edges=0;this.reasons={noRoute:0,noSnap:0,far:0,sameEdgeTooLong:0,noPath:0,ratio:0,success:0};}
 add(route,part){
  if(route===undefined||route===null||!part?.xy||part.xy.length<4)return;
  const key=String(route);
  // A separate exact-geometry graph allows bounded traversals over official
  // routing-number discontinuities, without inventing any connector points.
  if(key!==GLOBAL)this.add(GLOBAL,part);
  let r=this.routes.get(key);
  if(!r){r={nodes:new Map(),cells:new Map(),edges:[]};this.routes.set(key,r);}
  const xy=part.xy;
  // Endpoint coordinates of independently published DB geometries may differ
  // by a few metres and fall on opposite quantization-cell boundaries.
  // Snapping the closest REAL existing endpoint avoids artificial topology
  // gaps; it never adds a drawing segment or joins far-away tracks.
  const getNode=(x,y)=>{
   const ix=Math.round(x/STEP),iy=Math.round(y/STEP);
   // Across infrastructure-number boundaries, published line ends may stop
   // at opposite sides of a switch/junction. Search a cartographic-scale
   // radius (no synthetic path is drawn between these endpoint records).
   const radius=key===GLOBAL?.60:.28;
   const cells=Math.ceil(radius/STEP);
   let nearest=null,dist=radius**2;
   for(let ax=ix-cells;ax<=ix+cells;ax++)for(let ay=iy-cells;ay<=iy+cells;ay++){
    const node=r.nodes.get(ax+','+ay);if(!node)continue;
    const d=(node.xy[0]-x)**2+(node.xy[1]-y)**2;
    if(d<dist){dist=d;nearest=node;}
   }
   if(nearest)return nearest;
   const nodeId=ix+','+iy,node={key:nodeId,xy:[x,y],adj:[]};
   r.nodes.set(nodeId,node);return node;
  };
  const nodes=[getNode(xy[0],xy[1]),getNode(xy[xy.length-2],xy[xy.length-1])];
  const edge={part,nodes,length:length(xy)};
  r.edges.push(edge);if(key!==GLOBAL)this.edges++;
  if(nodes[0]!==nodes[1]){
   nodes[0].adj.push([nodes[1],edge,0]);
   nodes[1].adj.push([nodes[0],edge,1]);
  }
  const x0=Math.floor(part.minX/CELL),x1=Math.floor(part.maxX/CELL);
  const y0=Math.floor(part.minY/CELL),y1=Math.floor(part.maxY/CELL);
  // The rare very long segment is still indexed; never approximate geometry.
  for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++){
   const k=x+','+y;
   if(!r.cells.has(k))r.cells.set(k,[]);
   r.cells.get(k).push(edge);
   if(key!==GLOBAL){
    if(!this.allCells.has(k))this.allCells.set(k,[]);
    this.allCells.get(k).push({route:key,edge});
   }
  }
 }
 nearest(route,pt){
  const r=this.routes.get(String(route));if(!r)return null;
  const [x,y]=pt,cx=Math.floor(x/CELL),cy=Math.floor(y/CELL);
  const seen=new Set();let best=null;
  for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++){
   for(const edge of r.cells.get((cx+dx)+','+(cy+dy))||[]){
    if(seen.has(edge))continue;seen.add(edge);
    if(x<edge.part.minX-MAX_SNAP||x>edge.part.maxX+MAX_SNAP||
       y<edge.part.minY-MAX_SNAP||y>edge.part.maxY+MAX_SNAP)continue;
    const hit=closest(edge.part.xy,x,y);
    if(hit.d>MAX_SNAP**2||best&&hit.d>=best.d)continue;
    best={edge,...hit};
   }
  }
  return best;
 }
 // Certain published observation links refer to a different DB route label
 // than the later infrastructure extract. Reconcile only through identical
 // geographic curves, never by guessing a numerical ID.
 resolveRoute(observedRoute,from,to){
  const direct=String(observedRoute);
  if(this.routes.has(direct)&&this.nearest(direct,from)&&this.nearest(direct,to))return direct;
  const options=pt=>{
   const [x,y]=pt,cx=Math.floor(x/CELL),cy=Math.floor(y/CELL);
   const seen=new Set(),matches=new Map();
   for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++){
    for(const {route,edge} of this.allCells.get((cx+dx)+','+(cy+dy))||[]){
     if(seen.has(edge))continue;seen.add(edge);
     if(x<edge.part.minX-.5||x>edge.part.maxX+.5||
        y<edge.part.minY-.5||y>edge.part.maxY+.5)continue;
     const hit=closest(edge.part.xy,x,y);
     if(hit.d>.5**2)continue;
     if(!matches.has(route)||hit.d<matches.get(route))matches.set(route,hit.d);
    }
   }
   return matches;
  };
  const a=options(from),b=options(to),common=[];
  for(const [route,dist] of a){
   if(b.has(route))common.push([route,dist+b.get(route)]);
  }
  common.sort((x,y)=>x[1]-y[1]);
  if(!common.length)return null;
  // Official geometry may contain several parallel track records; accept
  // only a clearly closest physical alignment for both ends.
  if(common.length>1&&common[1][1]<common[0][1]*1.5+.003)return false;
  return common[0][0];
 }
 find(route,from,to,maxKm=MAX_GAP){
  const resolved=this.resolveRoute(route,from,to);
  // At major stations several equally near official infrastructure labels
  // can be present. A long, geographically separated pair may still be
  // verified by a strictly bounded path in the complete physical graph.
  const spanKm=Math.hypot(from[0]-to[0],from[1]-to[1])*kmPerPixel((from[1]+to[1])/2);
  if(resolved===false&&spanKm<6){this.reasons.noRoute++;return null;}
  const actual=resolved||GLOBAL;
  const r=this.routes.get(actual);
  if(!r){this.reasons.noRoute++;return null;}
  const a=this.nearest(actual,from),b=this.nearest(actual,to);
  // Avoid attaching a measured leg to a nearby unrelated parallel line.
  if(!a||!b||(actual===GLOBAL&&(a.d>.35**2||b.d>.35**2))){this.reasons.noSnap++;return null;}
  const distance=Math.hypot(from[0]-to[0],from[1]-to[1]);
  if(distance>maxKm/Math.min(kmPerPixel(from[1]),kmPerPixel(to[1]))+5){this.reasons.far++;return null;}
  // Same original source element: trace its REAL curve between projections.
  if(a.edge===b.edge){
   const xy=a.edge.part.xy;
   const al=a.index/2-1+a.t,bl=b.index/2-1+b.t;
   const start=al<=bl?a:b,end=al<=bl?b:a;
   const coords=[...start.point];
   for(let i=start.index;i<end.index;i+=2)coords.push(xy[i],xy[i+1]);
   coords.push(...end.point);
   const path=al<=bl?shape(coords):shape(coords.reverse===undefined?coords:reverseCoords(coords));
   const km=length(path.xy);
   if(km<=maxKm){this.reasons.success++;return {parts:[path],km,crossRoute:actual===GLOBAL};}
   this.reasons.sameEdgeTooLong++;return null;
  }
  // Dijkstra from both endpoints of the snapped source section. Per-route
  // capped search and a small heap; all returned segments are official curves.
  const best=new Map(),prev=new Map(),heap=[];
  function push(v){heap.push(v);let k=heap.length-1;
   while(k){const j=(k-1)>>1;if(heap[j][0]<=v[0])break;heap[k]=heap[j];k=j;}heap[k]=v;}
  function pop(){const top=heap[0],v=heap.pop();if(heap.length){let i=0;
   while(i*2+1<heap.length){let j=i*2+1;if(j+1<heap.length&&heap[j+1][0]<heap[j][0])j++;
    if(heap[j][0]>=v[0])break;heap[i]=heap[j];i=j;}heap[i]=v;}return top;}
  for(let dir=0;dir<2;dir++){
   const part=partial(a,dir),n=a.edge.nodes[dir],cost=length(part.xy);
   if(cost>maxKm)continue;
   if(!best.has(n)||cost<best.get(n)){
    best.set(n,cost);prev.set(n,{start:part});push([cost,n]);
   }
  }
  const goals=new Map();
  for(let dir=0;dir<2;dir++){
   const part=reversed(partial(b,dir)),n=b.edge.nodes[dir],cost=length(part.xy);
   if(!goals.has(n)||cost<goals.get(n).cost)goals.set(n,{cost,part});
  }
  let goal=null,score=Infinity,steps=0;
  while(heap.length&&steps++<r.nodes.size+50){
   const [cost,n]=pop();if(cost!==best.get(n)||cost>=score||cost>maxKm)continue;
   const g=goals.get(n);
   if(g&&cost+g.cost<score){score=cost+g.cost;goal=n;}
   for(const [other,edge,dir] of n.adj){
    const next=cost+edge.length;
    if(next>=score||next>maxKm||next>=(best.get(other)??Infinity))continue;
    best.set(other,next);prev.set(other,{parent:n,edge,dir});push([next,other]);
   }
  }
  if(!goal||score>maxKm){this.reasons.noPath++;return null;}
  const straightKm=distance*kmPerPixel((from[1]+to[1])/2);
  // Cross-number routing gets an especially strict detour cap.
  if(score>straightKm*(actual===GLOBAL?1.42:2.2)+(actual===GLOBAL?1.5:3)){
   this.reasons.ratio++;return null;
  }
  const chain=[];let n=goal,start=null;
  while(n){
   const p=prev.get(n);if(!p)return null;
   if(p.start){start=p.start;break;}
   chain.push(p.dir===0?p.edge.part:reversed(p.edge.part));n=p.parent;
  }
  if(!start)return null;
  chain.reverse();
  this.reasons.success++;
  return {parts:[start,...chain,goals.get(goal).part],km:score,crossRoute:actual===GLOBAL};
 }
}
function reverseCoords(points){
 const out=[];for(let i=points.length-2;i>=0;i-=2)out.push(points[i],points[i+1]);
 return out;
}
function ends(group){
 const first=group.members[0],last=group.members[group.members.length-1];
 const out=[];
 for(const m of [first,last])for(const p of m.parts||[]){
  const a=p.xy;
  out.push([a[0],a[1]],[a[a.length-2],a[a.length-1]]);
 }
 return out;
}
function bestAnchors(a,b){
 const ax=ends(a),bx=ends(b);let best=null,dist=Infinity;
 for(const x of ax)for(const y of bx){
  const d=(x[0]-y[0])**2+(x[1]-y[1])**2;
  if(d<dist){dist=d;best=[x,y];}
 }
 return best;
}
function interval(group){
 const vals=group.members.flatMap(x=>x.leg.km_range||[]).map(Number);
 if(vals.length<2||vals.some(x=>!Number.isFinite(x)))return null;
 return [Math.min(...vals),Math.max(...vals)];
}
// A public map depicts a PHYSICAL railway corridor, not separately
// duplicated strokes for two directions. Collapse observations occupying
// the same route, risk tier and actual geographic section before searching
// for missing links. Raw directed stop counts are retained in members.
function collapseOverlaps(groups){
 const rows=groups.map(g=>({g,span:interval(g),route:String(g.members[0].leg.route)}))
  .filter(x=>x.span);
 const parent=rows.map((_,i)=>i);
 const root=i=>{while(parent[i]!==i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
 const join=(a,b)=>{a=root(a);b=root(b);if(a!==b)parent[b]=a;};
 const byRoute=new Map();
 rows.forEach((row,i)=>{
  const k=row.route+'|'+row.g.grade;
  if(!byRoute.has(k))byRoute.set(k,[]);
  byRoute.get(k).push(i);
 });
 for(const ids of byRoute.values()){
  ids.sort((a,b)=>rows[a].span[0]-rows[b].span[0]);
  for(let k=0;k<ids.length;k++){
   const a=rows[ids[k]];
   for(let l=k+1;l<ids.length;l++){
    const b=rows[ids[l]];
    if(b.span[0]>a.span[1]-.5)break;
    const overlap=Math.min(a.span[1],b.span[1])-Math.max(a.span[0],b.span[0]);
    if(overlap<.5)continue;
    const x=a.g.bounds,y=b.g.bounds,buffer=.45;
    if(x.maxX+buffer<y.minX||x.minX-buffer>y.maxX||
       x.maxY+buffer<y.minY||x.minY-buffer>y.maxY)continue;
    join(ids[k],ids[l]);
   }
  }
 }
 const clusters=new Map();
 rows.forEach(({g},i)=>{
  const id=root(i);
  if(!clusters.has(id))clusters.set(id,[]);
  clusters.get(id).push(g);
 });
 // Invalid km ranges remain separate and are never eligible for a bridge.
 const invalid=groups.filter(g=>!interval(g));
 const out=[...invalid];
 for(const gs of clusters.values()){
  if(gs.length===1){out.push(gs[0]);continue;}
  const members=gs.flatMap(g=>g.members);
  const parts=members.flatMap(m=>m.parts);
  const nArrival=members.reduce((n,m)=>n+m.m.nArrival,0);
  const nPlanned=members.reduce((n,m)=>n+m.m.nPlanned,0);
  const lateCount=members.reduce((n,m)=>n+Number(m.leg.v11?.late6||0),0);
  const cancelCount=members.reduce((n,m)=>n+Number(m.leg.v11?.boundary_cancel||0),0);
  const late=nArrival?100*lateCount/nArrival:null;
  const cancel=nPlanned?100*cancelCount/nPlanned:null;
  const g={members,parts,bounds:actualBounds(parts),grade:gs[0].grade,
   m:{late,onTime:late===null?null:100-late,cancel,nArrival,nPlanned}};
  for(const m of members)m.group=g;
  out.push(g);
 }
 return out;
}
function mergeGroups(groups,graph,allObservations,config={}){
 const originalGroups=groups.length;
 groups=collapseOverlaps(groups);
 const cap=config.maxGapKm??MAX_GAP,capItems=config.maxItems??1000;
 // Treat existing same-grade corridors as indivisible measured units.
 const ordered=groups.map(g=>({g,span:interval(g),route:String(g.members[0].leg.route)}))
  .filter(x=>x.span).sort((a,b)=>a.route.localeCompare(b.route)||a.span[0]-b.span[0]);
 const bucket=new Map();
 for(const x of ordered){
  const k=x.route+'|'+x.g.grade;
  if(!bucket.has(k))bucket.set(k,[]);bucket.get(k).push(x);
 }
 const next=new Map(),prev=new Map();let bridged=0,checks=0;
 const debug={originalGroups,groups:groups.length,routes:bucket.size,withinGap:0,unblocked:0,near:0,tries:0,paths:0,unique:0,ambiguous:0};
 for(const rows of bucket.values()){
  for(let i=0;i<rows.length-1;i++){
   const left=rows[i],candidates=[];
   for(let j=i+1;j<rows.length;j++){
    const right=rows[j],gap=right.span[0]-left.span[1];
    if(left.route==='5900')debug.bamberg={gap,left:left.span,right:right.span,stage:'consider'};
    if(gap>cap)break;
    if(gap<.12)continue; // overlapping opposite-direction observations
    debug.withinGap++;
    if(next.has(left.g)||prev.has(right.g))continue;
    // A known grade in the intervening km range is not an unknown gap.
    if(allObservations.some(o=>String(o.leg.route)===left.route&&o.grade!==left.g.grade&&
       o.leg.km_range?.[0]<right.span[0]-.05&&o.leg.km_range?.[1]>left.span[1]+.05)){
       if(left.route==='5900')debug.bamberg.stage='grade-conflict';
       continue;
    }
    debug.unblocked++;
    const anchors=bestAnchors(left.g,right.g);
    if(!anchors){if(left.route==='5900')debug.bamberg.stage='no-anchors';continue;}
    const straight=Math.hypot(anchors[0][0]-anchors[1][0],anchors[0][1]-anchors[1][1])*
      kmPerPixel((anchors[0][1]+anchors[1][1])/2);
    if(straight>cap*1.1+1||Math.abs(gap-straight)>Math.max(8,gap*.9)){
     if(left.route==='5900')Object.assign(debug.bamberg,{stage:'far-anchors',straight});continue;
    }
    debug.near++;
    if(checks++>=capItems)break;
    debug.tries++;
    const bridge=graph.find(left.route,...anchors,Math.min(cap,gap*2+3));
    if(bridge)debug.paths++;
    if(left.route==='5900')Object.assign(debug.bamberg,{stage:bridge?'path-found':'no-official-path',straight,actualRoute:graph.resolveRoute(left.route,...anchors),failure:{...graph.reasons},bridgeKm:bridge?.km});
    if(bridge&&bridge.km<=Math.max(3,gap*2.2+2))
      candidates.push({right,bridge});
   }
   // Ambiguous continuation at a junction: do not choose a branch by chance.
   if(candidates.length>1){
    // Multiple branches are acceptable only when the official path to the
    // closest continuation is distinctly shorter than all alternatives.
    // Near-ties, parallel tracks and junction forks remain separate.
    candidates.sort((a,b)=>a.bridge.km-b.bridge.km);
    if(candidates[0].bridge.km>=candidates[1].bridge.km*.68){
     debug.ambiguous++;continue;
    }
   }
   if(!candidates.length)continue;
   debug.unique++;
   const {right,bridge}=candidates[0];
   if(prev.has(right.g))continue;
   next.set(left.g,{other:right.g,bridge});
   prev.set(right.g,left.g);bridged++;
  }
 }
 const seen=new Set(),result=[];
 for(const start of groups){
  if(seen.has(start))continue;
  let head=start,scan=new Set();
  while(prev.has(head)&&!scan.has(head)){scan.add(head);head=prev.get(head);}
  const chain=[],bridges=[];
  while(head&&!seen.has(head)){
   seen.add(head);chain.push(head);
   const n=next.get(head);
   if(n){bridges.push(n.bridge);head=n.other;}else head=null;
  }
  const members=chain.flatMap(g=>g.members);
  const parts=members.flatMap(m=>m.parts);
  const bridgeParts=bridges.flatMap(g=>g.parts);
  const nArrival=chain.reduce((n,g)=>n+g.m.nArrival,0);
  const nPlanned=chain.reduce((n,g)=>n+g.m.nPlanned,0);
  const lateCount=members.reduce((n,m)=>n+Number(m.leg.v11?.late6||0),0);
  const canceled=members.reduce((n,m)=>n+Number(m.leg.v11?.boundary_cancel||0),0);
  const late=nArrival?100*lateCount/nArrival:null;
  const cancel=nPlanned?100*canceled/nPlanned:null;
  const output={members,parts:[...parts,...bridgeParts],bridgeParts,bridges:bridges.length,
   bridgeKm:bridges.reduce((s,g)=>s+g.km,0),
   bounds:actualBounds([...parts,...bridgeParts]),grade:chain[0].grade,
   m:{late,onTime:late===null?null:100-late,cancel,nArrival,nPlanned}};
  for(const m of members)m.group=output;
  result.push(output);
 }
 return {groups:result,bridged,checks,debug};
}
window.Railway07Bridge=Object.freeze({RouteGraph,mergeGroups,closest,length});
})();
