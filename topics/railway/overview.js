/* Railway 07 — same Leaflet / OSM base as 01–06.
   Official DB InfraGO tracks and matched service observations use two Canvas
   layers, not thousands of SVG nodes or invented straight-line joins. */
(()=>{
'use strict';
const $=s=>document.querySelector(s);
const COLORS={red:'#c74753',orange:'#cf7f27',green:'#16865e',missing:'#16865e'};
const sources={REGIONAL:['RE','RB'],LONG:['LONG'],OTHER:['HLB','BRB','ERB','NWB','OE']};
const labels={REGIONAL:'区域列车（RE / RB）',LONG:'长途列车（ICE / IC / EC / FLX）',OTHER:'其他运营商'};
const specs={
 RE:['v12_re_evidence',8],RB:['v13_rb_evidence',6],
 LONG:['v10_september_evidence',4],HLB:['v14_hlb_evidence',2],
 BRB:['v14_brb_evidence',1],ERB:['v14_erb_evidence',1],
 NWB:['v14_nwb_evidence',1],OE:['v14_oe_evidence',1]
};
const stationZh=name=>window.GermanRailStations?.localize(name)||name;
const CELL=64, NATION=[[47.05,5.45],[55.15,15.65]];
const {REF_ZOOM,WORLD,officialPart,observedParts,actualBounds,currentViewport,visible,drawPath,unproject,segmentDist}=window.Railway07Geometry;
// Fixed 100-observation inclusion threshold (not a user-facing filter).
const view={service:'REGIONAL',metric:'both',minimum:100,selected:null,links:[],
  rendered:[],groups:[],bridgePaths:[],bridged:0,bridgeGraph:new window.Railway07Bridge.RouteGraph(),ticket:0,networkReady:false,statesReady:false,countiesReady:false,tiles:false,networkParts:[],grid:new Map(),map:null,
  baseLayer:null,observedLayer:null,repaints:0};
const cache=new Map();
const fmt=n=>Number(n).toLocaleString('zh-CN');
const pct=n=>n===null||!Number.isFinite(n)?'—':n.toFixed(1)+'%';
function status(s){$('#status').textContent=s;}
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
   // Unknown samples use the same green family without pretending to be on-time.
   ctx.strokeStyle=COLORS.green;ctx.globalAlpha=.53;
   ctx.lineWidth=m.getZoom()<7?.9:1.1;ctx.stroke();
  }else{
   // Genuine DB InfraGO curves bridge observational gaps, but stay faint
   // green; unknown observations never inherit their neighbours' red grade.
   if(view.bridgePaths.length){
    ctx.beginPath();
    for(const p of view.bridgePaths)if(visible(p,v))drawPath(ctx,p,v);
    ctx.strokeStyle=COLORS.green;ctx.globalAlpha=.75;ctx.lineWidth=1.8;ctx.stroke();
   }
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
  if(!view.tiles){view.tiles=true;$('#mapStatus').textContent='';$('#mapStatus').classList.add('ok');}
 });
 let errors=0;
 tiles.on('tileerror',()=>{
  if(++errors>5&&!view.tiles){$('#mapStatus').textContent='地图底图暂不可用';$('#mapStatus').classList.remove('ok');}
 });
 tiles.addTo(m);
 fetch('../../data/germany-states.geojson',{cache:'force-cache'}).then(r=>{
  if(!r.ok)throw Error('州界 HTTP '+r.status);return r.json();
 }).then(data=>{
  if(data.features?.length!==16)throw Error('州界不完整');
  const layer=L.geoJSON(data,{pane:'rail-state-pane',interactive:false,
   style:()=>({color:'#315065',weight:1.2,opacity:.7,fill:false})}).addTo(m);
  view.statesReady=layer.getLayers().length===16;
 }).catch(e=>console.warn('State boundaries unavailable',e));
 fetch('../../data/germany-counties.geojson',{cache:'force-cache'}).then(r=>{
  if(!r.ok)throw Error('县界 HTTP '+r.status);return r.json();
 }).then(data=>{
  m.createPane('rail-counties-pane').style.zIndex='315';
  const county=L.geoJSON(data,{pane:'rail-counties-pane',interactive:false,
   style:()=>({color:'#607c8f',weight:.32,opacity:.24,fill:false})}).addTo(m);
  view.countiesReady=county.getLayers().length>350;
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
   const p=officialPart(sections[cursor]);
   if(p){
    view.networkParts.push(p);
    view.bridgeGraph.add(sections[cursor][0],p);
   }
  }
  if(cursor<sections.length){
   if(cursor===950)$('#mapStatus').textContent='';
   requestAnimationFrame(batch);
  }else{
   view.networkReady=true;view.baseLayer.schedule();
   if(view.tiles)$('#mapStatus').textContent='';
   // Observations may have loaded before the official graph.
   if(view.links.length)recalc();
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
// Adapter functions bind pure observation computations to the current filter.
const {mergeObserved}=window.Railway07Analysis;
const metrics=leg=>window.Railway07Analysis.metrics(leg,view.metric,view.minimum);
const grade=m=>window.Railway07Analysis.grade(m,view.metric);
const attention=m=>window.Railway07Analysis.attention(m,view.metric);
const buildCorridors=items=>window.Railway07Analysis.buildCorridors(items);

function fillLegend(){
 const mode=view.metric;
 const thresholds=mode==='late'?['晚点比例','<25%','25%–<40%','≥40%']
 :mode==='cancel'?['停靠取消标记率','<4%','4%–<8%','≥8%']
 :['晚点 / 取消标记','','晚点 ≥25% 或取消 ≥4%','晚点 ≥40% 或取消 ≥8%'];
 const box=$('#railLegend');
 box.replaceChildren();
 const title=document.createElement('b');title.textContent=thresholds[0];box.appendChild(title);
 for(const [col,s] of [[COLORS.green,'其他线路'],[COLORS.orange,thresholds[2]],[COLORS.red,thresholds[3]]]){
  const row=document.createElement('span'),dot=document.createElement('i');
  dot.style.background=col;row.append(dot,document.createTextNode(s));box.append(row);
 }
 
}
function placeLegend(){
 const box=$('#railLegend');
 if(window.innerWidth<=760){
  const target=$('.map-panel');if(target&&box.parentElement!==target)target.appendChild(box);
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
  element(box,'h3','点击地图上的彩色铁路');
  return;
 }
 box.classList.remove('empty');
 const {m,grade:g,members}=o;
 const first=members[0].leg,last=members[members.length-1].leg;
 const title=stationZh(first.from_station)+' → '+stationZh(last.to_station);
 element(box,'span',g===2?'● 晚点或取消较多':g===1?'● 需要关注':'● 表现相对较好','grade');
 element(box,'h3',title);
 if(members.length>1||o.bridges)
  element(box,'p','连续区段 · '+members.length+' 个有观测站间'+(o.bridges?' · '+o.bridges+' 处观测缺口':''),'corridor-count');
 const grid=element(box,'div','','detail-grid');
 for(const [value,label] of [[pct(m.onTime),'准点率（晚点不足6分钟）'],
  [pct(m.cancel),'停靠取消标记率']]){
  const cell=document.createElement('div');
  element(cell,'b',value);element(cell,'span',label);grid.append(cell);
 }
 const more=document.createElement('details');more.className='corridor-more';
 const summary=document.createElement('summary');summary.textContent='查看站间明细与样本（'+members.length+' 段）';more.append(summary);
 const sub=element(more,'div','','corridor-items');
 for(const item of members){
  const r=element(sub,'div','','corridor-row');
  element(r,'strong',stationZh(item.leg.from_station)+' → '+stationZh(item.leg.to_station));
  element(r,'span','准点 '+pct(item.m.late===null?null:100-item.m.late)+' · 取消标记 '+pct(item.m.cancel));
 }
 element(more,'p','线路 '+first.route+' · 有效到站 '+fmt(m.nArrival)+' 次 · 计划站间配对 '+fmt(m.nPlanned)+' 次');
 element(more,'p','晚点率 '+pct(m.late)+'（至少6分钟）；相邻区间可能重复观测同一趟车。');
 if(o.bridges){
  const verified=o.bridges-(o.schematicBridges||0);
  if(verified)element(more,'p','沿 DB InfraGO 官方轨道曲线核实连接 '+verified+' 处；没有给缺失区段补造统计数据。');
  if(o.schematicBridges)element(more,'p','另有 '+o.schematicBridges+' 处约定的连续统计走廊，依据同线路公里范围及两端实际轨道位置归并；中间缺少可追踪的完整轨道路径，仅保留原有绿色底网，不补画假线路或假准点率。');
 }
 element(more,'p','原始站名：'+first.from_station+' → '+last.to_station,'original-stations');
 box.append(more);
}

function updateHotspots(){
 const list=$('#hotList');list.replaceChildren();
 const items=view.groups.filter(o=>o.grade>0)
  .sort((a,b)=>b.grade-a.grade||attention(b.m)-attention(a.m)).slice(0,10);
 if(!items.length){element(list,'p','当前没有高关注区间。','hot-empty');return;}
 items.forEach((o,i)=>{
  const row=document.createElement('button');row.type='button';row.className='hot-row';
  element(row,'span',String(i+1),'hot-rank');
  const main=element(row,'span','','hot-main');
  const first=o.members[0].leg,last=o.members[o.members.length-1].leg;
  element(main,'strong',stationZh(first.from_station)+' → '+stationZh(last.to_station));
  element(main,'small','准点 '+pct(o.m.onTime)+' · 取消标记 '+pct(o.m.cancel));
  element(row,'span',o.grade===2?'高':'中','hot-grade '+(o.grade===2?'high':'medium'));
  row.onclick=()=>{
   view.selected=o;showDetail();view.observedLayer.schedule();
   const b=o.bounds,ll1=unproject(b.minX,b.minY),ll2=unproject(b.maxX,b.maxY);
   const bounds=L.latLngBounds(ll1,ll2);
   if(bounds.isValid())view.map.fitBounds(bounds.pad(.38),{maxZoom:11,animate:false});
   $('#detail').scrollIntoView({block:'nearest',behavior:'smooth'});
  };
  list.append(row);
 });
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
 // Hit-testing also works on the real geometry of a visual-only bridge.
 for(const g of view.groups)for(const p of g.bridgeParts||[])
  addToGrid({parts:[p],group:g,bridge:true});
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
  view.selected=best.group;showDetail();view.observedLayer.schedule();
 }
}
function recalc(){
 const previous=view.selected?.members?.[0]?.leg||null;
 const items=[];
 for(const leg of view.links){
  const m=metrics(leg);
  if(!m.sufficient)continue;
  const parts=observedParts(leg);
  if(!parts.length)continue;
  items.push({leg,m,parts,bounds:actualBounds(parts),grade:grade(m)});
 }
 view.rendered=items;
 const measured=buildCorridors(items);
 if(view.networkReady){
  const combined=window.Railway07Bridge.mergeGroups(measured,view.bridgeGraph,items);
  view.groups=combined.groups;
  view.bridged=combined.bridged;view.bridgeDiagnostics=combined.debug;
 }else{
  view.groups=measured;view.bridged=0;
 }
 view.bridgePaths=view.groups.flatMap(g=>g.bridgeParts||[]);
 view.selected=previous?(view.groups.find(g=>g.members.some(x=>x.leg===previous))||null):null;
 rebuildIndex();
 // The research dashboard retains all overall counts; the map stays focused on picked segments.
 status(labels[view.service]+' · '+fmt(view.groups.length)+' 段连续区间');
 fillLegend();placeLegend();updateHotspots();showDetail();
 view.observedLayer.schedule();
}

async function chooseService(){
 const id=++view.ticket,service=view.service;
 view.selected=null;view.links=[];view.rendered=[];view.groups=[];view.bridgePaths=[];view.bridged=0;view.grid.clear();
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
 window.addEventListener('resize',placeLegend);
}
try{
 makeMap();
 bindControls();
 fillLegend();placeLegend();showDetail();
 // The extra sixth topic otherwise appears off-screen in the mobile nav.
 const nav=$('.toplinks');if(nav)nav.scrollLeft=nav.scrollWidth;
 buildNetwork();
 window.__RAILWAY_OVERVIEW__=Object.freeze({
  getService:()=>view.service,getMetric:()=>view.metric,getMinimum:()=>view.minimum,
  getVisible:()=>view.rendered.length,getMergedLinks:()=>view.links.length,
  getSelected:()=>view.selected,getScale:()=>view.map?.getZoom(),
  getMap:()=>view.map,getNetworkGeometryCount:()=>view.networkParts.length,
  getNetworkReady:()=>view.networkReady,getStatesReady:()=>view.statesReady,
  getCountiesReady:()=>view.countiesReady,getRendered:()=>view.rendered,
  getCorridors:()=>view.groups,getBridgedCount:()=>view.bridged,
  getBridgeDiagnostics:()=>view.bridgeDiagnostics,getBridgeFailureCounts:()=>view.bridgeGraph.reasons,getBridgedGeometryCount:()=>view.bridgePaths.length,getGraphEdgeCount:()=>view.bridgeGraph.edges,
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
