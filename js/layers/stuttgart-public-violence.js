/* Stuttgart 2025 public-space Gewaltkriminalität: official local CASE COUNTS.
 * Independent from nationwide general-violence risk rates. */
(()=>{'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=v=>Number(v).toLocaleString('zh-CN');
const names={public_violence:'公共场所暴力犯罪',public_robbery:'公共场所抢劫／暴力勒索',public_serious_injury:'公共场所危险／严重伤害'};
const metrics=Object.keys(names);
const palette=['#f2e9f3','#e6cfe9','#d9b5df','#c596d1','#a774bf','#87549f','#64397e'];
let mapApi,conf,geo,bounds,layer,renderer,metric='public_violence',active=false,selected=null,epoch=0,q=[];
const panel=document.createElement('section');panel.id='stuttgartViolencePanel';panel.className='supp-city-info bremen-category-panel stuttgart-violence-panel';panel.hidden=true;
const cases=f=>f.properties.metrics[metric]['2025'];
const quantiles=()=>{const sorted=geo.features.map(cases).sort((a,b)=>a-b);return [1,2,3,4,5,6].map(i=>sorted[Math.max(0,Math.ceil(sorted.length*i/7)-1)]);};
const style=f=>({pane:'supplementaryPane',color:'#66476c',opacity:.85,weight:.7,fillOpacity:.85,fillColor:palette[Math.max(0,q.findIndex(n=>cases(f)<=n))<0?6:(q.findIndex(n=>cases(f)<=n)<0?6:q.findIndex(n=>cases(f)<=n))]});
function popup(f){
 const p=f.properties,items=metrics.map(k=>'<span><small>'+esc(names[k])+'</small><b>'+fmt(p.metrics[k]['2025'])+'</b></span>').join('');
 return '<div class="supp-popup"><strong>'+esc(p.name)+'</strong><div class="supp-big">'+fmt(cases(f))+' 起</div>'+
 '<div>2025 · '+esc(names[metric])+' · 登记案件数量</div><div class="supp-history stuttgart-metrics">'+items+'</div>'+
 '<small>仅限公共场所发生的犯罪。不是全国地图的全部场景暴力犯罪，也不是居民人均犯罪率。</small></div>';
}
function clear(){
 if(!mapApi)return;
 if(layer){mapApi.map.removeLayer(layer);layer=null;}
 selected=null;panel.hidden=true;mapApi.setCountyFocus?.(null);
 document.querySelector('.mapwrap')?.classList.remove('supp-city-focus','stuttgart-public-focus');
 $('legend')?.querySelectorAll('.stuttgart-public-legend').forEach(x=>x.remove());
 const btn=$('focusStuttgartViolence');if(btn){btn.classList.remove('active');btn.setAttribute('aria-pressed','false');}
}
function disable(){active=false;epoch++;clear();}
function legend(){
 const r=$('legend');if(!r)return;
 r.querySelectorAll('.stuttgart-public-legend').forEach(x=>x.remove());
 r.insertAdjacentHTML('beforeend','<div class="legend-block supp-city-legend stuttgart-public-legend">'+
  '<div class="legend-title">斯图加特 · '+esc(names[metric])+'</div><div>2025年公共场所犯罪案件绝对数（起）</div>'+
  '<div class="scale">'+palette.map(c=>'<span style="background:'+c+'"></span>').join('')+'</div>'+
  '<div class="legend-labels">'+q.map(n=>'<span>≤'+fmt(n)+'</span>').join('')+'<span>更高</span></div>'+
  '<div class="supp-warning">⚠ 仅限公共场所；不是全部暴力犯罪或每10万人率。全市统计与23区合计相差'+fmt(geo.meta.unlocated_city_cases[metric])+'起，差额不分配到街区。</div></div>');
}
function showPanel(){
 const mapped=geo.meta.mapped_totals[metric],city=geo.meta.city_totals[metric];
 panel.innerHTML='<div class="supp-city-head"><strong>斯图加特 Stuttgart · 公共场所暴力</strong>'+
 '<button id="stuttgartViolenceClose" type="button" aria-label="关闭斯图加特专题">×</button></div>'+
 '<div class="supp-city-sub">2025警方统计 · 州议会内政部门正式答复 · 23个市辖区</div>'+
 '<label for="stuttgartViolenceMetric" class="bremen-select-label">犯罪类别</label>'+
 '<select id="stuttgartViolenceMetric" class="bremen-select">'+metrics.map(k=>'<option value="'+k+'"'+(k===metric?' selected':'')+'>'+esc(names[k])+'</option>').join('')+'</select>'+
 '<div class="supp-city-numbers"><span><b>'+fmt(mapped)+'</b><small>23区已对应案件（起）</small></span>'+
 '<span><b>'+fmt(city-mapped)+'</b><small>全市与分区统计差额（起）</small></span></div>'+
 '<p>全市共'+fmt(city)+'起。<b>仅统计公共场所</b>；按登记案件绝对数着色，不能当作居民的犯罪受害风险或与全国暴力犯罪率直接比较。</p>'+
 '<div class="supp-city-source"><a target="_blank" rel="noopener noreferrer" href="'+esc(conf.source_url)+'">州议会2025官方统计 PDF↗</a> · '+
 '<a target="_blank" rel="noopener noreferrer" href="'+esc(conf.geometry_url)+'">市政府官方23区边界（CC BY 4.0）↗</a></div>';
 panel.hidden=false;
 $('stuttgartViolenceClose').onclick=disable;
 $('stuttgartViolenceMetric').onchange=e=>{metric=e.target.value;redraw();};
}
function redraw(){
 if(!active||!geo)return;
 q=quantiles();if(layer){selected=null;layer.eachLayer(l=>layer.resetStyle(l));}
 legend();showPanel();
}
const inCity=()=>active&&geo&&mapApi.map.getZoom()>=8&&bounds.contains(mapApi.map.getCenter());
function render(){
 if(!active||!geo)return;
 if(!inCity()){disable();return;}
 if(layer){redraw();return;}
 if(!mapApi.map.getPane('supplementaryPane')){
   mapApi.map.createPane('supplementaryPane');mapApi.map.getPane('supplementaryPane').style.zIndex=275;
 }
 renderer=renderer||L.svg({pane:'supplementaryPane',padding:.2});q=quantiles();
 layer=L.geoJSON(geo,{pane:'supplementaryPane',renderer,style,onEachFeature:(f,l)=>{
   l.bindTooltip(()=>'<b>'+esc(f.properties.name)+'</b><div>'+esc(names[metric])+'：'+fmt(cases(f))+'起（非犯罪率）</div>',{sticky:true});
   l.bindPopup(()=>popup(f),{maxWidth:370});
   l.on('mouseover',()=>{if(selected!==l)l.setStyle({color:'#fff',weight:1.8,opacity:1})});
   l.on('mouseout',()=>{if(selected!==l&&layer)layer.resetStyle(l)});
   l.on('click',()=>{if(selected&&layer)layer.resetStyle(selected);selected=l;l.setStyle({color:'#fff',weight:2,opacity:1})});
 }}).addTo(mapApi.map);
 mapApi.setCountyFocus?.('08111');document.querySelector('.mapwrap')?.classList.add('supp-city-focus','stuttgart-public-focus');
 $('focusStuttgartViolence')?.classList.add('active');$('focusStuttgartViolence')?.setAttribute('aria-pressed','true');
 legend();showPanel();
}
async function load(){
 const registry=await fetch('data/city_count_layers.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('city registry '+r.status);return r.json();});
 conf=registry.layers?.find(x=>x.id==='stuttgart');
 if(!conf||conf.metric!=='public_space_violence_cases')throw Error('Stuttgart supplementary category not approved');
 geo=await fetch(conf.file,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Stuttgart data '+r.status);return r.json();});
 if(geo.meta?.status!=='supplementary_public_violence_count_only'||
    geo.meta?.metric_scope!=='public_space_violent_crime_only_NOT_all_violence'||
    geo.features?.length!==23||
    geo.features.some(f=>metrics.some(k=>!Number.isInteger(f.properties.metrics?.[k]?.['2025'])||f.properties.metrics[k].rate!==null)))
      throw Error('Stuttgart government 23-area data integrity failed');
 for(const k of metrics){
   const sum=geo.features.reduce((n,f)=>n+f.properties.metrics[k]['2025'],0);
   if(sum!==geo.meta.mapped_totals[k]||sum+geo.meta.unlocated_city_cases[k]!==geo.meta.city_totals[k])
      throw Error('Stuttgart official city district total discrepancy: '+k);
 }
 bounds=L.geoJSON(geo).getBounds();
}
async function activate(){
 if(active){disable();return;}
 const ticket=++epoch;if(!geo)await load();if(ticket!==epoch)return;
 window.__BREMEN_CATEGORY_MAP__?.disable?.();window.__KIEL_COUNT_MAP__?.disable?.();
 window.__DUESSELDORF_COUNT_MAP__?.disable?.();
 mapApi.clearSelection?.();active=true;
 mapApi.map.fitBounds(bounds,{padding:[32,32],maxZoom:10,animate:false});render();
}
async function boot(){
 for(let n=0;n<100&&!window.__CRIME_MAP__;n++)await new Promise(r=>setTimeout(r,80));
 mapApi=window.__CRIME_MAP__;if(!mapApi)return;
 document.querySelector('.mapwrap')?.appendChild(panel);
 $('focusStuttgartViolence')?.addEventListener('click',()=>activate().catch(err=>{disable();console.error('Stuttgart official overlay',err);}));
 mapApi.map.on('zoomend',()=>{if(active&&!inCity())disable()});
 mapApi.map.on('moveend',()=>{if(active&&!inCity())disable()});
 ['viewGermany','focusBerlin','modeViolence','modeProperty'].forEach(k=>$(k)?.addEventListener('click',()=>{if(active)disable()}));
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&active)disable();});
 window.__STUTTGART_PUBLIC_MAP__=Object.freeze({getActive:()=>active&&!!layer,getMetric:()=>metric,getLayer:()=>layer,getData:()=>geo,disable});
}
boot().catch(e=>console.error('Stuttgart supplementary boot',e));
})();
