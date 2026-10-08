/* Bremen police PKS 2024/25 - separately labelled city case COUNTS.
   Never conflates local case totals with nationwide per-100k rates. */
(()=>{'use strict';
const $=id=>document.getElementById(id),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=v=>Number(v).toLocaleString('zh-CN');
const metricNames={all_offenses:'全部登记犯罪',theft:'盗窃总体',robbery:'抢劫与暴力勒索',
 bodily_injury:'伤害犯罪',burglary:'住宅入室盗窃',sexual:'性犯罪',drug:'毒品犯罪'};
const metricOrder=['all_offenses','theft','robbery','bodily_injury','burglary','sexual','drug'];
const palette=['#e8f2fc','#cee5f5','#a5d0ec','#78b6db','#4c95c6','#2973a9','#155080'];
let api=null,config=null,geo=null,active=false,layer=null,renderer=null,metric='theft',selected=null,epoch=0;
const box=document.createElement('section');
box.id='bremenCategoryPanel';box.className='supp-city-info bremen-category-panel';box.hidden=true;
const paneClass='bremen-case-focus';
function caseVal(f){return f.properties.metrics[metric]['2025']}
function cuts(){const values=geo.features.map(f=>f.properties.metrics[metric]['2025']).filter(Number.isInteger).sort((a,b)=>a-b);return [1,2,3,4,5,6].map(i=>values[Math.min(values.length-1,Math.max(0,Math.ceil(values.length*i/7)-1))]);}
let thresholds=[];
function fill(f){const n=caseVal(f);if(n===null)return '#e1e8ee';const i=thresholds.findIndex(v=>n<=v);return palette[i<0?6:i]}
function style(f){return {pane:'supplementaryPane',color:'#667e91',weight:.7,opacity:.65,fillColor:fill(f),fillOpacity:caseVal(f)===null?.38:.84}}
function popup(f){const p=f.properties,m=p.metrics[metric],n=m['2025'],prev=m['2024'];
 const d=n!==null&&prev!==null?n-prev:null,sign=d!==null&&d>0?'+':'';
 const detail=Object.entries(p.metrics).map(([k,v])=>'<span><small>'+esc(metricNames[k])+'</small><b>'+(v['2025']===null?'未列出':fmt(v['2025']))+'</b></span>').join('');
 return '<div class="supp-popup"><strong>'+esc(p.name)+'</strong><div class="supp-big">'+(n===null?'未列出':fmt(n)+' 起')+'</div>'+
 '<div>'+esc(metricNames[metric])+' · 2025年登记案件绝对数（非犯罪率）</div>'+
 '<div class="supp-change">2024年：'+(prev===null?'未列出':fmt(prev)+' 起')+'；年度变化：'+(d===null?'无法计算':sign+fmt(d)+' 起')+'</div>'+
 '<div class="supp-history">'+detail+'</div><small>此数据按警方统计区计数。类别之间可能交叉，不能相加；—表示官方未列出，不是零。</small></div>';
}
function clear(){
 if(layer){api.map.removeLayer(layer);layer=null}
 if(active||box.hidden===false)api.setCountyFocus?.(null);
 selected=null;box.hidden=true;
 document.querySelector('.mapwrap')?.classList.remove(paneClass,'supp-city-focus');
 $('legend')?.querySelectorAll('.bremen-category-legend').forEach(x=>x.remove());
 const btn=$('focusBremenCategory');if(btn){btn.classList.remove('active');btn.setAttribute('aria-pressed','false')}
}
function disable(){active=false;epoch++;clear()}
function legend(){
 const root=$('legend');if(!root)return;root.querySelectorAll('.bremen-category-legend').forEach(x=>x.remove());
 const summaries=geo.meta.mapped_categories[metric],unknown=summaries.missing_2025;
 const html='<div class="legend-block supp-city-legend bremen-category-legend"><div class="legend-title">不来梅 · '+esc(metricNames[metric])+'</div>'+
 '<div>官方PKS 2025 · 各统计区登记案件绝对数（起）</div>'+
 '<div class="scale">'+palette.map(x=>'<span style="background:'+x+'"></span>').join('')+'</div>'+
 '<div class="legend-labels">'+thresholds.map(x=>'<span>≤'+fmt(x)+'</span>').join('')+'<span>更高</span></div>'+
 '<div class="supp-warning">⚠ 非每10万人犯罪率，不能直接判断居民受害风险。'+
 (unknown?unknown+'个区域此项未列数值，灰色表示缺失，不等于零。':'')+
 '各区合计不等于不来梅全市PKS总数，未定位案件不可擅自分配。</div></div>';
 root.insertAdjacentHTML('beforeend',html);
}
function panel(){
 const totals=geo.meta.mapped_categories[metric],missing=totals.missing_2025;
 box.innerHTML='<div class="supp-city-head"><strong>不来梅 Bremen · 犯罪分类</strong><button id="bremenCategoryClose" type="button" aria-label="退出不来梅细分地图">×</button></div>'+
 '<div class="supp-city-sub">警方2025年登记案件 · 不同类别可切换 · 仅绝对数量</div>'+
 '<label for="bremenCategoryMetric" class="bremen-select-label">犯罪类别</label>'+
 '<select id="bremenCategoryMetric" class="bremen-select">'+metricOrder.map(k=>'<option value="'+k+'"'+(k===metric?' selected':'')+'>'+esc(metricNames[k])+'</option>').join('')+'</select>'+
 '<div class="supp-city-numbers"><span><b>'+fmt(totals['2025'])+'</b><small>可统计区域合计（起）</small></span><span><b>'+missing+'</b><small>本类别未列数值的区域</small></span></div>'+
 '<p>2024年这些区域的已列案件合计 '+fmt(totals['2024'])+' 起。个别区域以“—”代替数字，<b>没有按零计入</b>。</p>'+
 '<p>地区按案件数量着色，<b>不是人均犯罪率</b>；在商业区和交通枢纽，案件数不等于居民的受害风险。</p>'+
 '<div class="supp-city-source"><a href="'+esc(config.source_url)+'" target="_blank" rel="noopener noreferrer">不来梅议会官方PKS（2025） ↗</a> · <a href="'+esc(config.geometry_url)+'" target="_blank" rel="noopener noreferrer">官方行政边界 ↗</a></div>';
 box.hidden=false;
 $('bremenCategoryClose').onclick=disable;
 $('bremenCategoryMetric').onchange=e=>{metric=e.target.value;redraw()};
}
function within(){
 return active && api.map.getZoom()>=8 && geo &&
  L.geoJSON(geo).getBounds().contains(api.map.getCenter());
}
function redraw(){
 if(!geo||!active)return;
 thresholds=cuts();
 if(layer){layer.eachLayer(l=>layer.resetStyle(l));}
 legend();panel();
}
function render(){
 if(!geo||!active)return;
 if(!within()){disable();return}
 if(layer){redraw();return}
 if(!api.map.getPane('supplementaryPane')){
   api.map.createPane('supplementaryPane');api.map.getPane('supplementaryPane').style.zIndex=275;
 }
 renderer=renderer||L.svg({pane:'supplementaryPane',padding:.2});
 thresholds=cuts();
 layer=L.geoJSON(geo,{pane:'supplementaryPane',renderer,style,
   onEachFeature:(feature,l)=>{
     l.bindTooltip(()=>'<b>'+esc(feature.properties.name)+'</b><div>'+esc(metricNames[metric])+'：'+(caseVal(feature)===null?'未列出':fmt(caseVal(feature))+' 起')+'（非犯罪率）</div>',{sticky:true});
     l.bindPopup(()=>popup(feature),{maxWidth:370});
     l.on('mouseover',()=>{if(selected!==l)l.setStyle({color:'#ffffff',opacity:1,weight:1.7})});
     l.on('mouseout',()=>{if(selected!==l&&layer)layer.resetStyle(l)});
     l.on('click',()=>{if(selected&&layer)layer.resetStyle(selected);selected=l;l.setStyle({color:'#ffffff',opacity:1,weight:2})});
   }}).addTo(api.map);
 api.setCountyFocus?.('04011');
 document.querySelector('.mapwrap')?.classList.add('supp-city-focus',paneClass);
 $('focusBremenCategory')?.setAttribute('aria-pressed','true');
 $('focusBremenCategory')?.classList.add('active');
 legend();panel();
}
async function load(){
 const registry=await fetch('data/city_count_layers.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('city count registry '+r.status);return r.json()});
 config=registry.layers?.find(c=>c.id==='bremen');
 if(!config||config.metric!=='local_category_cases')throw Error('Bremen count categories not approved');
 const data=await fetch(config.file,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Bremen geoJSON '+r.status);return r.json()});
 if(data.meta?.status!=='supplementary_category_counts_only' ||
    data.features?.length!==22 ||data.meta?.metric_scope!=='seven_official_local_categories_absolute_cases_no_rates' ||
    data.features.some(f=>metricOrder.some(k=>!f.properties?.metrics?.[k] ||
        f.properties.metrics[k].rate!==null ||
        (f.properties.metrics[k]['2025']!==null&&!Number.isInteger(f.properties.metrics[k]['2025'])))))
      throw Error('Bremen city PKS counts failed public integrity test');
 geo=data;
}
async function activate(){
 if(active){disable();return}
 const ticket=++epoch;
 if(!geo)await load();
 if(ticket!==epoch)return;
 window.__KIEL_COUNT_MAP__?.disable?.();
 window.__STUTTGART_PUBLIC_MAP__?.disable?.();
 window.__DUESSELDORF_COUNT_MAP__?.disable?.();
 api.clearSelection?.();
 active=true;
 const bounds=L.geoJSON(geo).getBounds();
 api.map.fitBounds(bounds,{padding:[32,32],maxZoom:10,animate:false});
 render();
}
async function boot(){
 for(let i=0;i<100&&!window.__CRIME_MAP__;i++)await new Promise(resolve=>setTimeout(resolve,80));
 api=window.__CRIME_MAP__;if(!api)return;
 document.querySelector('.mapwrap')?.appendChild(box);
 $('focusBremenCategory')?.addEventListener('click',()=>activate().catch(err=>{disable();console.error('Bremen count layer failed',err)}));
 api.map.on('zoomend',()=>{if(active&&!within())disable()});
 api.map.on('moveend',()=>{if(active&&!within())disable()});
 ['viewGermany','focusBerlin','modeViolence','modeProperty'].forEach(id=>$(id)?.addEventListener('click',()=>{if(active)disable()}));
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&active)disable()});
 window.__BREMEN_CATEGORY_MAP__=Object.freeze({getActive:()=>active&&!!layer,getMetric:()=>metric,getLayer:()=>layer,getData:()=>geo,disable});
}
boot().catch(e=>console.error('Bremen module boot failed',e));
})();