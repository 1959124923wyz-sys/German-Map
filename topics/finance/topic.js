(() => {
 'use strict';
 const $ = id => document.getElementById(id);
 const D = window.GermanFinance08Data;
 const H = window.GermanFinance08History;
 const I = window.GermanFinance08Integrated;
 const R = window.GermanFinance08Regional;
 const escapeHTML = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const STATUSES={effective:'已生效/执行中（未必仍持续）',completed:'已经完成（可能是历史）',reversed:'已撤销或解除',withdrawn:'已撤回',adopted:'已批准、未证实执行',announced:'已宣布',proposed:'仅提议',rejected:'被否决',under_review:'审议或核查中'};
 const CAT={budget:'预算及监管',facilities:'公共设施及文化',transit:'公共交通',investment:'公共投资',staffing:'人事编制',taxfees:'税费',other:'其他'};
 const initial={showEvents:false,metric:'balance-2025',category:'all',status:'all',archive:false,selected:null,county:null,limit:8,rpPeriod:'2025-full-cities',focusState:null};
 let view={...initial}, map, statesLayer, countiesLayer, bubblesLayer;
 let stateRows=new Map(D.states.map(x=>[x.id,x])), cityRows=new Map(D.cities.map(x=>[x.id,x]));
 const debtRows=new Map(H.states.map(x=>[x.id,x]));
 const integratedRows=new Map(I.states.map(x=>[x.id,x]));
 const countyDebtRows=new Map((R?.counties||[]).map(x=>[x.id,x]));
 const independentCityDebtRows=new Map((R?.cities||[]).map(x=>[x.id,x]));
 const municipalByState=new Map();
 const municipalPending=new Map();
 const historicalPalette=['#dce9e5','#c1dad1','#a0c7b9','#7cafa2','#569385','#357a70','#205d5e'];
 const numericForCounty=id=>view.metric==='core-2023'?(countyDebtRows.get(id)?.value??null):
  view.metric==='city-2024'?(independentCityDebtRows.get(id)?.integrated2024??null):null;
 const historicalValues=key=>key==='core-2023'?[...countyDebtRows.values()].map(x=>x.value).filter(Number.isFinite):
  [...independentCityDebtRows.values()].map(x=>x.integrated2024).filter(Number.isFinite);
 const historicalBreaks=key=>{
  const values=historicalValues(key).sort((a,b)=>a-b);
  return [0.15,0.30,0.45,0.60,0.75,0.90].map(p=>values[Math.round((values.length-1)*p)]);
 };
 const breaksByMetric={'core-2023':historicalBreaks('core-2023'),'city-2024':historicalBreaks('city-2024')};
 function historicFill(value,metric){
  if(!Number.isFinite(value))return '#82909a';
  let idx=0;const br=breaksByMetric[metric];while(idx<br.length&&value>br[idx])idx++;
  return historicalPalette[idx];
 }
 function currentMetricLabel(){
  return view.metric==='core-2023'?'2023年县域核心预算债务':
   view.metric==='city-2024'?'2024年非县辖市综合地方债务':'2025年人均地方财政收支';
 }
 // Public map always shows the 2025 municipal financing balance. The
 // historic debt series is preserved exclusively in the state drilldown.
 const selectedStateValue=id=>stateRows.get(id)?.value??null;
 const selectedStateSource=id=>stateRows.get(id)?.source;
 const selectedStateNote=()=> '2025年辖内地方政府财政收支';
 const stateMetricText=value=>value==null?'无可比数值':money(value);
 const regionalRows=new Map(H.regional.map(x=>[x.period+'|'+x.scope+'|'+x.id,x]));
 const regionOptions={
  '2025-full-cities':{label:'2025全年 · 12座非县辖市',scope:'city',period:'2025-full',count:12},
  '2025-H1-cities':{label:'2025上半年 · 12座非县辖市',scope:'city',period:'2025-H1',count:12},
  '2026-H1-cities':{label:'2026上半年 · 12座非县辖市',scope:'city',period:'2026-H1',count:12},
  '2026-H1-counties':{label:'2026上半年 · 24县政府本级',scope:'county_budget_only',period:'2026-H1',count:24}
 };
 let allCountyShapes=new Map(), stateGeo=null, countyGeo=null, countyDisplayedFor=null;
 const readyCases=D.cases.filter(x=>x.map_ready);
 const withinBounds=L.latLngBounds([[47.15,5.4],[55.1,15.6]]);
 const number=n=>new Intl.NumberFormat('zh-CN',{maximumFractionDigits:1}).format(n);
 const money=n=>n===null||n===undefined?'无数据':(n>0?'+':'')+number(n)+' 欧元/人';
 function color(x){if(x===null||x===undefined||!Number.isFinite(x))return '#82909a'; if(x>=0)return '#6a9f8e';if(x< -550)return '#963f41';if(x< -450)return '#ae5957';if(x< -350)return '#c27666';if(x< -250)return '#d3997b';if(x< -150)return '#e0b597';return '#edd4b4'}
 function showStatus(msg,delay=false){$('mapStatus').textContent=msg;$('mapStatus').hidden=!msg;}
 function stateStyle(feature){
  const id=feature.properties?.id, value=selectedStateValue(id);
  return {color:id===view.focusState?'#e6f2f8':'#4b5d66',weight:id===view.focusState?2.3:1,
   fillColor:color(value),fillOpacity:view.metric==='balance-2025'?.81:0};
 }
 function regionalRow(id){
  if(view.rpPeriod==='2025-full-cities')return cityRows.get(id);
  const q=regionOptions[view.rpPeriod];
  return regionalRows.get(q.period+'|'+q.scope+'|'+id);
 }
 function cityStyle(feature){const v=regionalRow(feature.id)?.value;return{color:'#577281',weight:.8,fillColor:color(v),fillOpacity:v===undefined?0.03:0.84}}
 const billion=value=>(value/100).toFixed(2)+'亿欧元';
 function renderLoanHistory(stateId){
  $('loanDrawer').hidden=!stateId;
  if(!stateId)return;
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
 function renderRegionalDebt(code){
  const drawer=$('regionalDebtDrawer'),body=$('regionalDebtInfo');
  const core=countyDebtRows.get(code),city=independentCityDebtRows.get(code);
  drawer.open=false;
  drawer.hidden=!(core||city);
  if(!core&&!city){body.innerHTML='';return;}
  const coreHtml=core
   ? '<div class="finance-history-item"><small>2023年县域市镇及联合体核心预算债务</small><strong>'+
      (core.value===null?'未公布':number(core.value)+' 欧元/人')+'</strong></div>'
   : '';
  const cityHtml=city
   ? '<div class="finance-history-item"><small>2024年非县辖市综合地方债务</small><strong>'+
      number(city.integrated2024)+' 欧元/人</strong></div>'
   : '';
  const countyLink=core?'<a href="'+escapeHTML(R.meta.county_source)+'" target="_blank" rel="noopener noreferrer">2023年官方区域统计原表 ↗</a>':'';
  const cityLink=city?'<a href="'+escapeHTML(R.meta.city_source)+'" target="_blank" rel="noopener noreferrer">2024年官方综合债务原表 ↗</a>':'';
  body.innerHTML=coreHtml+cityHtml+
   '<p>2023年数据为县域内市镇与联合体核心预算债务，不是县政府本级债务；2024年数据仅为非县辖市综合债务，包含其分摊的企业债务。年份、主体、范围不一致，不可相加或计算同比。无数据不等于零。历史行政边界未强行投射为2026年值。</p>'+
   countyLink+cityLink;
 }
 function regionalDetailNote(row){
  const opt=regionOptions[view.rpPeriod];
  if(!row)return opt.label+'；该地区无同口径数据。';
  let s=opt.label+'。'+(opt.scope==='county_budget_only'?'县政府本级预算，不含下属市镇。':'非县辖市预算。');
  if(Number.isFinite(row.operating_eur))s+=' 日常收支：'+(row.operating_eur/1e6).toFixed(1)+'百万欧元；资本收支：'+(row.capital_eur/1e6).toFixed(1)+'百万欧元。';
  s+=' 全年与半年不可直接比较。';
  return s;
 }
 function displayArea(title,value,note){
  $('areaName').textContent=title;
  $('metricValue').textContent=value;
  $('coverageNote').textContent=note||'';
  if(!view.selected){$('detail').hidden=true;$('detail').innerHTML='';}
 }
 function resetArea(){
  displayArea('德国 · 全国',
   view.metric==='balance-2025'?'点击联邦州查看财政收支':'点击县市查看所选年份债务',
   view.metric==='balance-2025'?'2025年 · 欧元/人':
    (view.metric==='core-2023'?'2023年 · 392个有数值县域 · 核心预算':'2024年 · 102个非县辖市 · 综合债务'));
  $('districtPanel').hidden=true;
  $('regionalDebtDrawer').hidden=true;
  $('regionalDebtDrawer').open=false;
  $('loanDrawer').hidden=true;
  $('municipalDrawer').hidden=true;
  $('municipalDrawer').open=false;
  $('sectionTitle').textContent=currentMetricLabel();
 }
 function renderLegend(){
  const colors=['#963f41','#ae5957','#c27666','#d3997b','#e0b597','#edd4b4','#6a9f8e'];
  $('legend').innerHTML='<div class="legend-title">2025人均收支差额 · 欧元/人</div>'+
   '<div class="finance-legend-scale">'+colors.map(c=>'<span style="background:'+c+'"></span>').join('')+'</div>'+
   '<div class="finance-legend-labels"><span>−550以下</span><span>−350</span><span>−150</span><span>盈余≥0</span></div>';
 }
 function preview(text,limit=48){
  const clean=String(text||'').replace(/\s+/g,' ').trim();
  return clean.length>limit?clean.slice(0,limit).replace(/[，；、 ]+$/,'')+'…':clean;
 }
 function caseSource(row){
  const a=[['原始来源',row.source],['补充来源',row.source2]].filter(x=>/^https:\/\//.test(x[1]));
  return a.map(([label,url])=>`<a target="_blank" rel="noopener noreferrer" href="${escapeHTML(url)}">${label} ↗ ${escapeHTML(url)}</a>`).join('');
 }
 function chooseRecord(id){
  const r=D.cases.find(x=>x.id===id);if(!r)return;
  view.selected=id;
  const t=$('detail');t.hidden=false;
  t.innerHTML=`<h3>${escapeHTML(r.city)} · ${escapeHTML(r.facility || CAT[r.category] || '财政措施')}</h3>`+
   `<div class="finance-info-row">${escapeHTML(STATUSES[r.status])} · ${escapeHTML(r.effective||r.decision||'日期待核')}</div>`+
   `<p>${escapeHTML(r.description)}</p>`+
   (r.amount!=null?`<p>涉及金额：${escapeHTML(number(r.amount))} 欧元 · ${escapeHTML(r.amount_kind||'原始金额')}</p>`:'')+
   `<details><summary>证据与来源</summary>`+
   (r.note?`<p>${escapeHTML(r.note)}</p>`:'')+
   `<p>记录 ${escapeHTML(r.id)} · ${escapeHTML(r.geo_level)} · 核验于 ${escapeHTML(r.verified||'未说明')}</p>`+
   caseSource(r)+`</details>`;
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
  $('caseList').innerHTML=limit.map(r=>`<button type="button" class="finance-case ${view.selected===r.id?'selected':''}" data-case="${escapeHTML(r.id)}" title="${escapeHTML(preview(r.description,115))}"><div class="finance-case-title">${escapeHTML(r.city)} · ${escapeHTML(r.facility||CAT[r.category])}</div><div class="finance-case-preview">${escapeHTML(preview(r.description))}</div><div class="finance-case-meta">${escapeHTML(r.effective||r.decision||'日期待核')} · ${escapeHTML(STATUSES[r.status])}</div></button>`).join('') || '<p class="finance-coverage">本次筛选无匹配记录。</p>';
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
    .bindTooltip('<strong>'+escapeHTML(rows[0].city)+' · '+rows.length+'条事件</strong><div>'+escapeHTML(preview(rows[0].description,54))+'</div><small>点击查看 · 县域示意位置</small>',{direction:'top',offset:[0,-11],className:'finance-event-tooltip',opacity:1})
    .on('click',()=>{view.county=code;view.archive=false;view.limit=8;view.selected=null;toggleArchive();renderList();$('caseList').scrollTop=0;
      $('eventPanel').hidden=false;
      $('listHeading').textContent='该县财政事件';
      // Keep state-level financial summary instead of replacing it with an
      // unrelated count; event counts do not constitute a fiscal indicator.
    })
    .addTo(bubblesLayer);
  }
 }
 function displaySelectedState(id,name){
  view.focusState=id;
  displayArea(name||integratedRows.get(id)?.name||id,stateMetricText(selectedStateValue(id)),
   selectedStateNote());
  renderLoanHistory(id);
  if(statesLayer)statesLayer.setStyle(stateStyle);
 }

 const AGS={ 'DE-SH':'01','DE-HH':'02','DE-NI':'03','DE-HB':'04','DE-NW':'05',
  'DE-HE':'06','DE-RP':'07','DE-BW':'08','DE-BY':'09','DE-SL':'10',
  'DE-BE':'11','DE-BB':'12','DE-MV':'13','DE-SN':'14','DE-ST':'15','DE-TH':'16' };
 function countyStyle(feature){
  const active=view.focusState&&String(feature.id||'').startsWith(AGS[view.focusState]||'!!');
  return {color:active?'#566876':'#50606b',weight:active?.85:0,
   fillOpacity:0,opacity:active?.65:0};
 }
 function renderCountyOutline(){
  if(!map||!countiesLayer)return;
  // All counties previously shared one Canvas interaction layer with the
  // states. Even invisible counties in neighbouring states swallowed clicks.
  // The Leaflet Canvas element is shared; per-feature pointer-events changes
  // would disable or enable the ENTIRE canvas, not individual county paths.
  if(view.focusState&&map.getZoom()>=6.5){
   if(countyDisplayedFor!==view.focusState){
    countiesLayer.clearLayers();
    const prefix=AGS[view.focusState];
    for(const [id,layer] of allCountyShapes)
     if(prefix&&String(id).startsWith(prefix))countiesLayer.addLayer(layer);
    countyDisplayedFor=view.focusState;
   }
   if(!map.hasLayer(countiesLayer))countiesLayer.addTo(map);
  }else if(map.hasLayer(countiesLayer)){
   map.removeLayer(countiesLayer);
  }
 }
 function zoomToState(id,name){
  const layer=statesLayer.getLayers().find(x=>x.feature?.properties?.id===id);
  if(!layer)return;
  const changed=view.focusState!==id;
  view.county=null;view.currentCounty=null;view.selected=null;view.limit=8;
  if(changed)$('loanDrawer').open=false;
  $('regionalDebtDrawer').hidden=true;
  $('regionalDebtDrawer').open=false;
  // Preserve national colour, event visibility and current archive settings;
  // switching states is a one-click operation, not a reset-to-Germany flow.
  displaySelectedState(id,name||layer.feature?.properties?.name);
  $('sectionTitle').textContent='2025年人均地方财政收支';
  $('districtPanel').hidden=id!=='DE-RP';
  $('districtHint').textContent='点击县市边界查看地方数据；仅已公开的统计地区有数值。';
  $('mapGuideNote').textContent='点击县市查看历史债务；右侧详情区分统计年份';
  $('stateJump').value=id;
  if(countyDisplayedFor!==id&&countiesLayer){
   // Release the old county hitboxes BEFORE painting the next state's
   // polygons so a neighbour's first click always reaches its state.
   if(map.hasLayer(countiesLayer))map.removeLayer(countiesLayer);
   countiesLayer.clearLayers();
   countyDisplayedFor=null;
  }
  map.stop();
  map.fitBounds(layer.getBounds(),{padding:[32,32],maxZoom:8,animate:false});
  renderCountyOutline();
  renderList();
  const sidebar=document.querySelector('.finance-summary');
  if(sidebar)sidebar.scrollTop=0;
 }
 function showCounty(feature){
  if(!view.focusState||!String(feature.id||'').startsWith(AGS[view.focusState]))return;
  view.currentCounty=feature.id;
  const row=view.focusState==='DE-RP'?regionalRow(feature.id):null;
  const name=feature.properties?.name||'县级地区';
  if(row){
   displayArea(name,money(row.value),regionalDetailNote(row));
   $('sectionTitle').textContent=regionOptions[view.rpPeriod].label;
  }else{
   const core=countyDebtRows.get(feature.id);
   const city=independentCityDebtRows.get(feature.id);
   if(core&&core.value!==null){
    displayArea(name,number(core.value)+' 欧元/人',
     '2023年 · 县域市镇及联合体核心预算债务；不是2025年赤字，也不含市属企业综合债务。');
    $('sectionTitle').textContent='2023年县域核心预算债务';
   }else if(city){
    displayArea(name,number(city.integrated2024)+' 欧元/人',
     '2024年 · 非县辖市综合地方债务；与州级2025年财政收支不同指标。');
    $('sectionTitle').textContent='2024年非县辖市综合地方债务';
   }else{
    displayArea(name,'暂无该县可比财政数据','地图底色仍表示该州2025年财政收支；未发布数据不得填0。');
    $('sectionTitle').textContent='县市历史财政资料';
   }
  }
  renderRegionalDebt(feature.id);
  renderLoanHistory(view.focusState);
  statesLayer.setStyle(stateStyle);
 }
 function buildMapLayers(){
  statesLayer=L.geoJSON(stateGeo,{style:stateStyle,onEachFeature:(feature,layer)=>{
   const id=feature.properties?.id,name=feature.properties?.name||id;
   layer.bindTooltip('');
   layer.on('mouseover',()=>layer.setTooltipContent(escapeHTML(name)+' · '+escapeHTML(stateMetricText(selectedStateValue(id)))));
   layer.on('click',()=>zoomToState(id,name));
  }});
  countiesLayer=L.geoJSON(countyGeo,{style:countyStyle,onEachFeature:(feature,layer)=>{
   allCountyShapes.set(feature.id,layer);
   layer.on('click',()=>showCounty(feature));
  }});
 }
 function renderMap(){
  if(!map||!statesLayer)return;
  if(!map.hasLayer(statesLayer))statesLayer.addTo(map);
  statesLayer.setStyle(stateStyle);
  renderCountyOutline();
  renderLegend();renderMarkers();
 }
 function resetView(){
  view.focusState=null;view.county=null;view.currentCounty=null;view.selected=null;
  $('stateJump').value='';
  countyDisplayedFor=null;
  if(countiesLayer){if(map?.hasLayer(countiesLayer))map.removeLayer(countiesLayer);countiesLayer.clearLayers();}
  view.limit=8;view.rpPeriod='2025-full-cities';
  $('rpPeriod').value=view.rpPeriod;
  resetArea();renderList();
  $('mapGuideNote').textContent='点击州放大，查看该州财政数据';
  map?.stop();map?.fitBounds(withinBounds,{padding:[12,12],animate:false});
  renderMap();
 }
 function updateFilters(){
  view.category=$('category').value;view.status=$('status').value;
  view.county=null;view.limit=8;view.selected=null;
  renderList();renderMarkers();
 }
 function setupUI(){
  $('stateJump').addEventListener('change',()=>{
   const id=$('stateJump').value;
   if(!id){resetView();return;}
   const layer=statesLayer?.getLayers().find(x=>x.feature?.properties?.id===id);
   if(layer)zoomToState(id,layer.feature?.properties?.name);
  });
  $('showEvents').addEventListener('change',()=>{
   view.showEvents=$('showEvents').checked;
   $('eventPanel').hidden=!view.showEvents;
   $('extraControls').hidden=!view.showEvents;
   view.county=null;view.selected=null;view.archive=false;view.limit=8;
   toggleArchive();renderList();renderMarkers();
   if(!view.showEvents){$('detail').hidden=true;$('extraControls').open=false;}
  });
  $('resetView').addEventListener('click',resetView);
  $('rpPeriod').addEventListener('change',()=>{
   if(!regionOptions[$('rpPeriod').value])return;
   view.rpPeriod=$('rpPeriod').value;
   const row=allCountyShapes.get(view.currentCounty)?.feature;
   if(row)showCounty(row);
  });
  $('category').addEventListener('change',updateFilters);
  $('status').addEventListener('change',updateFilters);
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
  if(!R||R.counties.length!==398||R.cities.length!==102||
     R.counties.filter(x=>Number.isFinite(x.value)).length!==392)
    throw Error('县市历史债务资料不完整');
  setupUI();resetArea();renderList();renderLegend();
  map=L.map('finance-map',{zoomSnap:.25,minZoom:5,maxZoom:13,zoomControl:true,preferCanvas:true});
  window.__FINANCE_MAP__=map;
  map.fitBounds(withinBounds,{animate:false,padding:[12,12]});
  map.on('zoomend',renderCountyOutline);
  const tile=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'});
  tile.addTo(map);
  if(window.CrimeCityLabels && window.GermanPlaceNames)window.CrimeCityLabels.create(map,{paneName:'financeCityLabels',zIndex:440});
  bubblesLayer=L.layerGroup().addTo(map);
  const [sf,cf]=await Promise.all([
   fetch('../../data/germany-states.geojson').then(r=>{if(!r.ok)throw Error('州界无法读取');return r.json()}),
   fetch('../../data/germany-counties.geojson').then(r=>{if(!r.ok)throw Error('县界无法读取');return r.json()})]);
  stateGeo=sf;countyGeo=cf;
  const stateSelect=$('stateJump');
  const stateOptions=sf.features.map(f=>({
   id:f.properties?.id,name:f.properties?.name||f.properties?.id
  })).filter(x=>x.id&&x.name).sort((a,b)=>a.name.localeCompare(b.name,'zh-CN'));
  stateOptions.forEach(x=>stateSelect.add(new Option(x.name,x.id)));
  const countyIds=new Set(cf.features.map(f=>f.id));
  const unmatched=readyCases.filter(r=>!countyIds.has(r.county));
  if(unmatched.length)throw Error('地图候选县级AGS没有匹配的边界：'+unmatched.map(x=>x.id).join(','));
  buildMapLayers();
  window.__FINANCE_UI__=Object.freeze({
   getFocusState:()=>view.focusState,
   zoomToState,
   selectCounty:id=>{const l=allCountyShapes.get(id);if(l)showCounty(l.feature)},
   getBalance:id=>selectedStateValue(id),
   stateFill:id=>color(selectedStateValue(id)),
   getMode:()=> 'balance-2025',
   eventCount:()=>bubblesLayer.getLayers().length,
   hasStateLayer:()=>map.hasLayer(statesLayer),
   hasCountyDetail:()=>map.hasLayer(countiesLayer),
   stateLayer:()=>statesLayer,
   eventMarkers:()=>bubblesLayer.getLayers(),
   selectedCounties:()=>countiesLayer?.getLayers().map(l=>l.feature?.id)||[],
   countyRenderer:()=>countiesLayer?.getLayers()[0]?.getElement()?.tagName||null,
   historicalCore:id=>countyDebtRows.get(id)?.value??null,
   historicalCity:id=>independentCityDebtRows.get(id)?.integrated2024??null
  });
  renderMap();showStatus('');
 }
 document.addEventListener('DOMContentLoaded',()=>{boot().catch(err=>{console.error(err);showStatus('财政专题加载失败：'+err.message+'。可查看研究档案和来源说明。')})});
})();