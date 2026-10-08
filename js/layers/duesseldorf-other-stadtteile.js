/* Düsseldorf official 2025 police Stadtteil drilldowns: BV7 (8 categories,
 * five areas) and BV9 (2 categories, eight areas), no invented measures.
 * A shared Leaflet component avoids copy/paste lifetime bugs as new
 * officially evidenced city districts are admitted to the registry. */
(()=>{'use strict';
const $=id=>document.getElementById(id);
const fmt=n=>Number(n).toLocaleString('zh-CN');
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const LABELS={
 all_offenses:'全部登记犯罪',street_crime:'街头犯罪',street_robbery:'道路／广场抢劫',
 street_injury:'道路／广场伤害',vehicle_related_theft:'机动车相关盗窃',
 bicycle_theft:'自行车盗窃',pickpocketing:'扒窃',residential_burglary:'住宅入室盗窃'};
const PAL=['#f0e8f6','#ddc9e9','#ba9bd8','#9975c4','#7652ac','#54358b','#382063'];
const panel=document.createElement('section');
panel.id='duesseldorfOtherPanel';panel.className='supp-city-info duesseldorf-bv6-panel duesseldorf-other-panel';panel.hidden=true;
let mapApi,parent,registered=[],selectedDistrict=null,active=false,geo=null,layer=null,renderer=null,metric='street_crime',bounds=null,epoch=0,selected=null,originalPanel=null;
const listed=()=>geo?.meta?.categories||[];
const label=k=>LABELS[k]||k;
const local=f=>f.properties.metrics[metric]['2025'];
function cleanupPopups(){
 if(!mapApi)return;
 mapApi.map.closePopup();
 const pane=mapApi.map.getPanes().popupPane;
 if(pane)pane.querySelectorAll('.leaflet-popup').forEach(n=>n.remove());
}
function closeLayers(){
 if(layer){
   layer.eachLayer(l=>{l.closePopup?.();l.getPopup?.()?.remove?.();l.closeTooltip?.();});
   mapApi.map.removeLayer(layer);layer=null;
 }
 cleanupPopups();
 $('legend')?.querySelectorAll('.duesseldorf-other-legend').forEach(el=>el.remove());
 const old=$('legend')?.querySelector('.duesseldorf-count-legend');if(old)old.hidden=false;
 panel.hidden=true;if(originalPanel)originalPanel.hidden=false;
 document.querySelector('.mapwrap')?.classList.remove('duesseldorf-more-focus');
 selected=null;
}
function disable(restore=true){
 if(!active)return;
 active=false;epoch++;closeLayers();
 if(restore&&parent?.getActive?.()){
   const old=parent.getLayer();
   if(old&&!mapApi.map.hasLayer(old))mapApi.map.addLayer(old);
   mapApi.map.fitBounds(L.geoJSON(parent.getData()).getBounds(),{padding:[30,30],maxZoom:10,animate:false});
 }
 selectedDistrict=null;
}
function colors(){
 const arr=geo.features.map(local).slice().sort((a,b)=>a-b);
 const breaks=[1,2,3,4,5,6].map(i=>arr[Math.max(0,Math.ceil(arr.length*i/7)-1)]);
 return breaks;
}
let thresholds=[];
function style(f){
 const n=local(f),i=thresholds.findIndex(v=>n<=v);
 return {pane:'supplementaryPane',color:'#6d497a',opacity:.9,weight:.7,
         fillColor:PAL[i<0?6:i],fillOpacity:.86};
}
function popup(f){
 const p=f.properties,history=geo.meta.source_years;
 const annual=history.map(y=>'<span><small>'+y+'年</small><b>'+fmt(p.metrics[metric][String(y)])+'</b></span>').join('');
 const categories=listed().map(k=>'<span><small>'+esc(label(k))+'</small><b>'+fmt(p.metrics[k]['2025'])+'</b></span>').join('');
 const y25=local(f),y24=p.metrics[metric]['2024'],delta=y25-y24;
 return '<div class="supp-popup"><strong>'+esc(p.name)+'</strong><div class="supp-big">'+fmt(y25)+' 起</div>'+
 '<div>'+esc(label(metric))+' · 2025年登记案件（非犯罪率）</div>'+
 '<div class="supp-change">与2024年相比：'+(delta>0?'+':'')+fmt(delta)+' 起</div>'+
 '<div class="supp-history duesseldorf-year-list">'+annual+'</div>'+
 '<div class="supp-history duesseldorf-more-metrics">'+categories+'</div>'+
 '<small>此类统计仅适用于警方明确列出的第'+Number(selectedDistrict)+'区街区；其他市辖区数据不能估算。案件数不等于居民受害风险。</small></div>';
}
function legend(){
 const host=$('legend');if(!host)return;
 host.querySelectorAll('.duesseldorf-other-legend').forEach(e=>e.remove());
 const note=selectedDistrict==='09'?'第9区原始报告仅公开街头犯罪和住宅入室盗窃两类街区数据。':
   '第7区原始警方报告公开8类街区案件数量。';
 const txt='<div class="legend-block supp-city-legend duesseldorf-other-legend">'+
 '<div class="legend-title">杜塞尔多夫第'+Number(selectedDistrict)+'区 · '+esc(label(metric))+'</div>'+
 '<div>2025年登记案件绝对数（起），非每10万人率</div>'+
 '<div class="scale">'+PAL.map(c=>'<span style="background:'+c+'"></span>').join('')+'</div>'+
 '<div class="legend-labels">'+thresholds.map(n=>'<span>≤'+fmt(n)+'</span>').join('')+'<span>更高</span></div>'+
 '<div class="supp-warning">⚠ '+note+'不能填充未报告的罪种，也不能据绝对案件数直接判断风险。</div></div>';
 host.insertAdjacentHTML('beforeend',txt);
}
function showPanel(){
 const m=geo.meta,total=m.mapped_by_category[metric]['2025'];
 const cityNote=selectedDistrict==='07'
  ? '该区5街区全部登记案件合计2,490起，与杜塞尔多夫10区警方表格核对一致。'
  : '第9区没有官方街区全部犯罪表格；只有此处列出的两类指标。';
 const cards=geo.features.map(f=>'<div><span>'+esc(f.properties.name)+'</span><strong>'+fmt(local(f))+' 起</strong></div>').join('');
 panel.innerHTML='<div class="supp-city-head"><strong>杜塞尔多夫 · 第'+Number(selectedDistrict)+'区街区地图</strong>'+
 '<button type="button" id="duesseldorfOtherClose" aria-label="关闭本区详细地图">×</button></div>'+
 '<div class="supp-city-sub">'+geo.features.map(f=>esc(f.properties.name)).join(' · ')+'</div>'+
 '<label class="bremen-select-label" for="duesseldorfOtherMetric">2025年犯罪类别</label>'+
 '<select id="duesseldorfOtherMetric" class="bremen-select">'+listed().map(k=>
   '<option value="'+k+'"'+(k===metric?' selected':'')+'>'+esc(label(k))+'</option>').join('')+'</select>'+
 '<div class="supp-city-numbers"><span><b>'+fmt(total)+'</b><small>已列街区案件数（起）</small></span>'+
 '<span><b>'+geo.features.length+'</b><small>官方街区数量</small></span></div>'+
 '<div class="bv6-local-table">'+cards+'</div>'+
 '<p>'+cityNote+' 色阶仅表示<b>案件数量</b>，不提供未经核实的人均犯罪率。点击色块查看'+m.source_years.join('—')+'年的历史。</p>'+
 '<button class="bv6-back" id="duesseldorfOtherBack" type="button">← 返回杜塞尔多夫10区</button>'+
 '<div class="supp-city-source"><a target="_blank" rel="noopener noreferrer" href="'+esc(m.police_source)+'">警方原始2025年统计PDF↗</a> · '+
 '<a target="_blank" rel="noopener noreferrer" href="'+esc(m.municipal_geometry_source)+'">2025官方街区边界↗</a></div>';
 panel.hidden=false;
 $('duesseldorfOtherClose').onclick=()=>disable(true);
 $('duesseldorfOtherBack').onclick=()=>disable(true);
 $('duesseldorfOtherMetric').onchange=e=>{metric=e.target.value;redraw();};
}
function redraw(){
 if(!active||!geo)return;
 thresholds=colors();
 selected=null;
 if(layer)layer.eachLayer(l=>layer.resetStyle(l));
 legend();showPanel();
}
async function load(district){
 const registry=await fetch('data/city_count_layers.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('official city registry '+r.status);return r.json();});
 registered=registry.layers?.find(c=>c.id==='duesseldorf')?.neighbourhood_expansions||[];
 const r=registered.find(c=>c.parent_stadtbezirk===district);
 if(!r||!['07','09'].includes(district))throw Error('Düsseldorf neighborhood source not approved');
 const data=await fetch(r.file,{cache:'no-store'}).then(resp=>{if(!resp.ok)throw Error('source geoJSON '+resp.status);return resp.json();});
 if(data.meta?.status!=='supplementary_bv_additional_neighbourhood_cases_only'||
    data.meta.parent_stadtbezirk!==district||
    data.meta.neighbourhoods!==r.region_count||
    data.meta.categories?.length!==r.category_count||
    data.features?.length!==r.region_count||
    data.meta.scope!==r.metric_scope||
    data.meta.source_years?.join(',')!==r.history_years.join(','))throw Error('Unapproved source area/category mismatch');
 const keys=data.meta.categories,ys=data.meta.source_years.map(String);
 for(const f of data.features){
   if(f.properties.parent_stadtbezirk!==district ||
       Object.keys(f.properties.metrics||{}).length!==keys.length)throw Error('Misplaced public area');
   for(const k of keys){
     const v=f.properties.metrics[k];
     if(!v||v.rate!==null||ys.some(y=>!Number.isInteger(v[y])||v[y]<0))
        throw Error('Invalid/missing original 2025 local cases: '+k);
   }
 }
 for(const k of keys)for(const y of ys)
   if(data.features.reduce((s,f)=>s+f.properties.metrics[k][y],0)!==data.meta.mapped_by_category[k][y])
      throw Error('Official BV'+district+' category/count reconciliation failed');
 geo=data;
}
async function activate(district){
 if(!['07','09'].includes(district)||!parent?.getActive?.())return;
 if(active){disable(true);if(!parent.getActive())return;}
 const id=++epoch;
 await load(district);
 if(id!==epoch||!parent.getActive())return;
 window.__DUESSELDORF_BV6__?.disable?.(false);
 selectedDistrict=district;
 metric=geo.meta.categories.includes('street_crime')?'street_crime':geo.meta.categories[0];
 active=true;selected=null;
 originalPanel=$('duesseldorfCountPanel');
 const oldLayer=parent.getLayer();
 if(oldLayer){
   oldLayer.eachLayer(l=>{l.closePopup?.();l.getPopup?.()?.remove?.();l.closeTooltip?.();});
   if(mapApi.map.hasLayer(oldLayer))mapApi.map.removeLayer(oldLayer);
 }
 cleanupPopups();
 if(originalPanel)originalPanel.hidden=true;
 const old=$('legend')?.querySelector('.duesseldorf-count-legend');if(old)old.hidden=true;
 if(!mapApi.map.getPane('supplementaryPane')){
    mapApi.map.createPane('supplementaryPane');mapApi.map.getPane('supplementaryPane').style.zIndex=275;
 }
 renderer=renderer||L.svg({pane:'supplementaryPane',padding:.2});
 thresholds=colors();
 layer=L.geoJSON(geo,{pane:'supplementaryPane',renderer,style,
    onEachFeature:(f,l)=>{
      l.bindTooltip(()=>'<b>'+esc(f.properties.name)+'</b><div>'+esc(label(metric))+'：'+fmt(local(f))+'起（非犯罪率）</div>',{sticky:true});
      l.bindPopup(()=>popup(f),{maxWidth:400});
      l.on('mouseover',()=>{if(selected!==l)l.setStyle({color:'#fff',weight:1.8})});
      l.on('mouseout',()=>{if(selected!==l&&layer)layer.resetStyle(l)});
      l.on('click',()=>{if(selected&&layer)layer.resetStyle(selected);selected=l;l.setStyle({color:'#fff',weight:2.2})});
    }}).addTo(mapApi.map);
 document.querySelector('.mapwrap')?.classList.add('duesseldorf-more-focus');
 mapApi.map.fitBounds(layer.getBounds(),{padding:[34,34],maxZoom:12,animate:false});
 legend();showPanel();
}
async function boot(){
 for(let n=0;n<110&&(!window.__CRIME_MAP__||!window.__DUESSELDORF_COUNT_MAP__);n++)
    await new Promise(r=>setTimeout(r,80));
 mapApi=window.__CRIME_MAP__;parent=window.__DUESSELDORF_COUNT_MAP__;
 if(!mapApi||!parent)return;
 document.querySelector('.mapwrap')?.appendChild(panel);
 window.__DUESSELDORF_OTHER_MAP__=Object.freeze({activate,disable,
   getActive:()=>active&&!!layer,getDistrict:()=>selectedDistrict,
   getMetric:()=>metric,getLayer:()=>layer,getData:()=>geo});
}
boot().catch(e=>console.error('Düsseldorf BV7/BV9 official detail module',e));
})();