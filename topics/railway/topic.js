(() => {
'use strict';
const $=id=>document.getElementById(id);
const D=window.GermanRailway07Data;
const STYLE_META={
 speed:[['未知速度','#677886'],['<120 km/h','#517e9e'],['120–159 km/h','#55a0c5'],['160–199 km/h','#68bcaf'],['≥200 km/h','#e4b974']],
 elec:[['未标注','#6a7885'],['非电气化','#a3aab4'],['架空接触网','#55c1c7'],['第三轨','#b39bd4']],
 tracks:[['未标注','#6a7885'],['单线','#dda373'],['双线','#79bcd0']]
};
const CANVAS_PANE='railway-tracks', BOUNDS=[[47.05,5.45],[55.15,15.65]];
let style='speed', selected=null, map=null, layer=null, tilesLoaded=false;
let parts=[],groups={},byRoute=new Map();
const fmt=v=>Number(v||0).toLocaleString('zh-CN',{maximumFractionDigits:1});
const km=v=>fmt(v)+' km';
const pct=(v,n)=>n?(100*v/n).toFixed(1)+'%':'—';
const xyToLatLng=(x,y)=>[55.4-(y-6)/114.2,5.34+(x-15)/76.5];
const latLngToXY=ll=>[(ll.lng-5.34)*76.5+15,(55.4-ll.lat)*114.2+6];
const htmlSafe=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function decodePath(packed) {
  const xy=[];let x=0,y=0,i=0;
  while(i<packed.length){
    for(let k=0;k<2;k++){
      let n=0,shift=0,b;
      do{
        if(i>=packed.length) throw Error('铁路压缩几何截断');
        b=packed.charCodeAt(i++)-63;
        if(b<0||b>63)throw Error('铁路几何包含无效编码');
        n|=(b&31)<<shift;shift+=5;
        if(shift>35)throw Error('铁路几何编码溢出');
      }while(b>=32);
      const delta=(n&1)?~(n>>1):n>>1;
      if(k===0)x+=delta;else y+=delta;
    }
    xy.push(x/10,y/10);
  }
  return xy;
}
function category(s,mode){
  if(mode==='speed')return s.speed;
  if(mode==='elec')return s.e===1?2:s.e===2?3:s.e===0?1:0;
  return s.tracks===1?2:s.tracks===0?1:0;
}
function fail(msg,e){console.error('Railway 07:',msg,e||'');$('mapStatus').className='mapstatus rail-map-status-error';$('mapStatus').textContent=msg;}
function validateSource(){
  if(!D||!Array.isArray(D.routes)||!Array.isArray(D.sections)||!D.qa||!D.states)
    throw Error('07 铁路数据缺失');
  if(D.routes.length!==1546||D.sections.length!==33547||Object.keys(D.states).length!==16)
    throw Error('铁路参考数据数量未通过校验');
  if(D.qa.route_ids_in_germany!==1546||D.qa.source_line_geometries!==33547
     ||D.qa.in_german_states!==33376)
    throw Error('官方线路参考数据 QA 不一致');
  if(D.routes.some(r=>!Array.isArray(r)||r.length!==15||!r[0]))
    throw Error('线路记录结构错误');
}
function buildGeometry(){
  const samples=new Map();groups={
    speed:STYLE_META.speed.map(()=>[]),
    elec:STYLE_META.elec.map(()=>[]),
    tracks:STYLE_META.tracks.map(()=>[])
  };
  for(const [rid,sid,e,speed,tracks,encoded] of D.sections){
    if(!Number.isInteger(rid)||!D.routes[rid])throw Error('线路区段索引无效');
    const pts=decodePath(encoded);
    if(pts.length<4)continue;
    let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
    for(let i=0;i<pts.length;i+=2){
      minX=Math.min(minX,pts[i]);minY=Math.min(minY,pts[i+1]);
      maxX=Math.max(maxX,pts[i]);maxY=Math.max(maxY,pts[i+1]);
    }
    const sec={rid,e,speed,tracks,pts,minX,minY,maxX,maxY};
    parts.push(sec);
    let r=byRoute.get(rid);
    if(!r){r=[];byRoute.set(rid,r)}
    r.push(sec);
    for(const key of ['speed','elec','tracks'])groups[key][category(sec,key)].push(sec);
    samples.set(rid,(samples.get(rid)||0)+1);
  }
  if(parts.length!==33547)throw Error('线路几何丢失：'+parts.length+' / 33547');
}
const RailCanvas=L.Layer.extend({
  onAdd(m){
    this._map=m;
    this._canvas=L.DomUtil.create('canvas','rail-canvas',m.getPane(CANVAS_PANE));
    this._canvas.style.cssText='position:absolute;pointer-events:none';
    m.on('moveend zoomend resize',this.redraw,this);
    this.redraw();
  },
  onRemove(m){
    m.off('moveend zoomend resize',this.redraw,this);
    this._canvas.remove();
  },
  redraw(){
    if(!this._map)return;
    const m=this._map,size=m.getSize(),dpr=Math.min(2,window.devicePixelRatio||1);
    const cv=this._canvas,topLeft=m.containerPointToLayerPoint([0,0]);
    L.DomUtil.setPosition(cv,topLeft);
    cv.width=Math.max(1,Math.round(size.x*dpr));
    cv.height=Math.max(1,Math.round(size.y*dpr));
    cv.style.width=size.x+'px';cv.style.height=size.y+'px';
    const ctx=cv.getContext('2d',{alpha:true});
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,size.x,size.y);
    ctx.lineJoin='round';ctx.lineCap='round';
    const bounds=m.getBounds().pad(.2),a=latLngToXY(bounds.getNorthWest()),b=latLngToXY(bounds.getSouthEast());
    const view={minX:Math.min(a[0],b[0]),maxX:Math.max(a[0],b[0]),minY:Math.min(a[1],b[1]),maxY:Math.max(a[1],b[1])};
    function draw(secs){
      let n=0;
      for(const s of secs){
        if(s.maxX<view.minX||s.minX>view.maxX||s.maxY<view.minY||s.minY>view.maxY)continue;
        const p=s.pts;
        for(let k=0;k<p.length;k+=2){
          const point=m.latLngToContainerPoint(xyToLatLng(p[k],p[k+1]));
          if(k===0)ctx.moveTo(point.x,point.y);else ctx.lineTo(point.x,point.y);
        }
        n++;
      }
      return n;
    }
    let visible=0;
    const palette=STYLE_META[style];
    for(let i=0;i<palette.length;i++){
      ctx.beginPath();
      const secs=groups[style][i];
      visible+=draw(secs);
      ctx.strokeStyle=palette[i][1];
      ctx.globalAlpha=i===0?.4:.85;
      ctx.lineWidth=(style==='speed'&&i===4)?1.75:1.15;
      ctx.stroke();
    }
    if(selected!==null){
      const target=byRoute.get(selected)||[];
      ctx.beginPath();draw(target);
      ctx.globalAlpha=.85;ctx.lineWidth=7;ctx.strokeStyle='#152433';ctx.stroke();
      ctx.beginPath();draw(target);
      ctx.globalAlpha=1;ctx.lineWidth=3.4;ctx.strokeStyle='#f2c174';ctx.stroke();
    }
    ctx.globalAlpha=1;
    this.visibleSections=visible;
  }
});
function legend(){
  $('legend').innerHTML='<div class="rail-legend-label">铁路属性 · '+({speed:'最高速度',elec:'电气化',tracks:'单双线'}[style])+'</div>'
    +'<div class="rail-legend-rows">'+STYLE_META[style].map(([name,color])=>
      '<span class="rail-legend-item"><i class="rail-legend-swatch" style="background:'+color+'"></i>'+htmlSafe(name)+'</span>').join('')+'</div>';
}
function appendFact(label,value){
  const row=document.createElement('div');
  row.className='rail-fact';
  const a=document.createElement('span'),b=document.createElement('strong');
  a.textContent=label;b.textContent=value;row.append(a,b);$('facts').append(row);
}
function details(){
  $('facts').replaceChildren();$('stopList').replaceChildren();
  $('selectedTools').hidden=selected===null;
  $('stops').hidden=selected===null;
  if(selected===null){
    $('sectionTitle').textContent='全国铁路基础设施';
    $('detailName').textContent='德国铁路网';
    $('detailBadge').textContent='官方线路';
    $('detailSub').textContent='线路编号不同于客运车次或 ICE 运营线路';
    $('routeCount').textContent=fmt(D.routes.length);
    $('routeLabel').textContent='境内线路编号';
    $('segmentCount').textContent=fmt(D.qa.in_german_states);
    $('segmentLabel').textContent='境内原始分段';
    $('stateCount').textContent=fmt(Object.keys(D.states).length);
    $('stateLabel').textContent='覆盖联邦州';
    appendFact('轨道方向线段累计',km(D.summary.length));
    appendFact('电气化线段累计占比',pct(D.summary.elec_len,D.summary.length));
    appendFact('最高速度 ≥200 km/h 区段累计',km(D.summary.highspeed_len));
    appendFact('原始可绘制几何部件',fmt(D.sections.length));
    return;
  }
  const r=D.routes[selected];
  $('sectionTitle').textContent='线路编号 · '+r[0];
  $('detailName').textContent=r[2]||r[1];
  $('detailBadge').textContent='#'+r[0];
  $('detailSub').textContent=r[1];
  $('routeCount').textContent=fmt(r[4]);
  $('routeLabel').textContent='该线路原始分段';
  $('segmentCount').textContent=fmt(r[11]);
  $('segmentLabel').textContent='轨道几何部件';
  $('stateCount').textContent=fmt(r[8].length);
  $('stateLabel').textContent='涉及联邦州';
  $('selectedInfo').textContent='已选线路 #'+r[0];
  appendFact('轨道方向线段累计',km(r[3]));
  appendFact('电气化累计长度',km(r[5])+' · '+pct(r[5],r[3]));
  appendFact('最高速 ≥200 km/h 区段累计',km(r[6]));
  appendFact('速度未知属性区段累计',km(r[7]));
  appendFact('单线属性累计',km(r[14]));
  appendFact('双线属性累计',km(r[13]));
  for(const [k,value] of Object.entries(r[10]||{}))appendFact(k,km(value));
  $('stops').hidden=false;
  for(const [name,typ] of r[12].slice(0,20)){
    const el=document.createElement('div');el.className='rail-stop';
    const small=document.createElement('small');small.textContent=typ;
    el.append(small,document.createTextNode(name));$('stopList').append(el);
  }
  if(!r[12].length)$('stopList').textContent='该线路无可展示的匹配运营点';
}
function focusRoute(index){
  const bbox=D.routes[index][9];
  if(!bbox||bbox[0]>bbox[2])return;
  const bounds=L.latLngBounds(xyToLatLng(bbox[0],bbox[3]),xyToLatLng(bbox[2],bbox[1]));
  map.fitBounds(bounds.pad(.22),{animate:false,maxZoom:11});
}
function choose(index,zoom=true){
  if(!D.routes[index])return;
  selected=index;
  $('matches').hidden=true;
  $('routeSearch').value='#'+D.routes[index][0]+' · '+(D.routes[index][2]||D.routes[index][1]);
  details();
  if(zoom)focusRoute(index);
  layer.redraw();
}
function clear(){
  selected=null;
  $('routeSearch').value='';
  $('matches').hidden=true;
  details();map.fitBounds(BOUNDS,{padding:[12,12],animate:false});layer.redraw();
}
function search(term){
  const q=String(term||'').trim().toLowerCase();
  if(!q)return[];
  const result=[];
  for(let i=0;i<D.routes.length;i++){
    const r=D.routes[i];
    if((r[0]+' '+r[1]+' '+r[2]).toLowerCase().includes(q))result.push(i);
  }
  result.sort((a,b)=>(D.routes[a][0]===q?-1:0)-(D.routes[b][0]===q?-1:0)
    || D.routes[b][11]-D.routes[a][11]);
  return result.slice(0,12);
}
function searchResults(query){
  const ids=search(query),target=$('matches');
  target.replaceChildren();
  target.hidden=!query.trim();
  if(target.hidden)return;
  if(!ids.length){target.innerHTML='<div class="empty">没有匹配的线路编号或名称</div>';return}
  for(const idx of ids){
    const r=D.routes[idx],b=document.createElement('button');b.type='button';
    b.innerHTML='<strong>#'+htmlSafe(r[0])+' · '+htmlSafe(r[2]||r[1])+'</strong>'
      +'<small>'+htmlSafe(r[1])+' · '+fmt(r[11])+' 段几何</small>';
    b.onclick=()=>choose(idx);
    target.appendChild(b);
  }
}
function snapPoint(p,a,b){
  const dx=b[0]-a[0],dy=b[1]-a[1],den=dx*dx+dy*dy;
  const t=den?Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)):0;
  return (p[0]-a[0]-t*dx)**2+(p[1]-a[1]-t*dy)**2;
}
function hitRail(latlng){
  const p=latLngToXY(latlng),screen=map.latLngToContainerPoint(latlng);
  const nearby=map.containerPointToLatLng(screen.add([9,9]));
  const q=latLngToXY(nearby);
  const radius=Math.max(0.15,Math.hypot(q[0]-p[0],q[1]-p[1]));
  const radius2=radius*radius;
  let candidate=null,closest=radius2;
  for(const s of parts){
    if(s.minX>p[0]+radius||s.maxX<p[0]-radius||s.minY>p[1]+radius||s.maxY<p[1]-radius)continue;
    const pts=s.pts;
    for(let i=0;i<pts.length-2;i+=2){
      const dist=snapPoint(p,[pts[i],pts[i+1]],[pts[i+2],pts[i+3]]);
      if(dist<closest){closest=dist;candidate=s.rid}
    }
  }
  return candidate;
}
function initMap(){
  map=L.map('railway-map',{preferCanvas:true,minZoom:5,maxZoom:16,zoomControl:true,zoomSnap:.5});
  map.fitBounds(BOUNDS,{padding:[12,12],animate:false});
  map.setMaxBounds([[45.3,3.2],[57.1,18]]);
  map.createPane(CANVAS_PANE).style.zIndex=350;
  map.createPane('railway-states').style.zIndex=375;
  map.getPane('tilePane').style.filter='saturate(.45) contrast(.86) brightness(1.06)';
  const tile=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,opacity:.86,attribution:'© OpenStreetMap contributors'});
  tile.on('tileload',()=>{if(!tilesLoaded){tilesLoaded=true;$('mapStatus').className='mapstatus ok';$('mapStatus').textContent='OSM街道底图 · DB铁路网'}});
  let errors=0;tile.on('tileerror',()=>{if(++errors>6&&!tilesLoaded)$('mapStatus').textContent='底图暂不可用 · 铁路线路仍可浏览'});
  tile.addTo(map);
  L.geoJSON; // Map and style share the same data/geometry semantics as modules 01–06.
  fetch('../../data/germany-states.geojson',{cache:'force-cache'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json()})
    .then(data=>L.geoJSON(data,{pane:'railway-states',interactive:false,
      style:{color:'#273c50',weight:1.4,opacity:.75,fill:false}}).addTo(map))
    .catch(e=>console.warn('Optional state reference outlines unavailable',e));
  window.CrimeCityLabels?.create(map,{paneName:'railway-city-labels',zIndex:455});
  layer=new RailCanvas().addTo(map);
  map.on('click',e=>{
    const idx=hitRail(e.latlng);
    if(idx!==null)choose(idx,false);
  });
}
function wire(){
  for(const b of document.querySelectorAll('[data-style]'))b.onclick=()=>{
    style=b.dataset.style;
    for(const x of document.querySelectorAll('[data-style]')){
      const active=x===b;x.classList.toggle('active',active);x.setAttribute('aria-pressed',String(active));
    }
    legend();layer.redraw();
  };
  $('routeSearch').oninput=e=>searchResults(e.target.value);
  $('routeSearch').onkeydown=e=>{
    if(e.key==='Escape')$('matches').hidden=true;
    if(e.key==='Enter'){const matches=search(e.target.value);if(matches.length){choose(matches[0]);e.preventDefault();}}
  };
  $('clearRoute').onclick=clear;
}
try{
  validateSource();
  if(!window.L)throw Error('Leaflet 无法加载');
  buildGeometry();
  initMap();
  wire();legend();details();
  window.__RAILWAY_07__={getMap:()=>map,getStyle:()=>style,
    getRouteCount:()=>D.routes.length,getGeometryCount:()=>parts.length,
    getSelected:()=>selected,getVisibleGeometryCount:()=>layer.visibleSections,
    search,selectById:id=>{const idx=D.routes.findIndex(r=>r[0]===String(id));if(idx<0)return false;choose(idx);return true},
    getSource:()=>D, getNetworkBounds:()=>map.getBounds()};
}catch(e){fail('07 铁路预览初始化失败：'+e.message,e);}
})();