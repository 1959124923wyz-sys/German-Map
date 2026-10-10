/* Railway 07 public map: Leaflet + one Canvas of measured city-to-city passenger corridors.
   Full DB infrastructure and fine-grained station measurements remain research assets. */
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
const NATION=[[47.05,5.45],[55.15,15.65]];
const {REF_ZOOM,WORLD,officialPart,observedParts,actualBounds,currentViewport,visible,drawPath,unproject,segmentDist}=window.Railway07Geometry;
// Fixed 100-observation inclusion threshold (not a user-facing filter).
const view={service:'REGIONAL',metric:'both',minimum:100,selected:null,links:[],
  rendered:[],groups:[],riskIndexes:null,hiddenCorridors:0,physicalEdges:0,ticket:0,networkReady:false,statesReady:false,countiesReady:false,tiles:false,map:null,backbone:new window.Railway07Continuity.Backbone(),drawnObserved:[],
  observedLayer:null,picker:new window.Railway07Picker.RailwayPicker(),repaints:0};
const cache=new Map();
const fmt=n=>Number(n).toLocaleString('zh-CN');
const pct=n=>n===null||!Number.isFinite(n)?'—':n.toFixed(1)+'%';
function status(s){$('#status').textContent=s;}
const CanvasLayer=L.Layer.extend({
 initialize(kind){this.kind=kind;this._frame=null;},
 onAdd(m){
  this.map=m;
  this.canvas=L.DomUtil.create('canvas','railway-canvas railway-'+this.kind,m.getPane('rail-observed-pane'));
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
  // Round strokes close subpixel gaps at adjoining station endpoints without
  // adding any path geometry or borrowing missing observations.
  ctx.lineCap='round';ctx.lineJoin='round';
  const v=currentViewport(m,size);
  // 1. Complete actual DB railway geometry, including unsampled spans.
  // Different observation groups may change colour but cannot cut the rail.
  if(view.networkReady){
   // Underlying source geometry guarantees physical national continuity even
   // when no September observation exists anywhere on that DB route.
   ctx.beginPath();
   for(const part of view.backbone.all)if(visible(part,v))drawPath(ctx,part,v);
   ctx.strokeStyle=COLORS.green;ctx.globalAlpha=.6;
   ctx.lineWidth=m.getZoom()<7?1.15:1.5;ctx.stroke();
   // Passenger-relevant infrastructure is the dominant continuous GREEN line.
   ctx.beginPath();
   for(const part of view.backbone.active)if(visible(part,v))drawPath(ctx,part,v);
   ctx.strokeStyle=COLORS.green;ctx.globalAlpha=.95;
   ctx.lineWidth=m.getZoom()<7?1.8:2.3;ctx.stroke();
  }
  // 2. Genuine observed orange/red intervals only, never extrapolate a
  // missing station pair or recolour an unmeasured bridge.
  const widths=[2.95,3.75],colors=[COLORS.orange,COLORS.red];
  for(let level=1;level<=2;level++){
   ctx.beginPath();
   for(const observed of view.drawnObserved){
    if(observed.grade!==level||!visible(observed.bounds,v))continue;
    for(const part of observed.parts)if(visible(part,v))drawPath(ctx,part,v);
   }
   ctx.strokeStyle=colors[level-1];ctx.globalAlpha=1;ctx.lineWidth=widths[level-1];ctx.stroke();
  }
   if(view.selected?.parts){
    ctx.beginPath();
    for(const p of view.selected.parts)if(visible(p,v))drawPath(ctx,p,v);
    ctx.strokeStyle='#273b4b';
    ctx.globalAlpha=1;ctx.lineWidth=5.1;ctx.stroke();
    ctx.beginPath();
    for(const p of view.selected.parts)if(visible(p,v))drawPath(ctx,p,v);
    ctx.strokeStyle=view.selected.unobserved?'#a4ddbd':'#fee2a9';
    ctx.lineWidth=2.5;ctx.stroke();
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
 for(const [name,z] of [['rail-observed-pane',430],['rail-state-pane',325]]){
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
   style:()=>({color:'#657f8c',weight:.85,opacity:.36,dashArray:'3 5',fill:false})}).addTo(m);
  view.statesReady=layer.getLayers().length===16;
 }).catch(e=>console.warn('State boundaries unavailable',e));
 fetch('../../data/germany-counties.geojson',{cache:'force-cache'}).then(r=>{
  if(!r.ok)throw Error('县界 HTTP '+r.status);return r.json();
 }).then(data=>{
  m.createPane('rail-counties-pane').style.zIndex='315';
  const county=L.geoJSON(data,{pane:'rail-counties-pane',interactive:false,
   style:()=>({color:'#79919d',weight:.26,opacity:.14,fill:false})}).addTo(m);
  view.countiesReady=county.getLayers().length>350;
 }).catch(e=>console.warn('County boundaries unavailable',e));
 window.CrimeCityLabels?.create(m,{paneName:'rail-major-cities',zIndex:470});
 view.observedLayer=new CanvasLayer('observed').addTo(m);
 m.on('click',e=>pickAt(e.latlng));
 $('#home').onclick=()=>m.fitBounds(NATION,{padding:[12,12],animate:false});
 return m;
}
// Batch initialisation: all official sections are deliberately retained.
// Full DB source lines are drawn as GREEN continuity regardless of timetables.
function buildNetwork(){
 if(!DATA||DATA.sections.length!==33547||
   DATA.qa?.source_line_geometries!==33547)
   throw Error('DB InfraGO 官方线路几何数量校验失败');
 const sections=DATA.sections;let index=0;
 function batch(){
  const end=Math.min(index+850,sections.length);
  for(;index<end;index++){
   const part=officialPart(sections[index]);
   if(!part)continue;
   const route=sections[index][0];
   view.backbone.add(route,part);
   view.picker.addNetwork(route,part);
  }
  if(index<sections.length)requestAnimationFrame(batch);
  else{
   view.networkReady=true;
   refreshBackbone();
   view.observedLayer.schedule();
   $('#mapStatus').textContent='';
  }
 }
 requestAnimationFrame(batch);
}
function refreshBackbone(){
 if(!view.networkReady)return;
 const info=view.backbone.setActive(view.groups,view.picker);
 view.backboneCoverage=info;
 view.observedLayer?.schedule();
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
const shadeRuns=window.Railway07ColorRuns;

function fillLegend(){
 const thresholds=['晚点 / 取消标记','','晚点 ≥25% 或取消 ≥4%','晚点 ≥40% 或取消 ≥8%'];
 const box=$('#railLegend');
 box.replaceChildren();
 const title=document.createElement('b');title.textContent=thresholds[0];box.appendChild(title);
 for(const [col,s] of [[COLORS.green,'铁路／暂无高风险观测'],[COLORS.orange,thresholds[2]],[COLORS.red,thresholds[3]]]){
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
// Extract physical endpoint names from the undirected station chain rather
// than trusting arbitrary first/last reverse-direction observation order.
function corridorStations(members){
 const edges=new Map();
 for(const m of members){
  const leg=m.leg,a=leg.from_station,b=leg.to_station,km=leg.km_range;
  if(!a||!b||a===b||!Array.isArray(km)||km.length!==2)continue;
  const id=[a,b].sort().join('\u0000')+'|'+km.map(Number).sort((x,y)=>x-y).join(',');
  if(!edges.has(id))edges.set(id,{a,b,low:Math.min(...km),high:Math.max(...km)});
 }
 const unique=[...edges.values()];
 if(!unique.length)return [members[0].leg.from_station,members[members.length-1].leg.to_station];
 const comp=[],pending=new Set(unique);
 while(pending.size){
  const seed=pending.values().next().value,pieces=[seed];pending.delete(seed);
  const nodes=new Set([seed.a,seed.b]);let changed=true;
  while(changed){changed=false;
   for(const edge of [...pending]){
    if(nodes.has(edge.a)||nodes.has(edge.b)){
     pending.delete(edge);pieces.push(edge);nodes.add(edge.a);nodes.add(edge.b);changed=true;
    }
   }
  }
  pieces.sort((a,b)=>a.low-b.low);
  const degree=new Map();
  for(const e of pieces){degree.set(e.a,(degree.get(e.a)||0)+1);degree.set(e.b,(degree.get(e.b)||0)+1);}
  const lowEdge=pieces[0],highEdge=pieces[pieces.length-1];
  const termini=[...degree].filter(x=>x[1]===1).map(x=>x[0]);
  let low=lowEdge.a,high=highEdge.b;
  if(pieces.length>1){
   const next=pieces[1],prev=pieces[pieces.length-2];
   low=[lowEdge.a,lowEdge.b].find(x=>x!==next.a&&x!==next.b)||low;
   high=[highEdge.a,highEdge.b].find(x=>x!==prev.a&&x!==prev.b)||high;
  }else{
   const original=members.find(m=>(m.leg.from_station===lowEdge.a&&m.leg.to_station===lowEdge.b)||
     (m.leg.from_station===lowEdge.b&&m.leg.to_station===lowEdge.a));
   if(original){low=original.leg.from_station;high=original.leg.to_station;}
  }
  if(termini.length===2&&!termini.includes(low))low=termini[0];
  if(termini.length===2&&!termini.includes(high))high=termini.find(x=>x!==low)||termini[1];
  comp.push({min:lowEdge.low,low,high});
 }
 comp.sort((a,b)=>a.min-b.min);
 return [comp[0].low,comp[comp.length-1].high];
}
function showDetail(){
 const box=$('#detail');box.replaceChildren();
 const o=view.selected;
 if(!o){
  box.classList.add('empty');
  element(box,'h3','点击任意铁路线，查看城市间区段');
  return;
 }
 box.classList.remove('empty');
 if(o.unobserved){
  element(box,'span','● 绿色连续区段 · 暂无可比观测','grade');
  element(box,'h3',o.cityFrom&&o.cityTo?
    stationZh(o.cityFrom)+' → '+stationZh(o.cityTo):
    '官方铁路线路 '+o.route);
  const grid=element(box,'div','','detail-grid');
  for(const label of ['准点率（晚点不足6分钟）','停靠取消标记率']){
   const cell=element(grid,'div','');
   element(cell,'b','—');element(cell,'span',label);
  }
  const more=element(box,'details','','corridor-more');
  element(more,'summary','数据说明');
  element(more,'p','轨道几何来自 DB InfraGO，绿色表示没有可显示的高风险观测。此处可能缺少数据，不代表保证准点。');
  return;
 }
 const {m,grade:g,members}=o;
 const first=members[0].leg,last=members[members.length-1].leg;
 const startStation=o.startStation||members[0].leg.from_station;
 const endStation=o.endStation||members[members.length-1].leg.to_station;
 const from=o.cityFrom||startStation,to=o.cityTo||endStation;
 const prefix=o.serviceName&&!o.serviceName.startsWith('DB ')?o.serviceName+' · ':'';
 const title=prefix+stationZh(from)+' → '+stationZh(to);
 const colorNames=['绿色','橙色','红色'];
 element(box,'span',o.shadeRun?'● '+colorNames[g]+'连续区段'+
  (o.colorTotal?' · '+(o.colorIndex+1)+'/'+o.colorTotal:''):
  '● 城市间整体观测','grade');
 element(box,'h3',title);
 if(members.length>1)element(box,'p',(o.shadeRun?'同色区段':'城市间走廊')+
  ' · '+o.observedEdges+' 个实际观测站间','corridor-count');
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
 const routes=[...new Set(members.map(x=>String(x.leg.route)))].join('、');
 element(more,'p','官方线路 '+routes+' · 有效到站 '+fmt(m.nArrival)+' 次 · 计划站间配对 '+fmt(m.nPlanned)+' 次');
 element(more,'p','绿色官方轨道保证线路骨架可见，红橙仅对应实际晚点或取消偏高的已观测站间；缺失站间不计入两项比例。');
 element(more,'p','晚点率 '+pct(m.late)+'（至少6分钟）；相邻区间可能重复观测同一趟车。');
 element(more,'p','原始站名：'+startStation+' → '+endStation,'original-stations');
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
  element(main,'strong',stationZh(o.cityFrom)+' → '+stationZh(o.cityTo));
  element(main,'small','准点 '+pct(o.m.onTime)+' · 取消标记 '+pct(o.m.cancel));
  element(row,'span',o.grade===2?'高':'中','hot-grade '+(o.grade===2?'high':'medium'));
  row.onclick=()=>{
   selectCorridor(o);
   const b=o.bounds,ll1=unproject(b.minX,b.minY),ll2=unproject(b.maxX,b.maxY);
   const bounds=L.latLngBounds(ll1,ll2);
   if(bounds.isValid())view.map.fitBounds(bounds.pad(.38),{maxZoom:11,animate:false});
   $('#detail').scrollIntoView({block:'nearest',behavior:'smooth'});
  };
  list.append(row);
 });
}

function rebuildIndex(){
 // Give each source-coloured curve its own precise locator, but map it to the
 // maximal physical run in its CITY corridor on click.  A single group-wide
 // geometry hit was incorrectly choosing neighbouring tracks at junctions.
 view.picker.replaceObserved(view.drawnObserved
  .map(item=>({parts:item.parts,group:view.memberToGroup?.get(item),grade:item.grade}))
  .filter(x=>x.group),[]);
}
function selectShade(run){
 if(!run)return;
 view.selected=run;
 showDetail();view.observedLayer.schedule();
}
function selectCorridor(group,point=null,preferred=null){
 const runs=view.networkReady?
  shadeRuns.forCorridor(group,view.backbone):[group];
 let chosen;
 if(point)chosen=shadeRuns.findRun(runs,point,preferred,8);
 if(!chosen){
  chosen=preferred!==null?runs.find(x=>x.grade===preferred):null;
  if(!chosen)chosen=runs.reduce((a,b)=>
   !a||b.grade>a.grade?b:a,null);
 }
 selectShade(chosen||group);
}
function nearbyCityCorridor(route,point){
 const sections=view.groups.filter(g=>g.members.some(m=>
  String(m.leg.route)===String(route)));
 let best=null,d=Infinity;
 for(const group of sections){
  const b=group.bounds,margin=12;
  if(point[0]<b.minX-margin||point[0]>b.maxX+margin||
     point[1]<b.minY-margin||point[1]>b.maxY+margin)continue;
  for(const p of group.parts){
   const xy=p.xy;
   for(let i=2;i<xy.length;i+=2){
    const q=segmentDist(point[0],point[1],xy[i-2],xy[i-1],xy[i],xy[i+1]);
    if(q<d){d=q;best=group;}
   }
  }
 }
 return d<12*12?best:null;
}
function observedRiskAt(point){
 // The displayed red layer is on top of orange and green. Use the SAME
 // precedence to decide which contiguous segment a click refers to.
 const index=view.riskIndexes;
 if(!index)return 0;
 return index[2].nearest(point,1.25)?2:
   index[1].nearest(point,1.25)?1:0;
}
function pickAt(latlng){
 const p=view.map.project(latlng,REF_ZOOM),pt=[p.x,p.y];
 const hit=view.picker.hit(pt,view.map.getZoom());
 if(!hit)return;
 const gradeAt=observedRiskAt(pt);
 if(hit.kind==='observed'){
  selectCorridor(hit.group,pt,gradeAt);
  return;
 }
 const candidate=nearbyCityCorridor(hit.route,pt);
 if(candidate){
  const runs=shadeRuns.forCorridor(candidate,view.backbone);
  const chosen=shadeRuns.findRun(runs,pt,gradeAt,3.5);
  if(chosen){selectShade(chosen);return;}
 }
 // No observed statistics on the clicked official track. Its uninterrupted
 // GREEN portion still selects as a whole, stopping at real orange/red runs.
 const official=view.backbone.unobserved(hit.route,pt);
 const candidates=view.drawnObserved.filter(x=>x.grade>0);
 const runs=shadeRuns.forOfficial(official,candidates);
 const chosen=shadeRuns.findRun(runs,pt,0,4);
 if(chosen){selectShade(chosen);return;}
 view.selected=official;showDetail();view.observedLayer.schedule();
}
function recalc(){
 const previous=view.selected?.members?.[0]?.leg||null,items=[];
 for(const leg of view.links){
  const m=metrics(leg);
  if(!m.sufficient)continue;
  const parts=observedParts(leg);
  if(!parts.length)continue;
  items.push({leg,m,parts,bounds:actualBounds(parts),grade:grade(m)});
 }
 view.rendered=items;
 const result=window.Railway07Cities.buildCityCorridors(items,view.metric);
 view.groups=result.corridors;view.hiddenCorridors=result.hidden;
 view.physicalEdges=result.physicalEdges;
 view.memberToGroup=result.byItem;
 const displayed=new Set(view.groups.flatMap(g=>g.members));
 view.drawnObserved=items.filter(item=>displayed.has(item));
 view.riskIndexes=shadeRuns.indexItems(view.drawnObserved);
 refreshBackbone();
 // A service/category change invalidates cached per-grade runs.  Preserve
 // selection by physical observation identity only when it remains available.
 const restored=previous?view.groups.find(g=>g.members.some(x=>x.leg===previous)):null;
 view.selected=restored||null;
 // Never leave the old infrastructure-loading toast after passenger data loads.
 const mapStatus=$('#mapStatus');
 if(mapStatus.textContent.includes('客运运行线路加载中'))mapStatus.textContent='';
 rebuildIndex();
 status(labels[view.service]+' · '+fmt(view.groups.length)+' 段城市间走廊');
 fillLegend();placeLegend();updateHotspots();showDetail();
 view.observedLayer.schedule();
}
async function chooseService(){
 const id=++view.ticket,service=view.service;
 view.selected=null;view.links=[];view.rendered=[];view.groups=[];view.drawnObserved=[];view.riskIndexes=null;view.hiddenCorridors=0;view.picker.replaceObserved([],[]);
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
  getSelected:()=>view.selected,getMap:()=>view.map,getNetworkReady:()=>view.networkReady,
  getStatesReady:()=>view.statesReady,getCountiesReady:()=>view.countiesReady,
  getRendered:()=>view.rendered,getCorridors:()=>view.groups,
  getCityCorridors:()=>view.groups,getServiceCorridors:()=>view.groups,
  getHiddenCorridors:()=>view.hiddenCorridors,getPhysicalEdgeCount:()=>view.physicalEdges,
  getNetworkGeometryCount:()=>view.backbone.official,getBackboneCoverage:()=>view.backboneCoverage,
  getOfficialPickCount:()=>view.picker.network.items,getCompleteBackboneRoutes:()=>view.backbone.perRoute.size,
  getOfficialPickEntries:()=>view.picker.network.cells,getDrawnObserved:()=>view.drawnObserved,
  getVerifiedCorridorPaths:()=>view.backbone.verified,
  getColourRuns:g=>shadeRuns.forCorridor(g,view.backbone),
  getCurrentColourRun:()=>view.selected?.shadeRun?view.selected:null,
  traceVerifiedCorridor:g=>view.backbone.full(g),
  getRepaintCount:()=>view.repaints,
  getCanvasCount:()=>document.querySelectorAll('.railway-canvas').length,
  getSpatialBucketCount:()=>view.picker.observed.cells.size,
  clickPoint:ll=>pickAt(L.latLng(ll)),stationZh,corridorStations
 });
 chooseService();
}catch(e){
 console.error('Railway initialization failed',e);
 status('铁路地图初始化失败：'+e.message);
}
})();
