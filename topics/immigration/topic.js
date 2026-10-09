(() => {
'use strict';
const $ = id => document.getElementById(id);
const nf = new Intl.NumberFormat('zh-CN');
const COLORS = ['#d9e7ee','#b6d1e0','#8bb9d1','#62a2c5','#3c88b0','#247098','#10547b'];
const SHARE_COLORS = ['#dae8ed','#b9d7e4','#96c6d9','#6caccb','#4189b2','#266a99','#124b72'];
const BOUNDS = [[47.05,5.45],[55.15,15.65]];
const GEO_STATES = '../../data/germany-states.geojson';
const GEO_COUNTIES = '../../data/germany-counties.geojson';
const raw = () => [window.__IMMIGRATION_INLINE_FOREIGN__,window.__IMMIGRATION_INLINE_TREND__,window.__IMMIGRATION_INLINE_SHARE__,window.__IMMIGRATION_INLINE_COUNTIES__];
const format = n => n == null ? '—' : nf.format(n);
const escapeHtml = value => String(value??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','"':'&quot;',"'":'&#39;'}[c]));
function quantiles(values) {
 const a=values.filter(Number.isFinite).sort((x,y)=>x-y);
 return [0.14,0.28,0.42,0.56,0.70,0.84].map(p=>{
  const v=(a.length-1)*p, i=Math.floor(v), k=Math.ceil(v);return a[i]+(a[k]-a[i])*(v-i);
 });
}
function colorFor(v,breaks,colors) {if(!Number.isFinite(v))return '#cbd5d9';let i=0;while(i<breaks.length&&v>breaks[i])i++;return colors[i];}
function loadJson(path){return fetch(path,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('行政区数据 HTTP '+r.status);return r.json();});}
function validate(src){
 const [azr,trend,share,county]=src;
 if(azr?.totals?.national!==14070225||azr.records?.length!==16||trend?.years?.length!==8||trend.national?.[7]!==14070225||share?.records?.length!==16||county?.records?.length!==25)throw Error('官方数据完整性校验失败');
 if(azr.records.reduce((s,r)=>s+r.value,0)!==14070225)throw Error('AZR州级合计不一致');
 if(new Set(azr.records.map(r=>r.iso)).size!==16||new Set(county.records.map(r=>r.ags)).size!==25)throw Error('行政区编码重复');
 for(const c of county.records){if(!/^\d{5}$/.test(c.ags)||c.quality!=='direct_official_row'||!Number.isSafeInteger(c.value)||c.value<0)throw Error('县级行政编码/数据无效');}
 return {azr,trend,share,county};
}
const app={...validate(raw()),metric:'count',year:2025,selected:null,countySelected:null,stateGeo:null,stateLayer:null,countyGeo:null,countyLayer:null,countyBusy:false,mode:'states',stateByIso:new Map(),trendByIso:new Map(),shareByIso:new Map(),countyByAgs:new Map()};
for(const r of app.azr.records)app.stateByIso.set(r.iso,r);
for(const r of app.trend.records)app.trendByIso.set(r.iso,r);
for(const r of app.share.records)app.shareByIso.set(r.iso,r);
for(const r of app.county.records)app.countyByAgs.set(r.ags,r);
const map = window.L ? L.map('immigration-map',{minZoom:5,maxZoom:15,zoomControl:true,preferCanvas:false,worldCopyJump:false}) : null;
window.__IMMIGRATION_MAP_V13__=map;
function currentNumber(iso){
 if(app.metric==='share')return app.shareByIso.get(iso)?.share_percent??null;
 const row=app.trendByIso.get(iso);return row?.values[app.year-2018]??null;
}
function nationalNumber(){return app.metric==='share'?app.share.national.share_percent:app.trend.national[app.year-2018];}
function unitText(v){return app.metric==='share'?(v==null?'—':v.toFixed(1)+'%'):format(v);}
function isCountyAvailable(iso){return app.metric==='count'&&app.year===2025&&app.county.coverage_by_state?.[iso]?.complete===true;}
function stateEntries(){return [...app.stateByIso.values()].sort((a,b)=>currentNumber(b.iso)-currentNumber(a.iso));}
function chosenStateFeature(iso){return app.stateGeo?.features?.find(f=>f.properties?.id===iso);}
function stateStyle(feature){
 const iso=feature.properties?.id, sel=app.selected===iso;
 const v=currentNumber(iso),br=quantiles(app.azr.records.map(r=>currentNumber(r.iso)));
 return {pane:'immigrationStatePane',color:sel?'#ffffff':'#29475a',weight:sel?3:1.6,opacity:1,
  fillColor:colorFor(v,br,app.metric==='share'?SHARE_COLORS:COLORS),fillOpacity:sel?.64:.52};
}
function refreshLegend(){
 const values=app.azr.records.map(r=>currentNumber(r.iso));const a=values.filter(Number.isFinite);
 $('legend-title').textContent=app.metric==='share'?'非德国籍居民比例 · 2025':'外国籍人口 · AZR登记人数';
 $('legend-colors').replaceChildren(...(app.metric==='share'?SHARE_COLORS:COLORS).map(c=>{const s=document.createElement('span');s.style.background=c;return s;}));
 $('legend-limits').replaceChildren();
 const low=document.createElement('span'),high=document.createElement('span');low.textContent=unitText(Math.min(...a));high.textContent=unitText(Math.max(...a));
 $('legend-limits').append(low,high);
 $('legend-note').textContent=app.metric==='share'?'居民人口推算口径 · 与AZR人数不同':app.year+'年末 · AZR官方统计';
}
function updateMapStyles(){if(app.stateLayer)app.stateLayer.setStyle(stateStyle); if(app.countyLayer)app.countyLayer.eachLayer(l=>l.setStyle(countyStyle(l.feature)));}
function countyStyle(f){
 const id=String(f?.id??f?.properties?.AGS??'').padStart(5,'0'), c=app.countyByAgs.get(id), chosen=app.countySelected===id;
 return {pane:'immigrationCountyPane',color:chosen?'#fff':'#31546c',weight:chosen?3:1,opacity:1,
 fillColor:c?colorFor(c.value,quantiles([...app.countyByAgs.values()].filter(r=>r.state_iso===app.selected).map(r=>r.value)),COLORS):'#d6dee2',
 fillOpacity:c?.58:.09};
}
function renderCountry(){
 $('region-panel').hidden=true;$('national-panel').hidden=false;
 $('national-value').textContent=unitText(nationalNumber());
 $('national-label').textContent=app.metric==='share'?'非德国籍居民占全国居民比例 · 人口推算':'德国全国 · AZR登记外国籍人口';
 $('national-description').textContent=app.metric==='share'?'2025年底 · 人口统计推算，不是AZR人数除以人口':app.year+'年12月31日 · 外国人中央登记册（AZR）';
 $('state-list').replaceChildren();
 stateEntries().forEach((r,i)=>{const li=document.createElement('li'),b=document.createElement('button');b.type='button';
 const name=document.createElement('span'),value=document.createElement('span');name.textContent=(i+1)+'. '+r.name_de;value.textContent=unitText(currentNumber(r.iso));
 b.append(name,value);b.addEventListener('click',()=>selectState(r.iso));li.append(b);$('state-list').append(li);});
}
function renderTrend(){
 const x=app.trendByIso.get(app.selected),svg=$('trend-chart');svg.replaceChildren();if(!x)return;
 const nums=x.values,min=Math.min(...nums),max=Math.max(...nums),span=Math.max(1,max-min);
 const p=nums.map((v,i)=>[10+i*300/7,75-(v-min)/span*60]);
 const poly=document.createElementNS('http://www.w3.org/2000/svg','polyline');
 poly.setAttribute('points',p.map(v=>v.join(',')).join(' '));poly.setAttribute('fill','none');poly.setAttribute('stroke','#83c4e9');poly.setAttribute('stroke-width','2.6');
 poly.setAttribute('stroke-linecap','round');poly.setAttribute('stroke-linejoin','round');svg.append(poly);
 p.forEach(q=>{const dot=document.createElementNS('http://www.w3.org/2000/svg','circle');dot.setAttribute('cx',q[0]);dot.setAttribute('cy',q[1]);dot.setAttribute('r','2.5');dot.setAttribute('fill','#bce7fa');svg.append(dot);});
}
function renderState(){
 if(!app.selected){renderCountry();return;}
 const row=app.stateByIso.get(app.selected),x=app.trendByIso.get(app.selected),i=app.year-2018;
 $('national-panel').hidden=true;$('region-panel').hidden=false;$('region-name').textContent=row.name_de;$('region-crumb').textContent=row.name_de;
 $('region-value').textContent=unitText(currentNumber(app.selected));
 $('region-value-label').textContent=app.metric==='share'?'2025年非德国籍居民占比':'AZR登记外国籍人口';
 $('region-change').textContent=app.metric==='share'?'—':i===0?'—':(x.values[i]-x.values[i-1]>=0?'+':'')+format(x.values[i]-x.values[i-1]);
 $('region-change-label').textContent=app.metric==='share'?'不同统计口径，无可比同比':app.year===2018?'2018年为最早数据':'较上一年 · AZR人数';
 $('region-coverage').textContent=isCountyAvailable(app.selected)?'已核实县级':'州级统计';
 $('region-trend').hidden=app.metric==='share';if(app.metric==='count')renderTrend();
 const countyRows=app.county.records.filter(c=>c.state_iso===app.selected);
 const available=isCountyAvailable(app.selected);$('county-section').hidden=!available;
 $('county-list').replaceChildren();
 if(available){countyRows.sort((a,b)=>b.value-a.value).forEach(c=>{
  const li=document.createElement('li'),b=document.createElement('button');b.type='button';b.append(Object.assign(document.createElement('span'),{textContent:window.GermanPlaceNames?.byAGS(c.ags,c.name_de)||c.name_de}),Object.assign(document.createElement('span'),{textContent:format(c.value)}));b.addEventListener('click',()=>selectCounty(c.ags));li.append(b);$('county-list').append(li);
 });}
 const coverage=app.county.coverage_by_state?.[app.selected];
 $('county-coverage-note').textContent=available?countyRows.length+'个县级地区 · 2025年AZR官方记录'+(coverage?.rounding_difference?'；县合计与州合计相差'+coverage.rounding_difference+'人（官方五人舍入）':''):'';
 $('county-detail').hidden=!app.countySelected;
 $('show-counties').textContent=app.mode==='counties'?'返回州级地图':'查看县市地图';
}
function refreshAll(){refreshLegend();$('guide-year').textContent=app.metric==='share'?'2025':app.year;
 $('population-year').disabled=app.metric==='share';$('population-year').value=String(app.metric==='share'?2025:app.year);
 $('source-scope').textContent=app.metric==='share'?'2025年 · 人口统计推算口径 · 16州':app.year+'年 · AZR登记人数 · 16州';
 $('official-source').href=app.metric==='share'?app.share.source.url:app.azr.source.url;
 $('method-note').textContent=app.metric==='share'?'占比来自居民人口推算，与AZR登记人数属于不同统计体系，不能混合相除。':'外国籍人口是无德国国籍的登记居民，不等于非法居留，也不等于移民经历人口；部分县无2025年原始记录，不推算。';
 if(app.selected)renderState();else renderCountry();
 updateMapStyles();
}
function clearCounties(){
 if(app.countyLayer){app.countyLayer.remove();app.countyLayer=null;}app.mode='states';app.countySelected=null;
 if(app.stateLayer){
  app.stateLayer.eachLayer(l=>{l.options.interactive=true;if(l._path)l._path.style.pointerEvents='auto';});
  app.stateLayer.setStyle(stateStyle);
 }
}
function selectState(iso){
 if(!app.stateByIso.has(iso))return;
 if(app.selected!==iso)clearCounties();
 app.selected=iso;renderState();updateMapStyles();
 $('map-guide').textContent=app.stateByIso.get(iso).name_de+' · 点击其他联邦州可以切换';
}
function reset(){clearCounties();app.selected=null;refreshAll();if(map)map.fitBounds(BOUNDS,{padding:[18,18],animate:false});$('map-guide').textContent='点击联邦州查看人数、趋势与已核实的县级资料。';}
function selectCounty(ags){
 const c=app.countyByAgs.get(ags);if(!c||c.state_iso!==app.selected||!isCountyAvailable(app.selected))return;
 app.countySelected=ags;$('county-name').textContent=window.GermanPlaceNames?.byAGS(c.ags,c.name_de)||c.name_de;$('county-value').textContent=format(c.value);$('county-detail').hidden=false;
 renderState();$('county-detail').hidden=false;
 if(app.countyLayer){app.countyLayer.eachLayer(l=>{const id=String(l.feature?.id??l.feature?.properties?.AGS??'').padStart(5,'0');if(id===ags){l.setStyle(countyStyle(l.feature));map.fitBounds(l.getBounds(),{padding:[35,35],maxZoom:10,animate:false});}else l.setStyle(countyStyle(l.feature));});}
}
async function showCounties(){
 if(!isCountyAvailable(app.selected))return;
 if(app.mode==='counties'){clearCounties();renderState();const f=chosenStateFeature(app.selected);if(f)map.fitBounds(L.geoJSON(f).getBounds(),{padding:[35,35],maxZoom:7,animate:false});return;}
 if(app.countyBusy)return;app.countyBusy=true;
 $('show-counties').disabled=true;$('show-counties').textContent='正在加载县界…';
 try{
  if(!app.countyGeo)app.countyGeo=await loadJson(GEO_COUNTIES);
  if(!Array.isArray(app.countyGeo.features))throw Error('县界不是GeoJSON');
  const rows=app.county.records.filter(c=>c.state_iso===app.selected),ids=new Set(rows.map(c=>c.ags));
  const found=app.countyGeo.features.filter(f=>ids.has(String(f?.id??f?.properties?.AGS??'').padStart(5,'0')));
  const matched=new Set(found.map(f=>String(f?.id??f?.properties?.AGS??'').padStart(5,'0')));
  if(matched.size!==ids.size)throw Error('当前州县级行政边界与AGS编码不完全匹配，暂不绘图');
  if(!map.getPane('immigrationCountyPane'))map.createPane('immigrationCountyPane').style.zIndex=345;
  app.mode='counties';
  app.countyLayer=L.geoJSON({type:'FeatureCollection',features:found},{
    pane:'immigrationCountyPane',renderer:L.svg({pane:'immigrationCountyPane',padding:.2}),style:countyStyle,
    onEachFeature:(f,l)=>{
     const id=String(f?.id??f?.properties?.AGS??'').padStart(5,'0'),c=app.countyByAgs.get(id);
     l.bindTooltip(()=>'<b>'+escapeHtml(window.GermanPlaceNames?.byAGS(c?.ags,c?.name_de)||c?.name_de)+'</b><br>'+format(c?.value)+' 人',{sticky:true});
     l.on('mouseover',()=>{if(app.countySelected!==id)l.setStyle({color:'#fff',weight:2.0});});
     l.on('mouseout',()=>app.countyLayer?.resetStyle(l));
     l.on('click',e=>{L.DomEvent.stopPropagation(e);selectCounty(id);});
    }
  }).addTo(map);
  // State polygons must not intercept clicks on the county layer.
  if(app.stateLayer)app.stateLayer.eachLayer(l=>{l.options.interactive=false; if(l._path)l._path.style.pointerEvents='none';});
  map.fitBounds(app.countyLayer.getBounds(),{padding:[38,38],maxZoom:9,animate:false});
  renderState();$('map-status').textContent='官方县级行政边界 · '+found.length+'个县市';
 }catch(e){console.error(e);$('map-status').textContent='县级边界未匹配：'+e.message;clearCounties();}
 finally{app.countyBusy=false;$('show-counties').disabled=false;renderState();}
}
function setMetric(v){
 if(v!=='count'&&v!=='share')return;
 if(app.mode==='counties')clearCounties();app.metric=v;if(v==='share')app.year=2025;refreshAll();
}
function setYear(v){const n=Number(v);if(!Number.isInteger(n)||n<2018||n>2025||app.metric==='share')return;
 if(app.mode==='counties')clearCounties();app.year=n;refreshAll();
}
async function start(){
 if(!map){$('map-status').textContent='地图框架加载失败：无法连接Leaflet资源';return;}
 map.fitBounds(BOUNDS,{padding:[15,15]});map.setMaxBounds([[45.3,3.2],[57.1,18]]);
 map.createPane('immigrationStatePane').style.zIndex=330;
 const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,opacity:.84,attribution:'© OpenStreetMap contributors',crossOrigin:true});
 let tilesSeen=false;tiles.on('tileload',()=>{tilesSeen=true;});tiles.addTo(map);
 // Keep the OSM layer attached so slow connections and zoom-triggered retries can recover.
 setTimeout(()=>{if(!tilesSeen){$('map-status').textContent='OSM街道底图加载较慢 · 地区边界仍可使用';}},10000);
 window.CrimeCityLabels?.create(map,{paneName:'immigration-city-labels',zIndex:435});
 for(let y=2025;y>=2018;y--){const o=document.createElement('option');o.value=y;o.textContent=y+'年';$('population-year').append(o);}
 $('population-metric').addEventListener('change',e=>setMetric(e.target.value));
 $('population-year').addEventListener('change',e=>setYear(e.target.value));
 $('reset-map').addEventListener('click',reset);$('back-country').addEventListener('click',reset);
 $('show-counties').addEventListener('click',showCounties);
 refreshAll();
 try{
  const geo=await loadJson(GEO_STATES);
  const ids=geo?.features?.map(f=>f.properties?.id);
  if(geo?.type!=='FeatureCollection'||geo.features?.length!==16||new Set(ids).size!==16||ids.some(id=>!app.stateByIso.has(id)))throw Error('州界数量或ISO编码不匹配');
  app.stateGeo=geo;
  app.stateLayer=L.geoJSON(geo,{pane:'immigrationStatePane',renderer:L.svg({pane:'immigrationStatePane',padding:.2}),style:stateStyle,
   onEachFeature:(f,l)=>{const iso=f.properties.id,row=app.stateByIso.get(iso);
    l.bindTooltip(()=>'<b>'+escapeHtml(row.name_de)+'</b><br>'+unitText(currentNumber(iso)),{sticky:true});
    l.on('mouseover',()=>{if(app.selected!==iso)l.setStyle({color:'#fff',weight:2.3});});
    l.on('mouseout',()=>app.stateLayer?.resetStyle(l));
    l.on('click',e=>{if(app.mode==='counties')return;L.DomEvent.stopPropagation(e);selectState(iso);});
   }}).addTo(map);
  $('map-status').textContent='OSM街道底图 + 官方16州边界';
  window.__IMMIGRATION_READY__=true;
 }catch(e){console.error(e);$('map-status').textContent='真实州界加载失败：'+e.message+'。未绘制估算轮廓。';}
}
window.GermanMapTopics=window.GermanMapTopics||{};
window.GermanMapTopics.immigration={id:'immigration',title:'移民人口',selectState,selectMetric:setMetric,selectYear:setYear,reset,getViewState:()=>({metric:app.metric,year:app.year,state:app.selected,county:app.countySelected,countyMode:app.mode})};
start();
})();