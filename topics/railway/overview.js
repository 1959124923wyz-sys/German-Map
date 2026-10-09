/* Railway 07: low-noise national tracks, grouped service observations, Chinese station labels. */
(() => {
'use strict';
const $ = s => document.querySelector(s);
const P = p => [(p[0]-5.34)*76.5+15,(55.4-p[1])*114.2+6];
const ns = 'http://www.w3.org/2000/svg';
const color = {red:'#e7777d',orange:'#e5a46e',green:'#5cad91',nodata:'#4c6578'};
const stationZh=name=>window.GermanRailStations?.localize(name)||name;
const serviceSources={REGIONAL:['RE','RB'],LONG:['LONG'],OTHER:['HLB','BRB','ERB','NWB','OE']};
const serviceLabels={REGIONAL:'区域列车（RE / RB）',LONG:'长途列车（ICE / IC / EC / FLX）',OTHER:'其他运营商（HLB / BRB / ERB / NWB / OE）'};
const specs = {
  RE:['v12_re_evidence',8],
  RB:['v13_rb_evidence',6],
  HLB:['v14_hlb_evidence',2],
  BRB:['v14_brb_evidence',1],
  ERB:['v14_erb_evidence',1],
  NWB:['v14_nwb_evidence',1],
  OE:['v14_oe_evidence',1],
  LONG:['v10_september_evidence',4]
};
const cache = new Map();
const view = {service:'REGIONAL',metric:'both',minimum:100,selected:null,scale:1,tx:0,ty:0,links:[],rendered:[],ticket:0};
const viewport=$('#viewport'),world=$('#world'),canvas=$('#tracks'),ctx=canvas.getContext('2d',{alpha:true});
const overlay=$('#overlay'),states=$('#states'),cities=$('#cities'),group=$('#segments');
if(!ctx || !DATA || !STATES_PACKED) throw Error('Official rail geography missing');
ctx.setTransform(2,0,0,2,0,0);
function svg(tag,attrs={},root=null){const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));if(root)root.appendChild(e);return e}
function decode(str,mult=10){
 const out=[];let x=0,y=0,i=0;
 while(i<str.length){
  for(let axis=0;axis<2;axis++){
   let shift=0,num=0,b=0;
   do {b=str.charCodeAt(i++)-63;num|=(b&31)<<shift;shift+=5} while(b>=32&&i<str.length);
   const d=(num&1)?~(num>>1):(num>>1);
   if(axis===0)x+=d;else y+=d;
  }
  out.push(x/mult,y/mult);
 }
 return out;
}
function buildBase(){
 const rails = new Path2D();
 for(const section of DATA.sections){
  const xy=decode(section[5]);
  if(xy.length<4)continue;
  rails.moveTo(xy[0],xy[1]);for(let j=2;j<xy.length;j+=2)rails.lineTo(xy[j],xy[j+1]);
 }
 ctx.clearRect(0,0,790,1000);
 ctx.strokeStyle='#5b788c';ctx.globalAlpha=.18;ctx.lineWidth=.48;ctx.lineJoin='bevel';ctx.lineCap='butt';ctx.stroke(rails);ctx.globalAlpha=1;
 for(const parts of Object.values(STATES_PACKED)){
  let d='';
  for(const packed of parts){
   const xy=decode(packed,1000);if(xy.length<6)continue;
   for(let i=0;i<xy.length;i+=2){const [x,y]=P([xy[i],xy[i+1]]);d+=(i===0?'M':'L')+x.toFixed(1)+' '+y.toFixed(1)+' '}
   d+='Z';
  }
  if(d)svg('path',{d,class:'state-border'},states);
 }
 const cityList=[
  ['汉堡',10.006,53.554],['柏林',13.369,52.526],['汉诺威',9.741,52.377],
  ['莱比锡',12.381,51.346],['德累斯顿',13.735,51.04],['多特蒙德',7.46,51.518],
  ['科隆',6.96,50.943],['法兰克福',8.664,50.107],['纽伦堡',11.08,49.447],
  ['斯图加特',9.18,48.784],['慕尼黑',11.56,48.14]
 ];
 for(const [label,lon,lat] of cityList){
  const [x,y]=P([lon,lat]);svg('circle',{cx:x,cy:y,r:2.6,class:'city-dot'},cities);
  const t=svg('text',{x:x+6,y:y-7,class:'city'},cities);t.textContent=label;
 }
}
function fit(){
 const w=viewport.clientWidth,h=viewport.clientHeight;
 view.scale=Math.max(.38,Math.min(w/790,h/1000)*.94);
 view.tx=w/2-395*view.scale;view.ty=h/2-500*view.scale;camera();
}
function camera(){world.style.transform='translate('+view.tx+'px,'+view.ty+'px) scale('+view.scale+')'}
function zoom(f,cx,cy){
 const old=view.scale,now=Math.max(.38,Math.min(6,old*f)),x=(cx-view.tx)/old,y=(cy-view.ty)/old;
 view.scale=now;view.tx=cx-x*now;view.ty=cy-y*now;camera();
 if((old>=1.18)!==(now>=1.18)&&view.links.length)render();
}
$('#zoomIn').addEventListener('click',()=>zoom(1.25,viewport.clientWidth/2,viewport.clientHeight/2));
$('#zoomOut').addEventListener('click',()=>zoom(.8,viewport.clientWidth/2,viewport.clientHeight/2));
$('#home').addEventListener('click',fit);
viewport.addEventListener('wheel',e=>{e.preventDefault();const r=viewport.getBoundingClientRect();zoom(e.deltaY<0?1.13:.885,e.clientX-r.left,e.clientY-r.top)},{passive:false});
let drag=null;
viewport.addEventListener('pointerdown',e=>{
 if(e.button!==0||e.target.closest('.segment-hit'))return;
 drag={x:e.clientX,y:e.clientY,tx:view.tx,ty:view.ty};
 viewport.setPointerCapture(e.pointerId);
});
viewport.addEventListener('pointermove',e=>{
 if(!drag)return;
 view.tx=drag.tx+e.clientX-drag.x;view.ty=drag.ty+e.clientY-drag.y;
 viewport.classList.add('dragging');camera();
});
function stopDrag(){drag=null;viewport.classList.remove('dragging')}
viewport.addEventListener('pointerup',stopDrag);
viewport.addEventListener('pointercancel',stopDrag);
window.addEventListener('resize',fit);
window.addEventListener('resize',placeLegend);
const pad = n=>String(n).padStart(2,'0');
function script(src){
 return new Promise((resolve,reject)=>{
  const tag=document.createElement('script');tag.src=src;tag.onload=resolve;tag.onerror=()=>reject(new Error('无法加载 '+src));document.body.append(tag);
 });
}
function dataFor(key){
 switch(key){
  case 'RE': return V12_RE_EVIDENCE;
  case 'RB': return V13_RB_EVIDENCE;
  case 'HLB': return V14_HLB_EVIDENCE;
  case 'BRB': return V14_BRB_EVIDENCE;
  case 'ERB': return V14_ERB_EVIDENCE;
  case 'NWB': return V14_NWB_EVIDENCE;
  case 'OE': return V14_OE_EVIDENCE;
  default: return V10_SEPTEMBER_EVIDENCE;
 }
}
async function loadData(key){
 if(cache.has(key))return cache.get(key);
 if(!specs[key])throw Error('未知列车数据类别：'+key);
 const [base,n]=specs[key];
 const promise=(async()=>{
  await script('data/'+base+'-core.js');
  for(let i=0;i<n;i++)await script('data/'+base+'-links-'+pad(i)+'.js');
  return dataFor(key);
 })();
 cache.set(key,promise);
 try{return await promise}catch(err){cache.delete(key);throw err}
}
// Combine same-direction route-and-station pairs within one displayed group.
// Always aggregate integer stop observations before computing percentages.
// Original source datasets are left untouched and independently cached.
function mergeObserved(groupData){
 const byKey=new Map();
 for(const [type,data] of groupData){
  for(const leg of (data.links||[])){
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
   for(const fld of ['pairs','arrival_valid','late6','late15','boundary_cancel'])
    dest.v11[fld]+=Number(a[fld]||0);
   if(!dest.brands.includes(type))dest.brands.push(type);
  }
 }
 return [...byKey.values()];
}
function metrics(leg){
 const all=leg.v11||{};
 const a=all;
 const nArrival=Number(a.arrival_valid||0),nPlanned=Number(a.pairs||0);
 const late=nArrival?100*Number(a.late6||0)/nArrival:null;
 const cancel=nPlanned?100*Number(a.boundary_cancel||0)/nPlanned:null;
 const sufficient=view.metric==='both'?nArrival>=view.minimum&&nPlanned>=view.minimum:
 view.metric==='late'?nArrival>=view.minimum:nPlanned>=view.minimum;
 return {late,cancel,nArrival,nPlanned,sufficient};
}
function level(m){
 if(view.metric==='late')return m.late>=40?2:m.late>=25?1:0;
 if(view.metric==='cancel')return m.cancel>=8?2:m.cancel>=4?1:0;
 return (m.late>=40||m.cancel>=8)?2:(m.late>=25||m.cancel>=4)?1:0;
}
function placeLegend(){
 const box=$('#railLegend');
 if(!box)return;
 if(window.innerWidth<=760){
  const field=$('#metric').closest('.field');
  if(field&&box.previousElementSibling!==field)field.insertAdjacentElement('afterend',box);
 }else{
  const panel=$('.map-panel');
  if(panel&&box.parentElement!==panel)panel.appendChild(box);
 }
}
function renderLegend(){
 // No single "combined percentage" exists: the joint filter uses OR between
 // two different source-backed denominators. Display BOTH numeric cutoffs.
 const mode=view.metric;
 const single=mode==='late'?{
   title:'到站晚点 ≥6分钟 · 观测比例',
   low:'<25%',orange:'25%–<40%',red:'≥40%'
 }:mode==='cancel'?{
   title:'停靠取消标记 · 观测比例',
   low:'<4%',orange:'4%–<8%',red:'≥8%'
 }:{
   title:'综合关注 · 晚点≥6分钟 / 停靠取消比例',
   low:'晚点 <25% 且取消 <4%',
   orange:'晚点 ≥25% 或取消 ≥4%（未达红线）',
   red:'晚点 ≥40% 或取消 ≥8%'
 };
 const items=[
   [color.nodata,'无匹配或样本不足'],
   [color.green,single.low],
   [color.orange,single.orange],
   [color.red,single.red]
 ];
 const box=$('#railLegend');
 placeLegend();
 box.replaceChildren();
 const title=document.createElement('b');title.textContent=single.title;box.appendChild(title);
 for(const [c,label] of items){
   const row=document.createElement('span');
   const swatch=document.createElement('i');swatch.style.background=c;
   row.append(swatch,document.createTextNode(label));
   box.appendChild(row);
 }
 const note=document.createElement('small');note.className='rail-legend-note';
 note.textContent=mode==='both'
  ?'红橙按两项指标独立判定；灰色不表示运行正常。'
  :'按当前最低样本门槛分色；灰色不表示运行正常。';
 box.appendChild(note);
}
function pct(n){return n===null||!Number.isFinite(n)?'—':n.toFixed(1)+'%'}
function status(s){$('#status').textContent=s}
function linePath(geometry){
 if(!Array.isArray(geometry))return '';
 // Render-only decimation at national zoom; original official route geometry
 // is still retained and rendered at full fidelity after zooming in.
 const tolerance=view.scale<1.18?.85:0, tol2=tolerance*tolerance;
 let d='';
 for(const part of geometry){
  if(!Array.isArray(part)||part.length<2)continue;
  let prev=null,started=false;
  for(let j=0;j<part.length;j++){
   const point=part[j];if(!Array.isArray(point)||point.length<2)continue;
   const p=P(point);
   if(!Number.isFinite(p[0])||!Number.isFinite(p[1])){started=false;break;}
   if(started&&j<part.length-1&&tol2&&
       (p[0]-prev[0])**2+(p[1]-prev[1])**2<tol2)continue;
   d+=(started?'L':'M')+p[0].toFixed(2)+' '+p[1].toFixed(2)+' ';
   started=true;prev=p;
  }
 }
 return d;
}
function attention(m){
 const delay=(m.late??0)/40,cancel=(m.cancel??0)/8;
 return view.metric==='late'?delay:view.metric==='cancel'?cancel:Math.max(delay,cancel);
}
function renderHotspots(observations){
 const list=$('#hotList');list.replaceChildren();
 const hot=observations.filter(o=>o.grade>0)
  .sort((a,b)=>b.grade-a.grade||attention(b.m)-attention(a.m)).slice(0,10);
 if(!hot.length){
  const note=document.createElement('p');note.className='hot-empty';
  note.textContent='当前条件下没有达到关注门槛的区间。';list.appendChild(note);return;
 }
 for(const [i,o] of hot.entries()){
  const btn=document.createElement('button');btn.type='button';btn.className='hot-row';
  const title=stationZh(o.leg.from_station)+' → '+stationZh(o.leg.to_station);
  const desc='晚点 '+pct(o.m.late)+' · 取消标记 '+pct(o.m.cancel);
  btn.innerHTML='<span class="hot-rank">'+(i+1)+'</span><span class="hot-main"></span><span class="hot-grade '+(o.grade===2?'high':'medium')+'">'+(o.grade===2?'高':'中')+'</span>';
  const content=btn.querySelector('.hot-main');
  text(content,'strong',title);
  text(content,'small',desc);
  btn.addEventListener('click',()=>{view.selected=o;showDetail();highlight(o.node);
   const box=$('#detail');box.scrollIntoView({block:'nearest',behavior:'smooth'});});
  list.appendChild(btn);
 }
}
function render(){
 const observations=[];
 for(const leg of view.links){
  const m=metrics(leg);
  if(!m.sufficient)continue;
  const d=linePath(leg.geometry);
  if(!d)continue;
  observations.push({leg,m,d,grade:level(m)});
 }
 observations.sort((a,b)=>a.grade-b.grade);
 const fragment=document.createDocumentFragment();view.rendered=observations;
 // Keep every sufficiently observed link visible, including those below the
 // warning thresholds (green). Unmapped and insufficiently sampled rails
 // remain on the subdued infrastructure canvas and NEVER count as green.
 // Painting observations in ascending severity keeps the red stretches readable.
 for(const o of observations){
  const c=o.grade===2?color.red:o.grade===1?color.orange:color.green;
  const main=svg('path',{d:o.d,stroke:c,class:'segment'+(o.grade===2?' hot':o.grade===0?' normal':'')},fragment);
  const hit=svg('path',{d:o.d,class:'segment-hit'},fragment);
  o.node=main;
  const pick=e=>{e.stopPropagation();view.selected=o;showDetail();highlight(main)};
  main.addEventListener('click',pick);hit.addEventListener('click',pick);
  const tooltip=svg('title',{},main);
  tooltip.textContent=stationZh(o.leg.from_station)+' → '+stationZh(o.leg.to_station)
    +' · 晚点≥6分 '+pct(o.m.late)+' · 停靠取消 '+pct(o.m.cancel);
 }
 group.replaceChildren(fragment);
 $('#visibleCount').textContent=observations.length.toLocaleString('zh-CN');
 const red=observations.filter(o=>o.grade===2).length;
 $('#redCount').textContent=red.toLocaleString('zh-CN');
 $('#redShare').textContent=observations.length?(red/observations.length*100).toFixed(1)+'%':'—';
 status(serviceLabels[view.service]+' · '+observations.length+' 个达标方向性区间');
 if(view.selected){
  const one=observations.find(o=>o.leg===view.selected.leg);
  view.selected=one||null;
  if(one?.node)highlight(one.node);
 }
 renderLegend();
 renderHotspots(observations);
 showDetail();
}
function highlight(node){
 for(const p of group.querySelectorAll('.segment.selected'))p.classList.remove('selected');
 node?.classList.add('selected');
}
function text(parent,tag,value,className){
 const n=document.createElement(tag);n.textContent=value;
 if(className)n.className=className;
 parent.appendChild(n);return n;
}
function showDetail(){
 const box=$('#detail');box.replaceChildren();
 const item=view.selected;
 if(!item){
  box.classList.add('empty');
  text(box,'h3','选择一段彩色铁路');
  text(box,'p','绿色为已观测且低于阈值；点击任意彩色线路查看详情。');
  return;
 }
 box.classList.remove('empty');
 const {leg,m,grade}=item;
 text(box,'span',grade===2?'● 高关注':grade===1?'● 偏高':'● 低于关注门槛','grade');
 text(box,'h3',stationZh(leg.from_station)+' → '+stationZh(leg.to_station));
 text(box,'p',leg.from_station+' → '+leg.to_station,'original-stations');
 const lbl=leg.label_hints?.[0]?.[0];
 text(box,'p','官方线路 '+leg.route+(lbl?' · '+lbl:'')
   +(leg.brands?.length?' · '+leg.brands.join(' / '):''));
 const grid=text(box,'div','','detail-grid');
 for(const [v,label] of [
  [pct(m.late),'到站晚点≥6分钟'],
  [pct(m.cancel),'停靠取消标记'],
  [m.nArrival.toLocaleString('zh-CN'),'有效到站观测'],
  [m.nPlanned.toLocaleString('zh-CN'),'计划站间配对']]){
  const n=document.createElement('div');text(n,'b',v);text(n,'span',label);grid.appendChild(n);
 }
 text(box,'p','2026年9月 · 区间观测不等于轨道故障归因或整趟车取消概率。');
}
async function chooseService(){
 const id=++view.ticket,s=view.service;
 view.selected=null;group.replaceChildren();
 $('#visibleCount').textContent='—';$('#redCount').textContent='—';$('#redShare').textContent='—';
 status('正在读取 '+serviceLabels[s]+' 的实测区间…');
 try{
  const list=await Promise.all(serviceSources[s].map(async key=>[key,await loadData(key)]));
  if(id!==view.ticket)return;
  view.links=mergeObserved(list);
  render();
 }catch(e){
  if(id!==view.ticket)return;
  view.links=[];group.replaceChildren();status('数据加载失败，请刷新或检查网络：'+e.message);
  renderHotspots([]);showDetail();
 }
}
for(const b of document.querySelectorAll('[data-service]'))b.addEventListener('click',()=>{
 view.service=b.dataset.service;
 for(const x of document.querySelectorAll('[data-service]')){
  const active=x===b;x.classList.toggle('active',active);x.setAttribute('aria-pressed',String(active));
 }
 chooseService();
});
for(const b of document.querySelectorAll('[data-metric]'))b.addEventListener('click',()=>{
 view.metric=b.dataset.metric;
 for(const x of document.querySelectorAll('[data-metric]')){
  const active=x===b;x.classList.toggle('active',active);x.setAttribute('aria-pressed',String(active));
 }
 view.selected=null;render();
});
$('#minimum').addEventListener('change',e=>{view.minimum=Number(e.target.value);view.selected=null;render()});
window.__RAILWAY_OVERVIEW__={getService:()=>view.service,getMetric:()=>view.metric,
 getVisible:()=>view.rendered.length,getMergedLinks:()=>view.links.length,
 getSelected:()=>view.selected,getScale:()=>view.scale,stationZh};
buildBase();
fit();
showDetail();
chooseService();
})();
