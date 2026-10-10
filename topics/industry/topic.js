(() => {
'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const STATE_ISO={
'Baden-Württemberg':'DE-BW','Bayern':'DE-BY','Berlin':'DE-BE','Brandenburg':'DE-BB',
'Bremen':'DE-HB','Hamburg':'DE-HH','Hessen':'DE-HE','Mecklenburg-Vorpommern':'DE-MV',
'Niedersachsen':'DE-NI','Nordrhein-Westfalen':'DE-NW','Rheinland-Pfalz':'DE-RP',
'Saarland':'DE-SL','Sachsen':'DE-SN','Sachsen-Anhalt':'DE-ST','Schleswig-Holstein':'DE-SH','Thüringen':'DE-TH'};
const STATE_ZH={'DE-BW':'巴登-符腾堡','DE-BY':'巴伐利亚','DE-BE':'柏林','DE-BB':'勃兰登堡','DE-HB':'不来梅','DE-HH':'汉堡','DE-HE':'黑森','DE-MV':'梅克伦堡-前波美拉尼亚','DE-NI':'下萨克森','DE-NW':'北莱茵-威斯特法伦','DE-RP':'莱茵兰-普法尔茨','DE-SL':'萨尔兰','DE-SN':'萨克森','DE-ST':'萨克森-安哈尔特','DE-SH':'石勒苏益格-荷尔斯泰因','DE-TH':'图林根'};
/* Crosswalk resolves a PLACE to its legal county: a city is not always a Kreis.
   No fuzzy same-name join is allowed across states. These hints MUST NOT be taken
   as verified factory-gate coordinates. */
const COUNTY_HINTS={
'Fürstenwalde/Spree':'Oder-Spree','Eberswalde':'Barnim',
'Stuttgart-Feuerbach':'Stuttgart','Schwieberdingen':'Ludwigsburg','Waiblingen':'Rems-Murr-Kreis',
'Bühl/Bühlertal':'Rastatt','Plattling':'Deggendorf','Cadolzburg':'Fürth',
'Neustadt an der Donau':'Kelheim','Nördlingen':'Donau-Ries','Bremen-Farge':'Bremen',
'Babenhausen':'Darmstadt-Dieburg','Karben':'Wetteraukreis','Nentershausen':'Hersfeld-Rotenburg',
'Gründau':'Main-Kinzig-Kreis','Hannover-Vahrenwald':'Region Hannover',
'Stolzenau':'Nienburg (Weser)','Hameln':'Hameln-Pyrmont','Moers':'Wesel',
'Steinhagen':'Gütersloh','Lübbecke':'Minden-Lübbecke','Neuss':'Rhein-Kreis Neuss',
'Rheinberg':'Wesel','Rheinfelden':'Lörrach','Harzgerode':'Harz','Wernigerode':'Harz',
'Ueckermünde':'Vorpommern-Greifswald','Nobitz-Wilchwitz':'Altenburger Land',
'Dietenhofen':'Ansbach','Baiersbronn':'Freudenstadt','Malente':'Ostholstein',
'Frohburg':'Leipzig','Geithain':'Leipzig','Böhlen':'Leipzig','Radeburg':'Meißen',
'Oberlungwitz':'Zwickau','Schkopau':'Saalekreis','Bitterfeld-Wolfen':'Anhalt-Bitterfeld',
'Bad Blankenburg':'Saalfeld-Rudolstadt','Taufkirchen (Vils)':'Erding',
'Bad Harzburg':'Goslar','Korbach':'Waldeck-Frankenberg','Daaden/Weitefeld':'Altenkirchen (Westerwald)',
'Donaueschingen':'Schwarzwald-Baar-Kreis','Warstein':'Soest','Medebach':'Hochsauerlandkreis',
'Unterschneidheim':'Ostalbkreis','Augsburg-Pfersee':'Augsburg',
'Dorfprozelten':'Miltenberg','Torgau':'Nordsachsen','Waldaschaff':'Aschaffenburg',
'Bremervörde':'Rotenburg (Wümme)','Idar-Oberstein':'Birkenfeld','Marburg':'Marburg-Biedenkopf',
'Sonneberg':'Sonneberg','Homburg':'Saarpfalz-Kreis','Saarlouis':'Saarlouis',
'Fürth':'Fürth','Lüneburg':'Lüneburg','Fulda':'Fulda',
'Krefeld-Uerdingen':'Krefeld','Stuttgart':'Stuttgart','Speyer':'Speyer',
'Nürnberg':'Nürnberg','Wolfsburg':'Wolfsburg','Dresden':'Dresden',
'Mannheim':'Mannheim','Trier':'Trier','Ludwigshafen am Rhein':'Ludwigshafen am Rhein',
'Zwickau':'Zwickau','Rostock':'Rostock','Lübeck':'Lübeck','Hamburg':'Hamburg',
'Berlin-Neukölln':'Berlin','Bremen':'Bremen','Osnabrück':'Osnabrück',
'Neumünster':'Neumünster','Gütersloh':'Gütersloh','Duisburg':'Duisburg',
'Bochum':'Bochum','Essen':'Essen','Gelsenkirchen':'Gelsenkirchen',
'Mülheim an der Ruhr':'Mülheim an der Ruhr','Recklinghausen':'Recklinghausen'};
const STOP_TYPES=new Set(['plant_closure','production_cessation','production_line_closure','production_unit_closure',
 'vehicle_production_cessation','production_winddown','capacity_reduction','production_relocation',
 'production_suspension','manufacturing_exit','plant_closure_domestic_relocation']);
const STATUS_COMPLETE=new Set(['reported_closed','reported_completed','reported_implemented',
'confirmed_closed_activity','confirmed_by_subsequent_report']);
const POLYGON_BOUNDS=[[47.05,5.45],[55.15,15.65]];
const app={map:null,events:[],countyGeo:null,features:[],featureLookup:new Map(),byCounty:new Map(),
 selectedCounty:null,selectedEvent:null,eventMarkers:new Map(),markers:null,counties:null,metric:null,agsRemap:{}};
// AGS has five digits. The bundled geometry predates 2016/2021 mergers; use the current
// canonical AGS for district statistics, keeping historic shapes explicitly marked.
const stateKey=f=>app.agsRemap[f.id]||f.id;
function nameZh(s){return window.GermanPlaceNames?.translate(s)||s;}
function cleanCity(e){
 const raw=String(e.city||'').trim();
 if(e.event_id.startsWith('RUHR_'))return '';
 if(/[;]/.test(raw))return '';
 return raw;
}
function getCounty(e){
 if(e.eligible_factory_marker===false)return null;
 if(/^\d{5}$/.test(e.county_ags||'')){
  // Some current AGS (notably Göttingen 03159) consist of multiple old polygons.
  // Select the most appropriate historic county reference, never claim updated geometry.
  const matched=app.features.filter(f=>stateKey(f)===e.county_ags);
  return matched.find(f=>f.id===e.county_ags)||matched.find(f=>f.properties.name===e.county_name)||matched[0]||null;
 }
 if(e.county_label||e.county_name)return findCounty(String(e.county_label||e.county_name),e.state_iso);
 const raw=cleanCity(e);
 if(!raw||e.eligible_factory_marker===false)return null;
 const district=COUNTY_HINTS[raw]||raw;
 return findCounty(district,e.state_iso,raw);
}
function findCounty(name,iso,raw){
 if(!iso||!name)return null;
 const rows=app.features.filter(f=>!app.agsRemap[f.id]&&STATE_ISO[f.properties.state]===iso&&f.properties.name===name);
 if(!rows.length)return null;
 if(rows.length===1)return rows[0];
 const isCity=raw&&raw===name&&!['Fürth'].includes(raw);
 const independent=f=>['Kreisfreie Stadt','Stadtkreis'].includes(f.properties.districtType);
 return rows.find(f=>independent(f)===Boolean(isCity))||rows[0];
}
function normalize(e,batch){
 const title=e.headline_zh||e.company+' · '+e.city;
 const status=e.implementation_status||'not_checked';
 return { ...e,id:e.event_id,title,batch,
  jobs:Number.isFinite(Number(e.jobs_affected))&&e.jobs_affected!==null&&e.jobs_affected!==''?Number(e.jobs_affected):null,
  url:e.source_url||null,
  source_kind:e.source_type|| (batch==='R1'?'prior_research':'traceable_candidate'),
  note:e.caveat||e.notes||'',
  isPlan:!STATUS_COMPLETE.has(status)&&!/已结束|已关闭|已实施|停产完成|2023年底已/.test(status),
  isMajor:e.eligible_factory_marker!==false && (STOP_TYPES.has(e.event_type)||Number(e.jobs_affected)>=250)
 };
}
function colorByCount(n){
 return !n?'#e6e8e8':n===1?'#fbe2c8':n===2?'#f6b780':n===3?'#e4825d':'#bc4945';
}
function officialMetricFor(feature){
 const ags5=String(stateKey(feature)||'');
 // Official county employment is indexed by canonical five-digit AGS, never by district name or retired ID.
 const r=app.metric?.records?.[ags5];
 return r&&Number.isFinite(r.change_pct)?r:null;
}
function regionEntries(feature){
 return app.byCounty.get(stateKey(feature))||[];
}
function countyStyle(feature){
 const official=officialMetricFor(feature);
 if(official){
  const p=Number(official.change_pct);
  return {color:'#869ca9',weight:0.65,fillColor:p<=-20?'#9e3439':p<=-10?'#cb5c4c':p<=-2?'#e9976a':p<2?'#e8ded1':'#cde1d9',fillOpacity:0.72};
 }
 // When ANY official county series is present, NEVER mix it with sampled news-count colors.
 if(app.metric&&Object.keys(app.metric.records||{}).length>0)
  return {color:'#869ca9',weight:0.65,fillColor:'#e3e5e7',fillOpacity:0.72};
 const n=regionEntries(feature).filter(e=>e.isMajor).length;
 return {color:'#79909c',weight:0.65,fillColor:colorByCount(n),fillOpacity:0.8};
}
function createLegend(){
 const official=app.metric&&Object.keys(app.metric.records||{}).length>0;
 const legend=official
 ? [['工业就业降幅≥20%','#9e3439'],['下降10%—20%','#cb5c4c'],['下降2%—10%','#e9976a'],['基本稳定','#e8ded1'],['就业增长','#cde1d9'],['无同口径统计数据','#e3e5e7']]
 : [['未收录重大事件','#e6e8e8'],['1条重大事件','#fbe2c8'],['2条重大事件','#f6b780'],['3条重大事件','#e4825d'],['4条及以上','#bc4945']];
 $('legend').innerHTML='<div class="industry-legend"><strong>'+(official?'制造业就业变化':'已登记工业收缩事件')+'</strong>'
  +legend.map(([label,color])=>'<div class="swatch-row"><i class="industry-swatch" style="background:'+color+'"></i>'+label+'</div>').join('')
  +'<div class="mini-note">'+(official?'同口径就业人数；详见统计说明':'研究样本数量，不代表地区真实工业收缩率或全面普查')+'</div></div>';
}
function getMapPoint(e,county,geocache){
 if(Number.isFinite(Number(e.lat))&&Number.isFinite(Number(e.lon))&&e.lat!==null&&e.lon!==null)
  return {lat:+e.lat,lon:+e.lon,precision:'既有试点的厂区附近示意点（非精确厂门）'};
 const city=cleanCity(e);
 const stateName=Object.keys(STATE_ISO).find(k=>STATE_ISO[k]===e.state_iso);
 if(city&&stateName){
  const candidates=Object.entries(geocache||{}).filter(([k,v])=>
   k.toLowerCase().startsWith(city.toLowerCase()+',')&&
   (v.address?.['ISO3166-2-lvl4']===e.state_iso||v.address?.state===stateName));
  if(candidates.length){
   const z=candidates[0][1];
   if(Number.isFinite(z.lat)&&Number.isFinite(z.lon))
    return {lat:z.lat,lon:z.lon,precision:'城市名称参考位置（非工厂精确坐标）'};
  }
 }
 if(county){
  const b=L.geoJSON(county).getBounds();
  const c=b.getCenter();
  if(c&&c.lat&&c.lng)return {lat:c.lat,lon:c.lng,precision:'县市区域中心参考点（非工厂位置）'};
 }
 return null;
}
function markerStyle(e,active){
 return {radius:active?7:5,color:active?'#ffffff':'#f8e8e2',weight:active?2.5:1.2,
 fillColor:active?'#82262c':'#b94b42',fillOpacity:0.94};
}
function selectEvent(e){
 app.selectedEvent=e.id; const county=app.featureLookup.get(e.id);
 if(county)app.selectedCounty=stateKey(county);
 renderSummary();
 app.eventMarkers.forEach((mk,id)=>mk.setStyle(markerStyle(app.events.find(r=>r.id===id),id===e.id)));
 if(e.point)app.map.panTo([e.point.lat,e.point.lon],{animate:true});
}
function openSource(e){
 return e.url&&/^https:\/\//.test(e.url) ? '<a target="_blank" rel="noopener noreferrer" href="'+esc(e.url)+'">查看原始公告或媒体来源 ↗</a>' : '<span>尚无可点击来源</span>';
}
function detail(e){
 $('eventDetail').hidden=false;
 $('eventDetail').innerHTML='<h3>'+esc(e.title)+'</h3>'
  +'<div class="meta">'+esc(e.company)+' · '+esc(e.city)+' · '+esc(STATE_ZH[e.state_iso]||e.state_iso)+' · '+esc(e.event_date||'日期待核')+'</div>'
  +'<p>事件：'+esc(e.event_type)+'<br>状态：'+esc(e.implementation_status)+'<br>涉及岗位：'+(e.jobs===null?'未取得可单独归属数字':esc(e.jobs)+'（'+esc(e.jobs_basis||'报告值')+'）')+'</p>'
  +(e.relocation_destination?'<p>转移去向：'+esc(e.relocation_destination)+'</p>':'')
  +(e.note?'<p>'+esc(e.note)+'</p>':'')
  +'<p>'+openSource(e)+'</p>'
  +'<div class="disclaimer">'+esc(e.point?.precision||'位置未核实，不在地图标点')+'；计划影响人数≠已经失业人数。'+(e.shared_program_id?' 关联计划：'+esc(e.shared_program_id):'')+'</div>';
}
function listRows(rows){
 const sorted=[...rows].sort((a,b)=>(b.isMajor-a.isMajor)||(b.jobs??0)-(a.jobs??0)||String(b.event_date).localeCompare(String(a.event_date)));
 const slice=sorted.slice(0,30);
 $('listCount').textContent=sorted.length+'条记录';
 $('eventList').innerHTML=slice.map(e=>'<button type="button" class="industry-row '+(app.selectedEvent===e.id?'selected':'')+'" data-id="'+esc(e.id)+'">'
  +'<div class="name"><span>'+esc(e.company)+'</span><span class="industry-date">'+esc(e.event_date?.slice(0,10)||'')+'</span></div>'
  +'<div class="subtitle">'+esc(e.title)+' · '+(e.isPlan?'计划/待实施核查':'已有实施证据')+(e.jobs!==null?' · '+esc(e.jobs)+'岗（非实际失业数）':'')+'</div></button>').join('')
  +(sorted.length>30?'<div class="area-note">优先显示前30条重要记录；按地区点击查看更多本地事件。</div>':'');
 $('eventList').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{const ev=app.events.find(e=>e.id===b.dataset.id);if(ev){selectEvent(ev);detail(ev);}}));
}
function renderSummary(){
 let records,area,official=null;
 if(app.selectedCounty){
  const feat=app.features.find(f=>stateKey(f)===app.selectedCounty);
  records=app.byCounty.get(app.selectedCounty)||[];
  area=feat?nameZh(feat.properties.name):'选定地区';
  if(feat)official=officialMetricFor(feat);
 } else {records=app.events;area='德国全国';}
 $('areaName').textContent=area;
 $('areaEvents').textContent=records.length;
 $('areaMajor').textContent=records.filter(e=>e.isMajor).length;
 $('areaPlans').textContent=records.filter(e=>e.isPlan).length;
 $('areaMetric').textContent=official?'2019至最新同口径制造业就业变化：'+official.change_pct.toFixed(1)+'%':
   (app.selectedCounty?'本地区收录事件数量；非工业就业下降率':'各州已收录重大工业收缩新闻档案');
 $('riskBadge').textContent=official?'官方就业变化':'事件样本';
 $('riskBadge').className='risk-badge '+(official&&official.change_pct<=-10?'high':'mid');
 if(!app.selectedEvent){$('eventDetail').hidden=true;$('eventDetail').innerHTML='';}
 listRows(records);
}
function selectCounty(f){
 app.selectedCounty=stateKey(f);app.selectedEvent=null;renderSummary();
}
async function start(){
 const sources=['../../data/germany-counties.geojson','../../data/germany-states.geojson',
   'research/r1-events.json','research/r2-r3-events.json','../../data/geocode_cache.json',
   'data/county-employment.json','research/r4-events-and-updates.json','research/r5a-eurofound-sites.json','research/r5b-manufacturing-cases.json','data/ags-crosswalk-402-to-400.json','research/r5c-screened-manufacturing.json','research/r5d-2025-factory-closures.json','research/r6-events.json',
   'research/r7a-screened-2026-events.json','research/r7b-2025-retrospective.json',
   'research/r7-legacy-identity-audit.json','research/r7c-plant-closures-offshoring.json',
   'research/r7d-2024-company-primary-audited.json','research/r7e-2025-undercovered-sites.json'];
 const results=await Promise.all(sources.map(async src=>{
  const r=await fetch(src,{cache:'no-store'});if(!r.ok)throw Error(src+': HTTP '+r.status);return r.json();
 }));
 const [counties,states,r1,r2,geocache,metric,r4,r5a,r5b,agsCrosswalk,r5c,r5d,r6,r7a,r7b,r7audit,r7c,r7d,r7e]=results;
 if(!Array.isArray(counties.features)||counties.features.length!==402||!Array.isArray(states.features)||states.features.length!==16)
  throw Error('官方边界记录数量异常');
 if(r1.events.length!==61||r2.events.length!==38||r4.events.length!==18||r5a.events.length!==10||r5b.events.length!==16||r5c.events.length!==12||r5d.events.length!==18||r6.events.length!==1||r7a.events.length!==10||r7b.events.length!==11||r7c.events.length!==7||r7d.events.length!==13||r7e.events.length!==5)throw Error('事件档案数量异常');
 if(agsCrosswalk.features.length!==402||agsCrosswalk.canonical_ags_distinct!==400)throw Error('地区AGS对照表无效');
 const agsIds=new Set(counties.features.map(f=>f.id));
 if(agsIds.size!==402||[...agsIds].some(id=>!/^\d{5}$/.test(id)))throw Error('县市AGS缺失/重复');
 app.agsRemap=agsCrosswalk.canonical_remaps;
 if(new Set(counties.features.map(stateKey)).size!==400)throw Error('现行县市AGS数量不符');
 app.features=counties.features;app.countyGeo=counties;app.metric=metric;
 const allRaw=[...r1.events,...r2.events,...r4.events,...r5a.events,...r5b.events,...r5c.events,...r5d.events,...r6.events,...r7a.events,...r7b.events,...r7c.events,...r7d.events,...r7e.events];
 const patches={...(r4.updates||{}),...(r7audit.updates||{})};
 for(const [id,patch] of Object.entries(patches)){
  const original=allRaw.find(e=>e.event_id===id);
  if(!original)throw Error('找不到需修订的事件 '+id);
  Object.assign(original,patch);
 }
 app.events=allRaw.map(e=>normalize(e,e.batch||'R1'));
 const ids=new Set();for(const e of app.events){if(!e.id||ids.has(e.id)||!e.url)throw Error('事件重复ID或缺失来源 '+e.id);ids.add(e.id);}
 app.map=L.map('industry-map',{zoomControl:true,preferCanvas:true,minZoom:5,maxZoom:14}).fitBounds(POLYGON_BOUNDS);
 L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
   {maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(app.map);
 app.map.createPane('countyPane');app.map.getPane('countyPane').style.zIndex='350';
 app.counties=L.geoJSON(counties,{pane:'countyPane',style:countyStyle,onEachFeature:(f,l)=>{
  l.on('click',()=>selectCounty(f));
  l.on('mouseover',()=>l.setStyle({weight:1.75,color:'#3b627d'}));
  l.on('mouseout',()=>app.counties.resetStyle(l));
  l.bindTooltip((app.agsRemap[f.id]?'历史县界 · 已并入现行区域：':'')+nameZh(f.properties.name),{sticky:true,direction:'auto',className:'industry-tip'});
 }}).addTo(app.map);
 L.geoJSON(states,{interactive:false,style:{weight:1.1,color:'#43596b',fillOpacity:0}}).addTo(app.map);
 app.markers=L.layerGroup().addTo(app.map);
 for(const e of app.events){
  const county=getCounty(e);
  if(county){
   app.featureLookup.set(e.id,county);
   const key=stateKey(county);
   if(!app.byCounty.has(key))app.byCounty.set(key,[]);
   app.byCounty.get(key).push(e);
  }
  e.point=getMapPoint(e,county,geocache);
  if(!e.isMajor||!e.point)continue;
  const mk=L.circleMarker([e.point.lat,e.point.lon],markerStyle(e,false))
    .bindTooltip(esc(e.company)+' · '+esc(e.city)+' · '+esc(e.point.precision),
      {className:'industry-tip'});
  mk.on('click',()=>{selectEvent(e);detail(e);});
  mk.addTo(app.markers);app.eventMarkers.set(e.id,mk);
 }
 app.counties.setStyle(countyStyle);
 createLegend();renderSummary();
 $('viewGermany').addEventListener('click',()=>{
  app.selectedCounty=null;app.selectedEvent=null;renderSummary();app.map.fitBounds(POLYGON_BOUNDS);
  app.eventMarkers.forEach((mk,id)=>mk.setStyle(markerStyle(app.events.find(x=>x.id===id),false)));
 });
 $('showMarkers').addEventListener('change',evt=>{
  if(evt.target.checked)app.map.addLayer(app.markers);else app.map.removeLayer(app.markers);
 });
 $('mapStatus').style.display='none';
 window.GermanIndustryQA=Object.freeze({records:app.events.length,states:states.features.length,
  counties:counties.features.length,modernCounties:new Set(counties.features.map(stateKey)).size,major:app.events.filter(e=>e.isMajor).length,
  mappedCounties:app.byCounty.size,pointMarkers:app.eventMarkers.size,
  officialCoverage:Object.keys(metric.records||{}).length});
}
start().catch(err=>{console.error(err);$('mapStatus').textContent='工业地图资料加载失败：'+String(err.message||err);
 $('areaMetric').textContent='加载失败；保留错误信息，不以空数据替代。';});
})();
