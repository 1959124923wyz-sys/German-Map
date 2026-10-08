(() => {
  'use strict';

  const { scaleColor, quantileBreaks, riskLabel } = window.CrimeMapUtils;

  function create({
    map, getCountyGeo, getMode, getPksData, getPropertyData,
    getMetric, getRates, getRecord, getArea, isBerlinDetailActive,
    getPinnedArea, showArea, onLeave, formatNumber, escapeHtml,
    nationalPalette, propertyPalette,
  }) {
    let layer = null;
    let selected = null;
    let detailFocusAGS = null;

    function setDetailFocus(ags) {
      const next = ags ? String(ags).padStart(5,'0') : null;
      if (detailFocusAGS === next) return;
      detailFocusAGS = next;
      if (layer) layer.eachLayer(item => layer.resetStyle(item));
    }

    function style(feature) {
      const property = getMode() === 'property';
      const mode = property ? 'property' : 'violence';
      const key = getMetric(mode);
      const record = getRecord(feature, mode);
      const breaks = quantileBreaks(getRates(key, mode));
      const value = record?.[key]?.rate;
      if (detailFocusAGS) {
        const id = String(feature?.id??feature?.properties?.AGS??'').padStart(5,'0');
        return id === detailFocusAGS
          ? {pane:'countyPane',color:'transparent',weight:0,opacity:0,fillColor:'transparent',fillOpacity:0}
          : {pane:'countyPane',color:'#94a1a9',weight:.3,opacity:.32,fillColor:'#dbe3e8',fillOpacity:.12};
      }
      if (record?.name === 'Berlin' && isBerlinDetailActive()) {
        return {pane:'countyPane',color:'transparent',weight:0,opacity:0,fillColor:'transparent',fillOpacity:0};
      }
      return {
        pane: 'countyPane',
        color: property ? '#718390' : '#7c7f82',
        weight: .28,
        opacity: property ? .58 : .56,
        fillColor: record ? scaleColor(value,breaks,property ? propertyPalette : nationalPalette) : '#cbd4d9',
        fillOpacity: record && value != null ? .68 : .07,
      };
    }

    function select(target) {
      if (!layer || !target) return;
      if (selected && selected !== target) layer.resetStyle(selected);
      selected = target;
      layer.resetStyle(target);
      target.setStyle({ color:'#ffffff', weight:2.65, opacity:1, fillOpacity:.78 });
      if (target.bringToFront) target.bringToFront();
    }

    function hover(target) {
      if (!target || target === selected) return;
      target.setStyle({color:'#d8f2ff',weight:1.45,opacity:1,fillOpacity:.74});
      if (target.bringToFront) target.bringToFront();
    }

    function unhover(target) {
      if (!layer || !target || target === selected) return;
      layer.resetStyle(target);
    }

    function clearSelection() {
      if (layer && selected) layer.resetStyle(selected);
      selected = null;
    }

    function render() {
      if (layer) { map.removeLayer(layer); layer = null; }
      selected = null;
      const geo = getCountyGeo();
      if (!geo) return null;
      if (getMode() === 'violence' && !getPksData()) return null;
      if (getMode() === 'property' && !getPropertyData()) return null;
      layer = L.geoJSON(geo, {
        pane: 'countyPane',
        style,
        onEachFeature: (feature, target) => {
          const mode = getMode();
          const record = getRecord(feature,mode);
          if (!record) return;
          const area = () => getArea(feature,record,mode);
          target.bindTooltip(() => {
            const a = area(), risk = riskLabel(a.pct);
            return '<b>'+escapeHtml(record.name)+'</b><br>'+
              escapeHtml(a.metric.replace('BKA PKS 2025 · ',''))+'<br>'+
              formatNumber(Math.round(a.rate))+' /10万人·年 · '+risk.text;
          }, {sticky:true});
          target.on('mouseover', () => {hover(target);showArea(area());});
          target.on('mouseout', () => {unhover(target);onLeave();showArea(getPinnedArea());});
          target.on('click', () => {select(target);showArea(area(),{pin:true});});
        },
      }).addTo(map);
      return layer;
    }

    return Object.freeze({
      render, select, hover, unhover, clearSelection, style, setDetailFocus,
      get layer() { return layer; },
      get selected() { return selected; },
    });
  }

  window.CrimeCountyLayer = Object.freeze({create});
})();
