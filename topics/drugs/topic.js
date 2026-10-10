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
  // State aggregates are computed from the same 400 county records.
  // The approximate rate is derived from the (rounded) county denominators,
  // NOT reported by BKA as an independently validated official state rate.
  function stateStats(name, data) {
    const rows = stateRows(name, data);
    const cases = rows.reduce((sum, row) => sum + row.drug_crime.cases, 0);
    const populationEstimate = rows.reduce((sum, row) => {
      const {cases, rate} = row.drug_crime;
      return sum + (rate > 0 ? cases / rate * 100000 : 0);
    }, 0);
    return {name, rows, cases, rateEstimate:populationEstimate ? cases / populationEstimate * 100000 : null};
  }
  function parseChange(value) {
    const match = String(value ?? '').trim().match(/^([+-]?\d+(?:[,.]\d+)?)\s*%$/);
    return match ? Number(match[1].replace(',', '.')) : null;
  }
  function safeNode(tag, value, className = '') {
    const node = document.createElement(tag);
    node.textContent = String(value);
    if (className) node.className = className;
    return node;
  }
  function text(id, value) { const element = el(id); if (element) element.textContent = value; }
  function linkButton(row, onClick) {
    const li = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    const label = document.createElement('span');
    const value = document.createElement('span');
    label.textContent = window.GermanPlaceNames?.byAGS(row.ags,row.name)||row.name;
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
    const countyRenderer = L.svg({ pane: 'drugsCountyPane', padding: .2 });
    const stateRenderer = L.svg({ pane: 'drugsStatePane', padding: .2 });
    let counties, states, selectedCounty = null, selectedState = null, selectedCountyLayer = null, stateFeature = null;
    const stateFeatures = new Map(stateGeo.features.map(f => [f.properties?.name, f]));
    const stateStatistics = new Map([...stateFeatures.keys()].map(name => [name, stateStats(name, data)]));
    const totalCountyCases = [...stateStatistics.values()].reduce((sum, v) => sum + v.cases, 0);
    const container = L.layerGroup().addTo(map);
    const isStandalone = Boolean(el('drug-map'));
    let lastBoardState = null;

    function renderRegionNews(name) {
      const list=el('region-news-list'),all=el('region-news-all');
      if(!list||!all)return;
      const item=document.createElement('li');
      item.className='note';
      item.textContent='正在读取本州公开通报…';
      list.replaceChildren(item);
      all.onclick=()=>window.GermanMapDrugNews?.openForState?.(name);
      const api=window.GermanMapDrugNews;
      if(!api?.reportsForState) {
        item.textContent='新闻模块尚未准备好';
        return;
      }
      api.reportsForState(name,3).then(entries=>{
        if(selectedState!==name || !el('region-navigator') || el('region-navigator').hidden)return;
        list.replaceChildren();
        if(!entries.length) {
          const li=document.createElement('li');li.className='note';
          li.textContent='目前没有收录本州相关通报；不代表没有发生相关事件。';
          list.append(li);
          return;
        }
        for(const entry of entries) {
          const li=document.createElement('li'), a=document.createElement('a');
          a.href=entry.source_url;
          a.target='_blank';a.rel='noopener noreferrer';
          a.className='region-news-link';
          a.append(safeNode('span',entry.publication_date+' · '+entry.city,'region-news-date'),
            safeNode('span',entry.title,'region-news-title'));
          li.append(a);list.append(li);
        }
      }).catch(()=>{
        if(selectedState!==name)return;
        list.replaceChildren();
        const li=document.createElement('li');li.className='note';
        li.textContent='近期通报暂时无法加载';list.append(li);
      });
    }
    function showRegionBoard(name, county = null) {
      if (!isStandalone) return;
      const board = el('region-navigator'), national = el('national-drug-summary');
      const stats = stateStatistics.get(name);
      if (!board || !national || !stats) return;
      // A new state opens as a clean summary, without carrying over
      // expanded long lists from a previously selected state. Moving among
      // counties in the same state preserves user-opened drawers.
      if (lastBoardState !== name) {
        for (const id of ['region-county-details','region-news','region-evidence','region-interpretation']) {
          const details = el(id);
          if (details) details.open = false;
        }
        lastBoardState = name;
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) sidebar.scrollTop = 0;
      }
      board.hidden = false;
      national.hidden = true;
      const countyMode = Boolean(county);
      const stateLink = el('region-state-link');
      stateLink.hidden = !countyMode;
      stateLink.textContent = name;
      el('region-county-separator').hidden = !countyMode;
      text('region-current', countyMode ? (window.GermanPlaceNames?.byAGS(county.ags,county.name)||county.name) : name);
      text('region-heading', countyMode ? (window.GermanPlaceNames?.byAGS(county.ags,county.name)||county.name) + ' · 县市详情' : name + ' · 州级汇总');
      text('region-cases', nf.format(countyMode ? county.drug_crime.cases : stats.cases));
      text('region-rate', nf.format(countyMode ? county.drug_crime.rate : Math.round(stats.rateEstimate || 0)));
      text('region-cases-label', countyMode ? '县级登记案件' : '州内县级案件总数（汇总）');
      text('region-rate-label', countyMode ? '该县/市每10万人登记案件' : '估算州级每10万人案件（参考）');
      text('region-completeness', countyMode
        ? '2025年 · ' + name + ' · 该县同比 ' + (county.drug_crime.change || '未公布')
        : '2025年 · 已收录 ' + stats.rows.length + ' 个县/独立市 · 占全国县级汇总 ' +
          (totalCountyCases ? (100 * stats.cases / totalCountyCases).toFixed(1) : '—') + '%');
      const change = countyMode ? parseChange(county.drug_crime.change) : null;
      const trend = el('region-change');
      if (trend) {
        trend.hidden = !countyMode;
        trend.classList.toggle('is-rising',countyMode && change !== null && change > 0);
        trend.classList.toggle('is-falling',countyMode && change !== null && change < 0);
        trend.textContent = countyMode
          ? '较2024年登记案件：' + (change === null ? '未公布' :
            (change > 0 ? '↑ +' : change < 0 ? '↓ −' : '→ ') +
            nf.format(Math.abs(change)) + '%')
          : '州级同比：暂无独立核实的可比数据';
      }
      text('region-compare-note', countyMode
        ? '变化率采用县级来源原值（已四舍五入），不是吸毒率变化。2024年大麻法律调整造成统计口径断点，跨年比较应谨慎。'
        : '不将各县已四舍五入的变化率相加推算全州同比。');
      const original = el('region-original-source');
      if (original) {
        const safe = countyMode && /^https:\/\/kriminalitaets-karte\.de\/kriminalitaet\//.test(county.source_url);
        original.hidden = !safe;
        if (safe) original.href = county.source_url;
        else original.removeAttribute('href');
      }
      renderRegionNews(name);
      window.GermanMapDrugEvidence?.show?.(name);
      text('region-list-heading', countyMode ? '州内其他县市 · 按登记率排序' : '州内全部县市 · 按登记率排序');
      text('region-subtitle', stats.rows.length + '个地区');
      text('region-footnote', countyMode
        ? '该地区数据来自PKS县级指标镜像，警方登记案件不代表实际毒品消费。点击列表可跳转州内其他县市。'
        : '州案件数由县级记录合计，估算州率由县级四舍五入的登记率反推人口加权得到，并非独立公布的官方州级率；不代表吸毒人数。大麻、可卡因等州级细分类数据尚待官方原表核实。');
      const focus = el('region-drill');
      focus.textContent = countyMode ? '定位当前县市' : '查看县市地图';
      focus.onclick = () => countyMode ? focusCounty(county) : focusState(name);
      stateLink.onclick = () => selectState(name);
      const list = el('region-county-list'); list.replaceChildren();
      stats.rows.forEach(row => {
        const li = document.createElement('li'), btn = document.createElement('button');
        btn.type = 'button';
        if (countyMode && row.ags === county.ags) {
          btn.classList.add('selected-region');
          btn.setAttribute('aria-current', 'true');
        }
        btn.append(safeNode('span', window.GermanPlaceNames?.byAGS(row.ags,row.name)||row.name),safeNode('span',
          nf.format(row.drug_crime.rate) + ' /10万人'));
        btn.title = row.name + '：' + nf.format(row.drug_crime.cases) + '起；同比 ' +
          (row.drug_crime.change || '未公布');
        btn.onclick = () => focusCounty(row);
        li.append(btn);list.append(li);
      });
    }
    function focusCounty(rec) {
      const layer = counties?.getLayers().find(l => l.feature &&
        recordFor(l.feature,data)?.ags === rec.ags);
      if (layer?.getBounds) {
        map.fitBounds(layer.getBounds(), {maxZoom:10,minZoom:8,padding:[55,55],animate:false});
        if (map.getZoom() < 8) map.setView(layer.getBounds().getCenter(),8,{animate:false});
      }
      renderCounty(rec,layer?.feature);
    }
    function focusState(name) {
      const layer = states?.getLayers().find(l => l.feature?.properties?.name === name);
      const geometry = stateFeatures.get(name);
      const bounds = layer?.getBounds() || (geometry && L.geoJSON(geometry).getBounds());
      if (bounds) {
        map.fitBounds(bounds,{padding:[45,45],maxZoom:8,animate:false});
        // Deep zoom is explicit, never automatic on first state click.
        if (map.getZoom() < 8) map.setView(bounds.getCenter(),8,{animate:false});
      }
      text('map-guide-title','县市级毒品违法案件');
      text('map-guide-desc','点击县市查看登记案件、每10万人案件率及同比变化。');
    }
    function selectState(name) {
      const feature = stateFeatures.get(name);
      if (feature) renderState(feature);
    }
    function resetRegion() {
      lastBoardState = null;
      selectedCounty = null;
      selectedState = null;
      if (selectedCountyLayer && counties) counties.resetStyle(selectedCountyLayer);
      selectedCountyLayer = null;
      refreshStateSelection();
      const board = el('region-navigator'),national=el('national-drug-summary');
      if (board) board.hidden=true;
      if (national) national.hidden=false;
      const regionNewsList=el('region-news-list');if(regionNewsList)regionNewsList.replaceChildren();
      window.GermanMapDrugNews?.setStateFilter?.('all');
      text('map-guide-title','警方登记毒品案件 · 2025');
      text('map-guide-desc','点击联邦州或县市查看详细数据');
      map.fitBounds(NATION_BOUNDS,{padding:[13,13],animate:false});
    }
    function renderCounty(rec, feature) {
      if (!rec || !metric(rec)) return;
      selectedCounty = rec.ags;
      selectedState = rec.state;
      if (selectedCountyLayer && counties) counties.resetStyle(selectedCountyLayer);
      selectedCountyLayer = counties?.getLayers().find(l => l.feature && recordFor(l.feature,data)?.ags === rec.ags) || null;
      if (selectedCountyLayer) {
        selectedCountyLayer.setStyle({color:'#ffffff',weight:3.2,opacity:1,fillOpacity:.72});
        selectedCountyLayer.bringToFront?.();
      }
      refreshStateSelection();
      showRegionBoard(rec.state, rec);
      window.GermanMapDrugNews?.setStateFilter?.(rec.state);
      if (typeof context.onSelection === 'function') {
        context.onSelection({kind:'drugs-county',feature,record:rec,metric:rec.drug_crime});
      }
    }
    function renderState(feature) {
      const name = feature.properties?.name;
      const rows = stateRows(name, data);
      selectedState = name;
      selectedCounty = null;
      if (selectedCountyLayer && counties) counties.resetStyle(selectedCountyLayer);
      selectedCountyLayer = null;
      stateFeature = feature;
      refreshStateSelection();
      showRegionBoard(name);
      window.GermanMapDrugNews?.setStateFilter?.(name);
      if (typeof context.onSelection === 'function') {
        context.onSelection({kind:'drugs-state',feature,name,rows,
          summedCases:rows.reduce((a,r)=>a+r.drug_crime.cases,0)});
      }
    }
    function countyStyle(f) {
      const rec = recordFor(f, data), datum = metric(rec);
      return {
        renderer: countyRenderer, pane:'drugsCountyPane',
        color:'#163b32',weight:.45,opacity:.75,
        fillColor:datum ? colorFor(Number(datum.rate),breaks) : '#64727b',
        fillOpacity:datum ? .56 : .16
      };
    }
    counties = L.geoJSON(countyGeo, {
      pane:'drugsCountyPane', renderer:countyRenderer, style:countyStyle,
      onEachFeature: (feature, layer) => {
        const rec = recordFor(feature, data);
        if (!rec || !metric(rec)) return;
        layer.bindTooltip('<b>'+esc(window.GermanPlaceNames?.byAGS(rec.ags,rec.name)||rec.name)+'</b><br>'+nf.format(rec.drug_crime.cases)+
          '起 · '+nf.format(rec.drug_crime.rate)+' /10万人', {sticky:true});
        layer.on('click', e => {
          L.DomEvent.stopPropagation(e);
          renderCounty(rec, feature);
        });
      }
    }).addTo(container);
    let stateInteractivity = null;
    function refreshStateSelection() {
      if (!states) return;
      states.eachLayer(layer => {
        if (!layer.feature) return;
        layer.setStyle({
          color:layer.feature.properties?.name===selectedState ? '#ffffff' : '#98c7ae',
          weight:layer.feature.properties?.name===selectedState ? 3.6 : 1.15,
          opacity:layer.feature.properties?.name===selectedState ? 1 : .8
        });
        if (layer.feature.properties?.name === selectedState) layer.bringToFront?.();
      });
    }
    function updateStates() {
      const interactive = map.getZoom() < 7.5;
      if (states && interactive === stateInteractivity) return;
      if (states) container.removeLayer(states);
      stateInteractivity = interactive;
      states = L.geoJSON(stateGeo, {
        pane:'drugsStatePane', renderer:stateRenderer, interactive,
        style: (feature) => ({pane:'drugsStatePane',renderer:stateRenderer,
          color:feature?.properties?.name===selectedState?'#ffffff':'#98c7ae',weight:feature?.properties?.name===selectedState?3.6:1.15,opacity:.8,
          fill:interactive,fillColor:'#fff',fillOpacity:interactive?0.001:0}),
        onEachFeature: (feature, layer) => {
          layer.bindTooltip(esc(feature.properties?.name || ''), {sticky:true});
          if (interactive) layer.on('click', e => {
            L.DomEvent.stopPropagation(e);
            renderState(feature);
          });
        }
      }).addTo(container);
      refreshStateSelection();
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
        ordered.slice(0,12).forEach(r=>list.append(linkButton(r,()=>focusCounty(r))));
      }
      const legends = el('legend-data');
      if (legends) {
        legends.innerHTML = '<div class="legend-gradient">'+COLORS.map(c=>'<span style="background:'+c+'"></span>').join('')+'</div>'+
          '<div class="legend-limits"><span>≤ '+nf.format(Math.round(breaks[0]))+'</span>'+
          '<span>> '+nf.format(Math.round(breaks[5]))+'</span></div>'+
          '<div class="legend-info">按2025年县市分位着色 · 灰色为缺失</div>';
      }
      const stateIndex = el('state-index-list');
      if (stateIndex) {
        stateIndex.replaceChildren();
        [...stateStatistics.values()].sort((a,b)=>b.cases-a.cases).forEach(entry => {
          const li=document.createElement('li'),btn=document.createElement('button');
          btn.type='button';
          btn.append(safeNode('span',entry.name),
            safeNode('span',nf.format(entry.cases)+' 起'));
          btn.title='来自'+entry.rows.length+'个县级统计的案件合计';
          btn.onclick=()=>selectState(entry.name);
          li.append(btn);stateIndex.append(li);
        });
      }
      const home = el('region-home');
      if (home) home.onclick=resetRegion;
      const reset = el('reset-map');
      if (reset) reset.onclick = resetRegion;
    }
    active = {
      map, container, updateStates,
      setVisible(visible) {
        if (visible && !map.hasLayer(container)) container.addTo(map);
        if (!visible && map.hasLayer(container)) map.removeLayer(container);
      },
      deactivate() {
        map.off('zoomend',updateStates);
        map.removeLayer(container);
        if (isStandalone) {
          const reset=el('reset-map'),regionDrill=el('region-drill');
          if(reset)reset.onclick=null;if(regionDrill)regionDrill.onclick=null;
        }
      }
    };
    if (isStandalone && window.GermanMapDrugWastewater?.init) {
      window.GermanMapDrugWastewater.init({map,crime:active});
    }
    if (isStandalone && window.GermanMapDrugNewsUI?.init) {
      window.GermanMapDrugNewsUI.init({map,crime:active,states:[...stateFeatures.keys()]});
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
    // Shared label placement with violence/property; city labels cannot capture map clicks.
    window.CrimeCityLabels?.create(map,{paneName:'drugs-city-labels',zIndex:440});
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom:19,opacity:.84,attribution:'© OpenStreetMap contributors'
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
