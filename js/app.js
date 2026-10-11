(() => {
  const $=id=>document.getElementById(id);
  const el={
    updated:$('updated'),
    modeViolence:$('modeViolence'),modeProperty:$('modeProperty'),
    toggleViolenceNews:$('toggleViolenceNews'),violenceMetric:$('violenceMetric'),
    togglePropertyNews:$('togglePropertyNews'),propertyMetric:$('propertyMetric'),
    violenceLayers:$('violenceLayers'),propertyLayers:$('propertyLayers'),
    viewGermany:$('viewGermany'),focusBerlin:$('focusBerlin'),mapStatus:$('mapStatus'),
    legend:$('legend'),layerInfo:$('layerInfo'),
    stateDrawer:$('stateDrawer'),stateDragHandle:$('stateDragHandle'),stateName:$('stateName'),stateClose:$('stateClose'),stateMetric:$('stateMetric'),stateJump:$('stateJump'),
    stateLocate:$('stateLocate'),stateDrawerExpand:$('stateDrawerExpand'),
    stateRate:$('stateRate'),stateCases:$('stateCases'),stateRank:$('stateRank'),stateRecent:$('stateRecent'),
    stateTopCounties:$('stateTopCounties'),stateNews:$('stateNews'),stateNewsCount:$('stateNewsCount'),
    safetyPanel:$('safetyPanel'),areaName:$('areaName'),riskBadge:$('riskBadge'),areaMetric:$('areaMetric'),
    coveragePill:$('coveragePill'),coverageText:$('coverageText'),
    areaRate:$('areaRate'),areaRateLabel:$('areaRateLabel'),areaQuarter:$('areaQuarter'),areaQuarterLabel:$('areaQuarterLabel'),
    areaRecent:$('areaRecent'),areaRecentLabel:$('areaRecentLabel'),
    areaNote:$('areaNote'),rankList:$('rankList'),
    listTitle:$('listTitle'),list:$('list')
  };
  const {categories:cats,palettes,propertyMetrics,violenceMetrics}=window.CrimeMapConfig;
  const {national:nationalPalette,berlin:berlinPalette,property:propertyPalette,berlinProperty:berlinPropertyPalette}=palettes;
  let mode=new URLSearchParams(window.location.search).get('mode')==='property'?'property':'violence',caseData=null,pksData=null,propertyData=null,countyGeo=null,berlinViolence=null,heatData=null,stateGeo=null;
  let countyLayer=null,stateLayer=null,countyController=null,stateController=null;
  let pinnedArea=null,hoverArea=null,showViolenceNews=false,showPropertyNews=false,statePanel=null,eventLayer=null,berlinDetail=null,areaPanel=null;
  let countyBrowse=false,syncingCountyState=false;
  const countyBrowseButton=$('stateCountyBrowse');
  function setCountyBrowse(next){
    countyBrowse=Boolean(next);
    if(countyBrowseButton){
      countyBrowseButton.setAttribute('aria-pressed',String(countyBrowse));
      countyBrowseButton.textContent=countyBrowse?'恢复按州选择':'跨州自由选县市';
    }
    if(stateController)buildStateLayer();
  }
  const stateDrawerDrag=window.CrimeDrawerDrag.create({drawer:el.stateDrawer,handle:el.stateDragHandle});

  const map=L.map('map',{minZoom:5,maxZoom:17,zoomControl:true,preferCanvas:true,worldCopyJump:false});
  const germanyBounds=L.latLngBounds([[47.05,5.45],[55.15,15.65]]);
  const berlinBounds=L.latLngBounds([[52.33,13.08],[52.69,13.77]]);
  map.fitBounds(germanyBounds,{padding:[14,14]});map.setMaxBounds([[45.3,3.2],[57.1,18.0]]);
  map.createPane('countyPane');map.getPane('countyPane').style.zIndex=230;
  map.createPane('statePane');map.getPane('statePane').style.zIndex=350;
  map.createPane('berlinPane');map.getPane('berlinPane').style.zIndex=260;
  map.createPane('newsPane');map.getPane('newsPane').style.zIndex=460;
  map.getPane('tilePane').style.filter='saturate(.45) contrast(.86) brightness(1.06)';

  let tileOk=false,tileErrors=0;
  const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,opacity:.86,attribution:'© OpenStreetMap contributors',crossOrigin:true,updateWhenIdle:true});
  tiles.on('tileload',()=>{if(!tileOk){tileOk=true;el.mapStatus.className='mapstatus ok';el.mapStatus.textContent='OSM街道底图 + 本地统计图层';}});
  // Never remove the tile layer merely because an initial request failed or is slow.
  // Keeping it mounted allows a subsequent zoom/retry to recover the street background.
  tiles.on('tileerror',()=>{tileErrors++;if(tileErrors>=6&&!tileOk){el.mapStatus.className='mapstatus fallback';el.mapStatus.textContent='OSM街道底图暂时不可用 · 地区统计仍可使用';}});
  tiles.addTo(map);
  // Consistent, high-contrast German city names shared with the drug topic.
  // Separate non-interactive pane: state/county clicks remain available.
  const cityLabels = window.CrimeCityLabels?.create(map,{paneName:'major-city-labels',zIndex:435});
  setTimeout(()=>{if(!tileOk){el.mapStatus.className='mapstatus fallback';el.mapStatus.textContent='OSM街道底图加载较慢 · 正在继续尝试';}},10000);

  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=n=>Number(n||0).toLocaleString('zh-CN');
  const pd=s=>{const [y,m,d]=String(s||'').split('-');return y&&m&&d?d+'.'+m+'.'+y:String(s||'')};
  const safe=u=>/^https:\/\//i.test(String(u||''))?u:'#';
  const {scaleColor,pointInGeometry,percentile,riskLabel,quantileBreaks}=window.CrimeMapUtils;

  function violentRecentCount(feature,metric=currentViolenceMetric()){
    if(!caseData||!feature?.geometry)return 0;
    const catsOk=new Set(violenceMetrics[metric]?.news||[]);
    return caseData.cases.filter(c=>catsOk.has(c.category)&&Number.isFinite(c.lon)&&Number.isFinite(c.lat)&&pointInGeometry(c.lon,c.lat,feature.geometry)).length;
  }
  function currentViolenceMetric(){return el.violenceMetric?.value||'violence';}
  function nationalRates(metric=currentViolenceMetric()){
    return Object.values(pksData?.records||{}).map(r=>Number(r?.[metric]?.rate)).filter(Number.isFinite);
  }
  function currentPropertyMetric(){return el.propertyMetric?.value||'property_total';}
  function propertyRates(metric=currentPropertyMetric()){
    return Object.values(propertyData?.records||{}).map(r=>Number(r?.[metric]?.rate)).filter(Number.isFinite);
  }
  function propertyHeatField(){return berlinDetail?.propertyField()||null;}
  function berlinLocalActive(){return berlinDetail?.isActive()||false;}
  function stateFeatureByName(name){
    return stateGeo?.features?.find(f=>f.properties?.name===name)||null;
  }
  function caseMatchesCurrentMetric(c){
    const key=mode==='property'?currentPropertyMetric():currentViolenceMetric();
    return window.CrimeDataModel.caseMatchesMetric(mode,key,c,violenceMetrics);
  }
  function caseInState(c,feature){return window.CrimeDataModel.caseInFeature(c,feature);}
  function stateStats(feature){
    const key=mode==='property'?currentPropertyMetric():currentViolenceMetric();
    return window.CrimeDataModel.stateStats({feature,stateGeo,mode,key,propertyData,pksData,caseData,violenceMetrics});
  }
  function stateTooltipHtml(feature){
    const s=stateStats(feature);
    const label=mode==='property'?(propertyMetrics[s.key]?.label||s.key):(violenceMetrics[s.key]?.label||s.key);
    return '<b>'+esc(window.GermanPlaceNames?.translate(s.name)||s.name)+'</b><br>'+esc(label)+' · '+fmt(Math.round(s.rate))+'/10万人<br>'+fmt(s.cases)+' 起 · 16州第 '+s.rank;
  }
  function countyArea(feature,rec){
    const key=currentViolenceMetric(),m=rec?.[key]||{},rate=Number(m.rate||0),cases=Number(m.cases||0),pct=percentile(rate,nationalRates(key));
    return {kind:'violence-county',ags:rec?.ags||'',name:window.GermanPlaceNames?.byAGS(rec?.ags,rec?.name)||rec?.name||'未知县/市',state:rec?.state||'',metric:'BKA PKS 2025 · '+(violenceMetrics[key]?.label||key),
      rate,cases,change:m.change||'—',recent:violentRecentCount(feature,key),pct,feature,metricKey:key,
      note:'2025年警方记录的县/市级年度数据。颜色按德国县/市同一指标的相对分位着色；未报案事件不在PKS中。'};
  }
  function propertyCountyArea(feature,rec){
    const key=currentPropertyMetric(),m=rec?.[key]||{},rate=Number(m.rate||0),cases=Number(m.cases||0),pct=percentile(rate,propertyRates(key));
    const recent=caseData?.cases?.filter(c=>c.category==='property'&&Number.isFinite(c.lon)&&Number.isFinite(c.lat)&&pointInGeometry(c.lon,c.lat,feature.geometry)).length||0;
    return {kind:'property-county',ags:rec?.ags||'',name:window.GermanPlaceNames?.byAGS(rec?.ags,rec?.name)||rec?.name||'未知县/市',state:rec?.state||'',metric:'BKA PKS 2025 · '+(propertyMetrics[key]?.label||key),
      rate,cases,change:m.change||'—',recent,pct,feature,metricKey:key,
      note:'2025年警方记录的县/市级年度数据。颜色按德国县/市同一指标的相对分位着色；未报案事件不在PKS中。'};
  }

  function berlinRates(){return berlinDetail?.violenceRates()||[];}
  function propertyLocalValues(field=propertyHeatField()){return berlinDetail?.propertyValues(field)||[];}

  function currentNationalSummary(){
    const key=mode==='property'?currentPropertyMetric():currentViolenceMetric();
    return window.CrimeDataModel.nationalSummary({mode,key,propertyData,pksData,propertyMetrics,violenceMetrics});
  }
  function renderRankList(){areaPanel.renderRankList();}
  function showArea(area,{pin=false}={}){
    if(pin)pinnedArea=area;
    hoverArea=pin?null:area;
    if(pin&&['violence-county','property-county'].includes(area?.kind)&&statePanel){
      const f=stateFeatureByName(area.state);
      if(f&&statePanel.selectedName!==f.properties.name){
        syncingCountyState=true;
        try{statePanel.select(f)}finally{syncingCountyState=false;}
      }
    }
    // Once selected, county details remain stable until the user selects a new area.
    areaPanel.show(pinnedArea&&!pin?pinnedArea:(area||pinnedArea));
    // Source-backed county archive responds to explicit pinned selections,
    // not to hover or an unrelated city/neighbourhood map overlay.
    document.dispatchEvent(new CustomEvent('crime:area-pinned',{
      detail:{
        ags:pinnedArea?.ags||null,
        kind:pinnedArea?.kind||null,
        mode
      }
    }));
  }

  function pksRecord(feature){
    const id=String(feature?.id??feature?.properties?.AGS??'').padStart(5,'0');
    const alias=pksData?.meta?.geometry_aliases?.[id];
    return pksData?.records?.[id]||pksData?.records?.[alias]||null;
  }
  function propertyRecord(feature){
    const id=String(feature?.id??feature?.properties?.AGS??'').padStart(5,'0');
    const alias=propertyData?.meta?.geometry_aliases?.[id];
    return propertyData?.records?.[id]||propertyData?.records?.[alias]||null;
  }
  function selectCountyLayer(layer){countyController.select(layer);}
  function buildCountyLayer(){countyLayer=countyController.render();}
  function buildStateLayer(){stateLayer=stateController.render();}

  function visibleCases(){
    if(!caseData)return[];
    let rows=caseData.cases.filter(caseMatchesCurrentMetric);
    const stateFilter=statePanel?.filterName;
    if(stateFilter){
      const f=stateFeatureByName(stateFilter);
      if(f)rows=rows.filter(c=>caseInState(c,f));
      return rows;
    }
    if(mode==='property')return showPropertyNews?rows:[];
    return showViolenceNews?rows:[];
  }
  function renderNews(){
    return eventLayer.render(visibleCases(),{titlePrefix:statePanel?.filterName||''});
  }

  function scaleHtml(palette,breaks){
    const labs=[
      '≤'+fmt(Math.round(breaks[0]||0)),
      '≤'+fmt(Math.round(breaks[1]||0)),
      '≤'+fmt(Math.round(breaks[2]||0)),
      '≤'+fmt(Math.round(breaks[3]||0)),
      '≤'+fmt(Math.round(breaks[4]||0)),
      '≤'+fmt(Math.round(breaks[5]||0)),
      '>'+fmt(Math.round(breaks[5]||0))
    ];
    return '<div class="scale">'+palette.map(c=>'<span style="background:'+c+'"></span>').join('')+'</div>'+
      '<div class="legend-labels">'+labs.map(x=>'<span>'+x+'</span>').join('')+'</div>';
  }
  function renderLegend(){
    if(mode==='violence'){
      const key=currentViolenceMetric(),meta=violenceMetrics[key]||{},n=quantileBreaks(nationalRates(key));
      const b=quantileBreaks(berlinRates());
      el.legend.innerHTML=
        '<div class="legend-block"><div class="legend-title">德国县/市 · BKA PKS 2025</div><div>'+esc(meta.label||key)+' · 每10万人/年</div>'+scaleHtml(nationalPalette,n)+'</div>'+
        (key==='violence'&&map.getZoom()>=7.5&&map.getBounds().intersects(berlinBounds)?'<div class="legend-block"><div class="legend-title">柏林 · 官方细分层</div><div>抢劫 + 危险/严重伤害 · 每10万人/年</div>'+scaleHtml(berlinPalette,b)+'</div>':'')+
        '<div class="legend-row">全国层按县/市分位；城市细分层仅在官方口径可对应时自动显示。</div>';
    }else{
      const key=currentPropertyMetric(),meta=propertyMetrics[key]||{},n=quantileBreaks(propertyRates(key));
      const localField=propertyHeatField(),localBreaks=localField?quantileBreaks(propertyLocalValues(localField)):[];
      el.legend.innerHTML=
        '<div class="legend-block"><div class="legend-title">德国县/市 · BKA PKS 2025</div><div>'+esc(meta.label||key)+' · 每10万人/年</div>'+scaleHtml(propertyPalette,n)+'</div>'+
        (localField&&map.getZoom()>=7.5&&map.getBounds().intersects(berlinBounds)?'<div class="legend-block"><div class="legend-title">柏林 · 官方90天分区</div><div>'+(localField==='bike'?'自行车盗窃':localField==='vehicle'?'车内/车上盗窃':'自行车 + 车辆相关')+' · 记录数</div>'+scaleHtml(berlinPropertyPalette,localBreaks)+'</div>':'')+
        '<div class="legend-row">全国层按县/市犯罪率分位；城市细分层仅在官方可比数据存在时显示。</div>';
    }
  }
  function renderLayerInfo(cs){
    if(hoverArea||pinnedArea){areaPanel.renderAreaOverlay(hoverArea||pinnedArea);return;}
    if(mode==='violence'){
      areaPanel.renderAreaOverlay(null);
    }else{
      areaPanel.renderAreaOverlay(null);
    }
  }
  function renderSummary(){
    if(mode==='violence'){
      if(!pinnedArea||pinnedArea.kind==='berlin')showArea(null);
    }else{
      if(!pinnedArea||pinnedArea.kind==='property-local')showArea(null);
    }
  }
  function render(){
    el.modeViolence.classList.toggle('active',mode==='violence');el.modeProperty.classList.toggle('active',mode==='property');
    el.violenceLayers.hidden=mode!=='violence';el.propertyLayers.hidden=mode!=='property';
    el.toggleViolenceNews.classList.toggle('active',showViolenceNews);el.toggleViolenceNews.setAttribute('aria-pressed',String(showViolenceNews));
    el.togglePropertyNews.classList.toggle('active',showPropertyNews);el.togglePropertyNews.setAttribute('aria-pressed',String(showPropertyNews));
    buildCountyLayer();buildStateLayer();berlinDetail.render();
    const cs=renderNews();renderLegend();renderLayerInfo(cs);renderSummary(cs);renderRankList();
    const stateFilter=statePanel?.filterName;if(stateFilter){const f=stateFeatureByName(stateFilter);if(f)statePanel.render(f);}
  }

  areaPanel=window.CrimeAreaPanel.create({
    elements:el,
    getMode:()=>mode,getPksData:()=>pksData,getPropertyData:()=>propertyData,
    getNationalSummary:currentNationalSummary,
    formatNumber:fmt,escapeHtml:esc,
    onRankSelect:r=>{
      const layer=countyLayer?.getLayers().find(x=>{
        const rec=mode==='property'?propertyRecord(x.feature):pksRecord(x.feature);
        return rec?.ags===r.ags;
      });
      if(layer){
        const a=mode==='property'?propertyCountyArea(layer.feature,r):countyArea(layer.feature,r);
        selectCountyLayer(layer);showArea(a,{pin:true});
        // Choosing a ranked county opens its archive without forcing the camera to move.
      }
    }
  });

  countyController=window.CrimeCountyLayer.create({
    map,getCountyGeo:()=>countyGeo,getMode:()=>mode,
    getPksData:()=>pksData,getPropertyData:()=>propertyData,
    getMetric:kind=>kind==='property'?currentPropertyMetric():currentViolenceMetric(),
    getRates:(key,kind)=>kind==='property'?propertyRates(key):nationalRates(key),
    getRecord:(feature,kind)=>kind==='property'?propertyRecord(feature):pksRecord(feature),
    getArea:(feature,record,kind)=>kind==='property'?propertyCountyArea(feature,record):countyArea(feature,record),
    isBerlinDetailActive:berlinLocalActive,
    showArea,getPinnedArea:()=>pinnedArea,onLeave:()=>{hoverArea=null;},
    formatNumber:fmt,escapeHtml:esc,nationalPalette,propertyPalette
  });
  stateController=window.CrimeStateLayer.create({
    map,getStateGeo:()=>stateGeo,getStatePanel:()=>statePanel,getCountyBrowse:()=>countyBrowse,
    tooltipHtml:stateTooltipHtml
  });

  berlinDetail=window.CrimeBerlinDetail.create({
    map,
    getMode:()=>mode,
    getViolenceMetric:currentViolenceMetric,
    getPropertyMetric:currentPropertyMetric,
    getCaseData:()=>caseData,
    getViolenceData:()=>berlinViolence,
    getPropertyData:()=>heatData,
    showArea,
    getPinnedArea:()=>pinnedArea,
    formatNumber:fmt,
    escapeHtml:esc,
    violencePalette:berlinPalette,
    propertyPalette:berlinPropertyPalette
  });

  eventLayer=window.CrimeRecentEvents.create({
    map,
    listElement:el.list,
    titleElement:el.listTitle,
    categories:cats,
    formatNumber:fmt,
    formatDate:pd,
    escapeHtml:esc,
    safeUrl:safe
  });

  statePanel=window.CrimeStatePanel.create({
    elements:{
      stateDrawer:el.stateDrawer,stateName:el.stateName,stateMetric:el.stateMetric,stateJump:el.stateJump,
      stateRate:el.stateRate,stateCases:el.stateCases,stateRank:el.stateRank,stateRecent:el.stateRecent,
      stateTopCounties:el.stateTopCounties,stateNews:el.stateNews,stateNewsCount:el.stateNewsCount
    },
    map,
    getMode:()=>mode,
    getStats:stateStats,
    getMetricLabel:key=>mode==='property'?(propertyMetrics[key]?.label||key):(violenceMetrics[key]?.label||key),
    onCountySelect:(row,key)=>{
      const layer=countyLayer?.getLayers().find(x=>{
        const rec=mode==='property'?propertyRecord(x.feature):pksRecord(x.feature);
        return rec?.ags===row.ags;
      });
      if(layer){
        const area=mode==='property'?propertyCountyArea(layer.feature,row):countyArea(layer.feature,row);
        selectCountyLayer(layer);showArea(area,{pin:true});
        // State directory selection does not automatically move the map.
      }
    },
    onNewsSelect:item=>eventLayer.open(item,{minZoom:10,duration:.45}),
    onStateChanged:change=>{
       if(change?.changed&&!syncingCountyState){
         pinnedArea=null;hoverArea=null;countyController?.clearSelection();
         showArea(null);
       }
       if(change?.changed&&stateController)buildStateLayer();
       renderNews();
     },
    formatNumber:fmt,formatDate:pd,escapeHtml:esc
  });

  el.modeViolence.onclick=()=>{setCountyBrowse(false);mode='violence';pinnedArea=null;hoverArea=null;statePanel.reset();render();showArea(null);};
  el.modeProperty.onclick=()=>{setCountyBrowse(false);mode='property';pinnedArea=null;hoverArea=null;statePanel.reset();render();showArea(null);};

  // Ordinary map clicks only navigate evidence. Camera motion is explicitly
  // requested by the state locator or state picker.
  function focusStateFeature(feature){
    if(!feature)return;
    const bounds=L.geoJSON(feature).getBounds();
    if(!bounds.isValid())return;
    const mobile=window.matchMedia('(max-width:920px)').matches;
    const size=map.getSize();
    const drawer=el.stateDrawer.getBoundingClientRect();
    // Reserve the overlay's occupied side; focus inside the visible map area.
    // Pixel padding, unlike manual longitude offsets, works at any latitude.
    const leftPad=mobile?20:Math.min(Math.round(size.x*.46),Math.round(drawer.width+70));
    const topPad=mobile?Math.min(Math.round(size.y*.44),Math.round(drawer.height+28)):26;
    map.stop();
    map.fitBounds(bounds,{
      paddingTopLeft:[leftPad,topPad],
      paddingBottomRight:[24,24],
      maxZoom:7,animate:false
    });
  }
  function setStateDrawerExpanded(next){
    const expanded=Boolean(next);
    el.stateDrawer.classList.toggle('is-expanded',expanded);
    if(el.stateDrawerExpand){
      el.stateDrawerExpand.setAttribute('aria-expanded',String(expanded));
      el.stateDrawerExpand.setAttribute('aria-label',expanded?'收起州资料室':'展开州资料室');
      el.stateDrawerExpand.textContent=expanded?'收起':'展开';
    }
    if(!expanded)el.stateDrawer.scrollTop=0;
  }
  el.stateDrawerExpand?.addEventListener('click',e=>{
    e.stopPropagation();
    setStateDrawerExpanded(!el.stateDrawer.classList.contains('is-expanded'));
  });
  el.stateLocate?.addEventListener('click',e=>{
    e.stopPropagation();
    focusStateFeature(stateFeatureByName(statePanel?.selectedName));
  });
  el.stateClose.onclick=e=>{
    e.stopPropagation();setCountyBrowse(false);setStateDrawerExpanded(false);
    statePanel.close({restore:false});buildStateLayer();
  };
  // A source-backed state picker: the change is explicit navigation; clicking
  // state polygons themselves still opens their drawer WITHOUT auto-zoom.
  el.stateJump?.addEventListener('change',event=>{
    const feature=stateFeatureByName(event.target.value);
    if(!feature)return;
    statePanel.select(feature);
    buildStateLayer();
    focusStateFeature(feature);
    el.stateDrawer.scrollTop=0;
  });
  countyBrowseButton?.addEventListener('click',()=>setCountyBrowse(!countyBrowse));
   $('crimeCountyBackState')?.addEventListener('click',()=>{
     const stateName=statePanel?.selectedName||pinnedArea?.state;
     setCountyBrowse(false);
     pinnedArea=null;hoverArea=null;countyController.clearSelection();showArea(null);
     const f=stateFeatureByName(stateName);
     if(f&&!statePanel.isOpen)statePanel.select(f);
   });
   el.stateClose.onpointerdown=e=>e.stopPropagation();
  el.stateDragHandle.addEventListener('pointerdown',stateDrawerDrag.begin);
  el.stateDragHandle.addEventListener('pointermove',stateDrawerDrag.move);
  el.stateDragHandle.addEventListener('pointerup',stateDrawerDrag.end);
  el.stateDragHandle.addEventListener('pointercancel',stateDrawerDrag.end);
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&statePanel.isOpen){
    setCountyBrowse(false);setStateDrawerExpanded(false);
    statePanel.close({restore:false});buildStateLayer();
  }});
  el.toggleViolenceNews.onclick=()=>{showViolenceNews=!showViolenceNews;render();};
  el.togglePropertyNews.onclick=()=>{showPropertyNews=!showPropertyNews;render();};
  el.violenceMetric.addEventListener('change',()=>{pinnedArea=null;hoverArea=null;render();showArea(null);});
  el.propertyMetric.addEventListener('change',()=>{pinnedArea=null;hoverArea=null;render();showArea(null);});
  el.viewGermany.onclick=()=>{setCountyBrowse(false);pinnedArea=null;hoverArea=null;countyController.clearSelection();statePanel.reset();render();showArea(null);map.stop();map.fitBounds(germanyBounds,{padding:[14,14],animate:false});};
  el.focusBerlin.onclick=()=>{setCountyBrowse(false);pinnedArea=null;hoverArea=null;countyController.clearSelection();statePanel.reset();showArea(null);map.stop();map.fitBounds(berlinBounds,{padding:[25,25],maxZoom:10,animate:false});};
  // Berlin's detailed LOR geometry is several MB. Keep nationwide startup light:
  // it is needed only after entering the Berlin city view at detail zoom.
  let berlinDataRequest=null, berlinRetryAfter=0;
  function ensureBerlinData(){
    if(!caseData || !countyGeo || berlinViolence || berlinDataRequest ||
       map.getZoom()<7.5 || !map.getBounds().intersects(berlinBounds) ||
       Date.now()<berlinRetryAfter) return;
    berlinDataRequest=fetch('data/berlin_violent_2025.geojson',{cache:'no-store'})
      .then(r=>{if(!r.ok)throw new Error('berlin violence '+r.status);return r.json();})
      .then(geo=>{
        if(geo?.type!=='FeatureCollection'||!Array.isArray(geo.features)||!geo.features.length)
          throw new Error('Invalid Berlin detail geometry');
        berlinViolence=geo;
        berlinDetail.render();
        // Restyle the existing national layer rather than rebuilding 402 polygons.
        const selected=countyController.selected;
        countyLayer?.eachLayer(layer=>countyLayer.resetStyle(layer));
        if(selected)countyController.select(selected);
        renderLegend();
      }).catch(err=>{
        console.warn('Berlin detail unavailable; nationwide county map stays usable',err);
        // Avoid a request storm after a transient failure, but allow zoom retries.
        berlinRetryAfter=Date.now()+30000;
      }).finally(()=>{berlinDataRequest=null;});
  }
  map.on('zoomend',()=>{buildStateLayer();berlinDetail.render();ensureBerlinData();renderLegend();});
  map.on('moveend',()=>{if(!stateLayer)buildStateLayer();if(el.stateDrawer.classList.contains('open'))stateDrawerDrag.keepInside();ensureBerlinData();});

  window.addEventListener('resize',()=>{
    if(el.stateDrawer.classList.contains('open'))stateDrawerDrag.keepInside();
    map.invalidateSize({pan:false});
  });
  Promise.all([
    fetch('data/cases.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('cases '+r.status);return r.json()}),
    fetch('data/germany-counties-display.geojson',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error('counties '+r.status);return r.json()}),
    fetch('data/germany-states.geojson',{cache:'force-cache'}).then(r=>{if(!r.ok)throw new Error('states '+r.status);return r.json()}),
    fetch('data/pks_violent_2025.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('pks '+r.status);return r.json()}),
    fetch('data/pks_property_2025.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('property pks '+r.status);return r.json()}),
    fetch('data/berlin_heatmap.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('heat '+r.status);return r.json()})
  ]).then(([cases,counties,states,pks,propertyPks,heat])=>{
    caseData=cases;countyGeo=counties;stateGeo=states;pksData=pks;propertyData=propertyPks;heatData=heat;
    // Populate only real German federal states from the same geometry that
    // owns map clicks, never a manually maintained list that can drift.
    if(el.stateJump){
      const options=[...stateGeo.features].filter(f=>f.properties?.name).map(f=>({
        name:f.properties.name,
        label:window.GermanPlaceNames?.translate(f.properties.name)||f.properties.name
      })).sort((a,b)=>a.label.localeCompare(b.label,'zh-CN'));
      el.stateJump.replaceChildren(new Option('选择联邦州',''),...options.map(o=>new Option(o.label,o.name)));
    }
    const t=caseData.meta?.generated_at?new Date(caseData.meta.generated_at):null;
    el.updated.textContent=t&&!Number.isNaN(+t)?'通报更新 '+t.toLocaleString():'通报更新时间未知';
    render();showArea(null);ensureBerlinData();
  }).catch(err=>{
    console.error(err);el.mapStatus.className='mapstatus fallback';el.mapStatus.textContent='数据加载失败：'+err.message;el.updated.textContent='数据加载失败';
  });

  window.__CRIME_MAP__={
    map,getMode:()=>mode,getCaseData:()=>caseData,getPksData:()=>pksData,getPropertyData:()=>propertyData,getBerlinViolence:()=>berlinViolence,getHeatData:()=>heatData,
    getCountyLayer:()=>countyLayer,setCountyFocus:ags=>countyController?.setDetailFocus(ags),getBerlinLayer:()=>berlinDetail?.violenceLayer||null,getHeatLayer:()=>berlinDetail?.propertyLayer||null,getVisibleCases:()=>visibleCases(),
    getPinnedArea:()=>pinnedArea,getHoverArea:()=>hoverArea,isCountyBrowse:()=>countyBrowse,getStateLayer:()=>stateLayer,
    clearSelection:()=>{pinnedArea=null;hoverArea=null;countyController.clearSelection();statePanel.reset();showArea(null);},
    showArea
  };
})();
