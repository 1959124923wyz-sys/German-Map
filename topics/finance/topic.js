(() => {
 'use strict';
 const $ = id => document.getElementById(id);
 const D = window.GermanFinance08Data;
 const H = window.GermanFinance08History;
 const I = window.GermanFinance08Integrated;
 const escapeHTML = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const STATUSES={effective:'已生效/执行中（未必仍持续）',completed:'已经完成（可能是历史）',reversed:'已撤销或解除',withdrawn:'已撤回',adopted:'已批准、未证实执行',announced:'已宣布',proposed:'仅提议',rejected:'被否决',under_review:'审议或核查中'};
 const CAT={budget:'预算及监管',facilities:'公共设施及文化',transit:'公共交通',investment:'公共投资',staffing:'人事编制',taxfees:'税费',other:'其他'};
 const MODE={state:'2025年地方财政人均收支 · 13个非城市州',rp:'2025年莱法州12个非县辖市人均财政收支',events:'财政事件 · 县域汇总锚点'};
 const initial={mode:'state',showEvents:false,category:'all',status:'all',archive:false,selected:null,county:null,limit:8,rpPeriod:'2025-full-cities',stateMetric:'balance-2025',focusState:null};
 let view={...initial}, map, statesLayer, countiesLayer, bubblesLayer;
 let stateRows=new Map(D.states.map(x=>[x.id,x])), cityRows=new Map(D.cities.map(x=>[x.id,x]));
 const debtRows=new Map(H.states.map(x=>[x.id,x]));
 const integratedRows=new Map(I.states.map(x=>[x.id,x]));
 const isIntegrated=()=>view.stateMetric.startsWith('integrated-');
 const metricYear=()=>view.stateMetric.split('-')[1];
 const selectedStateValue=id=>{
  if(isIntegrated())return integratedRows.get(id)?.per_capita_eur[metricYear()]??null;
  return stateRows.get(id)?.value??null;
 };
 const selectedStateSource=id=>isIntegrated()?I.meta.source:stateRows.get(id)?.source;
 const selectedStateLabel=()=>isIntegrated()?metricYear()+'年人均综合债务':'2025年人均财政收支';
 const selectedStateNote=()=>isIntegrated()
  ? '综合市镇债务包括预算与按持股比例分摊的市属企业债务；不是城市/州政府破产风险，也不同于2025年短期借款。'
  : '2025年非城市州辖内地方政府人均收支差额；不能把事件样本数当作财政困难程度。';
 const stateMetricText=value=>value==null?'无同口径数据':isIntegrated()?number(value)+' 欧元/人':money(value);
 const integratedColor=value=>{
  if(value==null||!Number.isFinite(value))return '#82909a';
  if(value<3000)return '#c3dfdf';
  if(value<4000)return '#95bfce';
  if(value<4500)return '#6d9fbf';
  if(value<5000)return '#4c81af';
  if(value<6000)return '#345f92';
  return '#27476b';
 };
 const regionalRows=new Map(H.regional.map(x=>[x.period+'|'+x.scope+'|'+x.id,x]));
 const regionOptions={
  '2025-full-cities':{label:'2025全年 · 12座非县辖市',scope:'city',period:'2025-full',count:12},
  '2025-H1-cities':{label:'2025上半年 · 12座非县辖市',scope:'city',period:'2025-H1',count:12},
  '2026-H1-cities':{label:'2026上半年 · 12座非县辖市',scope:'city',period:'2026-H1',count:12},
  '2026-H1-counties':{label:'2026上半年 · 24县政府本级',scope:'county_budget_only',period:'2026-H1',count:24}
 };
 let allCountyShapes=new Map(), stateGeo=null, countyGeo=null;
 const readyCases=D.cases.filter(x=>x.map_ready);
 const withinBounds=L.latLngBounds([[47.15,5.4],[55.1,15.6]]);
 const number=n=>new Intl.NumberFormat('zh-CN',{maximumFractionDigits:1}).format(n);
 const money=n=>n===null||n===undefined?'无数据':(n>0?'+':'')+number(n)+' 欧元/人';
 function color(x){if(x===null||x===undefined||!Number.isFinite(x))return '#82909a'; if(x>=0)return '#6a9f8e';if(x< -550)return '#963f41';if(x< -450)return '#ae5957';if(x< -350)return '#c27666';if(x< -250)return '#d3997b';if(x< -150)return '#e0b597';return '#edd4b4'}
 function showStatus(msg,delay=false){$('mapStatus').textContent=msg;$('mapStatus').hidden=!msg;}
 function stateStyle(feature){
  const id=feature.properties?.id, value=selectedStateValue(id);
  return {color:id===view.focusState?'#f4f8fa':'#51616b',weight:id===view.focusState?2:1,
   fillColor:isIntegrated()?integratedColor(value):color(value),fillOpacity:.8};
 }
 function regionalRow(id){
  if(view.rpPeriod==='2025-full-cities')return cityRows.get(id);
  const q=regionOptions[view.rpPeriod];
  return regionalRows.get(q.period+'|'+q.scope+'|'+id);
 }
 function cityStyle(feature){const v=regionalRow(feature.id)?.value;return{color:'#577281',weight:.8,fillColor:color(v),fillOpacity:v===undefined?0.03:0.84}}
 const billion=value=>(value/100).toFixed(2)+'亿欧元';
 function renderLoanHistory(stateId){
  $('loanDrawer').hidden=view.mode!=='state';
  if(view.mode!=='state')return;
  const row=debtRows.get(stateId)||null;
  const data=row?{cash:row.cash,investment:row.investment}:H.totals;
  if(stateId&&!row){$('loanDrawer').hidden=true;return;}
  $('loanScope').textContent=row?'所选州':'13州合计';
  const rows=H.meta.years.map((y,i)=>'<tr><td>'+y+'</td><td>'+billion(data.cash[i])+'</td><td>'+billion(data.investment[i])+'</td></tr>').join('');
  const integrated=stateId?integratedRows.get(stateId):null;
  const integratedInfo=integrated&&integrated.per_capita_eur['2024']!=null
   ? '<div class="finance-loan-integrated"><strong>综合地方债务（欧元/人）</strong>'+
     '<div class="finance-loan-integrated-grid">'+I.meta.years.map(y=>'<span><small>'+y+'</small><b>'+
        number(integrated.per_capita_eur[String(y)])+'</b></span>').join('')+'</div>'+
     '<p>含按比例分摊的市属企业债务；与下方借款存量不可相加。'+
     '<a target="_blank" rel="noopener noreferrer" href="'+escapeHTML(I.meta.source)+'">Destatis原始表 ↗</a></p></div>':'';
  $('loanHistory').innerHTML=integratedInfo+'<div class="finance-loan-totals"><div><small>2025短期借款</small><strong>'+billion(data.cash[4])+'</strong></div><div><small>2025投资借款</small><strong>'+billion(data.investment[4])+'</strong></div></div>'+
   '<table><thead><tr><th>年末</th><th>短期借款</th><th>投资借款</th></tr></thead><tbody>'+rows+'</tbody></table>'+
   '<p>存量金额（非人均）；不同州规模不能据此直接排名。2024年债务承接等政策可能影响历史变化。'+
   '<a target="_blank" rel="noopener noreferrer" href="'+escapeHTML(H.meta.source_debt)+'">2026地方财政报告（表9、10） ↗</a></p>';
 }
 function regionalDetailNote(row){
  const opt=regionOptions[view.rpPeriod];
  if(!row)return opt.label+'；该地区无同口径数据。';
  let s=opt.label+'。'+(opt.scope==='county_budget_only'?'县政府本级预算，不含下属市镇。':'非县辖市预算。');
  if(Number.isFinite(row.operating_eur))s+=' 日常收支：'+(row.operating_eur/1e6).toFixed(1)+'百万欧元；资本收支：'+(row.capital_eur/1e6).toFixed(1)+'百万欧元。';
  return s;
 }
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
  if(view.mode==='state'){
   const year=metricYear();
   displayArea('德国 · 13个非城市州','点击州查看人均数值',
     isIntegrated()?'综合市镇债务含企业分摊；3个城市州不适用，灰色不是零。':'3个城市州无同口径值，以灰色表示。');
  }else if(view.mode==='rp'){
   const o=regionOptions[view.rpPeriod];
   displayArea('莱茵兰-普法尔茨州 · '+o.count+'地区','点击地图查看人均收支',
    o.scope==='county_budget_only'?'县政府本级收支，不含下属市镇。':'仅非县辖市；全年和半年不可直接比较。');
  }else displayArea('德国 · 县域财政事件','72条地图候选（精选案例）',
   '事件圆点为县域中心示意，不是具体设施位置。');
  renderLoanHistory(view.mode==='state'?view.focusState:null);
 }

 function renderLegend(){
  if(view.mode==='events'){
   $('legend').innerHTML='<div class="legend-title">财政事件 · 县域汇总</div>'+
    '<div class="finance-legend-note">圆点是关联记录数量，位置不是具体设施坐标。</div>';
   return;
  }
  if(view.mode==='state'&&isIntegrated()){
   const ramp=['#c3dfdf','#95bfce','#6d9fbf','#4c81af','#345f92','#27476b'];
   $('legend').innerHTML='<div class="legend-title">综合市镇债务 · '+metricYear()+' · 欧元/人</div>'+
    '<div class="finance-legend-scale" style="grid-template-columns:repeat(6,1fr)">'+ramp.map(c=>'<span style="background:'+c+'"></span>').join('')+'</div>'+
    '<div class="finance-legend-labels"><span>&lt;3000</span><span>4000</span><span>5000</span><span>≥6000</span></div>'+
    '<div class="finance-legend-empty"><i></i>城市州：不适用</div>'+
    '<div class="finance-legend-note">蓝色仅代表债务数值大小，不等于财政破产风险。</div>';
   return;
  }
  const colors=['#963f41','#ae5957','#c27666','#d3997b','#e0b597','#edd4b4','#6a9f8e'];
  $('legend').innerHTML='<div class="legend-title">人均财政收支差额 · 欧元/人</div>'+
   '<div class="finance-legend-scale">'+colors.map(c=>'<span style="background:'+c+'"></span>').join('')+'</div>'+
   '<div class="finance-legend-labels"><span>−550 以下</span><span>−350</span><span>−150</span><span>盈余 ≥ 0</span></div>'+
   '<div class="finance-legend-empty"><i></i>灰色：无同口径数据</div>'+
   '<div class="finance-legend-note">'+(view.mode==='rp'?escapeHTML(regionOptions[view.rpPeriod].label+'；其他地区不涂色'):'2025年非城市州地方政府财政收支')+'</div>';
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
 function displaySelectedState(id,name){
  view.focusState=id;
  displayArea(name||integratedRows.get(id)?.name||id,stateMetricText(selectedStateValue(id)),
   selectedStateNote(),selectedStateSource(id));
  renderLoanHistory(id);
  if(statesLayer)statesLayer.setStyle(stateStyle);
 }
 function buildMapLayers(){
  // Exactly once per boot: cached county geometry is shared across all three views.
  statesLayer=L.geoJSON(stateGeo,{style:stateStyle,onEachFeature:(feature,layer)=>{
   const id=feature.properties?.id,name=feature.properties?.name||id;
   layer.bindTooltip('');
   layer.on('mouseover',()=>layer.setTooltipContent(escapeHTML(name)+' · '+escapeHTML(stateMetricText(selectedStateValue(id)))));
   layer.on('click',()=>{
    view.county=null;renderList();displaySelectedState(id,name);
   });
  }});
  countiesLayer=L.geoJSON(countyGeo,{
   style:feature=>view.mode==='rp'?cityStyle(feature):{color:'#647e8a',weight:.65,fillColor:'#a9c5d3',fillOpacity:.05},
   onEachFeature:(feature,layer)=>{
    allCountyShapes.set(feature.id,layer);
    layer.on('click',()=>{
     const row=regionalRow(feature.id);
     view.county=null;renderList();
     displayArea(feature.properties?.name||'县级地区',
      view.mode==='rp'?(row?money(row.value):'该层无数据'):'县级AGS '+feature.id,
      view.mode==='rp'?regionalDetailNote(row):'事件以县域近似中心显示，不代表设施精确位置。',row?.source);
    });
   }
  });
 }
 function renderMap(){
  if(!map||!statesLayer||!countiesLayer)return;
  if(view.mode==='state'){
   if(map.hasLayer(countiesLayer))map.removeLayer(countiesLayer);
   if(!map.hasLayer(statesLayer))statesLayer.addTo(map);
   statesLayer.setStyle(stateStyle);
  }else{
   if(map.hasLayer(statesLayer))map.removeLayer(statesLayer);
   if(!map.hasLayer(countiesLayer))countiesLayer.addTo(map);
   countiesLayer.setStyle(f=>view.mode==='rp'?cityStyle(f):
    {color:'#647e8a',weight:.65,fillColor:'#a9c5d3',fillOpacity:.05});
  }
  renderLegend();renderMarkers();
 }
 function selectMode(mode){
  if(!MODE[mode])return;
  const wasEvents=view.mode==='events';
  if(mode==='events'&&!wasEvents){view.overlayBeforeEvents=view.showEvents;view.showEvents=true;}
  else if(wasEvents&&mode!=='events')view.showEvents=Boolean(view.overlayBeforeEvents);
  view.mode=mode;view.selected=null;view.county=null;view.focusState=null;view.limit=8;
  $('showEvents').checked=view.showEvents;
  $('eventsControl').hidden=mode==='events';
  $('rpPeriodWrap').hidden=mode!=='rp';
  $('stateMetricWrap').hidden=mode!=='state';
  document.querySelectorAll('[data-mode]').forEach(el=>{
   const active=el.dataset.mode===mode;
   el.classList.toggle('active',active);el.setAttribute('aria-pressed',String(active));
  });
  const mapGuides={
   state:[isIntegrated()?'综合地方债务 · '+metricYear():'地方财政收支 · 2025','13个非城市州 · 点击州查看人均数值'],
   rp:['莱法州财政收支',regionOptions[view.rpPeriod].label+' · 点击地图查看'],
   events:['地方财政事件','县域汇总点，不是设施精确位置']
  };
  $('mapGuideTitle').textContent=mapGuides[mode][0];
  $('mapGuideNote').textContent=mapGuides[mode][1];
  $('sectionTitle').textContent=mode==='state'?selectedStateLabel():mode==='rp'?'莱法州 · '+regionOptions[view.rpPeriod].label:MODE[mode];
  resetArea();renderMap();renderList();
  if(map&&stateGeo){
   map.stop();
   if(mode==='rp'){
    const rp=stateGeo.features.find(f=>f.properties?.id==='DE-RP'||f.properties?.name==='Rheinland-Pfalz');
    if(rp)map.fitBounds(L.geoJSON(rp).getBounds(),{padding:[22,22],maxZoom:8,animate:false});
   }else map.fitBounds(withinBounds,{animate:false,padding:[12,12]});
  }
 }
 function updateFilters(){view.category=$('category').value;view.status=$('status').value;view.county=null;view.limit=8;view.selected=null;resetArea();renderList();renderMarkers()}
 function setupUI(){
  document.querySelectorAll('[data-mode]').forEach(el=>el.addEventListener('click',()=>selectMode(el.dataset.mode)));
  $('showEvents').addEventListener('change',()=>{view.showEvents=$('showEvents').checked;renderMarkers()});
  $('stateMetric').addEventListener('change',()=>{
   const value=$('stateMetric').value;
   if(!['balance-2025','integrated-2024','integrated-2023','integrated-2022'].includes(value))return;
   view.stateMetric=value;view.selected=null;
   $('sectionTitle').textContent=selectedStateLabel();
   $('countStateLabel').textContent=isIntegrated()?'综合债务数据':'州级收支数据';
   $('mapGuideTitle').textContent=isIntegrated()?'综合地方债务 · '+metricYear():'地方财政收支 · 2025';
   $('mapGuideNote').textContent='13个非城市州 · 点击州查看人均数值';
   renderMap();
   if(view.focusState){
    const layer=statesLayer.getLayers().find(l=>l.feature?.properties?.id===view.focusState);
    displaySelectedState(view.focusState,layer?.feature?.properties?.name);
   }else resetArea();
  });
  $('rpPeriod').addEventListener('change',()=>{
   const v=$('rpPeriod').value;
   if(!regionOptions[v])return;
   view.rpPeriod=v;view.selected=null;view.county=null;view.limit=8;
   $('sectionTitle').textContent='莱法州 · '+regionOptions[v].label;
   $('mapGuideNote').textContent=regionOptions[v].label+' · 点击地图查看';
   resetArea();renderMap();renderList();
  });
  $('resetView').addEventListener('click',()=>{view.archive=false;view.showEvents=false;view.overlayBeforeEvents=false;view.category='all';view.status='all';$('category').value='all';$('status').value='all';view.rpPeriod='2025-full-cities';$('rpPeriod').value=view.rpPeriod;view.stateMetric='balance-2025';$('stateMetric').value=view.stateMetric;toggleArchive();selectMode('state')});
  $('category').addEventListener('change',updateFilters);$('status').addEventListener('change',updateFilters);
  $('showMapCases').addEventListener('click',()=>{view.archive=false;view.limit=8;toggleArchive();renderList();renderMarkers()});
  $('showAllCases').addEventListener('click',()=>{view.archive=true;view.limit=8;toggleArchive();renderList();renderMarkers()});
  $('loadMore').addEventListener('click',()=>{view.limit+=20;renderList()});
 }
 function toggleArchive(){for(const [id,yes] of [['showMapCases',!view.archive],['showAllCases',view.archive]]){
   const el=$(id);el.classList.toggle('active',yes);el.setAttribute('aria-pressed',String(yes))}}
 async function boot(){
  if(!D||D.cases.length!==170||readyCases.length!==72)throw Error('财政数据不完整或版本不匹配');
  if(!H||H.states.length!==13||H.regional.length!==72||H.totals.cash[4]!==38587)throw Error('历史财政数据不完整');
  if(!I||I.states.length!==16||I.meta.years.length!==3)throw Error('综合地方债务数据不完整');
  setupUI();resetArea();renderList();renderLegend();
  map=L.map('finance-map',{zoomSnap:.25,minZoom:5,maxZoom:13,zoomControl:true,preferCanvas:true});
  window.__FINANCE_MAP__=map;
  map.fitBounds(withinBounds,{animate:false,padding:[12,12]});
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
  buildMapLayers();
  renderMap();showStatus('');
 }
 document.addEventListener('DOMContentLoaded',()=>{boot().catch(err=>{console.error(err);showStatus('财政专题加载失败：'+err.message+'。可查看研究档案和来源说明。')})});
})();