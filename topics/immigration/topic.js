/* German-Map 05 — isolated immigration mapping component.
 * This module never captures the host map's mouse/pointer handlers.
 * Statistics represent distinct legal/administrative concepts.
 */
(() => {
  'use strict';

  const script = typeof document !== 'undefined' ? document.currentScript : null;
  const base = script?.src || (typeof location !== 'undefined' ? location.href : 'https://example.invalid/topics/immigration/topic.js');
  const sources = Object.freeze({
    azr: new URL('data/state-return-obligations-2025.json', base).href,
    deport: new URL('data/state-deportations-2025.json', base).href,
  });
  const palette = Object.freeze(['#e5eff3','#b3d4df','#77b4c5','#39879f','#12566f']);
  const deportPalette = Object.freeze(['#f0e9f5','#d7c7e4','#b89cca','#8e6da9','#573c7c']);
  const METRICS = Object.freeze({
    return_total: {title:'负有离境义务', key:'total', data:'azr', note:'2025年12月31日 · AZR登记存量'},
    return_duldung: {title:'其中持有暂缓遣返证明', key:'with_duldung', data:'azr', note:'2025年12月31日 · Duldung'},
    return_no_duldung: {title:'其中未持暂缓遣返证明', key:'without_duldung', data:'azr', note:'2025年12月31日 · AZR登记存量'},
    deportations: {title:'全年实际遣返', key:'value', data:'deport', note:'2025全年 · 按执行机构统计'},
  });
  const INITIAL_METRIC = 'return_total';
  const TOPIC = {id:'immigration',title:'非法移民与边境管制'};

  let datasets = null;
  let pending = null;
  let active = null;
  let selectedMetric = INITIAL_METRIC;
  let selectedState = 'DE-NW';
  const fmt = n => n == null ? '无数据' : Number(n).toLocaleString('zh-CN');
  const safeCount = n => Number.isSafeInteger(n) && n >= 0;

  function verifyDataset(raw, kind) {
    const azr = kind === 'azr';
    if (!raw || raw.schema_version !== 1 || !Array.isArray(raw.records) ||
        raw.records.length !== 16 || !raw.source?.url?.startsWith('https://') ||
        raw.completeness?.reported_states !== 16)
      throw new Error('Immigration: incomplete or unsupported '+kind+' dataset');
    const ids = new Set();
    const sums = azr ? {total:0,with_duldung:0,without_duldung:0} : {value:0};
    for (const rec of raw.records) {
      if (!/^DE-[A-Z]{2}$/.test(rec.iso) || !/^\d{2}$/.test(rec.ags) ||
          ids.has(rec.iso) || !rec.name_de) throw new Error('Immigration: malformed region ID');
      ids.add(rec.iso);
      for (const key of Object.keys(sums)) {
        if (!safeCount(rec[key])) throw new Error('Immigration: invalid '+key+' for '+rec.iso);
        sums[key] += rec[key];
      }
      if (azr && rec.total !== rec.with_duldung + rec.without_duldung)
        throw new Error('Immigration: inconsistent Duldung categories');
    }
    if (azr) {
      if (raw.reference_date !== '2025-12-31' ||
          Object.keys(sums).some(key => sums[key] !== raw.totals?.[key]) ||
          sums.total !== 232067 || sums.with_duldung !== 190974 ||
          sums.without_duldung !== 41093)
        throw new Error('Immigration: AZR totals mismatch');
    } else if (raw.metric_id !== 'deportations_executed' ||
        sums.value !== raw.states_subtotal ||
        sums.value + raw.federal_police_separately !== raw.total_all_authorities ||
        raw.total_all_authorities !== 22787) {
      throw new Error('Immigration: deportation totals mismatch');
    }
    return raw;
  }

  async function loadData() {
    if (datasets) return datasets;
    if (pending) return pending;
    pending = Promise.all(Object.entries(sources).map(async ([kind,url]) => {
      const response = await fetch(url, {cache:'no-store'});
      if (!response.ok) throw new Error('Immigration: '+kind+' dataset HTTP '+response.status);
      return [kind, verifyDataset(await response.json(), kind)];
    })).then(entries => {
      const verified = Object.fromEntries(entries);
      const a = new Set(verified.azr.records.map(r => r.iso));
      if (verified.deport.records.some(r => !a.has(r.iso)))
        throw new Error('Immigration: geographic mismatch between sources');
      datasets = verified;
      return datasets;
    }).finally(() => {pending = null;});
    return pending;
  }

  function element(tag, text, cls) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text != null) el.textContent = text;
    return el;
  }
  function metricRows(metricId) {
    const meta = METRICS[metricId];
    return datasets[meta.data].records.map(rec => ({...rec, metricValue:rec[meta.key]}));
  }
  function metricValue(metricId, iso) {
    const meta = METRICS[metricId];
    const record = datasets[meta.data].records.find(r => r.iso === iso);
    return record?.[meta.key] ?? null;
  }
  function quantileBreaks(metricId) {
    const vals = metricRows(metricId).map(r => r.metricValue)
      .filter(Number.isFinite).sort((a,b) => a-b);
    if (!vals.length) return [];
    return [1,2,3,4].map(q => vals[Math.ceil((q/5)*vals.length)-1]);
  }
  function colorFor(value, breaks, metricId) {
    if (value == null || !Number.isFinite(value)) return '#c8d0d8';
    const colors = metricId === 'deportations' ? deportPalette : palette;
    let band = breaks.findIndex(b => value <= b);
    if (band < 0) band = colors.length - 1;
    return colors[band];
  }
  function appendSourceLink(parent, source) {
    const a = element('a', source.document);
    a.href = source.url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    parent.append(a);
  }

  function activate(context) {
    if (active) deactivate();
    if (!datasets) throw new Error('Immigration: call loadData() before activate()');
    if (!context?.map || !context.container || !Array.isArray(context.stateGeoJSON?.features) ||
        typeof L === 'undefined' || typeof L.geoJSON !== 'function')
      throw new Error('Immigration: missing Leaflet map, panel, or state GeoJSON');
    const {map, container, stateGeoJSON} = context;
    const paneName = 'immigrationDataPane';
    const pane = map.getPane(paneName) || map.createPane(paneName);
    // Dedicated, strictly noninteractive pane below the host county/state layers.
    pane.style.zIndex = '215';
    pane.style.pointerEvents = 'none';
    const known = new Set(datasets.azr.records.map(r => r.iso));
    const matched = new Set(stateGeoJSON.features
      .map(f => f?.properties?.id).filter(id => known.has(id)));
    const missing = [...known].filter(id => !matched.has(id));

    const root = element('section', null, 'immigration-topic');
    const brand = element('div', 'GERMAN-MAP · 专题 05', 'im-brand');
    const heading = element('h2', '非法移民与边境管制');
    const intro = element('p',
      '官方州级统计 · 不以庇护申请或外国人口替代非法居留指标', 'im-intro');
    const tabsTitle = element('h3', '选择专题指标');
    const tabs = element('div', null, 'im-metrics');
    const tabButtons = new Map();
    const listeners = [];
    const rankListeners = [];
    function listen(node,event,handler) {
      node.addEventListener(event,handler);
      listeners.push([node,event,handler]);
    }
    for (const [id, meta] of Object.entries(METRICS)) {
      const btn = element('button', meta.title, 'im-metric');
      btn.type = 'button';
      btn.setAttribute('aria-pressed', String(id === selectedMetric));
      listen(btn,'click',() => selectMetric(id));
      tabButtons.set(id,btn);
      tabs.append(btn);
    }
    const contextLine = element('p','', 'im-period');
    const national = element('div',null,'im-national');
    const nationalLabel = element('div','全国官方统计','im-national-label');
    const nationalNumber = element('div','', 'im-national-value');
    const nationalNote = element('div','', 'im-national-note');
    national.append(nationalLabel,nationalNumber,nationalNote);
    const legendHeading = element('h3','地图图例 · 相同指标按五档着色');
    const legend = element('div',null,'im-legend');
    const legendNote = element('p','各州绝对人数，未经人口规模标准化。灰色表示缺少数据。','im-footnote');
    const stateTitle = element('h3','查看联邦州');
    const picker = element('select',null,'im-picker');
    picker.setAttribute('aria-label','选择德国联邦州');
    const sorted = [...datasets.azr.records].sort((a,b)=>a.name_de.localeCompare(b.name_de,'de'));
    for (const rec of sorted) {
      const option=element('option',rec.name_de);
      option.value=rec.iso;
      picker.append(option);
    }
    const selection = element('section',null,'im-selection');
    const areaTitle = element('h3','', 'im-area-title');
    const areaFigure = element('div','', 'im-area-number');
    const areaUnit = element('p','', 'im-area-subtitle');
    const miniStats = element('div',null,'im-mini-stats');
    selection.append(areaTitle,areaFigure,areaUnit,miniStats);
    const rankingTitle = element('h3','当前指标 · 前五州');
    const ranking = element('ol',null,'im-ranking');
    const caution = element('div',
      '统计口径说明：负有离境义务不等于刑事犯罪；暂缓遣返是法律/执行状态。2025年底登记存量与2025全年遣返执行量不可直接相除计算“遣返率”。',
      'im-caution');
    const coverage = element('p',
      '行政边界匹配 '+matched.size+'/16 州'+(missing.length?'；未匹配 '+missing.length+' 州显示为缺失':'；无缺失'),
      'im-coverage');
    const sourceTitle = element('h3','原始数据与出处');
    const references = element('div',null,'im-sources');
    appendSourceLink(references,datasets.azr.source);
    appendSourceLink(references,datasets.deport.source);
    root.append(brand,heading,intro,tabsTitle,tabs,contextLine,national,legendHeading,
      legend,legendNote,stateTitle,picker,selection,rankingTitle,ranking,caution,
      coverage,sourceTitle,references);

    const geoLayer=L.geoJSON(stateGeoJSON,{
      pane:paneName,
      interactive:false,
      style: feature=>{
        const iso=feature?.properties?.id;
        const rec=known.has(iso) ? metricValue(selectedMetric,iso) : null;
        const breaks=quantileBreaks(selectedMetric);
        return {
          pane:paneName,interactive:false,color:iso===selectedState?'#153b4c':'#8a9fab',
          weight:iso===selectedState?2.8:.7,
          opacity:iso===selectedState?1:.8,
          fillColor:colorFor(rec,breaks,selectedMetric),
          fillOpacity:rec == null ? .13 : .79,
        };
      },
    });
    geoLayer.addTo(map);
    container.append(root);

    function selectState(iso, notifyHost = false) {
      if (!known.has(iso)) return false;
      selectedState=iso;
      picker.value=iso;
      const meta=METRICS[selectedMetric];
      const row=datasets.azr.records.find(r=>r.iso===iso);
      const count=metricValue(selectedMetric,iso);
      areaTitle.textContent=row.name_de;
      areaFigure.textContent=fmt(count)+' 人';
      areaUnit.textContent=meta.title+' · '+meta.note;
      miniStats.replaceChildren();
      const data=[
        ['离境义务总数',row.total],
        ['持暂缓遣返',row.with_duldung],
        ['无暂缓遣返',row.without_duldung],
        ['全年实际遣返',metricValue('deportations',iso)],
      ];
      for (const [label,value] of data) {
        const cell=element('div',null,'im-mini-cell');
        cell.append(element('span',label),element('strong',fmt(value)));
        miniStats.append(cell);
      }
      if (typeof geoLayer.setStyle === 'function') geoLayer.setStyle(geoLayer.options.style);
      if (notifyHost && typeof context.onStateSelected === 'function') context.onStateSelected(iso);
      return true;
    }

    function selectMetric(id) {
      if (!METRICS[id]) return false;
      selectedMetric=id;
      const meta=METRICS[id],raw=datasets[meta.data];
      tabButtons.forEach((button,key)=>button.setAttribute('aria-pressed',String(key===id)));
      contextLine.textContent=meta.note;
      nationalNumber.textContent=fmt(meta.data==='azr'?raw.totals[meta.key]:raw.total_all_authorities);
      nationalNote.textContent=meta.data==='deport'
        ? '人 · 全国包含联邦警察单列 '+fmt(raw.federal_police_separately)+' 人；州级着色仅计算16州执行部分'
        : '人 · 全国16州登记存量；不是非法入境案件数';
      legend.replaceChildren();
      const breaks=quantileBreaks(id),colors=id==='deportations'?deportPalette:palette;
      breaks.concat([null]).forEach((high,i)=>{
        const entry=element('div',null,'im-legend-item');
        const swatch=element('i',null,'im-swatch');
        swatch.style.background=colors[i];
        const low=i===0?0:breaks[i-1]+1;
        const label=high==null ? fmt(low)+' 及以上':fmt(low)+' — '+fmt(high);
        entry.append(swatch,element('span',label));
        legend.append(entry);
      });
      for (const [node,event,handler] of rankListeners) node.removeEventListener(event,handler);
      rankListeners.length = 0;
      ranking.replaceChildren();
      metricRows(id).sort((a,b)=>b.metricValue-a.metricValue).slice(0,5)
        .forEach((rec,index)=>{
          const item=element('li',null,'im-rank-row');
          const btn=element('button',null,'im-rank-button');
          btn.type='button';
          btn.append(element('span',(index+1)+'. '+rec.name_de),element('strong',fmt(rec.metricValue)));
          const handler = () => selectState(rec.iso,true);
          btn.addEventListener('click',handler);
          rankListeners.push([btn,'click',handler]);
          item.append(btn);
          ranking.append(item);
        });
      selectState(selectedState);
      return true;
    }
    listen(picker,'change',()=>selectState(picker.value,true));
    active={map,geoLayer,root,listeners,rankListeners,selectMetric,selectState,matched};
    selectMetric(selectedMetric);
    return {matchedStates:matched.size,reportedStates:datasets.azr.records.length};
  }

  function selectMetric(id) {
    if (!METRICS[id]) return false;
    if (active) return active.selectMetric(id);
    selectedMetric=id;
    return true;
  }
  function selectState(iso) {
    if (!/^DE-[A-Z]{2}$/.test(String(iso))) return false;
    if (active) return active.selectState(iso,true);
    if (!datasets?.azr.records.some(r=>r.iso===iso)) return false;
    selectedState=iso;
    return true;
  }
  function getViewState() {
    return Object.freeze({metric:selectedMetric,state:selectedState,active:!!active});
  }

  function deactivate() {
    if (!active) return;
    const {map,geoLayer,root,listeners,rankListeners}=active;
    for (const [node,event,handler] of [...listeners,...rankListeners]) node.removeEventListener(event,handler);
    if (map.hasLayer(geoLayer)) map.removeLayer(geoLayer);
    root.remove();
    active=null;
  }
  window.GermanMapTopics=window.GermanMapTopics||{};
  window.GermanMapTopics.immigration=Object.freeze({
    ...TOPIC,loadData,activate,deactivate,selectMetric,selectState,getViewState,
  });
})();
