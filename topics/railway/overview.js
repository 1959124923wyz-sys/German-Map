/* Railway 07 — same Leaflet / OSM base as 01–06.
   Official DB InfraGO tracks and matched service observations use two Canvas
   layers, not thousands of SVG nodes or invented straight-line joins. */
(()=>{
'use strict';
const $=s=>document.querySelector(s);
const COLORS={red:'#c74753',orange:'#cf7f27',green:'#167f63',missing:'#5c7380'};
const sources={REGIONAL:['RE','RB'],LONG:['LONG'],OTHER:['HLB','BRB','ERB','NWB','OE']};
const labels={REGIONAL:'区域列车（RE / RB）',LONG:'长途列车（ICE / IC / EC / FLX）',OTHER:'其他运营商'};
const specs={
 RE:['v12_re_evidence',8],RB:['v13_rb_evidence',6],
 LONG:['v10_september_evidence',4],HLB:['v14_hlb_evidence',2],
 BRB:['v14_brb_evidence',1],ERB:['v14_erb_evidence',1],
 NWB:['v14_nwb_evidence',1],OE:['v14_oe_evidence',1]
};
const stationZh=name=>window.GermanRailStations?.localize(name)||name;
const REF_ZOOM=9, WORLD=256*2**REF_ZOOM, CELL=64, NATION=[[47.05,5.45],[55.15,15.65]];
const view={service:'REGIONAL',metric:'both',minimum:100,selected:null,links:[],
  rendered:[],ticket:0,networkReady:false,tiles:false,networkParts:[],grid:new Map(),map:null,
  baseLayer:null,observedLayer:null,repaints:0};
const cache=new Map(),geomCache=new WeakMap();
const fmt=n=>Number(n).toLocaleString('zh-CN');
const pct=n=>n===null||!Number.isFinite(n)?'—':n.toFixed(1)+'%';
function status(s){$('#status').textContent=s;}
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
const CanvasLayer=L.Layer.extend({
 initialize(kind){this.kind=kind;this._frame=null;},
 onAdd(m){
  this.map=m;
  this.canvas=L.DomUtil.create('canvas','railway-canvas railway-'+this.kind,m.getPane(this.kind==='network'?'rail-network-pane':'rail-observed-pane'));
  this.canvas.style.cssText='position:absolute;pointer-events:none';
  m.on('moveend zoomend resize',this.schedule,this);
  this.schedule();
 },
 onRemove(m){
  m.off('moveend zoomend resize',this.schedule,this);
  if(this._frame)cancelAnimationFrame(this._frame);
  this.canvas.remove();
 },
 schedule(){
  if(this._frame)return;
  this._frame=requestAnimationFrame(()=>{this._frame=null;this.paint();});
 },
 paint(){
  const m=this.map,size=m.getSize(),cv=this.canvas;
  if(!size.x||!size.y)return;
  const dpr=Math.min(window.devicePixelRatio||1,2);
  L.DomUtil.setPosition(cv,m.containerPointToLayerPoint([0,0]));
  cv.width=Math.round(size.x*dpr);cv.height=Math.round(size.y*dpr);
  cv.style.width=size.x+'px';cv.style.height=size.y+'px';
  const ctx=cv.getContext('2d',{alpha:true,desynchronized:true});
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,size.x,size.y);
  ctx.lineCap='butt';ctx.lineJoin='bevel';
  const v=currentViewport(m,size);
  if(this.kind==='network'){
   if(!view.networkReady)return;
   ctx.beginPath();
   for(const p of view.networkParts)if(visible(p,v))drawPath(ctx,p,v);
   ctx.strokeStyle=COLORS.missing;ctx.globalAlpha=.66;
   ctx.lineWidth=m.getZoom()<7?.75:.95;ctx.stroke();
  }else{
   const widths=[1.65,2.25,2.65];
   const colors=[COLORS.green,COLORS.orange,COLORS.red];
   for(let grade=0;grade<3;grade++){
    ctx.beginPath();
    for(const o of view.rendered){
     if(o.grade!==grade||!visible(o.bounds,v))continue;
     for(const p of o.parts)if(visible(p,v))drawPath(ctx,p,v);
    }
    ctx.strokeStyle=colors[grade];ctx.globalAlpha=grade===0?.92:1;
    ctx.lineWidth=widths[grade];ctx.stroke();
   }
   if(view.selected?.parts){
    ctx.beginPath();
    for(const p of view.selected.parts)if(visible(p,v))drawPath(ctx,p,v);
    ctx.strokeStyle='#273b4b';ctx.globalAlpha=1;ctx.lineWidth=6;ctx.stroke();
    ctx.beginPath();
    for(const p of view.selected.parts)if(visible(p,v))drawPath(ctx,p,v);
    ctx.strokeStyle='#fee2a9';ctx.lineWidth=3.2;ctx.stroke();
   }
  }
  ctx.globalAlpha=1;view.repaints++;
 }
});
function makeMap(){
 if(!window.L)throw Error('Leaflet 无法加载');
 const m=L.map('railway-map',{zoomControl:true,minZoom:4,maxZoom:16,
  preferCanvas:false,zoomSnap:.5,zoomAnimation:false,worldCopyJump:false});
 view.map=m;
 m.fitBounds(NATION,{padding:[12,12],animate:false});
 m.setMaxBounds([[45.3,3.2],[57.1,18]]);
 m.getPane('tilePane').style.filter='saturate(.45) contrast(.86) brightness(1.06)';
 for(const [name,z] of [['rail-network-pane',355],['rail-observed-pane',430],['rail-state-pane',390]]){
  m.createPane(name).style.zIndex=String(z);
 }
 const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
  maxZoom:19,opacity:.9,attribution:'© OpenStreetMap contributors',
  crossOrigin:true,updateWhenIdle:true,keepBuffer:2});
 tiles.on('tileload',()=>{
  if(!view.tiles){view.tiles=true;$('#mapStatus').textContent='OSM街道底图 · DB InfraGO 官方铁路网';$('#mapStatus').classList.add('ok');}
 });
 let errors=0;
 tiles.on('tileerror',()=>{
  if(++errors>5&&!view.tiles){$('#mapStatus').textContent='底图暂不可用 · 官方轨道及运行区间仍可查看';}
 });
 tiles.addTo(m);
 fetch('../../data/germany-states.geojson',{cache:'force-cache'}).then(r=>{
  if(!r.ok)throw Error('州界 HTTP '+r.status);return r.json();
 }).then(data=>{
  if(data.features?.length!==16)throw Error('州界不完整');
  L.geoJSON(data,{pane:'rail-state-pane',interactive:false,
   style:()=>({color:'#315065',weight:1.2,opacity:.7,fill:false})}).addTo(m);
 }).catch(e=>console.warn('State boundaries unavailable',e));
 fetch('../../data/germany-counties.geojson',{cache:'force-cache'}).then(r=>{
  if(!r.ok)throw Error('县界 HTTP '+r.status);return r.json();
 }).then(data=>{
  m.createPane('rail-counties-pane').style.zIndex='315';
  L.geoJSON(data,{pane:'rail-counties-pane',interactive:false,
   style:()=>({color:'#607c8f',weight:.32,opacity:.24,fill:false})}).addTo(m);
 }).catch(e=>console.warn('County boundaries unavailable',e));
 window.CrimeCityLabels?.create(m,{paneName:'rail-major-cities',zIndex:470});
 view.baseLayer=new CanvasLayer('network').addTo(m);
 view.observedLayer=new CanvasLayer('observed').addTo(m);
 m.on('click',e=>pickAt(e.latlng));
 $('#home').onclick=()=>m.fitBounds(NATION,{padding:[12,12],animate:false});
 return m;
}
function buildNetwork(){
 if(!DATA||DATA.sections.length!==33547||DATA.qa?.source_line_geometries!==33547)
  throw Error('官方轨道数据数量未通过校验');
 const sections=DATA.sections;
 let cursor=0;
 const batch=()=>{
  const until=Math.min(cursor+950,sections.length);
  for(;cursor<until;cursor++){
   const p=officialPart(sections[cursor]);if(p)view.networkParts.push(p);
  }
  if(cursor<sections.length){
   if(cursor===950)$('#mapStatus').textContent='正在读取 DB InfraGO 真实轨道…';
   requestAnimationFrame(batch);
  }else{
   view.networkReady=true;view.baseLayer.schedule();
   $('#mapStatus').textContent=view.tiles?'OSM街道底图 · 官方完整铁路网':'官方完整铁路网 · 街道底图加载中';
  }
 };
 requestAnimationFrame(batch);
}
const pad=n=>String(n).padStart(2,'0');
function script(src){
 return new Promise((resolve,reject)=>{
  const tag=document.createElement('script');
  tag.src=src;tag.onload=resolve;tag.onerror=()=>reject(Error('无法加载 '+src));
  document.body.append(tag);
 });
}
function dataFor(key){
 switch(key){
  case 'RE':return V12_RE_EVIDENCE;
  case 'RB':return V13_RB_EVIDENCE;
  case 'HLB':return V14_HLB_EVIDENCE;
  case 'BRB':return V14_BRB_EVIDENCE;
  case 'ERB':return V14_ERB_EVIDENCE;
  case 'NWB':return V14_NWB_EVIDENCE;
  case 'OE':return V14_OE_EVIDENCE;
  default:return V10_SEPTEMBER_EVIDENCE;
 }
}
async function loadData(key){
 if(cache.has(key))return cache.get(key);
 const [name,n]=specs[key];
 const promise=(async()=>{
  await script('data/'+name+'-core.js');
  for(let i=0;i<n;i++)await script('data/'+name+'-links-'+pad(i)+'.js');
  return dataFor(key);
 })();
 cache.set(key,promise);
 try{return await promise}catch(e){cache.delete(key);throw e;}
}
function mergeObserved(groupData){
 const byKey=new Map();
 for(const [kind,data] of groupData){
  for(const leg of data.links||[]){
   const range=leg.km_range||[];
   const key=[leg.route,leg.from_station,leg.to_station,
    range.map(x=>Number(x).toFixed(2)).join(':')].join('|');
   let dest=byKey.get(key);
   if(!dest){
    dest={...leg,v11:{pairs:0,arrival_valid:0,late6:0,late15:0,boundary_cancel:0},
      brands:[],label_hints:leg.label_hints||[]};
    byKey.set(key,dest);
   }
   const a=leg.v11||{};
   for(const field of ['pairs','arrival_valid','late6','late15','boundary_cancel'])
    dest.v11[field]+=Number(a[field]||0);
   if(!dest.brands.includes(kind))dest.brands.push(kind);
  }
 }
 return [...byKey.values()];
}
function metrics(leg){
 const a=leg.v11||{},nArrival=Number(a.arrival_valid||0),nPlanned=Number(a.pairs||0);
 const late=nArrival?100*Number(a.late6||0)/nArrival:null;
 const cancel=nPlanned?100*Number(a.boundary_cancel||0)/nPlanned:null;
 const enough=view.metric==='both'?nArrival>=view.minimum&&nPlanned>=view.minimum:
  view.metric==='late'?nArrival>=view.minimum:nPlanned>=view.minimum;
 return {late,cancel,nArrival,nPlanned,sufficient:enough};
}
function grade(m){
 if(view.metric==='late')return m.late>=40?2:m.late>=25?1:0;
 if(view.metric==='cancel')return m.cancel>=8?2:m.cancel>=4?1:0;
 return m.late>=40||m.cancel>=8?2:m.late>=25||m.cancel>=4?1:0;
}
function attention(m){
 const a=(m.late??0)/40,b=(m.cancel??0)/8;
 return view.metric==='late'?a:view.metric==='cancel'?b:Math.max(a,b);
}
function fillLegend(){
 const mode=view.metric;
 const thresholds=mode==='late'?['到站晚点 ≥6分钟 · 观测比例','<25%','25%–<40%','≥40%']
 :mode==='cancel'?['停靠取消标记 · 观测比例','<4%','4%–<8%','≥8%']
 :['综合关注 · 晚点≥6分钟 / 停靠取消比例','晚点 <25% 且取消 <4%',
   '晚点 ≥25% 或取消 ≥4%（未达红线）','晚点 ≥40% 或取消 ≥8%'];
 const box=$('#railLegend');
 box.replaceChildren();
 const title=document.createElement('b');title.textContent=thresholds[0];box.appendChild(title);
 for(const [col,s] of [[COLORS.missing,'无匹配或样本不足'],
   [COLORS.green,thresholds[1]],[COLORS.orange,thresholds[2]],[COLORS.red,thresholds[3]]]){
  const row=document.createElement('span'),dot=document.createElement('i');
  dot.style.background=col;row.append(dot,document.createTextNode(s));box.append(row);
 }
 const note=document.createElement('small');note.className='rail-legend-note';
 note.textContent=mode==='both'?'红橙依两项独立指标判定；灰色不代表正常。':'按当前样本门槛分色；灰色不代表正常。';
 box.appendChild(note);
}
function placeLegend(){
 const box=$('#railLegend');
 if(window.innerWidth<=760){
  const field=$('#metric')?.closest('.field');
  if(field&&box.previousElementSibling!==field)field.insertAdjacentElement('afterend',box);
 }else{
  const target=$('.map-panel');if(target&&box.parentElement!==target)target.appendChild(box);
 }
}
function element(parent,tag,value,className){
 const item=document.createElement(tag);item.textContent=value;
 if(className)item.className=className;
 parent.appendChild(item);return item;
}
function showDetail(){
 const box=$('#detail');box.replaceChildren();
 const o=view.selected;
 if(!o){
  box.classList.add('empty');
  element(box,'h3','选择一段彩色铁路');
  element(box,'p','绿色为有观测且低于警示门槛，点击地图或下方区间榜单查看详情。');
  return;
 }
 box.classList.remove('empty');
 const {leg,m,grade:g}=o;
 element(box,'span',g===2?'● 高关注':g===1?'● 偏高':'● 低于关注门槛','grade');
 element(box,'h3',stationZh(leg.from_station)+' → '+stationZh(leg.to_station));
 element(box,'p',leg.from_station+' → '+leg.to_station,'original-stations');
 const hint=leg.label_hints?.[0]?.[0];
 element(box,'p','官方线路 '+leg.route+(hint?' · '+hint:'')+
  (leg.brands?.length?' · '+leg.brands.join(' / '):''));
 const grid=element(box,'div','','detail-grid');
 for(const [v,label] of [[pct(m.late),'到站晚点≥6分钟'],
   [pct(m.cancel),'停靠取消标记'],[fmt(m.nArrival),'有效到站观测'],[fmt(m.nPlanned),'计划站间配对']]){
  const cell=document.createElement('div');
  element(cell,'b',v);element(cell,'span',label);grid.append(cell);
 }
 element(box,'p','2026年9月 · 区间观测不代表轨道故障归因或整趟车取消概率。');
}
function updateHotspots(){
 const list=$('#hotList');list.replaceChildren();
 const items=view.rendered.filter(o=>o.grade>0)
  .sort((a,b)=>b.grade-a.grade||attention(b.m)-attention(a.m)).slice(0,10);
 if(!items.length){element(list,'p','当前条件下没有达到关注门槛的区间。','hot-empty');return;}
 items.forEach((o,i)=>{
  const row=document.createElement('button');row.type='button';row.className='hot-row';
  const rank=element(row,'span',String(i+1),'hot-rank');
  const main=element(row,'span','','hot-main');
  element(main,'strong',stationZh(o.leg.from_station)+' → '+stationZh(o.leg.to_station));
  element(main,'small','晚点 '+pct(o.m.late)+' · 取消标记 '+pct(o.m.cancel));
  element(row,'span',o.grade===2?'高':'中','hot-grade '+(o.grade===2?'high':'medium'));
  row.onclick=()=>{
   view.selected=o;showDetail();view.observedLayer.schedule();
   const b=o.bounds;
   const ll1=unproject(b.minX,b.minY),ll2=unproject(b.maxX,b.maxY);
   const bounds=L.latLngBounds(ll1,ll2);
   if(bounds.isValid())view.map.fitBounds(bounds.pad(.38),{maxZoom:11,animate:false});
   $('#detail').scrollIntoView({block:'nearest',behavior:'smooth'});
  };
  list.append(row);
 });
}
function unproject(x,y){
 const lng=x/WORLD*360-180;
 const n=Math.PI-2*Math.PI*y/WORLD;
 return [180/Math.PI*Math.atan(Math.sinh(n)),lng];
}
function addToGrid(o){
 for(const p of o.parts){
  const x0=Math.floor(p.minX/CELL),x1=Math.floor(p.maxX/CELL);
  const y0=Math.floor(p.minY/CELL),y1=Math.floor(p.maxY/CELL);
  for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++){
   const id=x+','+y;
   if(!view.grid.has(id))view.grid.set(id,new Set());
   view.grid.get(id).add(o);
  }
 }
}
function rebuildIndex(){
 view.grid.clear();
 for(const o of view.rendered)addToGrid(o);
}
function segmentDist(px,py,ax,ay,bx,by){
 const dx=bx-ax,dy=by-ay;
 const t=(dx*dx+dy*dy)?Math.max(0,Math.min(1,((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy))):0;
 const x=px-ax-t*dx,y=py-ay-t*dy;return x*x+y*y;
}
function pickAt(latlng){
 if(!view.rendered.length)return;
 const pt=view.map.project(latlng,REF_ZOOM);
 const tolerance=Math.min(30,12/2**(view.map.getZoom()-REF_ZOOM));
 const candidates=new Set();
 for(let x=Math.floor((pt.x-tolerance)/CELL);x<=Math.floor((pt.x+tolerance)/CELL);x++)
  for(let y=Math.floor((pt.y-tolerance)/CELL);y<=Math.floor((pt.y+tolerance)/CELL);y++)
   for(const o of view.grid.get(x+','+y)||[])candidates.add(o);
 let best=null,bestDist=tolerance*tolerance;
 for(const o of candidates){
  for(const p of o.parts){
   if(pt.x<p.minX-tolerance||pt.x>p.maxX+tolerance||pt.y<p.minY-tolerance||pt.y>p.maxY+tolerance)continue;
   const a=p.xy;
   for(let i=2;i<a.length;i+=2){
    const d=segmentDist(pt.x,pt.y,a[i-2],a[i-1],a[i],a[i+1]);
    if(d<bestDist){bestDist=d;best=o;}
   }
  }
 }
 if(best){
  view.selected=best;showDetail();view.observedLayer.schedule();
 }
}
function recalc(){
 const previous=view.selected?.leg||null;
 const items=[];
 for(const leg of view.links){
  const m=metrics(leg);
  if(!m.sufficient)continue;
  const parts=observedParts(leg);
  if(!parts.length)continue;
  items.push({leg,m,parts,bounds:actualBounds(parts),grade:grade(m)});
 }
 view.rendered=items;
 view.selected=items.find(x=>x.leg===previous)||null;
 rebuildIndex();
 $('#visibleCount').textContent=fmt(items.length);
 const count=items.filter(o=>o.grade===2).length;
 $('#redCount').textContent=fmt(count);
 $('#redShare').textContent=items.length?(100*count/items.length).toFixed(1)+'%':'—';
 status(labels[view.service]+' · '+fmt(items.length)+' 个达标方向性区间');
 fillLegend();placeLegend();updateHotspots();showDetail();
 view.observedLayer.schedule();
}
async function chooseService(){
 const id=++view.ticket,service=view.service;
 view.selected=null;view.links=[];view.rendered=[];view.grid.clear();
 $('#visibleCount').textContent='—';$('#redCount').textContent='—';$('#redShare').textContent='—';
 view.observedLayer.schedule();status('正在读取 '+labels[service]+' 的观测…');
 try{
  const data=await Promise.all(sources[service].map(async k=>[k,await loadData(k)]));
  if(id!==view.ticket)return;
  view.links=mergeObserved(data);
  recalc();
 }catch(e){
  if(id!==view.ticket)return;
  console.error('Railway data error',e);status('区间数据加载失败：'+e.message);showDetail();
 }
}
function bindControls(){
 for(const b of document.querySelectorAll('[data-service]'))b.onclick=()=>{
  view.service=b.dataset.service;
  for(const el of document.querySelectorAll('[data-service]')){
   const active=el===b;el.classList.toggle('active',active);el.setAttribute('aria-pressed',String(active));
  }
  chooseService();
 };
 for(const b of document.querySelectorAll('[data-metric]'))b.onclick=()=>{
  view.metric=b.dataset.metric;
  for(const el of document.querySelectorAll('[data-metric]')){
   const active=el===b;el.classList.toggle('active',active);el.setAttribute('aria-pressed',String(active));
  }
  view.selected=null;recalc();
 };
 $('#minimum').onchange=e=>{view.minimum=Number(e.target.value);view.selected=null;recalc();};
 window.addEventListener('resize',placeLegend);
}
try{
 makeMap();
 bindControls();
 fillLegend();placeLegend();showDetail();
 buildNetwork();
 window.__RAILWAY_OVERVIEW__=Object.freeze({
  getService:()=>view.service,getMetric:()=>view.metric,
  getVisible:()=>view.rendered.length,getMergedLinks:()=>view.links.length,
  getSelected:()=>view.selected,getScale:()=>view.map?.getZoom(),
  getMap:()=>view.map,getNetworkGeometryCount:()=>view.networkParts.length,
  getNetworkReady:()=>view.networkReady,getRendered:()=>view.rendered,
  getRepaintCount:()=>view.repaints,getCanvasCount:()=>document.querySelectorAll('.railway-canvas').length,
  getSpatialBucketCount:()=>view.grid.size,
  clickPoint:ll=>pickAt(L.latLng(ll)),stationZh
 });
 chooseService();
}catch(e){
 console.error('Railway initialization failed',e);
 status('铁路地图初始化失败：'+e.message);
}
})();
