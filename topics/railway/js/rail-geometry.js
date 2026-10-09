/* Geometry operations for Railway 07. No DOM mutations or data downloads.
   DB InfraGO WGS84 curves remain authoritative. Keep in sync with Node tests. */
(()=>{
'use strict';
const REF_ZOOM=9,WORLD=256*2**REF_ZOOM;
const geomCache=new WeakMap();

function proj(lon,lat){
 const sine=Math.sin(Math.max(-85,Math.min(85,lat))*Math.PI/180);
 return [(lon+180)/360*WORLD,(.5-Math.log((1+sine)/(1-sine))/(4*Math.PI))*WORLD];
}
function decodePolyline(str,mult=10){
 const a=[];let x=0,y=0,i=0;
 while(i<str.length){
  for(let axis=0;axis<2;axis++){
   let value=0,shift=0,b;
   do{
    if(i>=str.length)throw Error('官方铁路几何编码截断');
    b=str.charCodeAt(i++)-63;
    if(b<0||b>63)throw Error('铁路几何编码无效');
    value|=(b&31)<<shift;shift+=5;
   }while(b>=32);
   const delta=value&1?~(value>>1):value>>1;
   if(axis===0)x+=delta;else y+=delta;
  }
  a.push(x/mult,y/mult);
 }
 return a;
}
function shape(points){
 let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
 for(let i=0;i<points.length;i+=2){
  const x=points[i],y=points[i+1];
  if(x<minX)minX=x;if(x>maxX)maxX=x;
  if(y<minY)minY=y;if(y>maxY)maxY=y;
 }
 return {xy:new Float32Array(points),minX,minY,maxX,maxY};
}
function officialPart(sec){
 // Original DB InfraGO WGS84 source has already been packed into x/y,
 // not invented by interpolating between stations.
 const xy=decodePolyline(sec[5]);
 const points=[];
 for(let i=0;i<xy.length;i+=2){
  const lon=5.34+(xy[i]-15)/76.5,lat=55.4-(xy[i+1]-6)/114.2;
  points.push(...proj(lon,lat));
 }
 return points.length>=4?shape(points):null;
}
function observedParts(leg){
 if(geomCache.has(leg))return geomCache.get(leg);
 const parts=[];
 for(const segment of leg.geometry||[]){
  if(!Array.isArray(segment)||segment.length<2)continue;
  const points=[];
  for(const p of segment){
   if(!Array.isArray(p)||p.length<2)continue;
   const [lon,lat]=p;
   if(!Number.isFinite(lon)||!Number.isFinite(lat))continue;
   points.push(...proj(lon,lat));
  }
  if(points.length>=4)parts.push(shape(points));
 }
 geomCache.set(leg,parts);return parts;
}
function actualBounds(parts){
 let x0=Infinity,y0=Infinity,x1=-Infinity,y1=-Infinity;
 for(const p of parts){
  x0=Math.min(x0,p.minX);y0=Math.min(y0,p.minY);
  x1=Math.max(x1,p.maxX);y1=Math.max(y1,p.maxY);
 }
 return {minX:x0,minY:y0,maxX:x1,maxY:y1};
}
function currentViewport(m,size){
 const factor=2**(m.getZoom()-REF_ZOOM),origin=m.getPixelOrigin();
 // Leaflet pixel-origin is in layer coordinates, not container coordinates.
 // Include the pan-pane translation so overlaid Canvas pixels line up with
 // real OSM tiles even after repeated pan operations.
 const pane=L.DomUtil.getPosition(m.getPanes().mapPane)||L.point(0,0);
 const ox=origin.x-pane.x,oy=origin.y-pane.y;
 return {factor,ox,oy,
   minX:(ox-15)/factor,maxX:(ox+size.x+15)/factor,
   minY:(oy-15)/factor,maxY:(oy+size.y+15)/factor};
}
function visible(p,v){
 return !(p.maxX<v.minX||p.minX>v.maxX||p.maxY<v.minY||p.minY>v.maxY);
}
function drawPath(ctx,p,v){
 const a=p.xy,f=v.factor,ox=v.ox,oy=v.oy;
 ctx.moveTo(a[0]*f-ox,a[1]*f-oy);
 // At national zoom, skip subpixel intermediate vertices without altering
 // either the source geometry or the detailed zoom view.
 let lx=a[0]*f-ox,ly=a[1]*f-oy;
 const skip=v.factor<1?.45:0;
 for(let i=2;i<a.length;i+=2){
  const x=a[i]*f-ox,y=a[i+1]*f-oy;
  if(skip&&i<a.length-2&&(x-lx)**2+(y-ly)**2<skip*skip)continue;
  ctx.lineTo(x,y);lx=x;ly=y;
 }
}

function unproject(x,y){
 const lng=x/WORLD*360-180;
 const n=Math.PI-2*Math.PI*y/WORLD;
 return [180/Math.PI*Math.atan(Math.sinh(n)),lng];
}

function segmentDist(px,py,ax,ay,bx,by){
 const dx=bx-ax,dy=by-ay;
 const t=(dx*dx+dy*dy)?Math.max(0,Math.min(1,((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy))):0;
 const x=px-ax-t*dx,y=py-ay-t*dy;return x*x+y*y;
}

window.Railway07Geometry=Object.freeze({
 REF_ZOOM,WORLD,proj,decodePolyline,shape,officialPart,observedParts,
 actualBounds,currentViewport,visible,drawPath,unproject,segmentDist
});
})();
