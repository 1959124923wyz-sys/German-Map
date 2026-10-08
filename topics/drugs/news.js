(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const STYLE = Object.freeze({
    trade:{label:'贩卖／走私',color:'#ee9e60'},
    seizure:{label:'查获／搜查',color:'#dec36a'},
    production:{label:'非法生产／种植',color:'#b48de4'},
    death:{label:'死亡／中毒急救',color:'#ed737d'},
    health:{label:'公共卫生／政策',color:'#76bce0'}
  });
  const n = v => Number(v||0).toLocaleString('zh-CN');
  function cleanUrl(src) {
    try {
      const u = new URL(src);
      return u.protocol === 'https:' && (/^www\.presseportal\.de$/.test(u.hostname) ||
        /^www\.bundesdrogenbeauftragter\.de$/.test(u.hostname) ||
        /^www\.berlin\.de$/.test(u.hostname)) ? u.href : '';
    } catch{return '';}
  }
  function sourceCheck(data) {
    if (!data?.reports || !Array.isArray(data.reports) || data.reports.length < 6) {
      throw new Error('近期通报文件缺失或不完整');
    }
    for (const item of data.reports) {
      if (!STYLE[item.category] || !item.id || !item.title || !item.city ||
        !/^\d{4}-\d\d-\d\d$/.test(item.publication_date) || !cleanUrl(item.source_url) ||
        (item.lat!==null && (!Number.isFinite(item.lat)||!Number.isFinite(item.lon)))) {
        throw new Error('新闻字段或来源链接校验失败');
      }
    }
  }
  function init({map,crime,states=[]}) {
    const crimeButton=$('drugs-tab-crime'),waterButton=$('drugs-tab-wastewater'),
      newsButton=$('drugs-tab-news'),newsContent=$('drugs-news-content'),
      crimeContent=$('drugs-crime-content'),waterContent=$('drugs-wastewater-content');
    if (!map || !crime || !newsButton || !newsContent) return;
    const region=$('drug-news-state'),kind=$('drug-news-type');
    const list=$('drug-news-list'),status=$('drug-news-status'),total=$('drug-news-count'),
      mapped=$('drug-news-mapped'),more=$('drug-news-more'),fit=$('drug-news-fit');
    if (!map.getPane('drugNewsPane'))map.createPane('drugNewsPane');
    const pane=map.getPane('drugNewsPane');
    pane.style.zIndex='462';
    const renderer=L.svg({pane:'drugNewsPane',padding:.2});
    const group=L.layerGroup();
    let enabled=false, dataset=null, loadTask=null, rows=[],shown=20,markers=new Map();
    const palette=STYLE;
    function safe(tag,value) {
      const node=document.createElement(tag);
      node.textContent=String(value||'');
      return node;
    }
    function popupFor(city,items) {
      const panel=document.createElement('div');
      panel.className='drug-news-popup';
      panel.append(safe('b',city+' · '+items.length+'条公开通报'));
      const ul=document.createElement('ul');
      for (const item of items.slice(0,8)) {
        const li=document.createElement('li'),a=document.createElement('a');
        a.href=cleanUrl(item.source_url);
        a.target='_blank';a.rel='noopener noreferrer';
        a.textContent=item.publication_date+' · '+item.title.slice(0,94);
        li.append(a);ul.append(li);
      }
      panel.append(ul);
      if(items.length>8)panel.append(safe('small','更多通报请查看右侧列表'));
      return panel;
    }
    async function ensureData() {
      if(dataset)return dataset;
      if(!loadTask)loadTask=fetch('data/drug_news.json',{cache:'no-store'})
        .then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
        .then(data=>{sourceCheck(data);dataset=data;return data;})
        .finally(()=>{loadTask=null});
      return loadTask;
    }
    async function reportsForState(state,limit=3) {
      if(!state)return [];
      const data=await ensureData();
      return data.reports.filter(row=>row.state===state)
        .sort((a,b)=>b.publication_date.localeCompare(a.publication_date))
        .slice(0,Math.max(1,Math.min(10,limit)));
    }
    function visibleRows() {
      if(!dataset)return [];
      return dataset.reports.filter(row=>
        (kind.value==='all'||row.category===kind.value) &&
        (region.value==='all' || row.state===region.value)
      ).sort((a,b)=>b.publication_date.localeCompare(a.publication_date)||
        a.city.localeCompare(b.city));
    }
    function openReport(item) {
      const key=item.city+'|'+Number(item.lat).toFixed(3)+'|'+Number(item.lon).toFixed(3);
      if (Number.isFinite(item.lat) && Number.isFinite(item.lon) && markers.has(key)) {
        const marker=markers.get(key);
        map.setView(marker.getLatLng(),Math.max(7,map.getZoom()),{animate:false});
        marker.openPopup();
      } else {
        const url=cleanUrl(item.source_url);
        if(url)window.open(url,'_blank','noopener,noreferrer');
      }
    }
    function render() {
      if(!enabled || !dataset)return;
      rows=visibleRows();
      const geoRows=rows.filter(r=>Number.isFinite(r.lat)&&Number.isFinite(r.lon));
      total.textContent=n(rows.length);
      mapped.textContent=n(geoRows.length);
      const cityPoints=new Map();
      for(const item of geoRows) {
        const key=item.city+'|'+item.lat.toFixed(3)+'|'+item.lon.toFixed(3);
        if (!cityPoints.has(key))cityPoints.set(key,[]);
        cityPoints.get(key).push(item);
      }
      group.clearLayers();markers.clear();
      for (const [key,items] of cityPoints) {
        const first=items[0];
        const color=palette[first.category]?.color || '#84c8a9';
        const pin=L.circleMarker([first.lat,first.lon],{
          renderer,pane:'drugNewsPane',radius:Math.min(12,6+Math.log2(1+items.length)*2),
          fillColor:color,fillOpacity:.9,color:'#fffdf1',weight:1.5,opacity:1
        });
        pin.bindTooltip(first.city+' · '+items.length+'条通报',{sticky:true});
        pin.bindPopup(popupFor(first.city,items),{maxWidth:360,minWidth:220});
        pin.on('click',e=>L.DomEvent.stopPropagation(e));
        pin.addTo(group);markers.set(key,pin);
      }
      const fragment=document.createDocumentFragment();
      for (const item of rows.slice(0,shown)) {
        const li=document.createElement('li'),button=document.createElement('button');
        button.type='button';button.className='drug-news-card';
        const top=document.createElement('div');top.className='drug-news-top';
        const label=safe('span',palette[item.category]?.label || item.category);
        label.className='drug-news-badge '+item.category;
        top.append(label,safe('span',item.publication_date),safe('span',item.city));
        button.append(top,safe('b',item.title));
        const source=safe('small',item.source_agency||'公开来源');
        button.append(source);
        if (item.summary && item.summary!==item.title)
          button.append(safe('small',item.summary.slice(0,130)));
        if(item.kind==='statistical_report')
          button.append(safe('small','全国年度背景资料 · 无地理点位'));
        button.onclick=()=>openReport(item);
        li.append(button);fragment.append(li);
      }
      list.replaceChildren(fragment);
      if (!rows.length) {
        const li=safe('li','本次筛选没有已核实的公开通报；不代表该地区没有毒品问题。');
        li.className='note';list.append(li);
      }
      more.hidden=rows.length<=shown;
      status.textContent='近90天警方公告与全国专题资料 · 城市定位仅为示意 · '+n(cityPoints.size)+'个地点';
      const updated=$('drug-news-updated');
      if(updated)updated.textContent='截至 '+dataset.meta.as_of;
    }
    async function showNews(){
      // Shut down potential wastewater site markers before drawing news markers.
      window.GermanMapDrugTabs?.showCrime?.();
      enabled=true;
      crime.setVisible(true); // police choropleth remains the background
      crimeContent.hidden=true;waterContent.hidden=true;newsContent.hidden=false;
      crimeButton.classList.remove('selected');
      waterButton.classList.remove('selected');
      newsButton.classList.add('selected');
      crimeButton.setAttribute('aria-current','false');
      waterButton.setAttribute('aria-current','false');
      newsButton.setAttribute('aria-current','true');
      if(!map.hasLayer(group))group.addTo(map);
      status.textContent='正在加载经来源核查的警方通报…';
      try{
        await ensureData();
        if(!enabled)return;
        const selectableStates=[...new Set([...states,...dataset.reports.map(r=>r.state)].filter(Boolean))].sort();
        if(region.options.length===1){
          for(const state of selectableStates){
            const option=document.createElement('option');option.value=state;option.textContent=state;
            region.append(option);
          }
        }
        render();
      }catch(err){
        status.textContent='通报暂时无法加载：'+err.message;
        list.replaceChildren(safe('li','数据源更新中，请稍后刷新。'));
        total.textContent='—';mapped.textContent='—';
        console.error('drug news',err);
      }
    }
    function hideNews(){
      enabled=false;newsContent.hidden=true;
      if(map.hasLayer(group))map.removeLayer(group);
      newsButton.classList.remove('selected');
      newsButton.setAttribute('aria-current','false');
    }
    crimeButton.addEventListener('click',hideNews);
    waterButton.addEventListener('click',hideNews);
    newsButton.addEventListener('click',()=>{void showNews()});
    kind.addEventListener('change',()=>{shown=20;render();});
    region.addEventListener('change',()=>{shown=20;render();});
    more.addEventListener('click',()=>{shown+=20;render();});
    fit.addEventListener('click',()=>{
      const points=[...markers.values()].map(m=>m.getLatLng());
      if(points.length)map.fitBounds(L.latLngBounds(points),{padding:[40,40],maxZoom:8});
    });
    window.GermanMapDrugNews=Object.freeze({
      get active(){return enabled;},
      get count(){return rows.length;},
      setStateFilter(name){
        if(!enabled)return;
        const state=name||'all';
        if([...region.options].some(o=>o.value===state)){
          region.value=state;shown=20;render();
        }
      },
      reportsForState,
      async openForState(state) {
        await showNews();
        if(!enabled || !dataset)return;
        if(state && ![...region.options].some(o=>o.value===state)) {
          const option=document.createElement('option');
          option.value=state;option.textContent=state;region.append(option);
        }
        kind.value='all';
        region.value=state || 'all';
        shown=20;
        render();
      },
      hideNews,
    });
  }
  window.GermanMapDrugNewsUI=Object.freeze({init});
})();
