/* Railway 07: nationwide official track backbone beneath measured risk strokes.
   Missing DB observations are always a visible GREEN railway, never a gap.
   Only official DB InfraGO source curves may be drawn: no straight invented track.
   Selecting a city pair may use its official route geometry, including
   unsampled sections, while rates use observed counts exclusively. */
(()=>{
'use strict';
const {actualBounds,segmentDist}=window.Railway07Geometry;
const kmPerPx=y=>(40075/131072)/Math.cosh(Math.PI-2*Math.PI*y/131072);
class Backbone{
 constructor(){
  this.graph=new window.Railway07Bridge.RouteGraph();
  this.all=[];this.active=[];this.perRoute=new Map();
  this.selectedRoutes=new Set();this.official=0;this.verified=0;
 }
 add(route,part){
  if(!part?.xy||part.xy.length<4)return;
  const id=String(route);
  this.all.push(part);
  if(!this.perRoute.has(id))this.perRoute.set(id,[]);
  this.perRoute.get(id).push(part);
  this.graph.add(id,part);
  this.official++;
 }
 setActive(groups,picker){
  const ids=new Set(),matched=new Map();
  for(const g of groups)for(const member of g.members||[]){
   const own=String(member.leg.route);
   if(this.perRoute.has(own))ids.add(own);
   // Observation route numbering often differs from the official
   // infrastructure extraction; use REAL geographic coincidence instead.
   for(const part of (member.parts||[]).slice(0,3)){
    const xy=part.xy;
    const points=[[xy[0],xy[1]],
      [xy[Math.floor((xy.length/2-1)/2)*2],xy[Math.floor((xy.length/2-1)/2)*2+1]],
      [xy[xy.length-2],xy[xy.length-1]]];
    const routes=new Map();
    for(const point of points){
     const found=picker?.network.nearest(point,.75);
     if(!found||found.d>.6*.6)continue;
     const key=String(found.entry.route);
     routes.set(key,(routes.get(key)||0)+1);
    }
    for(const [key,hits] of routes)
     if(hits>=2)matched.set(key,(matched.get(key)||0)+1);
   }
  }
  for(const [key,score] of matched)if(score>=1)ids.add(key);
  this.selectedRoutes=ids;
  this.active=[...ids].flatMap(id=>this.perRoute.get(id)||[]);
  return {routes:ids.size,sections:this.active.length,all:this.all.length,
    geographicMatches:matched.size};
 }
 // The stations at both ends of a city-pair corridor can be identified from
 // original stop records; they do not need to be guessed from route geometry.
 stations(group,city){
  const cityKey=String(city||'').toLowerCase();
  const cityLabel=window.Railway07Cities.cityName(city).toLowerCase();
  const alternatives=group.members.filter(m=>{
   const from=m.leg.from_station,to=m.leg.to_station;
   return [from,to].some(n=>n===city||
      window.Railway07Cities.cityName(n).toLowerCase()===cityLabel||
      String(n||'').toLowerCase().startsWith(cityKey+' '));
  });
  const points=[];
  for(const member of alternatives.slice(0,20))for(const part of member.parts){
   const a=part.xy;
   points.push([a[0],a[1]],[a[a.length-2],a[a.length-1]]);
  }
  // Reject station-less groups; never infer imaginary routes.
  return points;
 }
 // Lazily seek the authentic DB track curve between two city end stations.
 // This is a selection overlay, not an instruction to recolour a missing gap.
 full(group){
  if(group._backboneChecked)return group._officialPath;
  group._backboneChecked=true;
  if(!group.members?.length)return null;
  const route=String(group.members[0].leg.route);
  const source=this.stations(group,group.startStation);
  const dest=this.stations(group,group.endStation);
  let best=null;
  // Take geographically separated endpoint samples to avoid trivially
  // matching a short shared leg or an adjacent parallel platform track.
  for(const a of source.slice(0,5))for(const b of dest.slice(0,5)){
   const direct=Math.hypot(a[0]-b[0],a[1]-b[1])*kmPerPx((a[1]+b[1])/2);
   if(direct<2||direct>140)continue;
   const routePath=this.graph.find(route,a,b,Math.min(170,Math.max(10,direct*1.75+8)));
   if(!routePath?.parts?.length||routePath.km<direct*.85)continue;
   const penalty=routePath.km/direct;
   // A city-end station segment contributes *two* geometry endpoints. A
   // shortest-only ranking often chose the inner endpoints on either side
   // of a data gap, illuminating just the missing 2-km fragment instead of
   // the whole A--B corridor. Prefer the longest physically plausible path
   // whenever competing paths have comparable detour ratios.
   if(!best||
     (routePath.km>best.path.km*1.01 &&
       penalty<=best.penalty*1.12+.04)||
     (penalty<best.penalty*.83))
    best={path:routePath,penalty};
  }
  if(best){
   group._officialPath=best.path.parts;
   group._fullBounds=actualBounds(best.path.parts);
   this.verified++;
  }
  return group._officialPath||null;
 }
 // At a switch/junction, continue along the straightest VERIFIED official
 // track within the same DB line number. The original degree=2-only walk
 // stopped prematurely at every siding, creating tiny clickable pieces.
 walkPhysical(route,point,maxKm=135){
  const hit=this.graph.nearest(route,point);
  if(!hit)return null;
  const initial=hit.edge,seen=new Set([initial]),parts=[initial.part];
  let km=initial.length;
  const tangent=(edge,node)=>{
   const xy=edge.part.xy,a=xy.length-2;
   const start=edge.nodes[0]===node;
   const dx=start?xy[2]-xy[0]:xy[a-2]-xy[a];
   const dy=start?xy[3]-xy[1]:xy[a-1]-xy[a+1];
   const mag=Math.hypot(dx,dy)||1;return [dx/mag,dy/mag];
  };
  function extend(node,inbound){
   for(let hops=0;hops<900&&km<maxKm;hops++){
    const back=tangent(inbound,node);
    const choices=node.adj
     .filter(([,edge])=>!seen.has(edge)&&edge.length>0)
     .map(([other,edge])=>{
       const forward=tangent(edge,node);
       const alignment=-(back[0]*forward[0]+back[1]*forward[1]);
       return {other,edge,alignment};
     }).filter(c=>c.alignment>.32&&km+c.edge.length<=maxKm)
     .sort((a,b)=>b.alignment-a.alignment);
    if(!choices.length)break;
    // Two equally plausible diverging official tracks are not the same
    // corridor. Never guess an entirely different branch at a major fork.
    if(choices.length>1&&
       choices[0].alignment-choices[1].alignment<.075)break;
    const chosen=choices[0];
    seen.add(chosen.edge);parts.push(chosen.edge.part);
    km+=chosen.edge.length;inbound=chosen.edge;node=chosen.other;
   }
  }
  extend(initial.nodes[0],initial);
  extend(initial.nodes[1],initial);
  return {parts,km};
 }
 // Green click with no match follows a longer continuous official railway
 // through unambiguous switches, then stops at measured colour transitions.
 unobserved(route,point){
  const walked=this.walkPhysical(route,point,135);
  return {unobserved:true,route:String(route),
    parts:walked?.parts?.length?walked.parts:this.perRoute.get(String(route))?.slice(0,1)||[]};
 }
}
window.Railway07Continuity=Object.freeze({Backbone});
})();