/* Official count-only supplemental city layer.
   No nationwide crime rate semantics, independent from violence/property UI. */
(()=>{'use strict';
const $=id=>document.getElementById(id);
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>Number(n).toLocaleString('zh-CN');
const colors=['#edf3fb','#d7e7f6','#b8d6ea','#8dbbd9','#5c95c4','#3473ac','#174b81'];
let api=null,cfg=null,data=null,layer=null,epoch=0,enabled=false,selected=null,renderer=null;
const localInfo=document.createElement('section');
localInfo.id='suppCityInfo';
localInfo.className='supp-city-info';
localInfo.hidden=true;
function breaks(vals){
 const s=vals.slice().sort((a,b)=>a-b);
 return [1,2,3,4,5,6].map(i=>s[Math.min(s.length-1,Math.ceil(i*s.length/7)-1)]);
}
function col(n,b){
 let i=b.findIndex(v=>n<=v);
 return colors[i<0?6:i];
}
function style(f){
 return {pane:'supplementaryPane',color:'#607b96',weight:.8,opacity:.72,
  fillColor:col(f.properties.crime_total.cases,quantiles),fillOpacity:.86};
}
let quantiles=[];
function popup(f){
 const p=f.properties,series=p.annual_cases;
 const prev=series['2024'],curr=series['2025'];
 const delta=curr-prev,sign=delta>0?'+':'';
 const y=Object.keys(series).sort();
 const cells=y.map(k=>'<span><small>'+k+'</small><b>'+fmt(series[k])+'</b></span>').join('');
 return '<div class="supp-popup"><strong>'+esc(p.name)+'</strong><div class="supp-big">'+fmt(curr)+' 起</div>'+
  '<div>2025年全部登记犯罪案件数（不是犯罪率）</div>'+
  '<div class="supp-change">较2024年：'+sign+fmt(delta)+' 起'+(prev>0?'（'+sign+((delta/prev)*100).toFixed(1)+'%）':'')+'</div>'+
  '<div class="supp-history">'+cells+'</div><small>警方年度记录，不代表辖区居民受害概率；商圈、交通和流动人口会影响数量。</small></div>';
}
function legend(){
 const root=$('legend');if(!root)return;
 root.querySelectorAll('.supp-city-legend').forEach(x=>x.remove());
 let cut=quantiles.map(x=>'≤'+fmt(x));
 let html='<div class="legend-block supp-city-legend"><div class="legend-title">基尔街区 · 全部犯罪案件数量</div>'+
 '<div>2025年警方登记案件 · 绝对数（起）</div>'+
 '<div class="scale">'+colors.map(c=>'<span style="background:'+c+'"></span>').join('')+'</div>'+
 '<div class="legend-labels">'+[...cut,'>'+fmt(quantiles[5]||0)].map(x=>'<span>'+x+'</span>').join('')+'</div>'+
 '<div class="supp-warning">⚠ 非每10万人犯罪率，不能直接据此排名治安。817起未能精确定位，未涂入任何街区。</div></div>';
 root.insertAdjacentHTML('beforeend',html);
}
function clear(){
 if(layer){api.map.removeLayer(layer);layer=null}
 selected=null;
 api.setCountyFocus?.(null);
 document.querySelector('.mapwrap')?.classList.remove('supp-city-focus');
 $('legend')?.querySelectorAll('.supp-city-legend').forEach(x=>x.remove());
 localInfo.hidden=true;
 const button=$('focusKielCount');if(button){button.classList.remove('active');button.setAttribute('aria-pressed','false')}
}
function disable(){enabled=false;epoch++;clear()}
function panel(){
 localInfo.innerHTML='<div class="supp-city-head"><strong>基尔 Kiel · 街区全部案件</strong><button id="suppCityClose" aria-label="关闭基尔街区图层" type="button">×</button></div>'+
 '<div class="supp-city-sub">2025年警方登记 · 仅案件数量</div>'+
 '<div class="supp-city-numbers"><span><b>24,341</b><small>30个地图区域</small></span><span><b>817</b><small>不明/无法分区</small></span></div>'+
 '<p>全市合计25,158起。颜色仅按各街区案件数量分级，<b>不能视为人均犯罪风险</b>。</p>'+
 '<div class="supp-city-source"><a href="'+esc(cfg.source_url)+'" target="_blank" rel="noopener noreferrer">警方2025年PKS ↗</a> · <a href="'+esc(cfg.geometry_url)+'" target="_blank" rel="noopener noreferrer">市政府地理数据 (CC BY 4.0) ↗</a></div>';
 localInfo.hidden=false;
 $('suppCityClose').onclick=disable;
}
function shouldShow(){
 return enabled && api.map.getZoom()>=cfg.min_zoom &&
  L.latLngBounds(cfg.bounds).contains(api.map.getCenter());
}
function render(){
 if(!api||!cfg||!data)return;
 if(!shouldShow()){if(layer)clear();return}
 if(layer)return;
 const fs=data.features;
 quantiles=breaks(fs.map(f=>f.properties.crime_total.cases));
 if(!api.map.getPane('supplementaryPane')){
   api.map.createPane('supplementaryPane');
   api.map.getPane('supplementaryPane').style.zIndex=275;
 }
 renderer=renderer||L.svg({pane:'supplementaryPane',padding:.2});
 layer=L.geoJSON(data,{pane:'supplementaryPane',renderer,style,onEachFeature:(f,l)=>{
  l.bindTooltip(()=>'<b>'+esc(f.properties.name)+'</b><div>2025全部案件：'+fmt(f.properties.crime_total.cases)+' 起（非犯罪率）</div>',{sticky:true});
  l.bindPopup(()=>popup(f),{maxWidth:365});
  l.on('mouseover',()=>{if(selected!==l)l.setStyle({color:'#edf7ff',weight:1.6,opacity:1})});
  l.on('mouseout',()=>{if(selected!==l&&layer)layer.resetStyle(l)});
  l.on('click',()=>{if(selected&&layer)layer.resetStyle(selected);selected=l;l.setStyle({color:'#ffffff',weight:2.1,opacity:1})});
 }}).addTo(api.map);
 api.setCountyFocus?.('01002');
 document.querySelector('.mapwrap')?.classList.add('supp-city-focus');
 const button=$('focusKielCount');if(button){button.classList.add('active');button.setAttribute('aria-pressed','true')}
 panel();legend();
}
async function load(){
 const registry=await fetch('data/city_count_layers.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('count registry '+r.status);return r.json()});
 cfg=registry.layers?.find(x=>x.id==='kiel');
 if(!cfg)throw Error('no approved Kiel count layer');
 const f=await fetch(cfg.file,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Kiel data '+r.status);return r.json()});
 if(f.features?.length!==30||f.meta?.status!=='supplementary_count_only'||
   f.meta?.metric_scope!=='all_offenses_count_only_NOT_violence_or_theft' ||
   f.features.some(x=>!Number.isInteger(x.properties?.crime_total?.cases)||
                       x.properties.crime_total.rate!==null))
     throw Error('Kiel count-only QA marker or geometry incomplete');
 const sum=f.features.reduce((a,x)=>a+x.properties.crime_total.cases,0);
 if(sum!==cfg.mapped_total||sum+cfg.unassigned_total!==cfg.reported_total)
    throw Error('Kiel official crime totals mismatch');
 data=f;
}
async function activate(){
 if(enabled){disable();return}
 window.__BREMEN_CATEGORY_MAP__?.disable?.();
 window.__STUTTGART_PUBLIC_MAP__?.disable?.();
 window.__DUESSELDORF_COUNT_MAP__?.disable?.();
 if(!data)await load();
 enabled=true;epoch++;
 // Selecting a local count-only view must not edit nationwide crime modes.
 api.clearSelection?.();
 api.map.fitBounds(L.geoJSON(data).getBounds(),{padding:[35,35],maxZoom:10,animate:false});
 render();
}
async function boot(){
 for(let i=0;i<100&&!window.__CRIME_MAP__;i++)await new Promise(r=>setTimeout(r,80));
 api=window.__CRIME_MAP__;if(!api)return;
 document.querySelector('.mapwrap')?.appendChild(localInfo);
 const button=$('focusKielCount');
 if(button)button.onclick=()=>activate().catch(e=>{disable();console.error('Kiel count layer unavailable',e)});
 api.map.on('zoomend',()=>{if(enabled&&!shouldShow())disable();else render()});
 api.map.on('moveend',()=>{if(enabled&&!shouldShow())disable();else render()});
 for(const id of ['modeViolence','modeProperty','viewGermany','focusBerlin'])
   $(id)?.addEventListener('click',()=>{if(enabled)disable()});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&enabled)disable()});
 window.__KIEL_COUNT_MAP__=Object.freeze({getActive:()=>enabled&&!!layer,getLayer:()=>layer,getData:()=>data,disable});
}
boot().catch(e=>console.error('Kiel supplemental boot',e));
})();
