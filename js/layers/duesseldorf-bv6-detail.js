/* Official 2025 Düsseldorf BV6 street-level PKS (four Stadtteile, eight categories).
 * Nested drilldown ONLY for Stadtbezirk 6; other city areas have no such metrics.
 * 2022–2025 police CASE COUNTS, NEVER per-capita risk values.
 */
(()=>{'use strict';
const $=id=>document.getElementById(id);
const num=n=>Number(n).toLocaleString('zh-CN');
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const names={
 all_offenses:'全部登记犯罪',
 street_crime:'街头犯罪',
 street_robbery:'道路／广场抢劫',
 street_injury:'道路／广场伤害',
 vehicle_related_theft:'机动车相关盗窃',
 bicycle_theft:'自行车盗窃',
 pickpocketing:'扒窃',
 residential_burglary:'住宅入室盗窃'
};
const metrics=Object.keys(names);
const years=['2022','2023','2024','2025'];
const palette=['#f0ebf8','#d2c8e8','#a99cd3','#7b68b8'];
let mapApi,parent,reg,geo,layer,active=false,metric='street_crime',renderer=null,ticket=0,selected=null,originalPanel=null;
const panel=document.createElement('section');panel.id='duesseldorfBV6Panel';panel.className='supp-city-info duesseldorf-bv6-panel';panel.hidden=true;
const value=f=>f.properties.metrics[metric]['2025'];
const color=f=>{
 const sorted=geo.features.map(value).sort((a,b)=>a-b);
 return palette[Math.min(3,sorted.filter(n=>n<value(f)).length)];
};
const style=f=>({pane:'supplementaryPane',color:'#554683',opacity:1,weight:.85,fillOpacity:.87,fillColor:color(f)});
const metricCases=(p,k,y)=>p.metrics[k][y];
function clearPopupPane(){
 if(!mapApi)return;
 mapApi.map.closePopup();
 const pane=mapApi.map.getPanes().popupPane;
 // Leaflet popup instances from synthetic clicks / deactivated geometry
 // can retain stale DOM after a layer is removed. Remove the old popup
 // containers on the only two transitions where we replace full overlays.
 // Their popup objects were first closePopup()/remove()'d.
 if(pane)pane.querySelectorAll('.leaflet-popup').forEach(node=>node.remove());
}
function popup(f){
 const p=f.properties,m=p.metrics[metric],diff=m['2025']-m['2024'];
 return '<div class="supp-popup"><strong>'+esc(p.name)+'</strong><div class="supp-big">'+num(m['2025'])+' 起</div>'+
 '<div>2025年 '+esc(names[metric])+' · 第6区官方街区案件数量（非犯罪率）</div>'+
 '<div class="supp-change">相比2024年：'+(diff>0?'+':'')+num(diff)+' 起</div>'+
 '<div class="supp-history duesseldorf-year-list">'+years.map(y=>'<span><small>'+y+'年</small><b>'+num(m[y])+'</b></span>').join('')+'</div>'+
 '<div class="supp-history bv6-categories">'+metrics.map(k=>'<span><small>'+esc(names[k])+'</small><b>'+num(metricCases(p,k,'2025'))+'</b></span>').join('')+'</div>'+
 '<small>仅代表第6区的真实四个Stadtteile；其他市辖区没有这些指标的街区级数据。分类可能存在包含关系，不能相加。</small></div>';
}
function hide(){
 if(layer){
   layer.eachLayer(l=>{l.closePopup?.();l.getPopup?.()?.remove?.();l.closeTooltip?.();});
   mapApi.map.removeLayer(layer);layer=null;
 }
 clearPopupPane();
 $('legend')?.querySelectorAll('.duesseldorf-bv6-legend').forEach(x=>x.remove());
 panel.hidden=true;
 if(originalPanel)originalPanel.hidden=false;
 const old=$('legend')?.querySelector('.duesseldorf-count-legend');if(old)old.hidden=false;
 document.querySelector('.mapwrap')?.classList.remove('duesseldorf-bv6-focus');
 selected=null;
}
function disable(restore=true){
 if(!active)return;
 active=false;ticket++;
 hide();
 if(restore && parent?.getActive?.()){
   const original=parent.getLayer();
   if(original&&!mapApi.map.hasLayer(original))mapApi.map.addLayer(original);
   mapApi.map.fitBounds(L.geoJSON(parent.getData()).getBounds(),{padding:[30,30],maxZoom:10,animate:false});
 }
}
function legend(){
 const host=$('legend');if(!host)return;
 host.querySelectorAll('.duesseldorf-bv6-legend').forEach(x=>x.remove());
 const data=geo.meta.mapped_categories[metric],sorted=geo.features.map(value).sort((a,b)=>a-b);
 host.insertAdjacentHTML('beforeend','<div class="legend-block supp-city-legend duesseldorf-bv6-legend">'+
 '<div class="legend-title">杜塞尔多夫·第6区4街区 · '+esc(names[metric])+'</div>'+
 '<div>警方登记案件 · 2025年绝对数（起）</div>'+
 '<div class="scale">'+palette.map(c=>'<span style="background:'+c+'"></span>').join('')+'</div>'+
 '<div class="legend-labels">'+sorted.map(n=>'<span>'+num(n)+'</span>').join('')+'</div>'+
 '<div class="supp-warning">⚠ 只有第6区的4个街区有这8项官方犯罪分类。其他9个市辖区不能按同一指标涂色。没有人均犯罪率。</div></div>');
}
function showPanel(){
 const m=geo.meta,t=m.mapped_categories[metric],total=t['2025'];
 panel.innerHTML='<div class="supp-city-head"><strong>杜塞尔多夫 · 第6区街区细分</strong>'+
 '<button id="duesseldorfBV6Close" type="button" aria-label="退出街区地图并返回10个市辖区">×</button></div>'+
 '<div class="supp-city-sub">Lichtenbroich · Unterrath · Rath · Mörsenbroich</div>'+
 '<label class="bremen-select-label" for="duesseldorfBV6Metric">选择犯罪类别（2025）</label>'+
 '<select id="duesseldorfBV6Metric" class="bremen-select">'+metrics.map(k=>
 '<option value="'+k+'"'+(metric===k?' selected':'')+'>'+esc(names[k])+'</option>').join('')+'</select>'+
 '<div class="supp-city-numbers"><span><b>'+num(total)+'</b><small>四街区此项案件合计（起）</small></span>'+
 '<span><b>'+num(geo.meta.mapped_categories.all_offenses['2025'])+'</b><small>第6区全部登记案件（起）</small></span></div>'+
 '<div class="bv6-local-table">'+geo.features.map(f=>'<div><span>'+esc(f.properties.name)+'</span><strong>'+num(value(f))+' 起</strong></div>').join('')+'</div>'+
 '<p>点击色块可查看2022—2025年记录以及8类指标。颜色只比较这4个街区的<b>绝对数量</b>，不代表个人受害风险。</p>'+
 '<p class="supp-warning">其他9个市辖区没有同口径的街区分类数据；退出后可返回全市10区的“全部案件”地图。</p>'+
 '<button id="duesseldorfBV6Back" class="bv6-back" type="button">← 返回杜塞尔多夫10区</button>'+
 '<div class="supp-city-source"><a href="'+esc(m.police_source)+'" target="_blank" rel="noopener noreferrer">警方原始2025统计 PDF（第4—11页）↗</a> · '+
 '<a href="'+esc(m.municipal_geometry_source)+'" target="_blank" rel="noopener noreferrer">市政府2025年街区边界（DL-DE Zero 2.0）↗</a></div>';
 panel.hidden=false;
 $('duesseldorfBV6Close').onclick=()=>disable(true);
 $('duesseldorfBV6Back').onclick=()=>disable(true);
 $('duesseldorfBV6Metric').onchange=e=>{metric=e.target.value;redraw();};
}
function redraw(){
 if(!active||!geo)return;
 selected=null;
 if(layer)layer.eachLayer(l=>layer.resetStyle(l));
 legend();showPanel();
}
async function load(){
 const regData=await fetch('data/city_count_layers.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('local district registry '+r.status);return r.json()});
 reg=regData.layers?.find(x=>x.id==='duesseldorf')?.drilldown;
 if(!reg||reg.parent_stadtbezirk!=='06'||reg.region_count!==4||reg.category_count!==8)
    throw Error('Unapproved city BV6 detail');
 geo=await fetch(reg.file,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('BV6 official data '+r.status);return r.json()});
 const m=geo.meta;
 if(m?.status!=='supplementary_bv6_neighbourhood_cases_only'||
    m.scope!=='DUESSELDORF_STADTBEZIRK_06_ONLY_NOT_CITYWIDE'||
    geo.features?.length!==4||m.mapped_categories.all_offenses['2025']!==5097||
    m.polygons_overlap_m2>5||m.difference_parent_stadtbezirk_m2>1000)
      throw Error('BV6 mapped data integrity check failed');
 for(const f of geo.features){
   if(f.properties.parent_stadtbezirk!=='06'||Object.keys(f.properties.metrics||{}).length!==8)
     throw Error('BV6 original area/metrics mismatch');
   for(const k of metrics){
     const entry=f.properties.metrics[k];
     if(!entry||entry.rate!==null||years.some(y=>!Number.isInteger(entry[y])||entry[y]<0))
        throw Error('Fake or missing 2022-2025 BV6 metric '+k);
   }
 }
 for(const k of metrics)for(const y of years){
   if(geo.features.reduce((v,f)=>v+f.properties.metrics[k][y],0)!==m.mapped_categories[k][y])
     throw Error('BV6 area sum differs from original police source '+k+y);
 }
}
async function activate(){
 if(active||!parent?.getActive?.())return;
 window.__DUESSELDORF_OTHER_MAP__?.disable?.(false);
 const t=++ticket;
 if(!geo)await load();
 if(t!==ticket||!parent.getActive())return;
 active=true;
 originalPanel=$('duesseldorfCountPanel');
 mapApi.map.closePopup();
 const oldLayer=parent.getLayer();
 if(oldLayer){
   // Explicitly close bound Leaflet popups/tooltips before hiding the
   // district vector layer. Otherwise a synthetic or ordinary polygon
   // click can leave the old popup DOM behind the Stadtteil popup.
   oldLayer.eachLayer(l=>{
      l.closePopup?.();
      l.getPopup?.()?.remove?.();
      l.closeTooltip?.();
   });
   if(mapApi.map.hasLayer(oldLayer))mapApi.map.removeLayer(oldLayer);
 }
 clearPopupPane();
 if(originalPanel)originalPanel.hidden=true;
 const oldLegend=$('legend')?.querySelector('.duesseldorf-count-legend');
 if(oldLegend)oldLegend.hidden=true;
 if(!mapApi.map.getPane('supplementaryPane')){
   mapApi.map.createPane('supplementaryPane');mapApi.map.getPane('supplementaryPane').style.zIndex=275;
 }
 renderer=renderer||L.svg({pane:'supplementaryPane',padding:.2});
 layer=L.geoJSON(geo,{pane:'supplementaryPane',renderer,style,onEachFeature:(f,l)=>{
   l.bindTooltip(()=>'<b>'+esc(f.properties.name)+'</b><div>'+esc(names[metric])+'：'+num(value(f))+' 起（非犯罪率）</div>',{sticky:true});
   l.bindPopup(()=>popup(f),{maxWidth:400});
   l.on('mouseover',()=>{if(selected!==l)l.setStyle({color:'#fff',weight:1.9})});
   l.on('mouseout',()=>{if(selected!==l&&layer)layer.resetStyle(l)});
   l.on('click',()=>{if(selected&&layer)layer.resetStyle(selected);selected=l;l.setStyle({color:'#fff',weight:2.1})});
 }}).addTo(mapApi.map);
 document.querySelector('.mapwrap')?.classList.add('duesseldorf-bv6-focus');
 mapApi.map.fitBounds(layer.getBounds(),{padding:[34,34],maxZoom:12,animate:false});
 legend();showPanel();
}
async function boot(){
 for(let i=0;i<100&&!window.__CRIME_MAP__;i++)await new Promise(r=>setTimeout(r,80));
 mapApi=window.__CRIME_MAP__;parent=window.__DUESSELDORF_COUNT_MAP__;
 if(!mapApi||!parent)return;
 document.querySelector('.mapwrap')?.appendChild(panel);
 window.__DUESSELDORF_BV6__=Object.freeze({activate,disable,
   getActive:()=>active&&!!layer,getLayer:()=>layer,getData:()=>geo,getMetric:()=>metric});
}
boot().catch(e=>console.error('Düsseldorf BV6 module boot failed',e));
})();
