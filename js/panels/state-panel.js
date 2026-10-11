(() => {
  function create({
    elements,
    map,
    getMode,
    getStats,
    getMetricLabel,
    onCountySelect,
    onNewsSelect,
    onStateChanged,
    formatNumber,
    formatDate,
    escapeHtml,
  }) {
    let selectedName = null;
    let filterName = null;
    let returnView = null;

    // All 400 sourced county records already exist in the national data model.
    // The county directory reveals only the records for the currently selected state.
    let countyRows=[],countyKey=null;
    const countySearch=document.getElementById('stateCountySearch');
    const countyList=document.getElementById('stateCountyList');
    function renderCountyRows(){
      if(!countyList)return;
      const q=(countySearch?.value||'').trim().toLocaleLowerCase();
      const rows=countyRows.filter(row=>{
        const label=window.GermanPlaceNames?.byAGS(row.ags,row.name)||row.name;
        return !q||[row.ags,row.name,label].some(v=>String(v||'').toLocaleLowerCase().includes(q));
      }).sort((a,b)=>{
        const aName=window.GermanPlaceNames?.byAGS(a.ags,a.name)||a.name;
        const bName=window.GermanPlaceNames?.byAGS(b.ags,b.name)||b.name;
        return aName.localeCompare(bName,'zh');
      });
      countyList.replaceChildren();
      for(const row of rows){
        const button=document.createElement('button');button.type='button';
        button.className='state-county-row';
        const name=window.GermanPlaceNames?.byAGS(row.ags,row.name)||row.name;
        button.innerHTML='<span>'+escapeHtml(name)+'<small>AGS '+escapeHtml(row.ags)+'</small></span>'+
          '<b>'+formatNumber(Math.round(Number(row?.[countyKey]?.rate||0)))+' /10万人</b>';
        button.addEventListener('click',()=>onCountySelect(row,countyKey));
        countyList.appendChild(button);
      }
      if(!rows.length)countyList.textContent='没有匹配的县市。请尝试名称或AGS。';
    }
    countySearch?.addEventListener('input',renderCountyRows);


    function render(feature) {
      if (!feature) return;
      const s = getStats(feature);
      const label = getMetricLabel(s.key);

      elements.stateName.textContent = window.GermanPlaceNames?.translate(s.name)||s.name;
      if (elements.stateJump) elements.stateJump.value = s.name;
      elements.stateMetric.textContent = 'BKA PKS 2025 · ' + label;
      elements.stateRate.textContent = formatNumber(Math.round(s.rate));
      elements.stateCases.textContent = formatNumber(s.cases);
      elements.stateRank.textContent = '#' + s.rank;
      elements.stateRecent.textContent = formatNumber(s.news.length);

      countyRows=s.rows;countyKey=s.key;
      const count=document.getElementById('stateCountyCount');
      if(count)count.textContent=s.rows.length+'个';
      renderCountyRows();
      elements.stateTopCounties.innerHTML = '';
      for (const row of s.topCounties) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'state-county-row';
        button.innerHTML =
          '<span>' + escapeHtml(window.GermanPlaceNames?.byAGS(row.ags,row.name)||row.name) + '</span><b>' +
          formatNumber(Math.round(row[s.key].rate)) +
          '</b>';
        button.onclick = () => onCountySelect(row, s.key);
        elements.stateTopCounties.appendChild(button);
      }

      elements.stateNewsCount.textContent = s.news.length
        ? formatNumber(s.news.length) + ' 起'
        : '';
      elements.stateNews.innerHTML = '';

      if (!s.news.length) {
        elements.stateNews.innerHTML =
          '<div class="state-empty">当前公开抓取暂无匹配通报；不代表没有案件。</div>';
      } else {
        for (const item of s.news.slice(0, 6)) {
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'state-news-row';
          button.innerHTML =
            '<span>' +
            escapeHtml(item.city || s.name) +
            ' · ' +
            escapeHtml(item.offense || item.category_label || '事件') +
            '</span><small>' +
            formatDate(item.event_date) +
            '</small>';
          button.onclick = () => onNewsSelect(item);
          elements.stateNews.appendChild(button);
        }
      }

      elements.stateDrawer.classList.add('open');
      // City source registries subscribe to a stable canonical state name.
      // Do not infer a city's administrative state from visual map position.
      elements.stateDrawer.dispatchEvent(new CustomEvent('crime:state-rendered',{
        detail:{state:s.name,metric:s.key,browseMode:getMode()}
      }));
    }

    function select(feature) {
      if (!elements.stateDrawer.classList.contains('open')) {
        returnView = { center: map.getCenter(), zoom: map.getZoom() };
      }
      const nextName=feature?.properties?.name || null;
      const previousName=selectedName;
      if (selectedName!==nextName) {
        // Each new state begins with quiet local lists. A source-backed city
        // archive can still open by default via its own state-scoped handler.
        for (const id of ['stateCountyDisclosure','stateNewsDisclosure','stateCountyDirectory']) {
          const section=document.getElementById(id);
          if(section)section.open=false;
        }
      }
      if(previousName!==nextName&&countySearch)countySearch.value='';
      selectedName = nextName;
      filterName = selectedName;
      render(feature);
      onStateChanged?.({changed:previousName!==nextName,previousName,nextName});
    }

    function close({ restore = true } = {}) {
      selectedName = null;
      filterName = null;
      elements.stateDrawer.classList.remove('open');
      if(elements.stateJump)elements.stateJump.value='';

      const view = returnView;
      returnView = null;
      onStateChanged?.();

      // A state click itself no longer zooms. Only restore if the user
      // navigated deeper from a county/news row while the drawer was open.
      // Synchronous restoration avoids racing the zoomend state-layer rebuild.
      if (restore && view &&
          (Math.abs(map.getZoom()-view.zoom)>1e-4 ||
           map.getCenter().distanceTo(view.center)>2)) {
        map.stop();
        map.setView(view.center, view.zoom, { animate: false });
      }
    }

    function reset() {
      selectedName = null;
      filterName = null;
      returnView = null;
      elements.stateDrawer.classList.remove('open');
      if(elements.stateJump)elements.stateJump.value='';
      onStateChanged?.();
    }

    return Object.freeze({
      render,
      select,
      close,
      reset,
      get selectedName() { return selectedName; },
      get filterName() { return filterName; },
      get isOpen() { return elements.stateDrawer.classList.contains('open'); },
    });
  }

  window.CrimeStatePanel = Object.freeze({ create });
})();
