(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const escapeHtml = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const isUrl = s => typeof s === 'string' && /^https:\/\//i.test(s);
  const fmt = (v, decimals=1) => v==null || !Number.isFinite(Number(v)) ? '—' : Number(v).toFixed(decimals);
  const bounds = [[47.05,5.45],[55.15,15.65]];
  const palette = ['#e0e8dc','#d1dcc2','#d8d4ae','#d6b88b','#c79171','#b26c63','#854753'];
  const state = {selectedState:null,selectedEvent:null,showEvents:false,category:'all'};
  let map, stateLayer, markerGroup, scores, evidence, archive, rows, rowByIso, geo, markers = new Map();

  const categoryNames = {bridge:'桥梁损坏',delay:'工期延期',cost:'投资超支',strange:'闲置工程',access:'公共服务'};
  const statusNames = {in_progress:'分阶段施工',unconnected:'长期闲置',completed:'已完成',replacement:'待重建',partly_open:'部分恢复',closed:'封闭/限制',unavailable:'设施停用',temporary:'临时设施运行'};
  function color(v) {
    if(v == null || !Number.isFinite(v)) return '#83919b';
    if(v>=66)return palette[0];
    if(v>=62)return palette[1];
    if(v>=59)return palette[2];
    if(v>=56)return palette[3];
    if(v>=53)return palette[4];
    if(v>=50)return palette[5];
    return palette[6];
  }
  function anchor(url,label) {
    return isUrl(url) ? '<a href="'+escapeHtml(url)+'" target="_blank" rel="noopener noreferrer">'+escapeHtml(label)+' ↗</a>' : '';
  }
  function setStatus(message, ok=false) {
    $('mapStatus').textContent=message;
    $('mapStatus').className='mapstatus'+(ok?' ok':' fallback');
  }
  function legend() {
    $('legend').innerHTML='<div class="legend-title">基础设施试验指数 · 越低越需要关注</div>'
      +'<div class="scale">'+palette.map(x=>'<span style="background:'+x+'"></span>').join('')+'</div>'
      +'<div style="display:flex;justify-content:space-between;color:#b6c7d2;font-size:9px"><span>高分 · 相对较好</span><span>低分 · 相对较差</span></div>'
      +'<div style="margin-top:4px;color:#a8b9c6;font-size:9px">非官方综合评级；未纳入全国桥梁和路面</div>';
  }
  function selectState(iso) {
    if(!rowByIso.has(iso))return;
    state.selectedState=iso;
    state.selectedEvent=null;
    updateStateStyles();
    renderPanel();
  }
  function updateStateStyles() {
    if(!stateLayer)return;
    stateLayer.eachLayer(layer=>{
      const iso=layer.feature?.properties?.id;
      layer.setStyle({color:iso===state.selectedState?'#f3f8fb':'#526c7b',weight:iso===state.selectedState?2.2:1.1,fillColor:color(rowByIso.get(iso)?.score),fillOpacity:.85});
    });
  }
  function reset() {
    state.selectedState=null;
    state.selectedEvent=null;
    if(map)map.fitBounds(bounds,{padding:[14,14],animate:false});
    updateStateStyles();renderPanel();renderEvents();
  }
  function stateTooltip(row) {
    return '<strong>'+escapeHtml(row.name_zh)+'</strong><div>试验指数：'+fmt(row.score,2)+' / 100</div>';
  }
  function kpi(a,aLabel,b,bLabel,c,cLabel) {
    $('statA').textContent=a;$('statALabel').textContent=aLabel;
    $('statB').textContent=b;$('statBLabel').textContent=bLabel;
    $('statC').textContent=c;$('statCLabel').textContent=cLabel;
  }
  function metricRow(label,value) {
    return '<div class="metric-row"><span>'+escapeHtml(label)+'</span><b>'+escapeHtml(value)+'</b></div>';
  }
  function evidenceHtml(row) {
    const x=evidence.tli_motorway_2025.states.find(r=>r.iso===row.iso);
    const d=evidence.din_bridge_samples.filter(r=>r.iso===row.iso);
    const road=evidence.road_state_samples.filter(r=>r.iso===row.iso);
    const s=scores.source_urls;
    let h='<h3>实测指标 · 原始口径</h3>';
    h+=metricRow('铁路线路设施评分 · 2025（低为好）',fmt(row.rail_track_grade_2025,2));
    h+=metricRow('铁路车站设施评分 · 2025（低为好）',fmt(row.rail_station_grade_2025,2));
    h+=metricRow('FTTB/H光纤可覆盖率 · 2025',fmt(row.fiber_fttbh_pct_2025,2)+'%');
    h+=metricRow('SAIDI供电中断 · 2023–2024平均',fmt(row.power_saidi_two_year_mean,2)+'分钟');
    h+='<div class="metric-sub">铁路设施评分与服务覆盖率性质不同；SAIDI按电网运营商归州可能存在偏差。'+anchor(s.rail,'铁路')+' · '+anchor(s.fiber,'光纤')+' · '+anchor(s.power_primary,'电力')+'</div>';
    h+='<h3>桥梁及道路（仅作旁证，不加入试验分）</h3>';
    if(x) {
      h+='<div class="evidence-card"><strong>高速公路桥梁承载等级 TLI IV/V</strong><p>'+x.bad+' / '+x.total+' 分段 · '+fmt(x.percent,1)+'%</p><small>2025 IHK NRW同口径六州样本；不是DIN结构检查评分</small>'+anchor(evidence.tli_motorway_2025.source,'报告来源')+'</div>';
    }
    d.forEach(v=>{
      const pct=100*v.bad/v.total;
      h+='<div class="evidence-card"><strong>'+escapeHtml(v.scope)+'</strong><p>DIN状态≥3.0：'+v.bad+' / '+(v.total_approx?'约':'')+v.total+'，'+(v.total_approx?'约':'')+fmt(pct,1)+'%</p><small>'+v.year+'年 · 管理范围有别，勿跨州直接合并</small>'+(v.source_quality==='needs_exact_report'?'<small>⚠ 来源文件待二次核验，不能用于正式州际排名</small>':'')+anchor(v.source,'资料来源')+'</div>';
    });
    road.forEach(v=>{
      h+='<div class="evidence-card"><strong>'+escapeHtml(v.scope)+' · '+escapeHtml(v.metric)+'</strong><p>'+(v.approx?'约':'')+fmt(v.value_pct,1)+'% · '+v.year+'年</p><small>'+escapeHtml(v.definition)+'</small>'+(v.source_quality==='needs_exact_report'?'<small>⚠ 来源文件待二次核验，不能用于正式州际排名</small>':'')+anchor(v.source,'资料来源')+'</div>';
    });
    if(!x && !d.length && !road.length)h+='<div class="metric-sub">目前没有已整理的桥梁／道路地方样本；无数据不等于设施完好。</div>';
    return h;
  }
  function renderRank() {
    const box=$('rankList');box.replaceChildren();
    const sorted=[...rows].sort((a,b)=>a.score-b.score);
    sorted.forEach((r,i)=>{
      const b=document.createElement('button');b.type='button';b.className='rank-row';
      b.innerHTML='<span class="rank-no">'+(i+1)+'</span><span class="rank-place">'+escapeHtml(r.name_zh)+'</span><span class="rank-value">'+fmt(r.score,1)+'</span>';
      b.title='点击查看 '+r.name_zh+' 细节';b.addEventListener('click',()=>selectState(r.iso));box.append(b);
    });
  }
  function filteredEvents() {
    return archive.events.filter(e=>(state.category==='all'||e.category===state.category)
      &&(!state.selectedState||e.state_iso===state.selectedState))
      .sort((a,b)=>b.event_date.localeCompare(a.event_date));
  }
  function renderPanel() {
    const r=state.selectedState?rowByIso.get(state.selectedState):null;
    $('eventDetail').hidden=!state.selectedEvent;
    $('panelHeading').textContent=r?'所选联邦州':'16州试验指数';
    $('areaName').textContent=r?r.name_zh:'德国全国';
    $('metricValue').textContent=r?fmt(r.score,2)+' / 100':'16个联邦州';
    $('coverageBadge').textContent=r?'旧版试验值':'试验评分';
    $('metricNote').textContent=r
      ? '本州在旧试验模型中排第'+r.rank+'，四种权重方案下排名为第'+r.sensitivity_rank_min+'—'+r.sensitivity_rank_max+'；没有桥梁及道路分数。'
      : '铁路线路35% + 车站15% + 光纤30% + 电力20%，不是官方基建安全排名。颜色越深仅表示这一组指标的试验得分越低。';
    kpi(r?'第'+r.rank+'名':'16 / 16',r?'16州旧指数名次':'可比较州数量',
      r?fmt(r.rail_track_grade_2025,2):'4项',r?'铁路设施评分':'试验组成指标',
      r?archive.events.filter(e=>e.state_iso===r.iso).length:archive.events.length,
      r?'本州精选事件':'精选工程事件');
    $('indicatorDetail').hidden=!r;
    $('indicatorDetail').innerHTML=r?evidenceHtml(r):'';
    $('stateRanking').hidden=!!r;
    renderEventDetail();
    renderEvents();
  }
  function renderEventDetail() {
    const el=$('eventDetail'), e=archive.events.find(x=>x.id===state.selectedEvent);
    el.hidden=!e;if(!e){el.innerHTML='';return;}
    const precision=e.coordinates.precision==='locality_approx'?'城镇近似点':'设施附近示意点';
    el.innerHTML='<button type="button" aria-label="关闭事件详情" id="closeEventDetail">×</button>'
      +'<h3>'+escapeHtml(e.title)+'</h3>'
      +'<div class="meta">'+escapeHtml(e.city)+' · '+escapeHtml(e.event_date)+' · '+escapeHtml(categoryNames[e.category])+' · '+escapeHtml(statusNames[e.status]||e.status)+'</div>'
      +'<p>'+escapeHtml(e.summary)+'</p><p class="meta">定位精度：'+precision+'。该条为精选档案，不参与地区指数。</p>'
      +e.sources.filter(v=>isUrl(v.url)).map((s,i)=>anchor(s.url,'阅读来源 '+(i+1))).join(' · ');
    $('closeEventDetail').addEventListener('click',()=>{state.selectedEvent=null;renderEventDetail();renderEvents();});
  }
  function selectEvent(id) {
    const e=archive.events.find(v=>v.id===id);if(!e)return;
    state.selectedState=e.state_iso;state.selectedEvent=id;state.showEvents=true;$('showEvents').checked=true;
    $('filterWrap').hidden=false;
    updateStateStyles();renderPanel();
    map.panTo([e.coordinates.lat,e.coordinates.lon],{animate:false});
  }
  function renderEvents() {
    if(!markerGroup || !archive)return;
    markerGroup.clearLayers();markers=new Map();
    const box=$('eventList');box.replaceChildren();
    const shown=filteredEvents();
    $('eventSection').hidden=!state.showEvents;
    $('eventCount').textContent=shown.length+' 条精选记录';
    if(!state.showEvents)return;
    shown.forEach(e=>{
      const selected=e.id===state.selectedEvent;
      const symbol='<span class="infra-marker '+escapeHtml(e.status)+(selected?' selected':'')+'"></span>';
      const icon=L.divIcon({className:'infra-marker-icon',html:symbol,iconSize:[16,16],iconAnchor:[8,8]});
      const marker=L.marker([e.coordinates.lat,e.coordinates.lon],{icon,zIndexOffset:selected?1000:0,title:e.title,riseOnHover:true})
        .bindTooltip(escapeHtml(e.title)+'<br>'+escapeHtml(e.summary.slice(0,31))+'…',{className:'infra-tooltip',direction:'top',sticky:true});
      marker.on('click',()=>selectEvent(e.id));marker.addTo(markerGroup);markers.set(e.id,marker);
      const b=document.createElement('button');b.type='button';if(selected)b.className='selected';
      b.innerHTML='<b>'+escapeHtml(e.title)+'</b><small>'+escapeHtml(e.city)+' · '+escapeHtml(e.event_date)+' · '+escapeHtml(statusNames[e.status]||e.status)+'</small>';
      b.addEventListener('click',()=>selectEvent(e.id));box.append(b);
    });
  }
  function validate(geoData) {
    if(!Array.isArray(scores.states)||scores.states.length!==16||!geoData?.features||geoData.features.length!==16)throw Error('16州地图或评分数量不完整');
    const seen=new Set(scores.states.map(s=>s.iso));
    if(seen.size!==16||geoData.features.some(f=>!seen.has(f.properties?.id)))throw Error('州编码与边界不匹配');
    if(!archive.events?.length||archive.events.some(e=>!e.id||!e.sources?.length||!Number.isFinite(e.coordinates?.lat)||!Number.isFinite(e.coordinates?.lon)))throw Error('事件资料不完整');
    const eventIds=archive.events.map(e=>e.id);
    if(new Set(eventIds).size!==eventIds.length)throw Error('重复工程事件ID');
  }
  async function loadJson(path) {
    const res=await fetch(path,{cache:'no-store'});
    if(!res.ok)throw Error(path+' HTTP '+res.status);
    return res.json();
  }
  async function init() {
    if(typeof L==='undefined'){setStatus('地图脚本未加载；请检查网络');return;}
    map=L.map('infra-map',{preferCanvas:false,zoomControl:true,scrollWheelZoom:true,zoomSnap:.25});
    map.fitBounds(bounds,{padding:[12,12],animate:false});map.setMaxBounds([[45.5,3.2],[57.0,18.1]]);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap contributors',opacity:.83}).addTo(map);
    map.createPane('infraStatePane').style.zIndex=340;
    map.createPane('infraEventPane').style.zIndex=530;
    markerGroup=L.layerGroup().addTo(map);
    $('showEvents').addEventListener('change',e=>{state.showEvents=e.target.checked;$('filterWrap').hidden=!state.showEvents;renderEvents();});
    $('eventCategory').addEventListener('change',e=>{state.category=e.target.value;state.selectedEvent=null;renderEventDetail();renderEvents();});
    $('resetView').addEventListener('click',reset);
    legend();
    try{
      const results=await Promise.all([loadJson('data/state_scores_2025.json'),loadJson('data/condition_evidence.json'),loadJson('data/events.json'),loadJson('../../data/germany-states.geojson')]);
      [scores,evidence,archive,geo]=results;validate(geo);
      rows=scores.states;rowByIso=new Map(rows.map(r=>[r.iso,r]));
      stateLayer=L.geoJSON(geo,{
        pane:'infraStatePane',renderer:L.svg({pane:'infraStatePane'}),
        style:f=>({color:'#526c7b',weight:1.1,fillOpacity:.85,fillColor:color(rowByIso.get(f.properties.id)?.score)}),
        onEachFeature:(f,l)=>{
          const r=rowByIso.get(f.properties?.id);
          l.bindTooltip(()=>stateTooltip(r),{sticky:true,className:'infra-tooltip'});
          l.on('mouseover',()=>l.setStyle({weight:2,color:'#eef3f7'}));
          l.on('mouseout',()=>updateStateStyles());
          l.on('click',()=>selectState(f.properties?.id));
        }
      }).addTo(map);
      if(window.CrimeCityLabels?.create)window.CrimeCityLabels.create(map,{paneName:'infra-city-labels',zIndex:440});
      renderRank();renderPanel();
      setStatus('16州地图已就绪 · '+archive.events.length+'条精选工程事件',true);
      setTimeout(()=>{$('mapStatus').hidden=true;},5500);
    }catch(error){
      setStatus('数据读取失败：'+error.message);
      console.error('Infrastructure map initialization failed',error);
    }
  }
  document.addEventListener('DOMContentLoaded',init);
})();