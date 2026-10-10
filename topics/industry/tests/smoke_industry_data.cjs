'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const topic=path.resolve(__dirname,'..');
const site=path.resolve(topic,'../..');
const src=fs.readFileSync(path.join(topic,'topic.js'),'utf8');
const elements=new Map();
function el(id){
 if(!elements.has(id))elements.set(id,{style:{},textContent:'',innerHTML:'',hidden:false,className:'',addEventListener(){},querySelectorAll(){return [];}});
 return elements.get(id);
}
const panes={};
const fakeMap={fitBounds(){return this;},createPane(n){panes[n]={style:{}};},getPane(n){return panes[n];},addLayer(){},removeLayer(){},panTo(){}};
function layer(){
 return {on(){return this;},bindTooltip(){return this;},setStyle(){return this;},addTo(){return this;},resetStyle(){},getBounds(){return{getCenter:()=>({lat:51.2,lng:9.5})}}};
}
const L={
 map(){return fakeMap;},
 tileLayer(){return layer();},
 geoJSON(obj,cfg){
  if(obj.features&&cfg&&cfg.onEachFeature)for(const feat of obj.features)cfg.onEachFeature(feat,layer());
  return layer();
 },
 layerGroup(){return layer();},
 circleMarker(){return layer();}
};
async function fetchStatic(url){
 const filepath=path.resolve(topic,url);
 assert.ok(filepath.startsWith(site+path.sep),'static fetch must stay inside checked-out repository: '+url);
 const obj=JSON.parse(fs.readFileSync(filepath,'utf8'));
 return {ok:true,status:200,json:async()=>obj};
}
const w={GermanPlaceNames:{translate:s=>s}};
const context={window:w,document:{getElementById:el},L,fetch:fetchStatic,
 console:{error:e=>{throw e}},setTimeout};
vm.runInNewContext(src,context,{filename:'topics/industry/topic.js',timeout:6000});
(async()=>{
 for(let i=0;i<30&&!w.GermanIndustryQA;i++)await new Promise(resolve=>setImmediate(resolve));
 const qa=w.GermanIndustryQA;
 assert.ok(qa,'topic failed to boot');
 assert.equal(qa.records,174);
 assert.equal(qa.counties,402);
 assert.equal(qa.modernCounties,400);
 assert.equal(qa.states,16);
 assert.equal(qa.officialCoverage,0,'must not fabricate official employment series');
 assert.ok(qa.mappedCounties>80,'valid administrative assignment for sample events');
 assert.ok(qa.pointMarkers>90,'major markers should load');
 assert.equal(el('mapStatus').style.display,'none');
 assert.equal(el('areaEvents').textContent,174);
 assert.ok(el('legend').innerHTML.includes('已登记工业收缩事件'),'sampled-news shading must disclose its nature');
 console.log('industry runtime smoke succeeded',JSON.stringify(qa));
})().catch(e=>{process.stderr.write(String(e.stack||e)+'\\n');process.exitCode=1});
