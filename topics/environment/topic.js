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
  const CATEGORIES = {
    overview:'政策与能源退出总览',archive:'具体环保行动',policy:'环保政策',
    organization:'环保组织与项目争议',facility:'能源设施与退役安排',focus:'争议精选案例'
  };
  const NOTES = {
    overview:'包括政策、设施争议、已退役设施及未来法定期限。计划退役不等于已经停机。',
    archive:'机场／道路封锁、涂漆、能源干扰及工程冲击；行为性质和司法结果以逐条证据为准。',
    policy:'全国性政策定位于立法或发布地点，地图点位不代表该政策仅影响此处。',
    organization:'组织提出的合法行政异议，与已经实施的阻断、侵入或破坏行为分别记录。',
    facility:'退役、中标、监管命令及未来法定时间表各自独立；无法确认退出状态时不标为停机。',
    focus:'具有明确地点、争议内容及公开后续的精选案例，不构成全面的环保组织排名。'
  };
  const PHASE_LABELS = {retired:'历史退役',awarded:'招标中标',ordered:'监管命令',scheduled:'未来退出计划'};
  const ACTION_LABELS = {traffic:'交通干扰',energy:'能源干扰',sabotage:'设施破坏',culture:'文化设施',construction:'工程冲击'};
  const GERMANY = L.latLngBounds([[47.05,5.45],[55.15,15.65]]);
  const BERLIN = L.latLngBounds([[52.34,13.08],[52.67,13.75]]);
  const HAMBURG = L.latLngBounds([[53.38,9.68],[53.78,10.36]]);
  const state = {mode:'overview',action:'all',phase:'all',org:'all',search:'',selected:null,limit:18};
  let group=null, map=null, rows=[], activeMarkers=new Map(), tilesLoaded=false;

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
  function actorGroup(e) {
    const v=String(e.actor||'').toLowerCase();
    for(const key of ['Letzte Generation','Ende Gelände','Greenpeace','Tesla Stoppen','BUND','NABU','DUH']) {
      if (v.includes(key.toLowerCase())) return key;
    }
    return null;
  }
  function inMode(e) {
    if (state.mode==='overview') return ['policy','facility_story'].includes(e.kind)
      || e.kind==='facility' && ['retired','scheduled'].includes(e.facility_phase);
    if (state.mode==='focus') return ['policy','organization','facility_story'].includes(e.kind);
    if (state.mode==='archive') return e.kind==='archive';
    return e.kind===state.mode;
  }
  function filtered() {
    let result=state.org==='all' ? ALL.filter(inMode)
      : ALL.filter(e=>['organization','archive'].includes(e.kind)
          && String(e.actor||'').toLowerCase().includes(state.org.toLowerCase()));
    if(state.org==='all'&&state.mode==='archive'&&state.action!=='all')
      result=result.filter(e=>e.action_group===state.action);
    if(state.org==='all'&&state.mode==='facility'&&state.phase!=='all')
      result=result.filter(e=>e.facility_phase===state.phase);
    if(state.search) {
      result=result.filter(e=>[e.title,e.actor,e.city,e.summary,e.dispute,e.outcome,e.status_label]
        .some(x=>String(x||'').toLowerCase().includes(state.search)));
    }
    return result.sort((a,b) => (a.facility_phase==='scheduled'?1:0)-(b.facility_phase==='scheduled'?1:0)
      || b.date.localeCompare(a.date) || a.title.localeCompare(b.title));
  }
  function legend() {
    let items;
    if(state.mode==='archive'&&state.org==='all') {
      items=Object.entries(ACTION_LABELS).map(([k,v])=>[v,COLORS[k],'archive']);
    } else if(state.mode==='facility'&&state.org==='all') {
      items=Object.entries(PHASE_LABELS).map(([k,v])=>[v,COLORS[k],'facility']);
    } else {
      items=[['政策',COLORS.policy,'policy'],['行动',COLORS.archive,'archive'],
        ['组织争议',COLORS.organization,'organization'],['能源设施',COLORS.facility,'facility']];
    }
    $('legend').innerHTML='<div class="legend-title">环保争议点位 · 2026-10-09 数据基准</div>'
      +'<div class="env-legend-row">'+items.map(([name,c,shape])=>'<span class="env-legend-item">'
      +'<i class="env-symbol '+shape+'" style="color:'+c+'"></i>'+esc(name)+'</span>').join('')+'</div>'
      +'<div class="env-legend-note">图形表示对象类别，颜色表示分类或状态；不代表犯罪率、风险评分或实际损失规模。</div>';
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
    const actor=actorGroup(e);
    target.innerHTML='<div class="env-detail-head"><strong>记录详情 · '+esc(cityName(e))
      +'</strong><button type="button" id="closeDetail" aria-label="关闭详情">关闭 ×</button></div>'
      +'<div class="env-detail-title">'+esc(e.title)+'</div>'
      +'<div class="env-detail-meta"><span>'+esc(e.date)+'</span><span>'+esc(kind(e))+'</span>'
      +(e.status_label?'<span>'+esc(e.status_label)+'</span>':'')
      +'<span>'+esc(e.actor||'行为主体未确定')+'</span></div>'
      +fields.join('')
      +'<div class="env-detail-section"><h3>原始资料</h3><div class="env-sources">'+sources+'</div></div>'
      +'<div class="env-limit">位置说明：'+esc(locationDescription)
      +'。组织立场、行动认领、司法认定及实际经济损失均须依据原始证据分别判断。</div>'
      +(actor?'<button type="button" class="env-detail-actor" id="actorFilter">筛选 '+esc(actor)+' 关联的记录 →</button>':'');
    $('closeDetail').onclick=()=>selectRecord(null,false);
    if(actor) $('actorFilter').onclick=()=>{$('org').value=actor;state.org=actor;state.selected=null;state.limit=18;render();};
  }
  function selectRecord(id,fly) {
    const e=rows.find(v=>v.id===id);
    state.selected=e?e.id:null;
    detail(e||null);
    $('areaName').textContent=e?cityName(e):'德国全国';
    $('kindBadge').textContent=e?kind(e):'专题概览';
    $('areaMetric').textContent=e?(e.actor||'事件主体未确定')+' · '+e.date:'政策、直接行动和电厂退出的可核查记录';
    if(e&&fly&&map) map.setView([e.coordinates.lat,e.coordinates.lon],Math.max(8,map.getZoom()),{animate:false});
    renderMarkers();
    for(const node of $('entries').querySelectorAll('[data-id]'))
      node.classList.toggle('selected',node.dataset.id===state.selected);
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
    const events=rows.filter(e=>e.kind==='archive').length;
    const plants=rows.filter(e=>e.kind==='facility').length;
    $('count').textContent=rows.length;
    $('eventCount').textContent=events;
    $('facilityCount').textContent=plants;
    $('listCount').textContent=rows.length+' 条';
    $('sectionTitle').textContent=state.org==='all'?CATEGORIES[state.mode]:state.org+' · 关联记录';
    $('resultScope').textContent='点位 '+rows.length+' · 点击查看';
    $('listHint').textContent=state.org==='all'?NOTES[state.mode]:'当前仅展示明确涉及所选组织的行动或争议记录；不能推定该组织参与其他破坏事件。';
    $('actionFilter').hidden=state.mode!=='archive'||state.org!=='all';
    $('phaseFilter').hidden=state.mode!=='facility'||state.org!=='all';
    $('areaName').textContent=selected?cityName(selected):'德国全国';
    $('kindBadge').textContent=selected?kind(selected):'专题概览';
    $('areaMetric').textContent=selected?selected.actor+' · '+selected.date:'政策、直接行动和电厂退出的可核查记录';
    document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===state.mode));
    legend();detail(selected);rank();renderEntries();renderMarkers();
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
        L.geoJSON(g,{pane:'environmentStates',interactive:false,
          style:()=>({color:'#273c50',weight:1.45,opacity:.77,fill:false})}).addTo(map);})
      .catch(e=>console.warn('Optional state outlines unavailable:',e));
    window.__ENVIRONMENT_MAP__={map,getRows:()=>rows,getMode:()=>state.mode,
      getSelected:()=>state.selected,getMarkerCount:()=>activeMarkers.size,
      getMarkers:()=>activeMarkers,getAll:()=>ALL,selectRecord};
  }
  function wire() {
    for(const b of document.querySelectorAll('[data-mode]')) b.onclick=()=>{
      state.mode=b.dataset.mode;state.org='all';state.action='all';state.phase='all';state.search='';
      state.selected=null;state.limit=18;
      $('org').value='all';$('action').value='all';$('phase').value='all';$('search').value='';
      render();
    };
    $('org').onchange=e=>{state.org=e.target.value;state.limit=18;render();};
    $('action').onchange=e=>{state.action=e.target.value;state.limit=18;render();};
    $('phase').onchange=e=>{state.phase=e.target.value;state.limit=18;render();};
    $('search').oninput=e=>{state.search=e.target.value.toLowerCase().trim();state.limit=18;render();};
    $('viewGermany').onclick=()=>{map.fitBounds(GERMANY,{padding:[14,14],animate:false});selectRecord(null,false);};
    $('viewBerlin').onclick=()=>map.fitBounds(BERLIN,{padding:[20,20],animate:false});
    $('viewHamburg').onclick=()=>map.fitBounds(HAMBURG,{padding:[20,20],animate:false});
    $('clearSelection').onclick=()=>selectRecord(null,false);
    $('moreRecords').onclick=()=>{state.limit+=24;renderEntries();};
  }
  try{
    validData();
    initMap();
    if(map){wire();render();}
  }catch(e){
    console.error(e);
    $('mapStatus').className='mapstatus fallback';
    $('mapStatus').textContent='环保专题初始化失败：'+e.message;
  }
})();