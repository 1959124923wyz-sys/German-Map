(() => {
 'use strict';
 const $ = id => document.getElementById(id);
 const safe = v => String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const fmt = (v,dec=1) => new Intl.NumberFormat('zh-CN',{maximumFractionDigits:dec}).format(v);
 const isNum = v => typeof v==='number' && Number.isFinite(v);
 const metrics = {
  asking_rent_2025_eur_m2:{label:'2025年新租挂牌净冷租金',year:'2025',unit:'欧元/㎡',dec:2,source:'atlas',interpret:'互联网挂牌中重新出租住房的净冷租金，不是所有租房家庭正在支付的实际租金。'},
  completed_dwellings_new_residential_buildings_2023:{label:'2023年新建住宅建筑竣工住房',year:'2023',unit:'套',dec:0,source:'completions',interpret:'德国各州统计局联合地区统计，2023年新建住宅建筑内竣工住房套数，全国400县完整；不包含改建、扩建和非住宅建筑中的全部竣工住房。绝对套数受人口和县级规模影响。'},
  sheltered_homeless_2025:{label:'2025年已安置无住房人员',year:'2025-01-31',unit:'人',dec:0,source:'homeless',interpret:'仅统计2025年1月31日已获临时住宿的无住房人员，不含街头露宿和隐性无住房；按县绝对人数，受人口规模影响。394县有可用数字，6县缺失；保密五人取整。'},
  existing_cold_rent_2022_eur_m2:{label:'2022年存量租约实际净冷租金',year:'2022',unit:'欧元/㎡',dec:2,source:'census',interpret:'2022年5月住房普查中已出租住房的实际净冷租金均值，与2025年新增挂牌租金的抽样对象、时间都不同，不能直接当作租金增长率。'},
  vacant_12mo_plus_of_vacant_2022_pct:{label:'2022年空置超过12个月占空房比例',year:'2022',unit:'%',dec:2,source:'census',interpret:'分子为2022年普查空置12个月及以上的住房数，分母为所有空置住房数。并非所有住房中空置超过一年的比例。'},
  vacant_available_3mo_of_vacant_2022_pct:{label:'2022年空房中3个月内可入住比例',year:'2022',unit:'%',dec:2,source:'census',interpret:'分子为普查所列预计3个月内可供入住的空置住房，分母为所有空置住房。可入住不一定进入租赁市场，不能称为市场活跃空置率。'},
  vacancy_2022_pct:{label:'2022年住宅空置率',year:'2022',unit:'%',dec:1,source:'atlas',interpret:'全部空置住宅中的部分住宅可能并不适合出租；较高空置率不表示当地没有住房结构性问题。'},
  disposable_income_2023_keur_person:{label:'2023年人均可支配收入',year:'2023',unit:'千欧元/人·年',dec:2,source:'atlas',interpret:'这是地区所有私人家庭的平均可支配收入按全体居民折算，不是租房家庭收入，也不是工资中位数。不能将2023年此指标与2025年新租挂牌租金直接计算所谓住房负担率。'},
  owner_occupier_2022_pct:{label:'2022年自住住房家庭占比',year:'2022',unit:'%',dec:1,source:'atlas',interpret:'统计对象是住在自有房屋的家庭，不是市场租赁住房比例，也不是各地住房可负担性评分。'},
  living_area_2022_m2_person:{label:'2022年人均居住面积',year:'2022',unit:'㎡/人',dec:1,source:'atlas',interpret:'住房建筑面积分配的统计观察，受人口结构、住宅类型及统计口径影响。'},
  homes_per_1000_people_2025:{label:'2025年千人住宅存量',year:'2025',unit:'套/千人',dec:1,source:'stock',interpret:'以2025年住宅套数除以当地居民人数的比率；不是人均住房套数，也不能直接计算“住房缺口”。'},
  housing_stock_growth_2022_2025_pct:{label:'2022—2025住房存量变化',year:'2022—2025',unit:'%',dec:2,source:'stock',interpret:'住房存量净变化包含建设、拆除、转换和统计调整，不可误称新房竣工数量。'},
  population_growth_2022_2025_pct:{label:'2022—2025人口变化',year:'2022—2025',unit:'%',dec:2,source:'stock',interpret:'地区人口净变化，不可直接作为住房需求增长率；家庭户数和居住面积需要独立调查。'},
  renewable_heat_new_2024_pct:{label:'2024年新住宅可再生供暖占比',year:'2024',unit:'%',dec:1,source:'atlas',interpret:'仅对应2024年新建住宅，与既有住房的供暖结构是不同统计对象。'},
  renewable_heat_stock_2022_pct:{label:'2022年存量住宅可再生供暖占比',year:'2022',unit:'%',dec:1,source:'atlas',interpret:'存量住宅的供暖比例，不可与2024年新住宅供暖指标合并成趋势。'}
 };
 const colors=['#f5ead9','#f2d4ad','#eeb888','#e99a64','#df754e','#cb4d3d','#a52d37'];
 const gray='#8d989f';
 let map, countyLayer, stateLayer, cityLabels, sourceMeta;
 let selectedCounty=null, focusState=null, metric='asking_rent_2025_eur_m2';
 let stateFeatures=[], countyFeatures=[], byid=new Map(), countyShapes=new Map();
 let stockReady=false, homelessReady=false, completionsReady=false, censusReady=false, breaks=[], sortedAll=[];
 let saxonyRows=new Map(), nrwRows=new Map();
 const COUNTRY=[[47.2,5.5],[55.3,15.5]];
 const sourceURL = {
  atlas:'https://deutschlandatlas.bund.de/service/daten-herunterladen/aktuelle-downloaddaten/aktuelle-downloaddateien',
  stock:'https://mietkautionskonto.info/wohnungsmarkt-analyse-kreise/',
  homeless:'https://genesis.destatis.de/datenbank/online/statistic/22971/table/22971-0080',
  completions:'https://www.regionalstatistik.de/genesisws/downloader/00/tables/31121-01-02-4_00.csv',
  census:'https://www.destatis.de/static/DE/zensus/gitterdaten/Regionaltabelle_Gebaeude_Wohnungen.xlsx'
 };
 function ags(v){return String(v??'').padStart(5,'0')}
 function featureId(f){return ags(f.id??f.properties?.id)}
 function metricValue(id,key=metric){const d=byid.get(id);return isNum(d?.[key])?d[key]:null}
 const STATE_AGS=Object.freeze({'DE-SH':'01','DE-HH':'02','DE-NI':'03','DE-HB':'04','DE-NW':'05','DE-HE':'06','DE-RP':'07','DE-BW':'08','DE-BY':'09','DE-SL':'10','DE-BE':'11','DE-BB':'12','DE-MV':'13','DE-SN':'14','DE-ST':'15','DE-TH':'16'});
 function stateId(f){const raw=String(f.properties?.id??f.id??'');return STATE_AGS[raw]||(/^[0-9]{1,2}$/.test(raw)?raw.padStart(2,'0'):'')}
 function selectedRegion(){
  if(selectedCounty){const r=byid.get(selectedCounty);return {title:r?.name||selectedCounty,scope:'county',ids:[selectedCounty]}}
  if(focusState){
   const f=stateFeatures.find(f=>stateId(f)===focusState);
   return {title:f?.properties?.name||('州 '+focusState),scope:'state',ids:[...byid.keys()].filter(k=>k.startsWith(focusState))}
  }
  return {title:'德国 · 全国',scope:'nation',ids:[...byid.keys()]};
 }
 function sourceInfo(){
  const d=metrics[metric];
  if(d.source==='homeless')return {url:sourceURL.homeless,credit:'德国联邦统计局 Destatis GENESIS 22971-0080；2025-01-31；仅获安置无住房人员、五人取整，6个县缺数，不可代表全部无住房者。'};
  if(d.source==='completions')return {url:sourceURL.completions,credit:'德国联邦与各州统计局 Regionalstatistik 31121-01-02-4，2023年新建住宅建筑中的竣工住房套数，400县核验与全国总数一致；非全部住宅竣工。'};
  if(d.source==='census')return {url:sourceURL.census,credit:'德国 Zensus 2022 住房普查全国区域表；400县官方原始住房租金、空置持续时间及空房可入住原因；合计受保密处理存在小幅不一致。2022普查与2024边界存在年份差异。'};
  return d.source==='atlas'
    ?{url:sourceURL.atlas,credit:'德国联邦 Deutschlandatlas HA26，2026-10-08版，县级官方指标；2022与2024行政区边界混用，详见核验记录。'}
    :{url:sourceURL.stock,credit:'mietkautionskonto.info 公开再发布官方底表，CC BY 4.0；2025住房存量已做全国总量和四县数值交叉检查，非逐县官方原表复核。'};
 }
 function sortedVals(ids){return ids.map(id=>metricValue(id)).filter(isNum).sort((a,b)=>a-b)}
 function med(vals){return vals.length?(vals[(vals.length-1)>>1]+vals[vals.length>>1])/2:null}
 function displayVal(v,key=metric){return isNum(v)?fmt(v,metrics[key].dec)+' '+metrics[key].unit:'无可比数据'}
 function quantile(sorted,p){return sorted.length?sorted[Math.min(sorted.length-1,Math.floor((sorted.length-1)*p))]:null}
 function colorOf(v){if(!isNum(v))return gray;for(let i=0;i<breaks.length;i++){if(v<=breaks[i])return colors[i]}return colors[6]}
 function tooltipText(f){
  const id=featureId(f),d=byid.get(id),n=d?.name||f.properties?.name||id,v=metricValue(id);
  return '<strong>'+safe(n)+'</strong><div>'+safe(metrics[metric].label)+': '+safe(displayVal(v))+'</div>'+
   (v===null?'<small>当前指标无匹配记录</small>':'');
 }
 function paint(){
  if(!countyLayer)return;
  const vals=sortedVals([...byid.keys()]);
  breaks=Array.from({length:6},(_,i)=>quantile(vals,(i+1)/7));
  sortedAll=vals;
  countyLayer.eachLayer(l=>{
   const id=featureId(l.feature),v=metricValue(id);
   l.setStyle({color:id===selectedCounty?'#f8fafc':'#516373',weight:id===selectedCounty?2.3:0.68,fillColor:colorOf(v),fillOpacity:v===null?.45:.79});
   l.bindTooltip(tooltipText(l),{sticky:true,opacity:.98});
  });
  updateLegend();
  updateDetails();
  $('mapGuideTitle').textContent=metrics[metric].label;
 }
 function updateLegend(){
  const m=metrics[metric],low=sortedAll.length?sortedAll[0]:null,high=sortedAll.at(-1);
  $('legend').innerHTML='<div class="legend-title">'+safe(m.label)+' · '+safe(m.unit)+'</div>'+
   '<div class="housing-scale">'+colors.map(c=>'<i style="background:'+c+'"></i>').join('')+'</div>'+
   '<div class="housing-legend-labels"><span>'+safe(isNum(low)?fmt(low,m.dec):'—')+'</span>'+
   '<span>由浅至深：数值升高</span><span>'+safe(isNum(high)?fmt(high,m.dec):'—')+'</span></div>'+
   '<div style="font-size:9px;margin-top:7px;color:#aabac4"><i style="background:'+gray+';display:inline-block;width:10px;height:8px"></i> 灰色：该指标缺失或不可比较</div>';
 }
 function overview(ids,key){const v=ids.map(id=>metricValue(id,key)).filter(isNum).sort((a,b)=>a-b);return med(v)}
 function renderQuick(region){
  const stats=[
   ['asking_rent_2025_eur_m2','挂牌租金 · 2025'],
   ['vacancy_2022_pct','空置率 · 2022'],
   ['owner_occupier_2022_pct','自住家庭 · 2022'],
   ['homes_per_1000_people_2025','千人住宅 · 2025']
  ];
  $('quickStats').innerHTML=stats.map(([key,label])=>{
   const v=region.scope==='county'?metricValue(region.ids[0],key):overview(region.ids,key);
   return '<div class="housing-quick-card"><small>'+safe(label)+(region.scope==='county'?'':' · 县级中位值')+
     '</small><strong>'+safe(isNum(v)?fmt(v,metrics[key].dec):'—')+
     '</strong><small>'+safe(metrics[key].unit)+'</small></div>';
  }).join('');
 }
 function updateRanks(ids){
  const ranked=ids.map(id=>({id,v:metricValue(id)})).filter(row=>isNum(row.v)).sort((a,b)=>b.v-a.v);
  const top=ranked.slice(0,8);
  $('topRank').innerHTML=top.map(row=>'<button type="button" class="housing-rank-row" data-id="'+safe(row.id)+'"><span>'+
   safe(byid.get(row.id)?.name||row.id)+'</span><b>'+safe(displayVal(row.v))+'</b></button>').join('') ||
   '<p class="housing-note">本范围暂无可比较的县级记录</p>';
  $('topRank').querySelectorAll('[data-id]').forEach(el=>el.addEventListener('click',()=>chooseCounty(el.dataset.id)));
 }
 function renderLandPrice(region){
  const el=$('landPriceBand');
  const v=region.scope==='county'?byid.get(region.ids[0])?.building_land_price_band_2024:null;
  el.hidden=!v;
  if(!v)return;
  const nice=String(v).replace(/^(\\d+) bis unter (\\d+)$/,'$1—不足$2').replace(/^(\\d+) und mehr$/,'≥$1').replace(/^unter (\\d+)$/,'低于$1');
  el.textContent='2024年住宅建筑用地价格等级：'+nice+' 欧元/㎡（用于一、两户型住宅的中等地段；官方县级表仅给区间，非精确价格）';
 }
 function renderNRW(region){
  const panel=$('nrwCompletions');
  const row=region.scope==='county'?nrwRows.get(region.ids[0]):null;
  panel.hidden=!row;
  if(!row)return;
  const years=Object.entries(row.values_by_year).sort((a,b)=>b[0].localeCompare(a[0]));
  $('nrwHistory').innerHTML='<div class="housing-archive-grid">'+years.map(([year,x])=>
   '<div><small>'+safe(year)+'</small><b>'+safe(isNum(x.new_dwellings_in_residential_buildings)?fmt(x.new_dwellings_in_residential_buildings,0)+'套':'无数据')+'</b></div>').join('')+'</div>'+
   '<p>仅北威州53个县市，统计新建住宅建筑竣工住房套数，不含改建扩建及非住宅建筑中的全部新增住房，绝非德国所有竣工住宅。不同年份县界须注意行政调整。</p>'+
   '<a target="_blank" rel="noopener noreferrer" href="https://www.landesdatenbank.nrw.de/ldbnrwws/downloader/00/tables/31121-06i_00.csv">IT.NRW 官方31121-06i原始CSV ↗</a>';
 }
 function renderSaxony(region){
  const panel=$('saxonyDetails');
  const row=region.scope==='county'?saxonyRows.get(region.ids[0]):null;
  panel.hidden=!row;
  if(!row)return;
  $('saxonyHistory').innerHTML='<div class="housing-archive-grid">'+Object.entries(row.annual_counts).map(([year,count])=>
   '<div><small>'+safe(year)+'</small><b>'+safe(fmt(count,0))+'人</b></div>').join('')+'</div>'+
   '<p>每年1月31日登记的已被安置无住房人员，并非所有无家可归者；州统计局为保护隐私将人数四舍五入至5的倍数，年度不能简单解释为住房危机增减。</p>'+
   '<a target="_blank" rel="noopener noreferrer" href="https://www.statistik.sachsen.de/html/untergebrachte-wohnungslose-personen.html">萨克森州统计局原始资料 ↗</a>';
 }
 function updateDetails(){
  const region=selectedRegion(),v=region.scope==='county'?metricValue(region.ids[0]):overview(region.ids);
  const available=region.ids.filter(id=>isNum(metricValue(id))).length;
  $('areaName').textContent=region.title;
  $('yearLabel').textContent=metric==='sheltered_homeless_2025'?'2025年1月31日':metrics[metric].year+'年';
  $('value').textContent=displayVal(v);
  $('description').textContent=region.scope==='county'?metrics[metric].label:
   (metrics[metric].label+' · 县市简单中位数（非人口加权全国/全州值）');
  $('coverage').textContent=region.scope==='county'?'行政区编码 '+region.ids[0]+' · '+(v===null?'缺失':'有统计记录'):
   '当前范围 '+available+' / '+region.ids.length+' 个县市有数值；按县统计，不代表所有居民的加权平均';
  $('interpretNote').textContent=metrics[metric].interpret;
  const s=sourceInfo();$('sourceLink').href=s.url;
  $('sourceLink').textContent=(metrics[metric].source==='atlas'?'Deutschlandatlas HA26 官网':metrics[metric].source==='homeless'?'Destatis GENESIS 22971-0080 官方县级表':metrics[metric].source==='completions'?'Regionalstatistik 31121-01-02-4 官方县级表':metrics[metric].source==='census'?'Zensus 2022 全国官方住房普查':'第三方县级再发布与来源说明')+' ↗';
  $('sourceCredit').textContent=s.credit;
  renderQuick(region);
  renderLandPrice(region);
  renderNRW(region);
  renderSaxony(region);
  updateRanks(region.ids);
 }
 function chooseCounty(id){
  const shape=countyShapes.get(id);
  if(!shape)return;
  selectedCounty=id; focusState=id.slice(0,2);
  $('stateJump').value=focusState;
  map.fitBounds(shape.getBounds(),{padding:[38,38],maxZoom:9,animate:false});
  paint();
 }
 function selectState(id){
  if(!id){return reset()}
  const state=stateFeatures.find(f=>stateId(f)===id);
  if(!state)return;
  selectedCounty=null;focusState=id;
  const layer=stateLayer.getLayers().find(x=>stateId(x.feature)===id);
  if(layer)map.fitBounds(layer.getBounds(),{padding:[26,26],maxZoom:8,animate:false});
  paint();
 }
 function reset(){
  selectedCounty=null;focusState=null;$('stateJump').value='';
  map.fitBounds(COUNTRY,{padding:[15,15],animate:false});
  paint();
 }
 async function readJson(url){
  const resp=await fetch(url,{cache:'no-store'});
  if(!resp.ok)throw new Error(url+': HTTP '+resp.status);
  return resp.json();
 }
 function makeLayers(states,counties){
  stateFeatures=states.features;countyFeatures=counties.features;
  stateLayer=L.geoJSON(states,{interactive:false,style:{color:'#354756',weight:2,fill:false,opacity:.86}}).addTo(map);
  countyLayer=L.geoJSON(counties,{
   style:()=>({weight:.65,color:'#526574',fillColor:gray,fillOpacity:.6}),
   onEachFeature:(f,l)=>{
    const id=featureId(f);
    countyShapes.set(id,l);
    l.on('click',()=>chooseCounty(id));
   }
  }).addTo(map);
  stateLayer.bringToFront();
  const options=stateFeatures.map(f=>({id:stateId(f),name:f.properties?.name||stateId(f)})).sort((a,b)=>a.name.localeCompare(b.name));
  $('stateJump').insertAdjacentHTML('beforeend',options.map(s=>'<option value="'+safe(s.id)+'">'+safe(s.name)+'</option>').join(''));
  if(window.CrimeCityLabels?.create)cityLabels=window.CrimeCityLabels.create(map,{paneName:'housingCityLabels',zIndex:460});
 }
 async function start(){
  map=L.map('housingMap',{zoomControl:true,preferCanvas:false,minZoom:5,maxZoom:14,zoomSnap:.25});
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
   attribution:'© OpenStreetMap contributors',maxZoom:19,subdomains:'abc'
  }).addTo(map);
  map.fitBounds(COUNTRY,{padding:[15,15],animate:false});
  $('housingMetric').addEventListener('change',e=>{
   if(metrics[e.target.value]){metric=e.target.value;paint()}
  });
  $('stateJump').addEventListener('change',e=>selectState(e.target.value));
  $('resetView').addEventListener('click',reset);
  try{
   const [atlas,states,counties]=await Promise.all([
    readJson('data/atlas-counties.json'),
    readJson('../../data/germany-states.geojson'),
    readJson('data/germany-counties-2024.geojson')]);
   if(atlas.counties.length!==400||counties.features.length!==400||states.features.length!==16)throw new Error('地区文件覆盖与校验快照不符');
   byid=new Map(atlas.counties.map(d=>[ags(d.id),{...d}]));
   sourceMeta=atlas.meta;
   if([...byid.values()].filter(d=>isNum(d.asking_rent_2025_eur_m2)).length<390)throw new Error('全国县级租金覆盖不足');
   try{
    const stock=await readJson('data/stock-counties.json');
    if(stock.counties.length!==400)throw new Error('县级存量覆盖不完整');
    for(const d of stock.counties){
     const id=ags(d.id);if(byid.has(id))Object.assign(byid.get(id),{
       homes_per_1000_people_2025:d.homes_per_1000_people_2025,
       housing_stock_growth_2022_2025_pct:d.housing_stock_growth_2022_2025_pct,
       population_growth_2022_2025_pct:d.population_growth_2022_2025_pct
     });
    }
    stockReady=true;
   }catch(err){
    console.warn('Stock layer unavailable: retaining official primary map',err);
    document.querySelectorAll('#housingMetric option').forEach(o=>{if(metrics[o.value]?.source==='stock')o.disabled=true});
   }
   try{
    const nationwideHomeless=await readJson('data/germany-homeless-counties-2025.json');
    if(nationwideHomeless.counties.length!==400 || nationwideHomeless.meta.coverage_numerical!==394)throw new Error('Destatis national homeless series differs from QA');
    for(const d of nationwideHomeless.counties){
     const id=ags(d.id);
     if(byid.has(id))byid.get(id).sheltered_homeless_2025=d.sheltered_homeless_2025;
    }
    homelessReady=true;
   }catch(err){
    console.warn('Destatis national housed homelessness not available',err);
    document.querySelectorAll('#housingMetric option').forEach(o=>{if(metrics[o.value]?.source==='homeless')o.disabled=true});
   }
   try{
    const completed=await readJson('data/germany-residential-completions-2023.json');
    if(completed.counties.length!==400 || completed.meta.numerical!==400 || completed.meta.national_table_total!==257241)throw new Error('Nationwide 2023 completions do not match audited totals');
    for(const d of completed.counties){
     const id=ags(d.id);
     if(byid.has(id))byid.get(id).completed_dwellings_new_residential_buildings_2023=d.completed_dwellings_new_residential_buildings_2023;
    }
    completionsReady=true;
   }catch(err){
    console.warn('Nationwide new residential completions not available',err);
    document.querySelectorAll('#housingMetric option').forEach(o=>{if(metrics[o.value]?.source==='completions')o.disabled=true});
   }
   try{
    const census=await readJson('data/zensus2022-housing-indicators-counties.json');
    if(census.counties.length!==400)throw new Error('Zensus national 2022 county coverage not 400');
    const sourceKeys=['existing_cold_rent_2022_eur_m2','vacant_12mo_plus_of_vacant_2022_pct','vacant_available_3mo_of_vacant_2022_pct'];
    let found=0;
    for(const d of census.counties){
     const id=ags(d.id),target=byid.get(id);
     if(!target)throw new Error('Census county not in current BKG geometry: '+id);
     for(const k of sourceKeys)target[k]=d[k];
     if(Number.isFinite(d.existing_cold_rent_2022_eur_m2))found++;
    }
    if(found!==400)throw new Error('Zensus 2022 official existing rents incomplete: '+found);
    censusReady=true;
   }catch(err){
    console.warn('Zensus nationwide 2022 indicators not available',err);
    document.querySelectorAll('#housingMetric option').forEach(o=>{if(metrics[o.value]?.source==='census')o.disabled=true});
   }
   try{
    const saxony=await readJson('data/saxony-homeless-counties.json');
    if(saxony.counties.length!==13)throw new Error('Saxony county-series coverage changed');
    saxonyRows=new Map(saxony.counties.map(row=>[row.id,row]));
   }catch(err){console.warn('Saxony county detail unavailable',err)}
   try{
    const nrw=await readJson('data/nrw-new-home-completions.json');
    if(nrw.counties.length!==53)throw new Error('NRW official 2025 Kreis coverage changed');
    nrwRows=new Map(nrw.counties.map(row=>[row.id,row]));
   }catch(err){console.warn('NRW local construction detail unavailable',err)}
   makeLayers(states,counties);
   paint();
   const valid=sortedAll.length;
   $('mapStatus').textContent=valid+'处县级地图区域已载入；'+(stockReady?'含核验住房存量':'住房存量层暂不可用');
   $('mapStatus').classList.add('ok');
   window.GermanHousingResearch=Object.freeze({
     state:()=>({metric,selectedCounty,focusState,validCount:sortedAll.length,stockReady,homelessReady,completionsReady,censusReady,countyShapes:countyShapes.size}),
     metrics:Object.keys(metrics)
   });
  }catch(err){
   $('mapStatus').textContent='住房地图加载失败：'+String(err.message||err);
   $('mapStatus').classList.add('fallback');
   $('value').textContent='数据暂不可用';
   console.error(err);
  }
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);
 else start();
})();
