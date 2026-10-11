/* Crime: navigate published city sublayers from the verified state's source archive.
 * The seven supported states are derived solely from the curated manifests,
 * never from pin coordinates, guessed AGS or a countrywide pseudo-city ranking. */
(() => {
 'use strict';
 const byId=id=>document.getElementById(id);
 const box=byId('stateCityArchive'),list=byId('stateCityList'),summary=byId('stateCityArchiveTitle');
 if(!box||!list||!summary)return;
 const fmtKeys={
  violence:'暴力总体',serious_injury:'严重伤害',robbery:'抢劫',sexual:'性犯罪',
  homicide:'凶杀',property_total:'盗窃总体',burglary:'入室盗窃',
  bicycle_theft:'自行车盗窃',vehicle_theft:'机动车盗窃',
  theft_from_vehicle:'车内／车上盗窃'
 };
 const countTypes={
  kiel:'全部登记案件数',bremen:'7类警方登记案件数',
  stuttgart:'公共场所暴力犯罪案件数',duesseldorf:'全部案件数（含多年及街区下钻）'
 };
 const countControl={
  kiel:'focusKielCount',bremen:'focusBremenCategory',
  stuttgart:'focusStuttgartViolence',duesseldorf:'focusDuesseldorfCount'
 };
 let entries=[],activeState=null,loading=false,ready=false;
 const button=(text,cl)=>{
  const b=document.createElement('button');
  b.type='button';b.textContent=text;b.className=cl;
  return b;
 };
 function tag(parent,tag,text,cl){
  const item=document.createElement(tag);
  if(cl)item.className=cl;
  item.textContent=text;parent.append(item);return item;
 }
 function openRecord(item){
  const api=window.__CRIME_MAP__;
  if(!api)return;
  if(item.category==='rates'){
   const selector=api.getMode()==='property'?'propertyMetric':'violenceMetric';
   const select=byId(selector);
   if(select&&!item.info.metrics?.[select.value]){
    // Changing from homicide to a city with violence-only detail must not
    // silently show a dead, uncoloured map: use a real published city metric.
    const metric=api.getMode()==='property'?'property_total':'violence';
    if(item.info.metrics?.[metric]){
     select.value=metric;
     select.dispatchEvent(new Event('change',{bubbles:true}));
    }
   }
   api.clearSelection?.();
   api.map.fitBounds(L.latLngBounds(item.info.bounds),{padding:[26,26],maxZoom:10,animate:false});
  }else{
   const target=byId(countControl[item.info.id]);
   if(!target)return;
   target.click(); // Existing dedicated source validator and count-only layer.
  }
 }
 function render(){
  list.replaceChildren();
  const matched=entries.filter(item=>item.info.state===activeState);
  box.hidden=!activeState||!ready||!matched.length;
  if(box.hidden){box.open=false;return;}
  summary.textContent='本州城市细分地图 · '+matched.length+'组官方资料';
  for(const item of matched){
   const c=item.info;
   const row=button(c.name_zh||c.name,'state-city-row');
   tag(row,'strong',(c.name_zh||c.name)+' →');
   const label=item.category==='rates'?'每10万人犯罪率 · '+Object.keys(c.metrics||{}).map(k=>fmtKeys[k]||c.metrics[k].label||k).join('、'):
    '独立登记案件数 · '+(countTypes[c.id]||c.metric);
   tag(row,'small',label,'state-city-kind');
   const provenance=c.source_label||c.source||'原始警方统计';
   tag(row,'small',provenance,'state-city-source');
   if(c.coverage==='partial')tag(row,'small','只覆盖已公布细分地区，未覆盖区域不填零','state-city-partial');
   row.addEventListener('click',()=>openRecord(item));
   list.append(row);
  }
  // Automatically reveal each state's modest list. National default has none.
  box.open=true;
 }
 async function boot(){
  if(loading)return;loading=true;
  try{
   const [rates,counts]=await Promise.all([
    fetch('data/city_layers.json',{cache:'force-cache'}).then(r=>{if(!r.ok)throw Error('rate registry HTTP '+r.status);return r.json()}),
    fetch('data/city_count_layers.json',{cache:'force-cache'}).then(r=>{if(!r.ok)throw Error('count registry HTTP '+r.status);return r.json()})
   ]);
   if(rates.schema_version!==1||counts.schema_version!==1||rates.cities?.length!==5||counts.layers?.length!==4)
    throw Error('City-source registry schema or expected coverage changed; verify before publication');
   const ids=new Set();
   entries=[
    ...rates.cities.map(info=>({category:'rates',info})),
    ...counts.layers.map(info=>({category:'counts',info}))
   ];
   for(const item of entries){
    const c=item.info;
    if(!c.id||!c.state||!c.name_zh||ids.has(c.id))throw Error('Invalid or duplicate city registry: '+c.id);
    if(item.category==='rates'&&(!c.bounds||!c.metrics||!Object.keys(c.metrics).length))
     throw Error('Invalid crime-rate city boundary or metrics: '+c.id);
    if(item.category==='counts'&&!countControl[c.id])throw Error('Missing count-only verified handler: '+c.id);
    ids.add(c.id);
   }
   ready=true;render();
  }catch(error){
   console.warn('Verified city atlas unavailable; primary crime map remains active',error);
   box.hidden=true;
  }
 }
 box.addEventListener('crime:state-rendered',event=>{
  activeState=event.detail?.state||null;
  render();
 });
 document.addEventListener('click',event=>{
  if(event.target?.id==='viewGermany')activeState=null;
 });
 boot();
 window.__CRIME_CITY_CATALOG__=Object.freeze({
  getCount:()=>entries.length,
  getState:()=>activeState,
  getVisibleCount:()=>box.hidden?0:list.querySelectorAll('.state-city-row').length,
  getEntries:()=>entries.map(e=>({id:e.info.id,state:e.info.state,category:e.category}))
 });
})();