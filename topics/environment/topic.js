(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const ALL = window.GermanEnvironment06Data;
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const COLORS = {
    policy:'#e4b77b', organization:'#62b6a1', facility_story:'#b0a3de',
    archive:'#dc9663', facility:'#719ecb',
    retired:'#8b90ca', awarded:'#d6a16d', ordered:'#e4ce88', scheduled:'#70a8c9',
    traffic:'#dc9663',energy:'#edb766',sabotage:'#d77373',culture:'#bdaccb',construction:'#80afb7'
  };
  // A record belongs to exactly one of four primary classes. Editorial
  // selections and actor labels are FILTERS, never competing classes.
  const MODES = ['all','archive','policy','project','facility'];
  const CATEGORIES = {
    all:'全部记录',archive:'行动事件',policy:'环保政策',
    project:'组织争议',facility:'能源设施'
  };
  const NOTES = {
    all:'点选地图或列表，查看事件详情及资料来源。',
    archive:'交通、能源、设施、文化和工程行动可分别筛选。',
    policy:'政策点位代表表决或发布地点。',
    project:'项目争议和正常法律诉讼不等同于违法行动。',
    facility:'招标、命令及未来计划不等于实际退役。'
  };
  const PHASE_LABELS = {retired:'历史退役',awarded:'招标中标',ordered:'监管命令',scheduled:'未来退出计划'};
  const ACTION_LABELS = {traffic:'交通干扰',energy:'能源干扰',sabotage:'设施破坏',culture:'文化设施',construction:'工程冲击'};
  const GERMANY = L.latLngBounds([[47.05,5.45],[55.15,15.65]]);
  const state = {mode:'all',selected:null,selectedState:null,showPoints:false,limit:18};
  let group=null, map=null, rows=[], activeMarkers=new Map(), tilesLoaded=false;
  let dossier=null,stateShapes=new Map(),stateNames=new Map();
  // The 73 independently state-identified records are not the complete
  // 154-record environmental archive; anchored federal policy points should
  // not be silently assigned to Berlin based on their map coordinates.
  const STATE_CODES=Object.freeze({
   'Baden-Württemberg':'DE-BW','Bayern':'DE-BY','Berlin':'DE-BE','Brandenburg':'DE-BB',
   'Bremen':'DE-HB','Hamburg':'DE-HH','Hessen':'DE-HE','Mecklenburg-Vorpommern':'DE-MV',
   'Niedersachsen':'DE-NI','Nordrhein-Westfalen':'DE-NW','Rheinland-Pfalz':'DE-RP',
   'Saarland':'DE-SL','Sachsen':'DE-SN','Sachsen-Anhalt':'DE-ST',
   'Schleswig-Holstein':'DE-SH','Thüringen':'DE-TH'
  });
  const archivedInState=iso=>ALL.filter(e=>STATE_CODES[e.state]===iso);
  const localStateName=iso=>window.GermanPlaceNames?.translate(stateNames.get(iso)||iso)||stateNames.get(iso)||iso;

  function validData() {
    if (!Array.isArray(ALL) || ALL.length !== 154) throw Error('环保事件来源数据不完整');
    const ids = new Set();
    for (const e of ALL) {
      if (!e.id || ids.has(e.id)) throw Error('记录ID重复或缺失');
      ids.add(e.id);
      if (!Number.isFinite(e.coordinates?.lat) || !Number.isFinite(e.coordinates?.lon)
          || !Array.isArray(e.sources) || !e.sources.length) throw Error('事件位置或来源缺失：'+e.id);
    }
  }
  function color(e) {
    return e.kind === 'facility' ? COLORS[e.facility_phase] || COLORS.facility
      : e.kind === 'archive' ? COLORS[e.action_group] || COLORS.archive
      : COLORS[e.kind] || '#98adb9';
  }
  function kind(e) {
    return e.kind === 'policy' ? '政策' : e.kind === 'organization' ? '组织争议'
      : e.kind === 'facility_story' ? '设施争议' : e.kind === 'facility' ? '能源设施'
      : ACTION_LABELS[e.action_group] || '具体行动';
  }
  function cityName(e) {
    const raw = String(e.city || '').split(/[·（(]/)[0].trim();
    return window.GermanPlaceNames?.translate(raw) || raw || '未注明';
  }
  function primaryClass(e) {
    if(e.kind==='organization'||e.kind==='facility_story') return 'project';
    if(e.kind==='archive'||e.kind==='policy'||e.kind==='facility') return e.kind;
    throw Error('未知环保记录类型：'+e.kind);
  }
  function inMode(e) {return state.mode==='all'||primaryClass(e)===state.mode;}
  function filtered() {
    return ALL.filter(inMode).sort((a,b)=>
      (a.facility_phase==='scheduled'?1:0)-(b.facility_phase==='scheduled'?1:0)
      || b.date.localeCompare(a.date) || a.title.localeCompare(b.title));
  }
  function legend() {
    let items;
    if(state.mode==='archive') {
      items=Object.entries(ACTION_LABELS).map(([k,v])=>[v,COLORS[k],'archive']);
    } else if(state.mode==='facility') {
      items=Object.entries(PHASE_LABELS).map(([k,v])=>[v,COLORS[k],'facility']);
    } else if(state.mode==='project') {
      items=[['组织争议',COLORS.organization,'organization'],['设施项目争议',COLORS.facility_story,'organization']];
    } else {
      items=[['直接行动',COLORS.archive,'archive'],['政策措施',COLORS.policy,'policy'],
        ['组织／项目争议',COLORS.organization,'organization'],['设施项目争议',COLORS.facility_story,'organization'],
        ['能源设施',COLORS.facility,'facility']];
    }
    $('legend').innerHTML='<div class="legend-title">地图图例</div>'
      +'<div class="env-legend-row">'+items.map(([name,c,shape])=>'<span class="env-legend-item">'
      +'<i class="env-symbol '+shape+'" style="color:'+c+'"></i>'+esc(name)+'</span>').join('')+'</div>'
      +'<div class="env-legend-note">按事件类型或设施状态区分，不代表地区评分。</div>';
  }
  function markerHtml(e,index,total) {
    // Visual separation applies to glyphs only; geodata coordinates remain untouched.
    const radius=total>1 ? Math.min(27,10+total*1.4) : 0;
    const angle=total>1 ? index*2*Math.PI/total : 0;
    const dx=(radius*Math.cos(angle)).toFixed(1), dy=(radius*Math.sin(angle)).toFixed(1);
    return '<span class="env-marker '+esc(e.kind)+(e.id===state.selected?' selected':'')
      +'" style="--marker:'+color(e)+';translate:'+dx+'px '+dy+'px" aria-hidden="true">'
      +'<i class="env-marker-signal"></i></span>';
  }
  function renderMarkers() {
    if(!map) return;
    group.clearLayers(); activeMarkers=new Map();
    if(!state.showPoints)return;
    const coLoc=new Map();
    for(const e of rows) {
      const p=e.coordinates;
      const key=p.lat.toFixed(2)+','+p.lon.toFixed(2);
      const a=coLoc.get(key)||[];a.push(e.id);coLoc.set(key,a);
    }
    for(const e of rows) {
      const p=e.coordinates;
      const same=coLoc.get(p.lat.toFixed(2)+','+p.lon.toFixed(2));
      const icon=L.divIcon({className:'env-marker-icon',html:markerHtml(e,same.indexOf(e.id),same.length),
        iconSize:[18,18],iconAnchor:[9,9]});
      const marker=L.marker([p.lat,p.lon],{icon,keyboard:true,title:e.title,
        zIndexOffset:e.id===state.selected?1200:0, riseOnHover:true})
        .bindTooltip(esc(e.title)+'<br>'+esc(cityName(e))+' · '+esc(e.date),
          {className:'env-tooltip',sticky:true,direction:'top'});
      marker.on('click',()=>selectRecord(e.id,false));
      marker.addTo(group);activeMarkers.set(e.id,marker);
    }
  }
  function section(title,text) {
    return text ? '<div class="env-detail-section"><h3>'+esc(title)+'</h3><p>'+esc(text)+'</p></div>' : '';
  }
  function detail(e) {
    const target=$('detail');
    target.hidden=!e;
    $('rankSection').hidden=!!e;
    if(!e){target.replaceChildren();return;}
    const fields=[
      section('做了什么',e.summary),
      section('争议点',e.dispute),
      section('实际结果',e.outcome||e.measured_impact),
      section('司法／政策后续',e.court_followup||e.legal_status),
      section('经济影响／证据边界',e.limits||e.economic_evidence)
    ];
    if(e.auction_awards?.length) fields.push(section('官方中标记录',
      e.auction_awards.map(a=>a.award_id+' · '+a.name+' · '+a.capacity_mw+' MW').join('；')));
    if(e.capacity_mw) fields.push(section('历史装机',e.capacity_mw+' MW（并非经济损失金额）'));
    const sources=(e.sources||[]).filter(s=>/^https:\/\//.test(s.url)).map(s=>
      '<a target="_blank" rel="noopener noreferrer" href="'+esc(s.url)+'">↗ '+esc(s.publisher||s.url)+'</a>').join('');
    const locationDescription=e.location_type==='legislature'?'政策发布／表决地点；该政策实际适用范围可能覆盖全国'
      :e.location_type==='facility'?'设施附近定位'
      :e.location_type==='municipality'?'市镇级近似定位，并非精确设备位置'
      :'事件／项目附近的参考位置';
    target.innerHTML='<div class="env-detail-head"><strong>记录详情 · '+esc(cityName(e))
      +'</strong><button type="button" id="closeDetail" aria-label="关闭详情">关闭 ×</button></div>'
      +'<div class="env-detail-title">'+esc(e.title)+'</div>'
      +'<div class="env-detail-meta"><span>'+esc(e.date)+'</span><span>'+esc(kind(e))+'</span>'
      +(e.status_label?'<span>'+esc(e.status_label)+'</span>':'')
      +'<span>'+esc(e.actor||'行为主体未确定')+'</span></div>'
      +fields.join('')
      +'<div class="env-detail-section"><h3>原始资料</h3><div class="env-sources">'+sources+'</div></div>'
      +'<div class="env-limit">位置说明：'+esc(locationDescription)
      +'。组织立场、行动认领、司法认定及实际经济损失均须依据原始证据分别判断。</div>';
    $('closeDetail').onclick=()=>selectRecord(null,false);
  }
  function selectRecord(id,fly) {
    const e=rows.find(v=>v.id===id);
    if(e&&!state.showPoints){state.showPoints=true;$('showEnvPoints').checked=true;}
    state.selected=e?e.id:null;
    detail(e||null);
    $('summaryPanel').classList.toggle('has-selection',!!e);
    $('areaName').textContent=e?cityName(e):(state.selectedState?localStateName(state.selectedState):'德国全国');
    $('kindBadge').textContent=e?kind(e):'专题概览';
    $('areaMetric').textContent=e?(e.actor||'事件主体未确定')+' · '+e.date:'政策、直接行动和电厂退出的可核查记录';
    if(e&&fly&&map) map.setView([e.coordinates.lat,e.coordinates.lon],Math.max(8,map.getZoom()),{animate:false});
    renderMarkers();
    for(const node of $('entries').querySelectorAll('[data-id]'))
      node.classList.toggle('selected',node.dataset.id===state.selected);
  }
  function renderStateDossier(){
    const iso=state.selectedState;
    if(!iso)return;
    const records=archivedInState(iso);
    const sources=new Set(records.flatMap(e=>e.sources||[]).map(r=>r.url));
    const counted=(mode)=>records.filter(e=>primaryClass(e)===mode).length;
    $('envStateHeading').textContent=localStateName(iso)+' · 环保地方资料室';
    $('envStateStats').innerHTML=[
     ['明确州归属的记录',records.length+'条'],
     ['直接行动／扰动',counted('archive')+'条'],
     ['能源设施资料',counted('facility')+'条'],
     ['引用来源（去重URL）',sources.size+'条']
    ].map(([label,val])=>'<div><small>'+esc(label)+'</small><b>'+esc(val)+'</b></div>').join('');
    $('envStateCaveat').textContent='全库154条中有'+ALL.filter(e=>STATE_CODES[e.state]).length+
     '条明确登记联邦州；其余包括国家政策、无法据字段归属的设施与项目，不能从地图锚点位置反推所属州。'+
     (records.length?'本页只展示本州已归属档案，不能代表该州环保事件总量。':'本州暂无明确州归属的档案，并非没有环保行动或设施。');
    const q=$('envStateSearch').value.trim().toLocaleLowerCase();
    const matches=records.filter(e=>[e.title,e.actor,e.city,e.summary,e.id].some(x=>String(x||'').toLocaleLowerCase().includes(q)))
      .sort((a,b)=>String(b.date).localeCompare(String(a.date)));
    const brief=e=>'<button type="button" class="dossier-entry" data-env-id="'+esc(e.id)+'"><strong>'+esc(e.title)+'</strong>'+
     '<small>'+esc(e.date)+' · '+esc(cityName(e))+' · '+esc(kind(e))+'</small></button>';
    $('envStateList').innerHTML=matches.slice(0,90).map(brief).join('')||
     '<p class="dossier-note">本范围暂无匹配事件；缺失不是零。</p>';
    $('envStateEvidence').innerHTML=matches.slice(0,90).map(e=>
     '<div class="env-region-evidence"><strong>'+esc(e.title)+'</strong><p>'+esc(e.outcome||e.measured_impact||e.status_label||'原始记录未公布可确认结果')+'</p>'+
     '<small>'+esc(e.limits||e.verification||'具体后续以来源为准')+'</small>'+
     (e.sources?.find(x=>/^https:\/\//.test(x.url))?
       '<a target="_blank" rel="noopener noreferrer" href="'+esc(e.sources.find(x=>/^https:\/\//.test(x.url)).url)+'">核查原始资料 ↗</a>':'')+
     '</div>').join('')||
     '<p class="dossier-note">当前没有归属于本州的可审计结果。</p>';
    $('envStateList').querySelectorAll('[data-env-id]').forEach(b=>b.addEventListener('click',()=>{
     state.mode='all';state.selected=null;render();selectRecord(b.dataset.envId,true);
    }));
  }
  function selectState(iso){
   if(!iso||!STATE_CODES||!stateNames.has(iso))return;
   state.selectedState=iso;state.selected=null;
   $('envStateJump').value=iso;
   $('envStateSearch').value='';
   dossier.show(true);
   const layer=stateShapes.get(iso);
   if(layer)map.fitBounds(layer.getBounds(),{padding:[22,22],maxZoom:8,animate:false});
   render();
  }
  function resetState(){
   state.selectedState=null;state.selected=null;
   $('envStateJump').value='';
   dossier.show(false);
   map.fitBounds(GERMANY,{padding:[14,14],animate:false});
   render();
  }
  function rank() {
    const byCity=new Map();
    for(const e of rows) {
      const name=cityName(e);
      const v=byCity.get(name)||{name,count:0,example:e};
      v.count++;byCity.set(name,v);
    }
    const list=[...byCity.values()].sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name)).slice(0,8);
    $('rankList').replaceChildren();
    list.forEach((row,i)=>{
      const button=document.createElement('button');button.type='button';button.className='rank-row';
      button.innerHTML='<span class="rank-no">'+(i+1)+'</span><span class="rank-place">'+esc(row.name)
        +'</span><span class="rank-value">'+row.count+' 条</span>';
      button.onclick=()=>selectRecord(row.example.id,true);
      $('rankList').append(button);
    });
  }
  function renderEntries() {
    $('entries').replaceChildren();
    const shown=rows.slice(0,state.limit);
    for(const e of shown) {
      const item=document.createElement('button');
      item.type='button';item.className='env-entry'+(state.selected===e.id?' selected':'');
      item.dataset.id=e.id;
      item.innerHTML='<i class="swatch" style="background:'+color(e)+'"></i>'
        +'<span><span class="env-entry-title">'+esc(e.title)+'</span><span class="env-entry-meta">'
        +esc(cityName(e))+' · '+esc(e.date)+' · '+esc(e.status_label||kind(e))+'</span></span>';
      item.onclick=()=>selectRecord(e.id,true);
      $('entries').append(item);
    }
    const more=$('moreRecords');more.hidden=rows.length<=state.limit;
    more.textContent='显示更多 · 已列出 '+Math.min(state.limit,rows.length)+' / '+rows.length;
  }
  function render() {
    rows=filtered();
    if(state.selected&&!rows.some(e=>e.id===state.selected))state.selected=null;
    const selected=rows.find(e=>e.id===state.selected)||null;
    $('count').textContent=rows.length;
    $('regionCount').textContent=new Set(rows.map(cityName)).size;
    $('sourceCount').textContent=new Set(rows.flatMap(e=>e.sources||[]).map(x=>x.url)).size;
    $('listCount').textContent=rows.length+' 条';
    $('sectionTitle').textContent=CATEGORIES[state.mode];
    $('resultScope').textContent='点选查看详情';
    $('listHint').textContent=NOTES[state.mode];
    $('summaryPanel').classList.toggle('has-selection',!!selected);
    $('areaName').textContent=selected?cityName(selected):(state.selectedState?localStateName(state.selectedState):'德国全国');
    $('kindBadge').textContent=selected?kind(selected):'专题概览';
    $('areaMetric').textContent=selected?selected.actor+' · '+selected.date:'政策、直接行动和电厂退出的可核查记录';
    document.querySelectorAll('[data-mode]').forEach(b=>{
      const active=b.dataset.mode===state.mode;
      b.classList.toggle('active',active);
      b.setAttribute('aria-pressed',String(active));
    });
    legend();detail(selected);rank();renderEntries();renderMarkers();
    if(state.selectedState)renderStateDossier();
  }

  function initMap() {
    if(!window.L) { $('mapStatus').textContent='地图框架无法加载，请检查网络';return; }
    map=L.map('environment-map',{minZoom:5,maxZoom:17,zoomControl:true,preferCanvas:false,
      worldCopyJump:false,zoomSnap:.5});
    map.fitBounds(GERMANY,{padding:[14,14]});
    map.setMaxBounds([[45.3,3.2],[57.1,18]]);
    map.createPane('environmentCounties').style.zIndex=305;
    map.createPane('environmentStates').style.zIndex=370;
    map.getPane('tilePane').style.filter='saturate(.45) contrast(.86) brightness(1.06)';
    group=L.layerGroup().addTo(map);
    const tile=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      {maxZoom:19,opacity:.86,attribution:'© OpenStreetMap contributors',
       crossOrigin:true,updateWhenIdle:true});
    tile.on('tileload',()=>{
      if(!tilesLoaded) { tilesLoaded=true; $('mapStatus').className='mapstatus ok';
        $('mapStatus').textContent='OSM街道底图 + 环保争议点位'; }
    });
    let errors=0;
    tile.on('tileerror',()=>{if(++errors>=6&&!tilesLoaded){
      $('mapStatus').className='mapstatus fallback';
      $('mapStatus').textContent='OSM底图暂不可用 · 事件点位仍可使用';
    }});
    tile.addTo(map);
    setTimeout(()=>{if(!tilesLoaded){$('mapStatus').className='mapstatus fallback';
      $('mapStatus').textContent='OSM底图加载较慢 · 正在继续尝试';}},10000);
    window.CrimeCityLabels?.create(map,{paneName:'environment-city-labels',zIndex:455});
    // All boundary layers are reference outlines only; their failure cannot hide the map.
    fetch('../../data/germany-counties.geojson',{cache:'force-cache'})
      .then(r=>{if(!r.ok)throw Error('County geography '+r.status);return r.json();})
      .then(g=>L.geoJSON(g,{pane:'environmentCounties',interactive:false,
        style:()=>({color:'#536679',weight:.35,opacity:.22,fill:false})}).addTo(map))
      .catch(e=>console.warn('Optional county outlines unavailable:',e));
    fetch('../../data/germany-states.geojson',{cache:'force-cache'})
      .then(r=>{if(!r.ok)throw Error('State geography '+r.status);return r.json();})
      .then(g=>{if(!Array.isArray(g.features)||g.features.length!==16)throw Error('Invalid 16-state geometry');
        L.geoJSON(g,{pane:'environmentStates',interactive:true,
          style:()=>({color:'#273c50',weight:1.45,opacity:.77,fillColor:'#fff',fillOpacity:.012}),
          onEachFeature:(feature,layer)=>{
           const iso=feature.properties?.id;
           stateShapes.set(iso,layer);
           stateNames.set(iso,feature.properties?.name||iso);
           layer.on('click',()=>selectState(iso));
          }
        }).addTo(map);
        const sorted=[...stateNames].sort((a,b)=>localStateName(a[0]).localeCompare(localStateName(b[0]),'zh'));
        $('envStateJump').insertAdjacentHTML('beforeend',sorted.map(([id])=>'<option value="'+esc(id)+'">'+esc(localStateName(id))+'</option>').join(''));
       })
      .catch(e=>console.warn('Optional state outlines unavailable:',e));
    window.__ENVIRONMENT_MAP__={map,getRows:()=>rows,getMode:()=>state.mode,
      getSelected:()=>state.selected,getMarkerCount:()=>activeMarkers.size,
      getState:()=>state.selectedState,getStateAssigned:()=>ALL.filter(e=>STATE_CODES[e.state]).length,
      selectState,resetState,
      getMarkers:()=>activeMarkers,getAll:()=>ALL,selectRecord};
  }
  function wire() {
    dossier=window.GermanRegionDossier.mount('envStateDossier');
    $('showEnvPoints').addEventListener('change',e=>{state.showPoints=e.target.checked;renderMarkers()});
    $('envStateJump').addEventListener('change',e=>e.target.value?selectState(e.target.value):resetState());
    $('envStateSearch').addEventListener('input',renderStateDossier);
    for (const b of document.querySelectorAll('[data-mode]')) {
      b.onclick=()=>{
        state.mode=b.dataset.mode;
        state.selected=null;
        state.limit=18;
        render();
      };
    }
    $('moreRecords').onclick=()=>{state.limit+=24;renderEntries();};
  }
  try{
    validData();
    initMap();
    if(map){
      // Enforce exhaustiveness and disjoint primary groups before publishing numbers.
      const census=Object.fromEntries(MODES.map(mode=>[mode,0]));
      for(const e of ALL){census.all++;census[primaryClass(e)]++;}
      if(census.archive+census.policy+census.project+census.facility!==census.all)
        throw Error('主分类未覆盖完整环保数据');
      for(const el of document.querySelectorAll('[data-count-for]'))el.textContent=census[el.dataset.countFor];
      window.__ENVIRONMENT_TAXONOMY__=Object.freeze({...census});
      wire();render();
    }
  }catch(e){
    console.error(e);
    $('mapStatus').className='mapstatus fallback';
    $('mapStatus').textContent='环保专题初始化失败：'+e.message;
  }
})();