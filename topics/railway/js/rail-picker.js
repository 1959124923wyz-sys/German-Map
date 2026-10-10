/* Spatial picker shared by observed service segments and complete DB InfraGO
   infrastructure.  All distances use the same REF_ZOOM Mercator projection.
   The network index remains loaded when filters change; measured picks win. */
(()=>{
'use strict';
const {segmentDist}=window.Railway07Geometry;
const CELL=64;
class SpatialIndex{
 constructor(){this.cells=new Map();this.items=0;}
 clear(){this.cells.clear();this.items=0;}
 add(entry){
  if(!entry.parts?.length)return;
  this.items++;
  for(const p of entry.parts){
   if(!p.xy||p.xy.length<4)continue;
   const x0=Math.floor(p.minX/CELL),x1=Math.floor(p.maxX/CELL);
   const y0=Math.floor(p.minY/CELL),y1=Math.floor(p.maxY/CELL);
   for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++){
    const k=x+','+y;
    if(!this.cells.has(k))this.cells.set(k,[]);
    this.cells.get(k).push(entry);
   }
  }
 }
 nearest(point,tolerance){
  if(!this.items)return null;
  const [px,py]=point,r=tolerance,seen=new Set();
  let winner=null,best=r*r;
  for(let x=Math.floor((px-r)/CELL);x<=Math.floor((px+r)/CELL);x++){
   for(let y=Math.floor((py-r)/CELL);y<=Math.floor((py+r)/CELL);y++){
    const entries=this.cells.get(x+','+y)||[];
    for(const entry of entries){
     if(seen.has(entry))continue;seen.add(entry);
     for(const p of entry.parts){
      if(px<p.minX-r||px>p.maxX+r||py<p.minY-r||py>p.maxY+r)continue;
      const xy=p.xy;
      for(let j=2;j<xy.length;j+=2){
       const d=segmentDist(px,py,xy[j-2],xy[j-1],xy[j],xy[j+1]);
       if(d<best){best=d;winner={entry,part:p,d};}
      }
     }
    }
   }
  }
  return winner;
 }
}
class RailwayPicker{
 constructor(){this.observed=new SpatialIndex();this.network=new SpatialIndex();}
 addNetwork(route,part){this.network.add({route:String(route),parts:[part],part});}
 replaceObserved(items,groups){
  this.observed.clear();
  for(const item of items)this.observed.add({...item,group:item.group});
  for(const group of groups){
   for(const part of group.bridgeParts||[])
    this.observed.add({parts:[part],group,bridge:true});
  }
 }
 hit(point,zoom){
  const tol=Math.min(30,9/2**(zoom-9));
  // Do not allow a thick observed highlight to steal a click on an adjacent
  // unrelated physical line at close zoom levels.
  const sample=this.observed.nearest(point,tol);
  const base=this.network.nearest(point,tol);
  if(sample&&(!base||sample.d<=base.d+Math.max(.1,tol*.18)**2))
   return {kind:'observed',group:sample.entry.group,part:sample.part};
  if(base)return {kind:'network',route:base.entry.route,part:base.part};
  if(sample)return {kind:'observed',group:sample.entry.group,part:sample.part};
  return null;
 }
}
window.Railway07Picker=Object.freeze({SpatialIndex,RailwayPicker});
})();