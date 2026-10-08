(()=>{"use strict";
const {palettes:{national:WARM,property:COOL},violenceMetrics}=window.CrimeMapConfig;
let api=null,manifest=null,active=null,activeKey=null,layer=null,selected=null,cache=new Map(),activationEpoch=0;
let cityBackdrop=null,cityBorder=null,mutedCounties=null;
const boundaryCache=new Map();

const $=id=>document.getElementById(id);
const fmt=n=>Number(n||0).toLocaleString('zh-CN');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function metricKey(){return api?.getMode?.()==='property'?$('propertyMetric')?.value:$('violenceMetric')?.value}
const {quantileBreaks,scaleColor,percentile,riskLabel,pointInGeometry}=window.CrimeMapUtils;
function caseMatches(c,key){return window.CrimeDataModel.caseMatchesMetric(api.getMode(),key,c,violenceMetrics)}
function cityBounds(c){return L.latLngBounds(c.bounds)}
function matchingCity(){
  if(!manifest||!api)return null;
  const k=metricKey(),center=api.map.getCenter(),viewport=api.map.getBounds();
  const visible=manifest.cities.filter(c=>c.metrics?.[k]&&api.map.getZoom()>=(c.min_zoom||8)&&viewport.intersects(cityBounds(c)));
  // Nearby Dresden, Chemnitz and Leipzig can all intersect a wide viewport.
  // Prefer the city UNDER the map center, never registry insertion order.
  visible.sort((a,b)=>{
    const ba=cityBounds(a),bb=cityBounds(b);
    return Number(!ba.contains(center))-Number(!bb.contains(center))||
      center.distanceTo(ba.getCenter())-center.distanceTo(bb.getCenter());
  });
  return visible[0]||null
}
async function cityData(c){
  if(cache.has(c.id))return cache.get(c.id);
  const p=fetch(c.file,{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(c.id+' '+r.status);return r.json()})
    .catch(error=>{cache.delete(c.id);throw error});
  cache.set(c.id,p);return p
}
function values(data,field){return (data?.features||[]).map(f=>Number(f?.properties?.[field]?.rate)).filter(Number.isFinite)}
function firstCoordinate(tree){
  if(Array.isArray(tree)&&tree.length>=2&&typeof tree[0]==='number'&&typeof tree[1]==='number')return tree;
  if(Array.isArray(tree))for(const part of tree){const found=firstCoordinate(part);if(found)return found}
  return null
}
// A missing/bad municipality file must never leave a blank hole in the
// nationwide choropleth. WFS datasets can silently use projected UTM metres.
function validCityGeometry(data,city){
  if(!Array.isArray(data?.features)||data.features.length===0)return false;
  const [[south,west],[north,east]]=city.bounds;
  return data.features.every(feature=>{
    const type=feature?.geometry?.type;
    if(type!=='Polygon'&&type!=='MultiPolygon')return false;
    const point=firstCoordinate(feature.geometry.coordinates);
    if(!point||!Number.isFinite(point[0])||!Number.isFinite(point[1]))return false;
    const [lon,lat]=point;
    return lon>=west-0.5&&lon<=east+0.5&&lat>=south-0.5&&lat<=north+0.5
  });
}
function recordForFeature(feature,data){
  const id=String(feature?.id??feature?.properties?.AGS??'').padStart(5,'0'),alias=data?.meta?.geometry_aliases?.[id];
  return data?.records?.[id]||data?.records?.[alias]
}
function baseLayerFor(c){
  const cl=api.getCountyLayer?.();if(!cl)return null;
  // The city and the surrounding Landkreis can share a name (notably
  // München Stadt 09162 vs Landkreis München 09184). Match by canonical AGS.
  const ags=String(c.county_ags||'').padStart(5,'0');
  if(ags!=='00000'){
    return cl.getLayers().find(l=>String(l.feature?.id??l.feature?.properties?.AGS??'').padStart(5,'0')===ags)||null
  }
  const d=api.getMode()==='property'?api.getPropertyData():api.getPksData();
  return cl.getLayers().find(l=>recordForFeature(l.feature,d)?.name===c.name&&l.feature?.properties?.districtType!=='Landkreis')||null
}
function restoreBase(c){
  if(mutedCounties){
    mutedCounties.eachLayer(l=>mutedCounties.resetStyle(l));
    mutedCounties=null;
  }else{
    const cl=api.getCountyLayer?.(),l=baseLayerFor(c);
    if(cl&&l)cl.resetStyle(l);
  }
}
function hideBase(c){
  const cl=api.getCountyLayer?.(),l=baseLayerFor(c);
  if(!l)return;
  if(c.coverage==='partial'){
    // During Dresden focus, the neighbouring county heatmap is deliberately
    // quieted so its warm fill cannot bleed through the pastel city polygons.
    // All original crime figures remain available via county hover/click.
    if(cl && mutedCounties!==cl){
      if(mutedCounties)mutedCounties.eachLayer(item=>mutedCounties.resetStyle(item));
      mutedCounties=cl;
      cl.eachLayer(item=>item.setStyle({
        color:'#94a1a9',weight:.3,opacity:.32,fillOpacity:.12
      }));
    }
  }
  // The city-wide county rate MUST NOT shine through low-crime districts;
  // its saturated underside created the mauve/red slivers in Dresden.
  l.setStyle({color:'transparent',weight:0,opacity:0,fillOpacity:0});
}
async function boundaryData(c){
  if(!c.boundary_file)return null;
  if(!boundaryCache.has(c.id)){
    boundaryCache.set(c.id,fetch(c.boundary_file,{cache:'no-store'})
      .then(r=>{if(!r.ok)throw new Error('boundary '+r.status);return r.json()})
      .catch(error=>{boundaryCache.delete(c.id);throw error}));
  }
  return boundaryCache.get(c.id);
}
function clearFocusOverlays(){
  if(cityBorder){api.map.removeLayer(cityBorder);cityBorder=null}
  if(cityBackdrop){api.map.removeLayer(cityBackdrop);cityBackdrop=null}
  document.querySelector('.mapwrap')?.classList.remove('city-detail-focus');
}
function areaFor(c,data,f){
  const key=metricKey(),cfg=c.metrics[key],p=f.properties||{},m=p?.[cfg.field]||{},rate=Number(m.rate),cases=Number(m.cases||0),vals=values(data,cfg.field),pc=percentile(rate,vals);
  const recent=(api.getCaseData()?.cases||[]).filter(x=>caseMatches(x,key)&&Number.isFinite(x.lon)&&Number.isFinite(x.lat)&&pointInGeometry(x.lon,x.lat,f.geometry)).length;
  return {kind:'city-local-generic',name:p.name||c.name,state:c.state,metric:c.source_label+' · '+cfg.label,rate,cases,recent,pct:pc,feature:f,change:m.change||'—',city:c,note:cfg.note||''}
}
function showPanel(a,pin=false){
  api.showArea(a,{pin});
  const rsk=riskLabel(a.pct),c=a.city;
  const cp=$('coveragePill'),ct=$('coverageText'),rb=$('riskBadge'),ar=$('areaRate'),arl=$('areaRateLabel'),aq=$('areaQuarter'),aql=$('areaQuarterLabel'),an=$('areaRecent'),anl=$('areaRecentLabel'),note=$('areaNote');
  if(cp){cp.textContent='细分数据';cp.className='coverage-pill high'} if(ct)ct.textContent=c.source_label;
  if(rb){rb.textContent=rsk.text+' · '+(c.name_zh||c.name)+'P'+a.pct;rb.className='risk-badge '+rsk.cls}
  if(ar)ar.textContent=Number.isFinite(a.rate)?fmt(Math.round(a.rate)):'—';if(arl)arl.textContent='每10万人·年';
  if(aq)aq.textContent=fmt(a.cases);if(aql)aql.textContent='2025登记案件';
  if(an)an.textContent=a.change;if(anl)anl.textContent='较2024变化';
  if(note)note.textContent=(a.note?a.note+' ':c.source_label+' 官方城市细分数据。')+(a.recent?'近90天匹配公开通报 '+fmt(a.recent)+' 起。':'')
}
function addLegend(c,data){
  const root=$('legend');if(!root)return;
  // Each city has its own category/range/coverage note; never retain the
  // previous city legend after switching Hamburg → Munich → Dresden.
  root.querySelectorAll('.generic-city-legend').forEach(el=>el.remove());
  const cfg=c.metrics[metricKey()],b=quantileBreaks(values(data,cfg.field)),pal=api.getMode()==='property'?COOL:WARM;
  const labs=[...b.map(x=>'≤'+fmt(Math.round(x))), '>'+fmt(Math.round(b[5]||0))];
  root.insertAdjacentHTML('beforeend','<div class="legend-block generic-city-legend"><div class="legend-title">'+esc(c.name_zh||c.name)+' · 官方城市细分层</div><div>'+esc(cfg.label)+' · 每10万人/年</div><div class="scale">'+pal.map(x=>'<span style="background:'+x+'"></span>').join('')+'</div><div class="legend-labels">'+labs.map(x=>'<span>'+x+'</span>').join('')+'</div>'+(c.coverage_note?'<div class="city-coverage-note">'+esc(c.coverage_note)+'</div>':'')+'</div>')
}
async function rebuild(){
  const next=matchingCity(),nextKey=next?next.id+':'+api.getMode()+':'+metricKey():null;
  if(nextKey&&nextKey===activeKey&&layer){hideBase(next);return}
  const epoch=++activationEpoch;
  if(layer){api.map.removeLayer(layer);layer=null;selected=null}
  clearFocusOverlays();
  if(active)restoreBase(active);
  active=next;activeKey=nextKey;
  if(!active){
    $('legend')?.querySelectorAll('.generic-city-legend').forEach(el=>el.remove());
    return;
  }
  try{
    const city=active;
    const [data,boundary]=await Promise.all([cityData(city),boundaryData(city)]);
    // Ignore stale asynchronous results after the viewport/metric changes.
    if(epoch!==activationEpoch)return;
    const cfg=city.metrics[metricKey()],vals=values(data,cfg.field),br=quantileBreaks(vals),pal=api.getMode()==='property'?COOL:WARM;
    if(city.coverage==='partial'){
      if(!boundary||!validCityGeometry(boundary,city))
        throw new Error('complete official Dresden boundary unavailable');
      // A single opaque, neutral fill shows the parts of the municipality
      // without police-atlas neighbourhood figures. They are NO DATA, not
      // low- or high-crime districts. Draw before the actual 61 districts.
      cityBackdrop=L.geoJSON(boundary,{pane:'berlinPane',interactive:false,style:()=>({
        pane:'berlinPane',color:'transparent',weight:0,opacity:0,
        fillColor:'#e7ecef',fillOpacity:.38
      })}).addTo(api.map);
      document.querySelector('.mapwrap')?.classList.add('city-detail-focus');
    }
    if(!validCityGeometry(data,active))throw new Error(active.id+' invalid CRS/geometry: expected longitude/latitude near configured city bounds');
    layer=L.geoJSON(data,{pane:'berlinPane',filter:f=>Number.isFinite(Number(f?.properties?.[cfg.field]?.rate)),style:f=>({pane:'berlinPane',color:city.coverage==='partial'?'#78848b':(api.getMode()==='property'?'#486783':'#8a563b'),weight:city.coverage==='partial'?.65:.34,opacity:city.coverage==='partial'?.55:.62,fillColor:scaleColor(Number(f.properties[cfg.field].rate),br,pal),fillOpacity:city.coverage==='partial'?.88:.84}),onEachFeature:(f,l)=>{
      l.bindTooltip(()=>{const a=areaFor(active,data,f);return '<b>'+esc(a.name)+'</b><br>'+esc(cfg.label)+' '+fmt(Math.round(a.rate))+'/10万人 · '+riskLabel(a.pct).text},{sticky:true});
      l.on('mouseover',()=>{if(l!==selected)l.setStyle({color:'#fff',weight:1.35,opacity:1,fillOpacity:.89});showPanel(areaFor(active,data,f))});
      l.on('mouseout',()=>{if(l!==selected)layer?.resetStyle(l);const p=api.getPinnedArea?.();if(p?.kind==='city-local-generic')showPanel(p,false);else api.showArea(p)});
      l.on('click',()=>{if(selected&&selected!==l)layer?.resetStyle(selected);selected=l;layer?.resetStyle(l);l.setStyle({color:'#fff',weight:2.1,opacity:1,fillOpacity:.91});showPanel(areaFor(active,data,f),true)})
    }}).addTo(api.map);
    if(layer.getLayers().length===0){api.map.removeLayer(layer);layer=null;throw new Error(active.id+' has no drawable features for '+metricKey())}
    if(city.coverage==='partial'){
      // Draw one continuous municipal border ON TOP of detailed polygons.
      // This conceals hairline rasterisation seams at the outside edge.
      cityBorder=L.geoJSON(boundary,{pane:'berlinPane',interactive:false,style:()=>({
        pane:'berlinPane',color:'#59646c',weight:1.35,opacity:.93,fill:false
      })}).addTo(api.map);
    }
    hideBase(city);
    setTimeout(()=>{if(epoch===activationEpoch)addLegend(city,data)},0)
  }catch(e){
    if(epoch!==activationEpoch)return;
    if(layer){api.map.removeLayer(layer);layer=null}
    clearFocusOverlays();
    if(active)restoreBase(active);
    console.warn('city detail skipped; retaining nationwide county fill',active?.id,e)
  }
}
function addButtons(){
  const anchor=$('focusMunich')||$('focusBerlin');if(!anchor)return;
  for(const c of manifest.cities){
    const id='focusCity_'+c.id;if($(id))continue;
    const b=document.createElement('button');b.id=id;b.type='button';b.textContent=c.name_zh||c.name;b.onclick=()=>{api.clearSelection?.();api.map.fitBounds(cityBounds(c),{padding:[25,25],maxZoom:10});};anchor.before(b)
  }
}
async function boot(){
  for(let i=0;i<100&&!window.__CRIME_MAP__;i++)await new Promise(r=>setTimeout(r,80));
  api=window.__CRIME_MAP__;if(!api)return;
  manifest=await fetch('data/city_layers.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('city registry '+r.status);return r.json()});
  addButtons();
  api.map.on('zoomend',()=>setTimeout(rebuild,0));api.map.on('moveend',()=>setTimeout(rebuild,0));
  for(const id of ['modeViolence','modeProperty','violenceMetric','propertyMetric'])$(id)?.addEventListener('change',()=>setTimeout(rebuild,0));
  $('modeViolence')?.addEventListener('click',()=>setTimeout(rebuild,0));$('modeProperty')?.addEventListener('click',()=>setTimeout(rebuild,0));
  rebuild()
}
boot().catch(e=>console.error('city-local',e));
})();
