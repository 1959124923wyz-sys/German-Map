/* Düsseldorf PP official PKS 2022-2025: ten Stadtbezirke total offense CASE COUNTS.
 * NOT a crime rate; do not paint unassigned 1298 citywide cases. */
(()=>{'use strict';
const $=id=>document.getElementById(id);
const fmt=v=>Number(v).toLocaleString('zh-CN');
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const years=['2022','2023','2024','2025'];
const palette=['#e5f5ef','#cbebdb','#a7dcc4','#76c9a4','#50b184','#2d9267','#156443'];
const box=document.createElement('section');box.id='duesseldorfCountPanel';box.className='supp-city-info duesseldorf-count-panel';box.hidden=true;
let api,conf,geo,bounds,layer,renderer,active=false,epoch=0,selected=null,cut=[];
const cases=f=>f.properties.crime_total['2025'];
const cuts=()=>{const vals=geo.features.map(cases).sort((a,b)=>a-b);return [1,2,3,4,5,6].map(i=>vals[Math.max(0,Math.ceil(vals.length*i/7)-1)]);};
const fill=f=>{let i=cut.findIndex(v=>cases(f)<=v);if(i<0)i=6;return palette[i];};
const style=f=>({pane:'supplementaryPane',color:'#356856',weight:.85,opacity:.88,fillColor:fill(f),fillOpacity:.86});
function popup(f){
 const p=f.properties,v=p.crime_total,d=v['2025']-v['2024'];
 return '<div class="supp-popup"><strong>'+esc(p.name)+'</strong><div class="supp-big">'+fmt(cases(f))+' 起</div>'+
  '<div>2025年全部登记犯罪案件（绝对数，非犯罪率）</div>'+
  '<div class="supp-change">相比2024年：'+(d>0?'+':'')+fmt(d)+' 起</div>'+
  '<div class="supp-history duesseldorf-year-list">'+years.map(y=>'<span><small>'+y+'年</small><b>'+fmt(v[y])+'</b></span>').join('')+'</div>'+
  '<small>官方警方公布的统计区案件数。10区合计与全市总数存在差额，不按面积或人口分摊。</small></div>';
}
function clear(){
 window.__DUESSELDORF_BV6__?.disable?.(false);
 if(!api)return;
 if(layer){api.map.removeLayer(layer);layer=null;}
 selected=null;box.hidden=true;api.setCountyFocus?.(null);
 document.querySelector('.mapwrap')?.classList.remove('supp-city-focus','duesseldorf-count-focus');
 $('legend')?.querySelectorAll('.duesseldorf-count-legend').forEach(x=>x.remove());
 const btn=$('focusDuesseldorfCount');if(btn){btn.classList.remove('active');btn.setAttribute('aria-pressed','false');}
}
function disable(){active=false;epoch++;clear();}
function legend(){
 const root=$('legend');if(!root)return;
 root.querySelectorAll('.duesseldorf-count-legend').forEach(x=>x.remove());
 root.insertAdjacentHTML('beforeend','<div class="legend-block supp-city-legend duesseldorf-count-legend">'+
 '<div class="legend-title">杜塞尔多夫 · 全部登记犯罪</div>'+
 '<div>2025年10个Stadtbezirke · 绝对案件数（起）</div>'+
 '<div class="scale">'+palette.map(c=>'<span style="background:'+c+'"></span>').join('')+'</div>'+
 '<div class="legend-labels">'+cut.map(v=>'<span>≤'+fmt(v)+'</span>').join('')+'<span>更高</span></div>'+
 '<div class="supp-warning">⚠ 非每10万人犯罪率。全市与10区汇总相差'+
 fmt(geo.meta.undistributed_by_year['2025'])+'起，未分配到任何色块；区域案件数不代表居民受害概率。</div></div>');
}
function panel(){
 const m=geo.meta,d=m.mapped_by_year['2025'];
 box.innerHTML='<div class="supp-city-head"><strong>杜塞尔多夫 Düsseldorf · 全部案件</strong>'+
 '<button id="duesseldorfCountClose" type="button" aria-label="退出杜塞尔多夫区级案件地图">×</button></div>'+
 '<div class="supp-city-sub">警方官方统计 · 2022—2025年 · 10个市辖区</div>'+
 '<div class="supp-city-numbers"><span><b>'+fmt(d)+'</b><small>2025年10区案件合计</small></span>'+
 '<span><b>'+fmt(m.undistributed_by_year['2025'])+'</b><small>全市与分区统计差额</small></span></div>'+
 '<p>官方全市2025年共'+fmt(m.city_by_year['2025'])+'起，10区已统计'+fmt(d)+'起。</p>'+
 '<p>点按地图色块查看该区<b>2022—2025年逐年案件数</b>与2024—2025变化。此处展示的都是原始数量，<b>不是人均犯罪率</b>。</p>'+
 '<button id="duesseldorfOpenBV6" class="bv6-drilldown" type="button">查看第6区4街区 · 8类犯罪 →</button>'+
 '<div class="supp-city-source"><a href="'+esc(conf.source_url)+'" target="_blank" rel="noopener noreferrer">杜塞尔多夫警方原始统计演示 PDF（第2页）↗</a> · '+
 '<a href="'+esc(conf.geometry_url)+'" target="_blank" rel="noopener noreferrer">2025年官方行政边界↗</a></div>';
 box.hidden=false;$('duesseldorfCountClose').onclick=disable;
 $('duesseldorfOpenBV6').onclick=()=>window.__DUESSELDORF_BV6__?.activate?.().catch(
    e=>console.error('BV6 drilldown failed',e));
}
const within=()=>active&&geo&&api.map.getZoom()>=8&&bounds.contains(api.map.getCenter());
function render(){
 if(!active||!geo)return;
 if(!within()){disable();return;}
 if(!api.map.getPane('supplementaryPane')){
   api.map.createPane('supplementaryPane');api.map.getPane('supplementaryPane').style.zIndex=275;
 }
 renderer=renderer||L.svg({pane:'supplementaryPane',padding:.2});
 cut=cuts();
 layer=L.geoJSON(geo,{pane:'supplementaryPane',renderer,style,onEachFeature:(f,l)=>{
   l.bindTooltip(()=>'<b>'+esc(f.properties.name)+'</b><div>2025全部案件：'+fmt(cases(f))+' 起（非犯罪率）</div>',{sticky:true});
   l.bindPopup(()=>popup(f),{maxWidth:370});
   l.on('mouseover',()=>{if(selected!==l)l.setStyle({color:'#fff',weight:1.8,opacity:1})});
   l.on('mouseout',()=>{if(selected!==l&&layer)layer.resetStyle(l)});
   l.on('click',()=>{if(selected&&layer)layer.resetStyle(selected);selected=l;l.setStyle({color:'#fff',weight:2.2,opacity:1})});
 }}).addTo(api.map);
 api.setCountyFocus?.('05111');
 document.querySelector('.mapwrap')?.classList.add('supp-city-focus','duesseldorf-count-focus');
 $('focusDuesseldorfCount')?.classList.add('active');$('focusDuesseldorfCount')?.setAttribute('aria-pressed','true');
 legend();panel();
}
async function load(){
 const registry=await fetch('data/city_count_layers.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('count registry '+r.status);return r.json();});
 conf=registry.layers?.find(x=>x.id==='duesseldorf');
 if(!conf||conf.metric!=='all_offenses_cases_2025_by_stadtbezirk')throw Error('Düsseldorf metric not approved');
 geo=await fetch(conf.file,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Düsseldorf official data '+r.status);return r.json();});
 if(geo.meta?.status!=='supplementary_all_offense_count_only'||
    geo.meta?.metric_scope!=='all_offense_cases_by_police_stadtbezirk_NOT_violence_rates'||
    geo.features?.length!==10)throw Error('Düsseldorf numeric dataset not approved');
 for(const year of years){
   if(geo.features.some(f=>!Number.isInteger(f.properties?.crime_total?.[year])||
                              f.properties.crime_total.rate!==null))throw Error('Düsseldorf includes fake rates/missing cases');
   const sum=geo.features.reduce((s,f)=>s+f.properties.crime_total[year],0);
   if(sum!==geo.meta.mapped_by_year[year]||
      sum+geo.meta.undistributed_by_year[year]!==geo.meta.city_by_year[year])
      throw Error('Düsseldorf official district/year sum drift: '+year);
 }
 bounds=L.geoJSON(geo).getBounds();
}
async function activate(){
 if(active){disable();return;}
 const ticket=++epoch;
 if(!geo)await load();
 if(ticket!==epoch)return;
 window.__KIEL_COUNT_MAP__?.disable?.();
 window.__BREMEN_CATEGORY_MAP__?.disable?.();
 window.__STUTTGART_PUBLIC_MAP__?.disable?.();
 api.clearSelection?.();active=true;
 api.map.fitBounds(bounds,{padding:[30,30],maxZoom:10,animate:false});
 render();
}
async function boot(){
 for(let i=0;i<100&&!window.__CRIME_MAP__;i++)await new Promise(r=>setTimeout(r,80));
 api=window.__CRIME_MAP__;if(!api)return;
 document.querySelector('.mapwrap')?.appendChild(box);
 $('focusDuesseldorfCount')?.addEventListener('click',()=>activate().catch(e=>{disable();console.error('Düsseldorf police PKS layer unavailable',e);}));
 api.map.on('zoomend',()=>{if(active&&!within())disable();});
 api.map.on('moveend',()=>{if(active&&!within())disable();});
 ['viewGermany','focusBerlin','modeViolence','modeProperty'].forEach(k=>$(k)?.addEventListener('click',()=>{if(active)disable();}));
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&active)disable();});
 window.__DUESSELDORF_COUNT_MAP__=Object.freeze({getActive:()=>active&&!!layer,getData:()=>geo,getLayer:()=>layer,disable});
}
boot().catch(e=>console.error('Düsseldorf official local module boot',e));
})();
