/* BahnMonitor v15 — real geometry + transparent stop-observation thresholds. */
(() => {
'use strict';
const $ = s => document.querySelector(s);
const P = p => [(p[0]-5.34)*76.5+15,(55.4-p[1])*114.2+6];
const ns = 'http://www.w3.org/2000/svg';
const color = {red:'#ed5763',orange:'#eaa06c',low:'#8c9ca9',nodata:'#364c5d'};
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
const view = {service:'RE',metric:'both',minimum:100,selected:null,scale:1,tx:0,ty:0,links:[],rendered:[],ticket:0};
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
 ctx.strokeStyle='#668093';ctx.globalAlpha=.32;ctx.lineWidth=.62;ctx.lineJoin='round';ctx.lineCap='round';ctx.stroke(rails);ctx.globalAlpha=1;
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
function sourceKey(type){return ['ICE','IC','LONG'].includes(type)?'LONG':type}
async function loadData(type){
 const key=sourceKey(type);
 if(cache.has(key))return cache.get(key);
 const [base,n]=specs[key];
 const promise=(async()=>{
  await script('data/'+base+'-core.js');
  for(let i=0;i<n;i++)await script('data/'+base+'-links-'+pad(i)+'.js');
  return dataFor(key);
 })();
 cache.set(key,promise);
 try{return await promise}catch(err){cache.delete(key);throw err}
}
function metrics(leg){
 const all=leg.v11||{};
 const a=view.service==='ICE'||view.service==='IC'?(all.by_type?.[view.service]||{}):all;
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
function pct(n){return n===null||!Number.isFinite(n)?'—':n.toFixed(1)+'%'}
function status(s){$('#status').textContent=s}
function linePath(geometry){
 if(!Array.isArray(geometry))return '';
 let d='';
 for(const part of geometry){
  if(!Array.isArray(part)||part.length<2)continue;
  let p='';
  for(let j=0;j<part.length;j++){
   const point=part[j];if(!Array.isArray(point)||point.length<2)continue;
   const [x,y]=P(point);
   if(!Number.isFinite(x)||!Number.isFinite(y)){p='';break}
   p+=(p?'L':'M')+x.toFixed(2)+' '+y.toFixed(2)+' ';
  }
  d+=p;
 }
 return d;
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
 for(const o of observations){
  const c=o.grade===2?color.red:o.grade===1?color.orange:color.low;
  const main=svg('path',{d:o.d,stroke:c,class:'segment'+(o.grade===2?' hot':'')},fragment);
  const hit=svg('path',{d:o.d,class:'segment-hit'},fragment);
  const pick=e=>{e.stopPropagation();view.selected=o;showDetail();highlight(main)};
  main.addEventListener('click',pick);hit.addEventListener('click',pick);
  const tooltip=svg('title',{},main);tooltip.textContent=o.leg.from_station+' → '+o.leg.to_station+' · 晚点≥6分 '+pct(o.m.late)+' · 停靠取消 '+pct(o.m.cancel);
 }
 group.replaceChildren(fragment);
 $('#visibleCount').textContent=observations.length.toLocaleString('zh-CN');
 $('#redCount').textContent=observations.filter(o=>o.grade===2).length.toLocaleString('zh-CN');
 const serviceLabel=$('#service').selectedOptions[0]?.textContent||view.service;
 status('2026年9月 · '+serviceLabel+' · '+observations.length+' 个达标方向性区间');
 if(view.selected){
  const newOne=observations.find(o=>o.leg===view.selected.leg);
  view.selected=newOne||null;
 }
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
 if(!item){text(box,'h3','点击彩色铁路段');text(box,'p','查看该段的实际到站延误与停靠取消记录。');return}
 const {leg,m,grade}=item;
 text(box,'span',grade===2?'● 高关注区间':grade===1?'● 较高关注区间':'● 未达警示阈值','grade');
 text(box,'h3',leg.from_station+' → '+leg.to_station);
 const lbl=leg.label_hints?.[0]?.[0];
 text(box,'p','官方线路 '+leg.route+(lbl?' · '+lbl:''));
 const grid=text(box,'div','','detail-grid');
 for(const [v,label] of [
  [pct(m.late),'到站晚点≥6分钟'],
  [pct(m.cancel),'停靠取消标记'],
  [m.nArrival.toLocaleString('zh-CN'),'有效到站观测'],
  [m.nPlanned.toLocaleString('zh-CN'),'计划站间配对']]){
  const n=document.createElement('div');text(n,'b',v);text(n,'span',label);grid.appendChild(n);
 }
 text(box,'p','2026年9月 · 两端停站匹配至 DB InfraGO 官方线路。统计是观测区间，不是轨道故障归因。');
}
async function chooseService(){
 const id=++view.ticket;const s=$('#service').value;
 view.service=s;view.selected=null;group.replaceChildren();
 $('#visibleCount').textContent='—';$('#redCount').textContent='—';
 status('正在读取 '+$('#service').selectedOptions[0].textContent+' 的实测区间…');
 try{
  const data=await loadData(s);
  if(id!==view.ticket)return;
  view.links=data.links||[];
  render();
 }catch(e){if(id!==view.ticket)return;view.links=[];group.replaceChildren();status('数据加载失败，请刷新或检查网络：'+e.message);showDetail();}
}
$('#service').addEventListener('change',chooseService);
$('#metric').addEventListener('change',e=>{view.metric=e.target.value;view.selected=null;render()});
$('#minimum').addEventListener('change',e=>{view.minimum=Number(e.target.value);view.selected=null;render()});
buildBase();
fit();
showDetail();
chooseService();
})();
