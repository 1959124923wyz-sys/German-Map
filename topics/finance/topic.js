(() => {
 'use strict';
 const $ = id => document.getElementById(id);
 const D = window.GermanFinance08Data;
 const escapeHTML = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const STATUSES={effective:'已生效/执行中（未必仍持续）',completed:'已经完成（可能是历史）',reversed:'已撤销或解除',withdrawn:'已撤回',adopted:'已批准、未证实执行',announced:'已宣布',proposed:'仅提议',rejected:'被否决',under_review:'审议或核查中'};
 const CAT={budget:'预算及监管',facilities:'公共设施及文化',transit:'公共交通',investment:'公共投资',staffing:'人事编制',taxfees:'税费',other:'其他'};
 const MODE={state:'2025年地方财政人均收支 · 13个非城市州',rp:'2025年莱法州12个非县辖市人均财政收支',events:'财政事件 · 县域汇总锚点'};
 const initial={mode:'state',showEvents:false,category:'all',status:'all',archive:false,selected:null,county:null,limit:8};
 let view={...initial}, map, statesLayer, countiesLayer, bubblesLayer;
 let stateRows=new Map(D.states.map(x=>[x.id,x])), cityRows=new Map(D.cities.map(x=>[x.id,x]));
 let allCountyShapes=new Map(), stateGeo=null, countyGeo=null;
 const readyCases=D.cases.filter(x=>x.map_ready);
 const withinBounds=L.latLngBounds([[47.15,5.4],[55.1,15.6]]);
 const number=n=>new Intl.NumberFormat('zh-CN',{maximumFractionDigits:1}).format(n);
 const money=n=>n===null||n===undefined?'无数据':(n>0?'+':'')+number(n)+' 欧元/人';
 function color(x){if(x===null||x===undefined||!Number.isFinite(x))return '#82909a'; if(x>=0)return '#6a9f8e';if(x< -550)return '#963f41';if(x< -450)return '#ae5957';if(x< -350)return '#c27666';if(x< -250)return '#d3997b';if(x< -150)return '#e0b597';return '#edd4b4'}
 function showStatus(msg,delay=false){$('mapStatus').textContent=msg;$('mapStatus').hidden=!msg;}
 function stateStyle(feature){const v=stateRows.get(feature.properties?.id)?.value;return{color:'#51616b',weight:1.0,fillColor:color(v),fillOpacity:0.8}}
 function cityStyle(feature){const v=cityRows.get(feature.id)?.value;return{color:'#577281',weight:.8,fillColor:color(v),fillOpacity: v===undefined?0.03:0.84}}
 function displayArea(title,value,note,source){
  $('areaName').textContent=title;
  $('metricValue').textContent=value;
  $('coverageNote').textContent=note;
  if(!view.selected){$('detail').hidden=true;$('detail').innerHTML='';}
  if(source && /^https:\/\//.test(source)){
   $('coverageNote').append(' ');
   const a=document.createElement('a');a.href=source;a.target='_blank';a.rel='noopener noreferrer';a.textContent='统计原始来源 ↗';a.style.color='#94c9e9';$('coverageNote').appendChild(a);
  }
 }
 function resetArea(){
  if(view.mode==='state') displayArea('全国（13个非城市州）','2025年地方政府人均财政收支','德国16州中仅13个非城市州有这一市镇财政统计口径；3个城市州灰色不是零。');
  else if(view.mode==='rp') displayArea('莱茵兰-普法尔茨州 · 12城市','12个非县辖市，2025年全年','只涂12个非县辖市，普通县本级预算不在同一比较范围。');
  else displayArea('德国 · 县域财政事件','72条地图候选（精选案例）','圆点显示每个县域关联的记录数，位置不是具体设施地址；存在撤销及历史已结束措施。');
 }
 function renderLegend(){
  const notes={
   state:'2025年非城市州地方政府人均财政收支',
   rp:'2025年莱法州12个非县辖市；其他县市不涂色',
   events:'数字表示县域关联记录数，非设施定位'
  };
  if(view.mode==='events'){
   $('legend').innerHTML='<div class="legend-title">财政事件 · 县域汇总</div>'+
    '<div class="finance-legend-note">圆点是关联记录数量，位置不是具体设施坐标。</div>';
   return;
  }
  const colors=['#963f41','#ae5957','#c27666','#d3997b','#e0b597','#edd4b4','#6a9f8e'];
  $('legend').innerHTML='<div class="legend-title">人均财政收支差额 · 欧元/人</div>'+
   '<div class="finance-legend-scale">'+colors.map(c=>'<span style="background:'+c+'"></span>').join('')+'</div>'+
   '<div class="finance-legend-labels"><span>−550 以下</span><span>−350</span><span>−150</span><span>盈余 ≥ 0</span></div>'+
   '<div class="finance-legend-empty"><i></i>灰色：无同口径数据</div>'+
   '<div class="finance-legend-note">'+escapeHTML(notes[view.mode])+'</div>';
 }
 function caseSource(row){
  const a=[['原始来源',row.source],['补充来源',row.source2]].filter(x=>/^https:\/\//.test(x[1]));
  return a.map(([label,url])=>`<a target="_blank" rel="noopener noreferrer" href="${escapeHTML(url)}">${label} ↗ ${escapeHTML(url)}</a>`).join('');
 }
 function chooseRecord(id){
  const r=D.cases.find(x=>x.id===id);if(!r)return;
  view.selected=id;
  const t=$('detail');t.hidden=false;
  t.innerHTML=`<h3>${escapeHTML(r.city)} · ${escapeHTML(r.facility || CAT[r.category] || '地方财政措施')}</h3>`+
   `<div class="finance-info-row">记录 ${escapeHTML(r.id)} · ${escapeHTML(STATUSES[r.status])} · ${escapeHTML(r.decision||'决议日期未知')}</div>`+
   `<div class="finance-info-row">${escapeHTML(r.state)} · ${escapeHTML(r.geo_level)} · ${r.map_ready?'可在县域聚合上图':'档案记录（不独立上图）'}</div>`+
   `<p>${escapeHTML(r.description)}</p>`+
   (r.amount!==null?`<p><strong>原始金额：${escapeHTML(number(r.amount))} 欧元</strong> · ${escapeHTML(r.amount_kind||'金额性质待核，不可合计')}</p>`:'')+
   (r.note?`<p><strong>证据限制：</strong>${escapeHTML(r.note)}</p>`:'')+
   (r.parent?`<p>关联上级事件：${escapeHTML(r.parent)}；同一项目不得重复汇总金额。</p>`:'')+
   `<div class="finance-info-row">末次资料核对：${escapeHTML(r.verified||'未说明')} · ${escapeHTML(r.source_page)}</div>` +caseSource(r);
  $('detail').scrollIntoView({block:'nearest',behavior:'auto'});
  renderList();
 }
 function passFilters(r){
  if(!view.archive&&!r.map_ready)return false;
  if(view.category!=='all'&&view.category!==r.category)return false;
  if(view.status==='implemented'&&!['effective','completed'].includes(r.status))return false;
  if(view.status==='ended'&&!['reversed','withdrawn'].includes(r.status))return false;
  if(view.county&&r.county!==view.county)return false;
  return true;
 }
 function relevantCases(){return D.cases.filter(passFilters).sort((a,b)=>(b.effective||b.decision||'').localeCompare(a.effective||a.decision||'')||a.id.localeCompare(b.id))}
 function renderList(){
  const entries=relevantCases(), limit=entries.slice(0,view.limit);
  $('mappedCount').textContent=readyCases.length;
  const countyName=view.county?(allCountyShapes.get(view.county)?.feature?.properties?.name||view.county):'';
  $('listHeading').textContent=countyName?countyName+' · 事件':(view.archive?'全部研究档案':'已核实的地方事件');
  $('visibleCount').textContent=entries.length+'条 · 定向样本';
  $('caseList').innerHTML=limit.map(r=>`<button type="button" class="finance-case ${view.selected===r.id?'selected':''}" data-case="${escapeHTML(r.id)}"><div class="finance-case-title">${escapeHTML(r.city)} · ${escapeHTML(r.facility||CAT[r.category])}</div><div class="finance-case-meta">${escapeHTML(STATUSES[r.status])} · ${escapeHTML(r.effective||r.decision||'日期待核')} ${r.map_ready?'':'· 档案记录'}</div></button>`).join('') || '<p class="finance-coverage">本次筛选无匹配记录，不代表当地没有财政事件。</p>';
  $('loadMore').hidden=entries.length<=view.limit;
  $('caseList').querySelectorAll('[data-case]').forEach(el=>el.addEventListener('click',()=>chooseRecord(el.dataset.case)));
 }
 function renderMarkers(){
  if(!bubblesLayer)return;
  bubblesLayer.clearLayers();if(!view.showEvents)return;
  const byCounty=new Map();
  for(const r of readyCases){if(!passFilters(r))continue;const a=byCounty.get(r.county)||[];a.push(r);byCounty.set(r.county,a)}
  for(const [code,rows] of byCounty){
   const layer=allCountyShapes.get(code);if(!layer)continue;
   const p=layer.getBounds().getCenter();
   const html=`<div class="finance-bubble-inner ${rows.length>3?'many':''}">${rows.length}</div>`;
   L.marker(p,{icon:L.divIcon({html,className:'finance-bubble',iconSize:[34,34],iconAnchor:[17,17]}),keyboard:true,
     title:`县级AGS ${code} · ${rows.length}条有来源记录（县域示意位置）`})
    .bindTooltip(`${escapeHTML(rows[0].city)} 等 · ${rows.length}条记录<br>县域聚合，非设施精确地址`)
    .on('click',()=>{view.county=code;view.archive=false;view.limit=8;view.selected=null;toggleArchive();renderList();$('caseList').scrollTop=0;
      displayArea('县级AGS '+code,rows.length+'条地图候选记录','圆点标在县域概略中心。相同议会措施可有多条关联记录，不能解释为独立事件数。')})
    .addTo(bubblesLayer);
  }
 }
 function renderMap(){
  if(!map||!stateGeo||!countyGeo)return;
  if(statesLayer)map.removeLayer(statesLayer);
  if(countiesLayer)map.removeLayer(countiesLayer);
  statesLayer=null;countiesLayer=null;
  if(view.mode==='state'){
   statesLayer=L.geoJSON(stateGeo,{style:stateStyle,onEachFeature:(f,layer)=>{
    const row=stateRows.get(f.properties?.id);
    layer.bindTooltip(escapeHTML(f.properties?.name)+' · '+(row&&row.value!==null?escapeHTML(money(row.value)):'无同口径值'));
    layer.on('click',()=>{view.county=null;renderList();displayArea(f.properties?.name||'',row?money(row.value):'无同口径值','2025年非城市州辖内地方政府人均财政收支；不能与事件数量解释为因果。',row?.source)})
   }}).addTo(map);
  }else{
   countiesLayer=L.geoJSON(countyGeo,{style:f=>view.mode==='rp'?cityStyle(f):{color:'#647e8a',weight:.65,fillColor:'#a9c5d3',fillOpacity:.05},onEachFeature:(f,layer)=>{
    allCountyShapes.set(f.id,layer);
    layer.on('click',()=>{
     const row=cityRows.get(f.id);
     view.county=null;renderList();
     displayArea(f.properties?.name||'县级地区',view.mode==='rp'?(row?money(row.value):'该层无数据'):'县级AGS '+f.id,
      view.mode==='rp'?'仅12个非县辖市涂色；灰白/透明不等于财政平衡。':'事件以县域近似中心显示，不代表设施精确位置。',row?.source)
    })
   }}).addTo(map);
  }
  renderLegend();renderMarkers();
 }
 function selectMode(mode){
  if(!MODE[mode])return;
  const wasEvents=view.mode==='events';
  if(mode==='events'&&!wasEvents){view.overlayBeforeEvents=view.showEvents;view.showEvents=true;}
  else if(wasEvents&&mode!=='events')view.showEvents=Boolean(view.overlayBeforeEvents);
  view.mode=mode;view.selected=null;view.county=null;view.limit=8;
  $('showEvents').checked=view.showEvents;
  $('eventsControl').hidden=mode==='events';
  document.querySelectorAll('[data-mode]').forEach(el=>{
   const active=el.dataset.mode===mode;
   el.classList.toggle('active',active);el.setAttribute('aria-pressed',String(active));
  });
  const mapGuides={
   state:['地方财政收支 · 2025','13个非城市州 · 点击州查看人均收支'],
   rp:['城市收支 · 2025','莱茵兰-普法尔茨州 · 12座非县辖市'],
   events:['地方财政事件','县域汇总点，不是设施精确位置']
  };
  $('mapGuideTitle').textContent=mapGuides[mode][0];
  $('mapGuideNote').textContent=mapGuides[mode][1];
  $('sectionTitle').textContent=MODE[mode];
  resetArea();renderMap();renderList();
  if(map&&stateGeo){
   if(mode==='rp'){
    const rp=stateGeo.features.find(f=>f.properties?.id==='DE-RP'||f.properties?.name==='Rheinland-Pfalz');
    if(rp)map.fitBounds(L.geoJSON(rp).getBounds(),{padding:[22,22],maxZoom:8});
   }else map.fitBounds(withinBounds);
  }
 }
 function updateFilters(){view.category=$('category').value;view.status=$('status').value;view.county=null;view.limit=8;view.selected=null;resetArea();renderList();renderMarkers()}
 function setupUI(){
  document.querySelectorAll('[data-mode]').forEach(el=>el.addEventListener('click',()=>selectMode(el.dataset.mode)));
  $('showEvents').addEventListener('change',()=>{view.showEvents=$('showEvents').checked;renderMarkers()});
  $('resetView').addEventListener('click',()=>{view.archive=false;view.showEvents=false;view.overlayBeforeEvents=false;view.category='all';view.status='all';$('category').value='all';$('status').value='all';toggleArchive();selectMode('state')});
  $('category').addEventListener('change',updateFilters);$('status').addEventListener('change',updateFilters);
  $('showMapCases').addEventListener('click',()=>{view.archive=false;view.limit=8;toggleArchive();renderList();renderMarkers()});
  $('showAllCases').addEventListener('click',()=>{view.archive=true;view.limit=8;toggleArchive();renderList();renderMarkers()});
  $('loadMore').addEventListener('click',()=>{view.limit+=20;renderList()});
 }
 function toggleArchive(){for(const [id,yes] of [['showMapCases',!view.archive],['showAllCases',view.archive]]){
   const el=$(id);el.classList.toggle('active',yes);el.setAttribute('aria-pressed',String(yes))}}
 async function boot(){
  if(!D||D.cases.length!==170||readyCases.length!==72)throw Error('财政数据不完整或版本不匹配');
  setupUI();resetArea();renderList();renderLegend();
  map=L.map('finance-map',{zoomSnap:.25,minZoom:5,maxZoom:13,zoomControl:true,preferCanvas:true});map.fitBounds(withinBounds);
  const tile=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'});
  tile.addTo(map);
  if(window.CrimeCityLabels && window.GermanPlaceNames)window.CrimeCityLabels.create(map,{paneName:'financeCityLabels',zIndex:440});
  bubblesLayer=L.layerGroup().addTo(map);
  const [sf,cf]=await Promise.all([
   fetch('../../data/germany-states.geojson').then(r=>{if(!r.ok)throw Error('州界无法读取');return r.json()}),
   fetch('../../data/germany-counties.geojson').then(r=>{if(!r.ok)throw Error('县界无法读取');return r.json()})]);
  stateGeo=sf;countyGeo=cf;
  const countyIds=new Set(cf.features.map(f=>f.id));
  const unmatched=readyCases.filter(r=>!countyIds.has(r.county));
  if(unmatched.length)throw Error('地图候选县级AGS没有匹配的边界：'+unmatched.map(x=>x.id).join(','));
  for(const f of cf.features){const lyr=L.geoJSON(f);const first=lyr.getLayers()[0];if(first)allCountyShapes.set(f.id,first)}
  renderMap();showStatus('');
 }
 document.addEventListener('DOMContentLoaded',()=>{boot().catch(err=>{console.error(err);showStatus('财政专题加载失败：'+err.message+'。可查看研究档案和来源说明。')})});
})();