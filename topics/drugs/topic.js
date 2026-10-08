(() => {
  'use strict';
  const COLORS = ['#e5f4e8','#c5e7ce','#9dd4b0','#72bd91','#48a275','#267b59','#0e5139'];
  const nf = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 });
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const el = id => document.getElementById(id);
  const NATION_BOUNDS = [[47.05, 5.45], [55.15, 15.65]];
  const metric = rec => rec && rec.drug_crime && Number.isFinite(rec.drug_crime.rate)
    ? rec.drug_crime : null;

  function distribution(values) {
    const a = values.filter(Number.isFinite).sort((x, y) => x - y);
    if (!a.length) return [];
    return [0.15, 0.30, 0.45, 0.60, 0.75, 0.90].map(p => {
      const x = (a.length - 1) * p, lo = Math.floor(x), hi = Math.ceil(x);
      return a[lo] + (a[hi] - a[lo]) * (x - lo);
    });
  }
  function colorFor(value, breaks) {
    if (!Number.isFinite(value) || !breaks.length) return '#64727b';
    let i = 0;
    while (i < breaks.length && value > breaks[i]) i++;
    return COLORS[i];
  }
  function countyId(feature) {
    return String(feature?.id ?? feature?.properties?.AGS ?? '').padStart(5, '0');
  }
  function recordFor(feature, dataset) {
    const id = countyId(feature);
    const alias = dataset.meta.geometry_aliases?.[id];
    return dataset.records[id] || dataset.records[alias] || null;
  }
  function stateRows(name, dataset) {
    return Object.values(dataset.records || {}).filter(r => r.state === name && metric(r))
      .sort((a, b) => b.drug_crime.rate - a.drug_crime.rate);
  }
  function text(id, value) { const element = el(id); if (element) element.textContent = value; }
  function linkButton(row, onClick) {
    const li = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    const label = document.createElement('span');
    const value = document.createElement('span');
    label.textContent = row.name;
    value.textContent = nf.format(row.drug_crime.rate);
    button.append(label, value);
    button.onclick = () => onClick(row);
    li.append(button);
    return li;
  }
  function loadJson(url) {
    return fetch(url, { cache: 'no-store' }).then(r => {
      if (!r.ok) throw new Error(url + ': HTTP ' + r.status);
      return r.json();
    });
  }

  /**
   * Standalone page uses relative file paths; host integration may override
   * the three URLs or supply already loaded geometry.
   */
  async function loadData(options = {}) {
    const standalone = Boolean(el('drug-map'));
    const data = options.drugData || await loadJson(
      options.drugUrl || (standalone ? 'data/pks_drugs_2025.json' : 'topics/drugs/data/pks_drugs_2025.json'));
    if (!data?.records || !data?.meta || Object.keys(data.records).length < 390) {
      throw new Error('县级毒品数据未通过完整性检查，禁止显示为零案件');
    }
    const [countyGeo, stateGeo] = await Promise.all([
      options.countyGeo ? Promise.resolve(options.countyGeo) :
        loadJson(options.countiesUrl || (standalone ? '../../data/germany-counties-display.geojson' : 'data/germany-counties-display.geojson')),
      options.stateGeo ? Promise.resolve(options.stateGeo) :
        loadJson(options.statesUrl || (standalone ? '../../data/germany-states.geojson' : 'data/germany-states.geojson'))
    ]);
    if (!countyGeo?.features?.length || !stateGeo?.features?.length) {
      throw new Error('行政区边界数据不完整');
    }
    return { data, countyGeo, stateGeo };
  }

  let active = null;
  async function activate(context) {
    if (!window.L || !context?.map) throw new Error('Leaflet map instance required');
    deactivate();
    const {map} = context;
    const loaded = context.loaded || await loadData(context);
    const {data, countyGeo, stateGeo} = loaded;
    const rates = Object.values(data.records).map(r => Number(r.drug_crime?.rate))
      .filter(Number.isFinite);
    const breaks = distribution(rates);
    if (!breaks.length) throw new Error('No usable drug rates');
    for (const [name, z] of [['drugsCountyPane', 275], ['drugsStatePane', 365]]) {
      if (!map.getPane(name)) map.createPane(name);
      const pane = map.getPane(name);
      pane.style.zIndex = String(z);
    }
    const countyRenderer = L.svg({ pane: 'drugsCountyPane' });
    const stateRenderer = L.svg({ pane: 'drugsStatePane' });
    let counties, states, selectedCounty = null, selectedState = null, stateFeature = null;
    const container = L.layerGroup().addTo(map);
    const isStandalone = Boolean(el('drug-map'));
    const popup = el('state-panel');

    function showPanel() { if (isStandalone && popup) popup.hidden = false; }
    function closePanel() { if (popup) popup.hidden = true; selectedState = null; selectedCounty = null; }
    function renderCounty(rec, feature) {
      if (!rec || !metric(rec)) return;
      selectedCounty = rec.ags;
      selectedState = null;
      if (typeof context.onSelection === 'function') {
        context.onSelection({kind:'drugs-county',feature,record:rec,metric:rec.drug_crime});
      }
      if (!isStandalone) return;
      showPanel();
      text('state-name', rec.name);
      text('state-type', rec.state + ' · BKA PKS 2025 / 县级镜像');
      text('state-cases', nf.format(rec.drug_crime.cases));
      text('state-cases-label', '登记案件');
      text('state-rate', nf.format(rec.drug_crime.rate));
      text('state-rate-label', '每10万人登记案件');
      text('state-top-title', '当前县／市');
      const list = el('state-top'); list.replaceChildren();
      const item = document.createElement('li');item.className='note';
      const a = document.createElement('a');
      if (/^https:\/\/kriminalitaets-karte\.de\//.test(rec.source_url)) {
        a.href = rec.source_url; a.target = '_blank';a.rel='noopener noreferrer';a.textContent='查看本地区原始数据 ↗';
      } else a.textContent='来源不可用';
      item.appendChild(a); list.appendChild(item);
      text('state-note', '本指标为警方登记的Rauschgiftdelikte。部分合法化后大麻仍可能涉及违法交易等行为；本数字不是当地吸毒人口。');
      const focus = el('state-focus');
      if (focus) focus.onclick = () => {
        const layer = counties?.getLayers().find(l => l.feature && recordFor(l.feature, data)?.ags === rec.ags);
        if (layer?.getBounds) map.fitBounds(layer.getBounds(), {maxZoom:9,padding:[35,35]});
      };
    }
    function renderState(feature) {
      const name = feature.properties?.name;
      const rows = stateRows(name, data);
      selectedState = name;
      selectedCounty = null;
      stateFeature = feature;
      if (typeof context.onSelection === 'function') {
        context.onSelection({kind:'drugs-state',feature,name,rows,
          summedCases:rows.reduce((a,r)=>a+r.drug_crime.cases,0)});
      }
      if (!isStandalone) return;
      showPanel();
      text('state-name', name);
      text('state-type', 'BKA PKS 2025 · ' + rows.length + '个已覆盖县/市');
      text('state-cases', nf.format(rows.reduce((a,r) => a+r.drug_crime.cases, 0)));
      text('state-cases-label', '已覆盖县／市案件汇总');
      const middle = rows.length ? rows[Math.floor(rows.length / 2)].drug_crime.rate : null;
      text('state-rate', middle == null ? '—' : nf.format(middle));
      text('state-rate-label', '县市登记率中位值/10万人（非全州率）');
      text('state-top-title', '州内登记率较高县市');
      const list = el('state-top'); list.replaceChildren();
      rows.slice(0,8).forEach(r => list.append(linkButton(r, () => {
        const layer = counties?.getLayers().find(l => l.feature && recordFor(l.feature,data)?.ags===r.ags);
        if (layer?.getBounds) map.fitBounds(layer.getBounds(),{maxZoom:9,padding:[35,35]});
        renderCounty(r, layer?.feature);
      })));
      text('state-note', '显示州内已匹配的县级记录。中位值不代表全州人均案件率；警方查处数量亦不能直接反映实际消费规模。');
      const focus = el('state-focus');
      if (focus) focus.onclick = () => {
        const layer = states?.getLayers().find(l => l.feature?.properties?.name === name);
        if (layer?.getBounds) map.fitBounds(layer.getBounds(),{padding:[28,28],maxZoom:8});
      };
    }
    function countyStyle(f) {
      const rec = recordFor(f, data), datum = metric(rec);
      return {
        renderer: countyRenderer, pane:'drugsCountyPane',
        color:'#163b32',weight:.45,opacity:.75,
        fillColor:datum ? colorFor(Number(datum.rate),breaks) : '#64727b',
        fillOpacity:datum ? .91 : .35
      };
    }
    counties = L.geoJSON(countyGeo, {
      pane:'drugsCountyPane', renderer:countyRenderer, style:countyStyle,
      onEachFeature: (feature, layer) => {
        const rec = recordFor(feature, data);
        if (!rec || !metric(rec)) return;
        layer.bindTooltip('<b>'+esc(rec.name)+'</b><br>'+nf.format(rec.drug_crime.cases)+
          '起 · '+nf.format(rec.drug_crime.rate)+' /10万人', {sticky:true});
        layer.on('click', e => {
          L.DomEvent.stopPropagation(e);
          renderCounty(rec, feature);
          layer.setStyle({color:'#d7f7e4',weight:2,opacity:1});
        });
      }
    }).addTo(container);
    let stateInteractivity = null;
    function updateStates() {
      const interactive = map.getZoom() < 7.5;
      if (states && interactive === stateInteractivity) return;
      if (states) container.removeLayer(states);
      stateInteractivity = interactive;
      states = L.geoJSON(stateGeo, {
        pane:'drugsStatePane', renderer:stateRenderer, interactive,
        style: () => ({pane:'drugsStatePane',renderer:stateRenderer,
          color:'#98c7ae',weight:1.15,opacity:.8,
          fill:interactive,fillColor:'#fff',fillOpacity:interactive?0.001:0}),
        onEachFeature: (feature, layer) => {
          layer.bindTooltip(esc(feature.properties?.name || ''), {sticky:true});
          if (interactive) layer.on('click', e => {
            L.DomEvent.stopPropagation(e);
            renderState(feature);
          });
        }
      }).addTo(container);
    }
    map.on('zoomend', updateStates);
    updateStates();

    if (isStandalone) {
      const ordered = Object.values(data.records).filter(r=>metric(r))
        .sort((a,b)=>b.drug_crime.rate-a.drug_crime.rate);
      text('county-count', data.meta.matched_geometry + ' / ' + data.meta.geometry_count);
      text('highest-value', ordered.length ? nf.format(ordered[0].drug_crime.rate) : '—');
      text('highest-name', ordered.length ? ordered[0].name + ' · 每10万人' : '县市最高登记率');
      text('status', '2025年 · '+Object.keys(data.records).length+'条记录 · '+data.meta.matched_geometry+
        '个行政区匹配；国家统计与县级镜像口径分开');
      const list = el('top-list');
      if (list) {
        list.replaceChildren();
        ordered.slice(0,12).forEach(r=>list.append(linkButton(r,()=>{
          const layer = counties?.getLayers().find(l=>l.feature&&recordFor(l.feature,data)?.ags===r.ags);
          if (layer?.getBounds) map.fitBounds(layer.getBounds(),{maxZoom:9,padding:[32,32]});
          renderCounty(r,layer?.feature);
        })));
      }
      const legends = el('legend-data');
      if (legends) {
        legends.innerHTML = '<div class="legend-gradient">'+COLORS.map(c=>'<span style="background:'+c+'"></span>').join('')+'</div>'+
          '<div class="legend-limits"><span>≤ '+nf.format(Math.round(breaks[0]))+'</span>'+
          '<span>> '+nf.format(Math.round(breaks[5]))+'</span></div>'+
          '<div class="legend-info">按2025年县市分位着色 · 灰色为缺失</div>';
      }
      const close = el('close-state');
      if (close) close.onclick = closePanel;
      const reset = el('reset-map');
      if (reset) reset.onclick = () => {closePanel();map.fitBounds(NATION_BOUNDS,{padding:[13,13]});};
    }
    active = {
      map, container, updateStates,
      setVisible(visible) {
        if (visible && !map.hasLayer(container)) container.addTo(map);
        if (!visible && map.hasLayer(container)) map.removeLayer(container);
        if (!visible) closePanel();
      },
      deactivate() {
        map.off('zoomend',updateStates);
        map.removeLayer(container);
        closePanel();
        if (isStandalone) {
          const close=el('close-state'), reset=el('reset-map'),focus=el('state-focus');
          if(close)close.onclick=null;if(reset)reset.onclick=null;if(focus)focus.onclick=null;
        }
      }
    };
    if (isStandalone && window.GermanMapDrugWastewater?.init) {
      window.GermanMapDrugWastewater.init({map,crime:active});
    }
    return active;
  }
  function deactivate() {
    if (active) {active.deactivate();active=null;}
  }

  window.GermanMapTopics = window.GermanMapTopics || {};
  window.GermanMapTopics.drugs = Object.freeze({
    id: 'drugs', title: '毒品问题', loadData, activate, deactivate
  });

  if (el('drug-map')) {
    if (!window.L) { text('status','地图框架加载失败，请检查网络连接。'); return; }
    const map = L.map('drug-map',{minZoom:5,maxZoom:15,zoomControl:true,preferCanvas:false});
    map.fitBounds(NATION_BOUNDS, {padding:[15,15]});
    window.__DRUGS_PREVIEW_MAP__ = map;
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom:19,opacity:.56,attribution:'© OpenStreetMap contributors'
    }).addTo(map);
    activate({map}).catch(error => {
      console.error(error);
      text('status','数据加载失败：'+error.message);
      text('county-count','不可用');
      const legend=el('legend-data');
      if (legend) legend.textContent='数据暂不可用，未填充虚假数值';
    });
  }
})();
