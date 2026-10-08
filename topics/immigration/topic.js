/* Germany Crime Map — Immigration topic (independent, host-controlled).
 * No shared map state or global mouse handlers; all Leaflet shapes are noninteractive.
 */
(() => {
  'use strict';
  const selfScript = typeof document !== 'undefined' ? document.currentScript : null;
  const dataUrl = new URL('data/state-deportations-2025.json',
    selfScript?.src || (typeof location !== 'undefined' ? location.href : 'https://example.invalid/topics/immigration/')).href;

  const catalog = Object.freeze({
    id: 'immigration',
    title: '非法移民',
    metric: 'deportations_executed',
  });
  let dataset = null;
  let session = null;

  function verify(raw) {
    if (!raw || raw.schema_version !== 1 || raw.metric_id !== catalog.metric ||
        !Array.isArray(raw.records) || raw.records.length !== 16)
      throw new Error('Immigration: unsupported or incomplete dataset');
    const seen = new Set();
    let sum = 0;
    for (const row of raw.records) {
      if (!/^\d{2}$/.test(row.ags) || !/^DE-[A-Z]{2}$/.test(row.iso) ||
          typeof row.name_de !== 'string' ||
          !Number.isSafeInteger(row.value) || row.value < 0 || seen.has(row.iso))
        throw new Error('Immigration: invalid state record');
      seen.add(row.iso);
      sum += row.value;
    }
    if (sum !== raw.states_subtotal ||
        sum + raw.federal_police_separately !== raw.total_all_authorities ||
        raw.completeness?.reported_states !== 16 ||
        !/^https:\/\//.test(raw.source?.url || ''))
      throw new Error('Immigration: source metadata or totals inconsistent');
    return raw;
  }

  async function loadData() {
    if (dataset) return dataset;
    const response = await fetch(dataUrl, { cache: 'no-store' });
    if (!response.ok) throw new Error('Immigration: dataset HTTP ' + response.status);
    dataset = verify(await response.json());
    return dataset;
  }

  function textElement(tag, value, className) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    el.textContent = value;
    return el;
  }

  function fillColor(number) {
    if (number == null) return '#e2e8f0';
    const thresholds = [200, 500, 1000, 1600, 3000];
    const palette = ['#f3e7dc','#e4c9b5','#d8a989','#bd785b','#9e4e3a','#6f302c'];
    const level = thresholds.findIndex(t => number < t);
    return palette[level < 0 ? palette.length - 1 : level];
  }

  function activate(context) {
    if (session) deactivate();
    if (!dataset) throw new Error('Immigration: call loadData() before activate()');
    if (!context?.map || !context.container || !context.stateGeoJSON ||
        !Array.isArray(context.stateGeoJSON.features) ||
        typeof L === 'undefined' || typeof L.geoJSON !== 'function')
      throw new Error('Immigration: missing map, container, or GeoJSON context');

    const map = context.map;
    const paneName = 'immigrationDataPane';
    const pane = map.getPane(paneName) || map.createPane(paneName);
    pane.style.zIndex = '215'; // below original county (230) and state (350) panes
    pane.style.pointerEvents = 'none'; // crucial: never intercept state/county clicks

    const byIso = new Map(dataset.records.map(r => [r.iso, r]));
    const rendered = new Set();
    const layer = L.geoJSON(context.stateGeoJSON, {
      pane: paneName,
      interactive: false,
      style: feature => {
        const record = byIso.get(feature?.properties?.id);
        if (record) rendered.add(record.iso);
        return {
          pane: paneName, interactive: false, color: '#7d8a92',
          weight: .65, opacity: .35,
          fillColor: fillColor(record?.value),
          fillOpacity: record ? .77 : 0,
        };
      },
    });
    // Only add our own layer, never remove/mutate host map layers or listeners.
    layer.addTo(map);

    const root = document.createElement('section');
    root.className = 'immigration-topic';
    const heading = textElement('h2', '非法移民与边境管制 · 独立预览');
    const subtitle = textElement('p', '2025年各州执行遣返人数（官方统计）', 'immigration-subtitle');
    const scope = textElement('p',
      '注意：这是按执行机构统计的遣返人数，既不是该州非法居留人口，也不是其犯罪率。',
      'immigration-caution');
    const sum = textElement('p',
      '全国所有执行机构共 ' + dataset.total_all_authorities.toLocaleString('zh-CN') +
      ' 人；其中各州 ' + dataset.states_subtotal.toLocaleString('zh-CN') +
      ' 人，联邦警察单列 ' + dataset.federal_police_separately.toLocaleString('zh-CN') + ' 人。',
      'immigration-total');

    const selectorLabel = textElement('label', '查看具体联邦州：', 'immigration-label');
    const selector = document.createElement('select');
    selector.setAttribute('aria-label', '选择联邦州');
    for (const record of dataset.records.slice().sort((a,b) => a.name_de.localeCompare(b.name_de, 'de'))) {
      const option = document.createElement('option');
      option.value = record.iso;
      option.textContent = record.name_de;
      selector.append(option);
    }
    const detail = textElement('p', '', 'immigration-detail');
    const coverage = textElement('p',
      '当前地理图层匹配 ' + rendered.size + '/16 州；未匹配地区不作填充或推算。',
      'immigration-coverage');
    const ref = document.createElement('a');
    ref.textContent = '官方原始文件 · Bundestag 21/4403，第4页';
    ref.href = dataset.source.url;
    ref.target = '_blank';
    ref.rel = 'noopener noreferrer';
    function onSelection() {
      const record = byIso.get(selector.value);
      detail.textContent = record
        ? record.name_de + '：' + record.value.toLocaleString('zh-CN') + ' 人（2025年）'
        : '无数据';
    }
    selector.addEventListener('change', onSelection);
    onSelection();
    selectorLabel.append(selector);
    root.append(heading, subtitle, scope, sum, selectorLabel, detail, coverage, ref);
    context.container.append(root);
    session = { map, layer, root, selector, onSelection };
    return { matchedStates: rendered.size, reportedStates: dataset.records.length };
  }

  function deactivate() {
    if (!session) return;
    const {map, layer, root, selector, onSelection} = session;
    selector.removeEventListener('change', onSelection);
    if (map.hasLayer(layer)) map.removeLayer(layer);
    root.remove();
    session = null;
  }

  window.GermanMapTopics = window.GermanMapTopics || {};
  window.GermanMapTopics.immigration =
    Object.freeze({ ...catalog, loadData, activate, deactivate });
})();
