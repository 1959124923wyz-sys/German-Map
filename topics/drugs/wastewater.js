(() => {
  'use strict';
  // EUDA 2025 values are UNCORRECTED measured residues, mg/1000 residents/day.
  // This overlay is intentionally separate from PKS criminal case densities.
  const COLORS = ['#dff4e6','#c3e8d0','#9bd6b2','#73c192','#4ca577','#2d8060','#11513a'];
  const LABELS = Object.freeze({
    cannabis: '大麻 · THC-COOH', cocaine: '可卡因 · 苯甲酰爱康宁',
    methamphetamine: '冰毒 · 甲基苯丙胺', amphetamine: '安非他命',
    MDMA: '摇头丸 · MDMA', ketamine: '氯胺酮',
  });
  const $ = id => document.getElementById(id);
  const number = n => Number.isFinite(n) ? n.toLocaleString('zh-CN', {maximumFractionDigits:2}) : '—';
  const esc = x => String(x ?? '').replace(/[&<>"']/g,
    x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));

  function validateSource(data) {
    if (data?.meta?.study_year !== 2025 ||
        data?.sites?.length < 8 || data?.sites?.length > 100 ||
        data.meta.unit !== 'mg/1000 inhabitants/day') {
      throw new Error('EUDA数据未通过年份、站点数和单位验证');
    }
    const ids = new Set();
    for (const site of data.sites) {
      if (ids.has(site.id) || !site.id?.startsWith('DE') ||
        !Number.isFinite(site.lat) || !Number.isFinite(site.lon) ||
        site.lat < 47 || site.lat > 56 || site.lon < 5 || site.lon > 16) {
        throw new Error('EUDA站点编号或坐标校验失败');
      }
      ids.add(site.id);
      for (const [key, obs] of Object.entries(site.observations || {})) {
        if (!(key in LABELS) || (obs.daily !== null &&
           (!Number.isFinite(obs.daily) || obs.daily < 0))) {
          throw new Error('污水检测值或物质名称校验失败');
        }
      }
    }
  }

  function init({map, crime}) {
    if (!map || !crime?.setVisible || !window.L) return;
    const btnCrime = $('drugs-tab-crime'), btnWater = $('drugs-tab-wastewater');
    const crimeContent = $('drugs-crime-content'), waterContent = $('drugs-wastewater-content');
    const waterFlyout = $('wastewater-flyout'), countyFlyout = $('state-panel');
    const legend = $('legend-data'), legendTitle = $('legend-title');
    const selection = $('wastewater-substance');
    if (!btnCrime || !btnWater || !crimeContent || !waterContent || !legend || !selection) return;
    const baseLegend = legend.innerHTML;
    const baseLegendTitle = legendTitle.textContent;
    const overlay = L.layerGroup();
    let enabled = false, source = null, pending = null, markers = [], activeSubstance = 'cannabis';
    function status(value) { $('wastewater-status').textContent = value; }
    function closeWaterDetail() { waterFlyout.hidden = true; }
    function sourceData(substance) {
      return source.sites.map(site => ({site, obs:site.observations?.[substance]}))
        .filter(x => x.obs && Number.isFinite(x.obs.daily))
        .sort((a,b) => b.obs.daily - a.obs.daily || a.site.id.localeCompare(b.site.id));
    }
    function color(value, ceiling) {
      const ratio = ceiling > 0 ? value / ceiling : 0;
      return COLORS[Math.min(6, Math.floor(Math.max(0,ratio) * 7))];
    }
    function viewPoint(site, obs, marker) {
      if (!enabled) return;
      closeWaterDetail();
      waterFlyout.hidden = false;
      $('wastewater-city').textContent = site.city;
      $('wastewater-value').textContent = number(obs.daily);
      $('wastewater-previous').textContent = number(obs.previous_2024);
      const change = obs.previous_2024 !== null && Number.isFinite(obs.previous_2024)
        ? '该站点2024年同期值：' + number(obs.previous_2024) + '；不同年份采样地点及人口覆盖仍需核对。'
        : '该站点无可直接比较的2024年数据。';
      $('wastewater-note').textContent =
        '检测物质：' + LABELS[activeSubstance] + '。站点：' + site.id +
        '（' + (site.location && site.location !== 'NA' ? site.location : '具体设施名称未披露') +
        '）。工作日均值 ' + number(obs.weekday) + '，周末均值 ' + number(obs.weekend) +
        ' mg/每1000人/每天。' + change +
        ' 污水检测不是该城市的吸毒比例或警方案件数。';
      if (marker) map.panTo([site.lat,site.lon],{animate:false});
    }
    function render(substance) {
      if (!enabled || !source) return;
      activeSubstance = substance in LABELS ? substance : 'cannabis';
      const records = sourceData(activeSubstance);
      closeWaterDetail();
      overlay.clearLayers();
      markers = [];
      const max = Math.max(0,...records.map(x=>x.obs.daily));
      for (const {site,obs} of records) {
        const ratio = max ? obs.daily/max : 0;
        const marker = L.circleMarker([site.lat,site.lon], {
          radius:Math.max(6,8+Math.sqrt(ratio)*9),
          weight:1.7,color:'#e1f8e9',fillColor:color(obs.daily,max),
          fillOpacity:.9,opacity:.95,interactive:true,
        }).addTo(overlay);
        marker.bindTooltip('<strong>'+esc(site.city)+'</strong><br>'+
          esc(LABELS[activeSubstance])+' · '+number(obs.daily)+' mg/1000人/天',
          {sticky:true});
        marker.on('click',e => {L.DomEvent.stopPropagation(e);viewPoint(site,obs,marker);});
        markers.push(marker);
      }
      $('wastewater-sites').textContent = String(records.length);
      $('wastewater-peak').textContent = records.length ? number(records[0].obs.daily) : '—';
      $('wastewater-peak-city').textContent = records.length
        ? records[0].site.city + ' · mg/千人/天' : '暂无检测数据';
      const list = $('wastewater-rank'); list.replaceChildren();
      records.forEach(({site,obs}) => {
        const li=document.createElement('li'), button=document.createElement('button');
        button.type='button';
        const label=document.createElement('span'), value=document.createElement('span');
        label.textContent=site.city;value.textContent=number(obs.daily);
        button.append(label,value);
        button.addEventListener('click',()=>{
          map.setView([site.lat,site.lon],Math.max(map.getZoom(),8),{animate:false});
          viewPoint(site,obs);
        });
        li.appendChild(button);list.appendChild(li);
      });
      legendTitle.textContent = LABELS[activeSubstance]+' · 污水残留';
      legend.innerHTML = '<div class="legend-gradient">'+COLORS.map(c=>
        '<span style="background:'+c+'"></span>').join('')+'</div>'+
        '<div class="legend-limits"><span>0</span><span>'+number(max)+
        ' mg/千人/天</span></div><div class="legend-info">仅13个检测站点 · 各物质分别定标</div>';
      status('EUDA / SCORE · 2025 · '+records.length+
        '个站点 · 2026年公布；缺失数据不当作零。');
    }

    function setTabAppearance(water) {
      btnCrime.classList.toggle('selected',!water);
      btnWater.classList.toggle('selected',water);
      btnCrime.setAttribute('aria-current',String(!water));
      btnWater.setAttribute('aria-current',String(water));
      crimeContent.hidden=water;
      waterContent.hidden=!water;
    }
    async function switchWastewater() {
      enabled = true;
      setTabAppearance(true);
      crime.setVisible(false);
      if (countyFlyout) countyFlyout.hidden=true;
      if (!map.hasLayer(overlay)) overlay.addTo(map);
      status('正在读取 EUDA 官方实测数据…');
      try {
        if (!source) {
          if (!pending) pending = fetch('data/euda_wastewater_2025.json',{cache:'no-store'})
            .then(r => {if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
            .then(data => {validateSource(data);source=data;return data;})
            .finally(()=>{pending=null;});
          await pending;
        }
        render(selection.value);
      } catch (error) {
        console.error('EUDA wastewater',error);
        status('EUDA城市数据加载失败：'+error.message);
        $('wastewater-sites').textContent='不可用';
        $('wastewater-peak').textContent='—';
        $('wastewater-rank').replaceChildren();
        legendTitle.textContent='城市污水检测暂不可用';
        legend.textContent='原始数据加载失败，未填充虚假数值';
      }
    }
    function switchCrime() {
      enabled = false;
      setTabAppearance(false);
      if(map.hasLayer(overlay))map.removeLayer(overlay);
      closeWaterDetail();
      crime.setVisible(true);
      legend.innerHTML=baseLegend;
      legendTitle.textContent=baseLegendTitle;
    }
    // External news tab may temporarily activate the police background while
    // hiding this module's sidebar; the API prevents leaking wastewater markers.
    window.GermanMapDrugTabs = Object.freeze({showCrime:switchCrime,showWastewater:switchWastewater});
    btnCrime.addEventListener('click',switchCrime);
    btnWater.addEventListener('click',()=>{void switchWastewater();});
    selection.addEventListener('change',()=>render(selection.value));
    $('wastewater-fit').addEventListener('click',()=>{
      if (!markers.length) return;
      map.fitBounds(L.latLngBounds(markers.map(m=>m.getLatLng())),{padding:[38,38],maxZoom:8});
    });
    $('close-wastewater').addEventListener('click',closeWaterDetail);
    window.__DRUGS_WASTEWATER_TEST__ = Object.freeze({
      get isActive(){return enabled;},
      get markers(){return markers.length;},
      get activeSubstance(){return activeSubstance;}
    });
  }
  window.GermanMapDrugWastewater = Object.freeze({init});
})();
