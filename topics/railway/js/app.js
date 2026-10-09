
const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
const P=([lon,lat])=>[(lon-5.34)*76.5+15,(55.40-lat)*114.2+6];
let perfView='station',perfType='ICE',perfMetric='delay',minObservations=1000,selectedStation=null;
const perfIndex={'ALL':0,'ICE':1,'RE':2};
const obsStations=OBS.stations.map((s,i)=>({i,name:s[0],lon:s[1],lat:s[2],state:s[3],groups:s.slice(4),xy:[(s[1]-5.34)*76.5+15,(55.4-s[2])*114.2+6]}));
const cnStationNames={'Hamm (Westf) Hbf':'哈姆中央站','Hagen Hbf':'哈根中央站','Wuppertal Hbf':'伍珀塔尔中央站','Bielefeld Hbf':'比勒费尔德中央站','Solingen Hbf':'索林根中央站','Münster (Westf) Hbf':'明斯特中央站','Gelsenkirchen Hbf':'盖尔森基兴中央站','Dortmund Hbf':'多特蒙德中央站','Hannover Hbf':'汉诺威中央站','Berlin Hauptbahnhof':'柏林中央站','Hamburg Hbf':'汉堡中央站','Frankfurt (Main) Hbf':'法兰克福中央站','München Hbf':'慕尼黑中央站','Köln Hbf':'科隆中央站','Düsseldorf Hbf':'杜塞尔多夫中央站','Duisburg Hbf':'杜伊斯堡中央站','Dresden Hbf':'德累斯顿中央站','Saarbrücken Hbf':'萨尔布吕肯中央站','Rostock Hbf':'罗斯托克中央站','Schwerin Hbf':'什未林中央站','Kiel Hbf':'基尔中央站','Leipzig Hbf':'莱比锡中央站','Erfurt Hbf':'埃尔福特中央站','Stuttgart Hbf':'斯图加特中央站','Nürnberg Hbf':'纽伦堡中央站','Bremen Hbf':'不来梅中央站','Augsburg Hbf':'奥格斯堡中央站','Mannheim Hbf':'曼海姆中央站','Bonn Hbf':'波恩中央站','Braunschweig Hbf':'不伦瑞克中央站','Osnabrück Hbf':'奥斯纳布吕克中央站','Magdeburg Hbf':'马格德堡中央站','Würzburg Hbf':'维尔茨堡中央站','Freiburg (Breisgau) Hbf':'弗赖堡中央站','Kassel-Wilhelmshöhe':'卡塞尔-威廉高地站','Wolfsburg Hbf':'沃尔夫斯堡中央站','Saarbrücken Hbf':'萨尔布吕肯中央站','Siegburg/Bonn':'锡格堡／波恩站','Dresden Hbf':'德累斯顿中央站'};
function localizedStation(s){const name=window.GermanRailStations?.localize(s);return name&&name!==s?name:(cnStationNames[s]||s)}
const svgNS='http://www.w3.org/2000/svg';
function make(tag,attrs,into){const e=document.createElementNS(svgNS,tag);for(const [k,v] of Object.entries(attrs||{}))e.setAttribute(k,v);into?.appendChild(e);return e}
function decode(s,mult=10){let arr=[],i=0,x=0,y=0;while(i<s.length){let xy=[];for(let axis=0;axis<2;axis++){let n=0,shift=0,b;do{if(i>=s.length)return arr;b=s.charCodeAt(i++)-63;n|=(b&31)<<shift;shift+=5}while(b>=32);xy.push((n&1)?~(n>>1):(n>>1))}x+=xy[0];y+=xy[1];arr.push(x/mult,y/mult)}return arr}
const styles={speed:[['未知速度','#566a79'],['<120 km/h','#527f9a'],['120–159 km/h','#5fb0d0'],['160–199 km/h','#77d5be'],['≥200 km/h','#f0c875']],elec:[['未标注','#52677b'],['非电气化','#a4a8b2'],['架空接触网','#6bd3d8'],['第三轨','#b49bea']],tracks:[['未标注','#52677b'],['单线','#e3a66e'],['双线','#7dccd4']]};
let style='speed',selected=null,selectedRegion=null,areaMetric='none',viewScale=1,tx=0,ty=0;
const canvas=$('#canvas'),ctx=canvas.getContext('2d',{alpha:true}); ctx.setTransform(2,0,0,2,0,0);const stateEl=$('#stateG'),stateNames=$('#stateLabels'),hubEl=$('#hubs'),stopsEl=$('#selectedStops'),opsPane=$('#stops');
const stateNodes={},statePaths={},statePolys={};
const stateNameMap={'DE-BW':'巴登-符腾堡','DE-BY':'巴伐利亚','DE-BE':'柏林','DE-BB':'勃兰登堡','DE-HB':'不来梅','DE-HH':'汉堡','DE-HE':'黑森','DE-MV':'梅前州','DE-NI':'下萨克森','DE-NW':'北威州','DE-RP':'莱法州','DE-SL':'萨尔兰','DE-SN':'萨克森','DE-ST':'萨安州','DE-SH':'石荷州','DE-TH':'图林根'};
const stateCentres={'DE-BW':[9.1,48.5],'DE-BY':[11.5,48.75],'DE-BE':[13.4,52.52],'DE-BB':[13.72,52.72],'DE-HB':[8.81,53.04],'DE-HH':[10.02,53.55],'DE-HE':[9,50.4],'DE-MV':[12.3,53.9],'DE-NI':[9.5,52.8],'DE-NW':[7.55,51.45],'DE-RP':[7.5,49.84],'DE-SL':[7.04,49.35],'DE-ST':[11.7,52],'DE-SN':[13.1,51.05],'DE-SH':[9.9,54.1],'DE-TH':[11,50.84]};
for(const [id,parts] of Object.entries(STATES_PACKED)){
 let d='',pth=new Path2D();statePolys[id]=[];for(const str of parts){const pts=decode(str,1000);if(pts.length<6)continue;const ring=[];for(let i=0;i<pts.length;i+=2){const [x,y]=P([pts[i],pts[i+1]]);ring.push([x,y]);d+=(i===0?'M':'L')+x.toFixed(1)+' '+y.toFixed(1)+' ';if(i===0)pth.moveTo(x,y);else pth.lineTo(x,y)}d+='Z ';pth.closePath();statePolys[id].push(ring)}
 const path=make('path',{d,'class':'state'},stateEl);stateNodes[id]=path;statePaths[id]=pth;
 const c=P(stateCentres[id]),lab=make('text',{x:c[0],y:c[1],'class':'statename'},stateNames);lab.textContent=id.slice(3)
}
// Static major cities; not an assertion of actual station platform centroid.
const hubs=[['汉堡',10,53.55],['柏林',13.405,52.52],['汉诺威',9.735,52.375],['不来梅',8.8,53.08],['莱比锡',12.37,51.34],['德累斯顿',13.74,51.05],['科隆',6.96,50.94],['法兰克福',8.68,50.11],['纽伦堡',11.08,49.45],['斯图加特',9.18,48.78],['慕尼黑',11.58,48.14]];
for(const [name,lon,lat] of hubs){const p=P([lon,lat]),g=make('g',{},hubEl);make('circle',{cx:p[0],cy:p[1],r:2.8,'class':'station-dot'},g);const label=make('text',{x:p[0]+5,y:p[1]-7,'class':'station-label'},g);label.textContent=name}
// Build one Path2D per style/category and per official railway route. Both share exactly the same official geometry.
const geoGroups={speed:Array.from({length:5},()=>new Path2D()),elec:Array.from({length:4},()=>new Path2D()),tracks:Array.from({length:3},()=>new Path2D())};
const routePaths=DATA.routes.map(()=>new Path2D());
const CELL=24,grids=new Map();let lineCount=0;
const perfLayer=$('#stationPerformance');
const perfNodes=[];
for(const s of obsStations){ const g=make('g',{},perfLayer); const halo=make('circle',{cx:s.xy[0],cy:s.xy[1],r:6,'class':'perf-halo'},g);const dot=make('circle',{cx:s.xy[0],cy:s.xy[1],r:4,'class':'perf-dot'},g);perfNodes.push({g,halo,dot}) }
function currentObs(s){const q=s.groups[perfIndex[perfType]];return q&&q[1]>=minObservations?q:null}
function colorObs(v){const thresholds=perfMetric==='delay'?[5,10,15,20]:[2,4,7,11];const colors=['#66c5b8','#a0c99e','#edc16e','#ea8c69','#db6375'];let idx=thresholds.findIndex(t=>v<t);return colors[idx<0?4:idx]}
function valObs(q){return perfMetric==='delay'?q[0]:q[2]}
function fmtObs(q){return perfMetric==='delay'?q[0].toFixed(1)+' 分钟':q[2].toFixed(1)+'%'}
function updatePerf(){
 const visible=obsStations.filter(s=>perfView==='station'&&currentObs(s));
 for(let i=0;i<obsStations.length;i++){const s=obsStations[i],node=perfNodes[i],q=currentObs(s);const show=perfView==='station'&&!!q;node.g.style.display=show?'':'none'; if(!show)continue;node.dot.setAttribute('fill',colorObs(valObs(q)));node.dot.setAttribute('r',Math.min(6.6,Math.max(3.3,3.1+Math.log10(q[1]/600)*1.7)));node.dot.classList.toggle('active',selectedStation===i);node.halo.setAttribute('r',selectedStation===i?10:5.7);node.halo.style.opacity=selectedStation===i?'1':'.25';}
 $('#perfLegend').style.display=perfView==='station'?'':'none';$('#perfLegend').innerHTML=(perfMetric==='delay'?[['<5分钟','#66c5b8'],['5–9.9分钟','#a0c99e'],['10–14.9分钟','#edc16e'],['15–19.9分钟','#ea8c69'],['≥20分钟','#db6375']]:[['<2%','#66c5b8'],['2–3.9%','#a0c99e'],['4–6.9%','#edc16e'],['7–10.9%','#ea8c69'],['≥11%','#db6375']]).map(([t,c])=>`<div class="legend-item"><span class="line-key" style="background:${c}"></span>${t}</div>`).join('');$('#perfCoverage').textContent=perfView==='station'?`当前显示 ${visible.length} / ${obsStations.length} 个精选站点；全部为实测，不是线路准点率。`:'已隐藏运行观测点；仅显示 DB InfraGO 官方线路结构。';
 const rank=$('#stationRanks');rank.replaceChildren();
 const top=visible.sort((a,b)=>valObs(currentObs(b))-valObs(currentObs(a))).slice(0,7);
 for(const s of top){const b=document.createElement('button');const l=document.createElement('span');l.textContent=localizedStation(s.name);l.title=s.name;const v=document.createElement('b');v.textContent=fmtObs(currentObs(s));b.append(l,v);b.onclick=()=>selectStation(s.i,true);rank.appendChild(b)}
 $('#rankingSection').style.display=perfView==='station'?'':'none';
 $('#perfType').disabled=$('#perfMetric').disabled=$('#minSample').disabled=perfView==='infra';
}
function showStationDetail(){if(selectedStation===null)return false;const s=obsStations[selectedStation],q=currentObs(s);if(!q)return false;
 $('#kvlist').replaceChildren();opsPane.replaceChildren();
 $('#detailTitle').textContent=localizedStation(s.name)+' · 实测停靠';$('#detailSub').textContent='2026年8—9月 · '+({'ALL':'全部车次','ICE':'ICE','RE':'RE'}[perfType])+' · 数据取自 DB API 历史采集';
 $('#bigNum').textContent=fmtObs(q);$('#bigCaption').textContent=perfMetric==='delay'?'此站该车次类型的平均晚点':'此站该车次类型的停靠取消比例';
 $('#aVal').textContent=count(q[1]);$('#aLab').textContent='停靠观测记录数';$('#bVal').textContent=q[2].toFixed(1)+'%';$('#bLab').textContent='停靠取消率';
 kv('平均晚点',q[0].toFixed(2)+' 分钟');kv('站点德文名称',s.name);kv('坐标来源','DB InfraGO 运营点');kv('观测时间','2026-08 至 2026-09');kv('观测样本',count(q[1])+' 条');kv('其他车次类型','左侧可切换');
 opsPane.innerHTML='<div class="sub">该数值来自本站停靠记录，不是该地铁路线路的准点率；取消停靠不等同列车全程取消或途中终止。精选车站样本不支持全国最差车站排名。</div>';return true}
function selectStation(i,focus=false){selectedStation=i;selected=null;selectedRegion=null;$('#search').value='';if(perfView==='infra'){$('#perfView [data-view="station"]').click()}updatePerf();showDetails();updateStops();setArea();redraw();if(focus){const s=obsStations[i];viewScale=Math.max(1.35,viewScale);tx=vp.clientWidth/2-s.xy[0]*viewScale;ty=vp.clientHeight/2-s.xy[1]*viewScale;applyCam()}}
function hitStation(x,y){if(perfView!=='station')return null;const threshold=Math.max(4.5,12/viewScale);let best=threshold*threshold,idx=null;for(const s of obsStations){if(!currentObs(s))continue;const dx=x-s.xy[0],dy=y-s.xy[1],d=dx*dx+dy*dy;if(d<best){best=d;idx=s.i}}return idx}

function appendPath(path,pts){path.moveTo(pts[0],pts[1]);for(let i=2;i<pts.length;i+=2)path.lineTo(pts[i],pts[i+1]);}
for(const [rid,sid,e,speed,trk,encoded] of DATA.sections){const pts=decode(encoded);if(pts.length<4)continue;
 appendPath(routePaths[rid],pts);appendPath(geoGroups.speed[speed],pts);appendPath(geoGroups.elec[e===1?2:e===2?3:e===0?1:0],pts);appendPath(geoGroups.tracks[trk===1?2:trk===0?1:0],pts);lineCount++;
 // Hit test grid index: store small segments in their intersected cells; a click only tests nearby candidates.
 for(let j=0;j<pts.length-2;j+=2){const x1=pts[j],y1=pts[j+1],x2=pts[j+2],y2=pts[j+3];const miX=Math.floor((Math.min(x1,x2)-4)/CELL),maX=Math.floor((Math.max(x1,x2)+4)/CELL),miY=Math.floor((Math.min(y1,y2)-4)/CELL),maY=Math.floor((Math.max(y1,y2)+4)/CELL);
  for(let gx=miX;gx<=maX;gx++)for(let gy=miY;gy<=maY;gy++){const key=gx+','+gy;if(!grids.has(key))grids.set(key,[]);grids.get(key).push([rid,x1,y1,x2,y2])}
 }
}
function count(v){return Math.round(v||0).toLocaleString('zh-CN')}
function km(v){return (v||0).toLocaleString('zh-CN',{maximumFractionDigits:1})+' km'}
function share(a,b){return b?(a/b*100).toFixed(1)+'%':'—'}
function strokeStyle(){if(style==='speed')return ['#566a79','#527f9a','#5fb0d0','#77d5be','#f0c875'];if(style==='elec')return ['#52677b','#a4a8b2','#6bd3d8','#b49bea'];return ['#52677b','#e3a66e','#7dccd4']}
function redraw(){ctx.clearRect(0,0,790,1000);ctx.lineJoin='round';ctx.lineCap='round';let colors=strokeStyle();
 if(!$('#onlyRoute').checked||selected===null){const paths=geoGroups[style];for(let i=0;i<paths.length;i++){ctx.strokeStyle=colors[i];ctx.globalAlpha=i===0?.40:.69;ctx.lineWidth=(style==='speed'&&i===4)?1.35:1.03;ctx.stroke(paths[i])}}
 if(selected!==null){ctx.globalAlpha=.7;ctx.lineWidth=7;ctx.strokeStyle='#0d1622';ctx.stroke(routePaths[selected]);ctx.globalAlpha=1;ctx.lineWidth=3.2;ctx.strokeStyle='#ffc17a';ctx.stroke(routePaths[selected])}
 ctx.globalAlpha=1;
}
function renderLegend(){const colors=strokeStyle();$('#legend').innerHTML=styles[style].map(([label],i)=>`<div class="legend-item"><span class="line-key" style="background:${colors[i]}"></span>${label}<span></span></div>`).join('')}
function setArea(){let vals=[];for(const st of Object.values(DATA.states)){let val=areaMetric==='elec'?100*st.elec_len/st.length:areaMetric==='high'?st.highspeed_len:st.length;vals.push(val)}let min=Math.min(...vals),max=Math.max(...vals);for(const [id,el] of Object.entries(stateNodes)){if(areaMetric==='none'){el.setAttribute('fill','#153044');el.setAttribute('fill-opacity','.075')}else{let s=DATA.states[id],v=areaMetric==='elec'?100*s.elec_len/s.length:areaMetric==='high'?s.highspeed_len:s.length,t=(v-min)/(max-min||1);el.setAttribute('fill',`rgb(${22+Math.floor(t*58)},${42+Math.floor(t*103)},${68+Math.floor(t*104)})`);el.setAttribute('fill-opacity','.22')}el.classList.toggle('sel',(selected!==null&&DATA.routes[selected][8].includes(id))||selectedRegion===id)}}
function kv(label,value){const d=document.createElement('div');d.className='kv';const a=document.createElement('span'),b=document.createElement('b');a.textContent=label;b.textContent=value;d.append(a,b);$('#kvlist').appendChild(d)}
function showDetails(){if(showStationDetail())return;let r=selected===null?null:DATA.routes[selected];$('#kvlist').replaceChildren();opsPane.replaceChildren();opsPane.style.display='block';
 if(!r&&selectedRegion){const s=DATA.states[selectedRegion];$('#detailTitle').textContent=s.name+' · 基础设施';$('#detailSub').textContent=selectedRegion+' · DB InfraGO 官方线段及设施统计';$('#bigNum').textContent=km(s.length);$('#bigCaption').textContent='州内轨道方向线段长度累计，不是去重营业里程';$('#aVal').textContent=count(s.segments);$('#aLab').textContent='州内原始分段记录';$('#bVal').textContent=share(s.elec_len,s.length);$('#bLab').textContent='电气化累计长度占比';kv('高速≥200 km/h 累计',km(s.highspeed_len));kv('双线属性累计',km(s.double_len));kv('单线属性累计',km(s.single_len));kv('隧道记录',count(s.tunnels));kv('铁路桥记录',count(s.bridges));kv('道口记录',count(s.crossings));kv('运营点记录',count(s.ops));opsPane.innerHTML='<div class="sub">本页州级数字是原始记录汇总，不等于铁路故障或准点表现。</div>';return}
 if(!r){$('#detailTitle').textContent='德国铁路网 · 官方底图';$('#detailSub').textContent='基于 DB InfraGO 提供的轨道分段数据';$('#bigNum').textContent=count(DATA.qa.route_ids_in_germany);$('#bigCaption').textContent='16州境内出现的线路编号数量';$('#aVal').textContent=count(DATA.summary.segments);$('#aLab').textContent='境内原始记录条数';$('#bVal').textContent=count(DATA.qa.source_line_geometries);$('#bLab').textContent='独立几何部件数';kv('轨道方向分段累计',km(DATA.summary.length));kv('其中：线路轴线记录',km(DATA.qa.direction_length_km['Streckenachse']));kv('其中：正向轨道记录',km(DATA.qa.direction_length_km['Richtungsgleis']));kv('其中：反向轨道记录',km(DATA.qa.direction_length_km['Gegenrichtungsgleis']));kv('电气化累计占比',share(DATA.summary.elec_len,DATA.summary.length));kv('高速（≥200 km/h）线段累计',km(DATA.summary.highspeed_len));kv('已扫描省州',Object.keys(DATA.states).length+' 个');kv('未显示的跨境原始记录',Object.values(DATA.qa.excluded_foreign).reduce((a,b)=>a+b,0)+' 条');opsPane.innerHTML='<div class="sub">选中某条线路后显示对应官方站场/停靠点记录。</div>';return}
 const [id,name,cn,length,n,elec,high,unknown,states,bbox,dir,geom,ops,dbl,single]=r;
 $('#detailTitle').textContent=cn||name;$('#detailSub').textContent='官方 Streckennummer '+id+' · '+name;$('#bigNum').textContent='#'+id;$('#bigCaption').textContent='DB InfraGO 官方线路编号';$('#aVal').textContent=count(n);$('#aLab').textContent='原始线路分段条数';$('#bVal').textContent=count(geom);$('#bLab').textContent='可绘制几何部件数';
 kv('累计线段长度（未去重）',km(length));kv('电气化累计比例',share(elec,length));kv('最高速等级≥200累计',km(high));kv('未知速度记录长度',km(unknown));kv('双线属性累计',km(dbl));kv('单线属性累计',km(single));for(const [dn,dv] of Object.entries(dir))kv(dn,km(dv));kv('覆盖联邦州',states.map(id=>stateNameMap[id]||id).join('、'));
 if(ops.length===0){opsPane.innerHTML='<div class="sub">此线路没有可显示的匹配运营点记录。</div>'}else{for(const [name,typ] of ops.slice(0,18)){const x=document.createElement('div');x.className='stop';const m=document.createElement('em');m.textContent=typ; x.append(m,document.createTextNode(name));opsPane.appendChild(x)}if(ops.length>18){let t=document.createElement('div');t.className='sub';t.textContent='其余站点未在侧栏全部展开';opsPane.appendChild(t)}}
}
function updateStops(){stopsEl.replaceChildren();if(selected===null){$('#selectedStops').replaceChildren();return}const ops=DATA.routes[selected][12],g=$('#selectedStops');g.replaceChildren();for(const [name,typ,x,y] of ops.filter(v=>v[1]==='Bf').slice(0,50)){make('circle',{cx:x,cy:y,r:2.0,'class':'station-dot'},g)}}
function applyCam(){world.style.transform=`translate(${tx}px,${ty}px) scale(${viewScale})`}
const vp=$('#viewport'),world=$('#world');
function fit(){let w=vp.clientWidth,h=vp.clientHeight;viewScale=Math.min(w/800,h/1000)*.93;viewScale=Math.max(.4,viewScale);tx=w/2-395*viewScale;ty=h/2-505*viewScale;applyCam()}
function focusRoute(index){const r=DATA.routes[index],b=r[9];if(b[0]>b[2])return;const w=vp.clientWidth,h=vp.clientHeight;let bw=Math.max(45,b[2]-b[0]),bh=Math.max(45,b[3]-b[1]);viewScale=Math.min(5.2,Math.max(.65,Math.min(w/(bw+100),h/(bh+170))*.84));tx=w/2-(b[0]+b[2])/2*viewScale;ty=h/2-(b[1]+b[3])/2*viewScale;applyCam()}
function selectRoute(idx,zoom=true){selectedStation=null;updatePerf();selected=idx;selectedRegion=null;let r=DATA.routes[idx];$('#search').value=(r[2]||r[1])+' · '+r[0];$('#results').classList.remove('show');$('#resultStatus').textContent=`已选择官方线路 #${r[0]}，共 ${r[11].toLocaleString('zh-CN')} 个几何部件`;redraw();showDetails();updateStops();setArea();if(zoom)focusRoute(idx)}
function clearRoute(){selectedStation=null;updatePerf();selected=null;selectedRegion=null;$('#search').value='';$('#results').classList.remove('show');redraw();showDetails();updateStops();setArea();fit()}
const indexById=new Map(DATA.routes.map((r,i)=>[r[0],i]));
function search(q){q=q.trim().toLowerCase();if(!q)return[];let hits=[];for(let i=0;i<DATA.routes.length;i++){let r=DATA.routes[i],name=(r[0]+' '+r[1]+' '+r[2]).toLowerCase();if(name.includes(q))hits.push(i)}hits.sort((a,b)=>DATA.routes[a][0]===q?-1:DATA.routes[b][0]===q?1:DATA.routes[b][11]-DATA.routes[a][11]);return hits.slice(0,14)}
function drawResults(ids){let box=$('#results');box.replaceChildren();if(!ids.length){const x=document.createElement('div');x.className='result-empty';x.textContent='没有匹配的官方线路编号或名称';box.appendChild(x)}for(const i of ids){let r=DATA.routes[i],b=document.createElement('button'),top=document.createElement('b'),sub=document.createElement('span');top.textContent='#'+r[0]+' '+(r[2]||r[1]);sub.textContent=r[1]+' · '+r[11]+'段几何';b.append(top,sub);b.onclick=()=>selectRoute(i);box.appendChild(b)}box.classList.add('show')}
$('#search').addEventListener('input',e=>{let q=e.target.value;if(!q.trim()){$('#results').classList.remove('show');return}drawResults(search(q))});$('#search').addEventListener('keydown',e=>{if(e.key==='Enter'){const ids=search(e.target.value);if(ids.length){selectRoute(ids[0]);e.preventDefault()}}else if(e.key==='Escape')$('#results').classList.remove('show')});
$$('.presets button').forEach(b=>b.onclick=()=>{const i=indexById.get(b.dataset.route);if(i!==undefined)selectRoute(i)});
$$('#layers button').forEach(b=>b.onclick=()=>{style=b.dataset.style;$$('#layers button').forEach(q=>q.classList.toggle('active',q===b));renderLegend();redraw()});
$('#onlyRoute').onchange=redraw;$('#areaMetric').onchange=e=>{areaMetric=e.target.value;setArea()};$('#showStates').onchange=e=>stateNames.style.display=e.target.checked?'':'none';$('#showHubs').onchange=e=>hubEl.style.display=e.target.checked?'':'none';
function zoom(f,cx,cy){let s=Math.max(.48,Math.min(6.3,viewScale*f));let wx=(cx-tx)/viewScale,wy=(cy-ty)/viewScale;tx=cx-wx*s;ty=cy-wy*s;viewScale=s;applyCam()}
$('#zoomIn').onclick=()=>zoom(1.22,vp.clientWidth/2,vp.clientHeight/2);$('#zoomOut').onclick=()=>zoom(1/1.22,vp.clientWidth/2,vp.clientHeight/2);$('#reset').onclick=clearRoute;
vp.addEventListener('wheel',e=>{e.preventDefault();const rect=vp.getBoundingClientRect();zoom(e.deltaY<0?1.13:1/1.13,e.clientX-rect.left,e.clientY-rect.top)},{passive:false});
let drag=null;vp.addEventListener('pointerdown',e=>{if(e.button!==0)return;if(perfView==='links' && e.target.closest && e.target.closest('#verifiedLinkGeometry'))return;drag={x:e.clientX,y:e.clientY,tx,ty,moved:false};vp.setPointerCapture(e.pointerId)});vp.addEventListener('pointermove',e=>{if(!drag)return;let dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.hypot(dx,dy)>4){drag.moved=true;vp.classList.add('dragging')}if(drag.moved){tx=drag.tx+dx;ty=drag.ty+dy;applyCam()}});
function pointInRing(x,y,ring){let inside=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){let a=ring[i],b=ring[j];if(((a[1]>y)!=(b[1]>y))&&(x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]))inside=!inside}return inside}
function findRegion(x,y){for(const [id,poly] of Object.entries(statePolys))for(const ring of poly)if(pointInRing(x,y,ring))return id;return null}
function hit(x,y){const bx=Math.floor(x/CELL),by=Math.floor(y/CELL),threshold=5/viewScale,limit=threshold*threshold;let dBest=limit,rBest=null,seen=new Set();for(let gx=bx-1;gx<=bx+1;gx++)for(let gy=by-1;gy<=by+1;gy++){let list=grids.get(gx+','+gy)||[];for(const s of list){const [rid,x1,y1,x2,y2]=s,dx=x2-x1,dy=y2-y1,m=dx*dx+dy*dy,t=m?Math.max(0,Math.min(1,((x-x1)*dx+(y-y1)*dy)/m)):0,dist=(x-x1-t*dx)**2+(y-y1-t*dy)**2;if(dist<dBest){dBest=dist;rBest=rid}}}return rBest}
vp.addEventListener('pointerup',e=>{if(!drag)return;const moved=drag.moved;drag=null;vp.classList.remove('dragging');if(moved)return;const rect=vp.getBoundingClientRect();let x=(e.clientX-rect.left-tx)/viewScale,y=(e.clientY-rect.top-ty)/viewScale;const si=hitStation(x,y);if(si!==null){selectStation(si,false);return}let idx=hit(x,y);if(idx!==null){selectRoute(idx,false)}else{let region=findRegion(x,y);if(region){selectedStation=null;updatePerf();selected=null;selectedRegion=region;$('#search').value='';redraw();showDetails();updateStops();setArea()}}});vp.addEventListener('pointercancel',()=>{drag=null;vp.classList.remove('dragging')});
window.addEventListener('resize',()=>{if(selected===null)fit()});
$$('#perfView button').forEach(b=>b.onclick=()=>{perfView=b.dataset.view;$$('#perfView button').forEach(x=>x.classList.toggle('active',x===b));if(perfView==='infra')selectedStation=null;updatePerf();showDetails()});
$('#perfType').onchange=e=>{perfType=e.target.value;selectedStation=null;updatePerf();showDetails()};
$('#perfMetric').onchange=e=>{perfMetric=e.target.value;updatePerf();showDetails()};
$('#minSample').onchange=e=>{minObservations=+e.target.value;selectedStation=null;updatePerf();showDetails()};
// v07: derived train-number aggregates and validated optional stop-pair records.

let trainSelection=null,chainSelection=null,trainSort='volume',chainData=V14_HLB_EVIDENCE,chainMetric='ontime6';
const linkLayer=$('#verifiedLinkGeometry');
const trainProfiles=TRAIN_PROFILES.records.map((row,i)=>({i,name:row[0]+' '+row[1],delay:row[2],cancel:row[3],n:row[4]}));
function metricSample(leg){
 if(chainMetric==='drift')return leg.valid_delay_pairs||0;
 const a=leg.v11||{};const t=$('#linkTrainType')?.value||'ALL';const x=(['ALL','RE','RB','HLB','BRB','ERB','NWB','OE'].includes(t))?a:(a.by_type||{})[t]||{};
 return chainMetric==='boundary'?(x.pairs||0):(x.arrival_valid||0);
}
function metricValue(leg){
 if(chainMetric==='drift')return leg.delay_drift_mean_min;
 const a=leg.v11||{};const t=$('#linkTrainType')?.value||'ALL';const x=(['ALL','RE','RB','HLB','BRB','ERB','NWB','OE'].includes(t))?a:(a.by_type||{})[t]||{};
 if(chainMetric==='boundary')return x.pairs?100*(x.boundary_cancel||0)/x.pairs:null;
 if(!x.arrival_valid)return null;
 return chainMetric==='late15'?100*(x.late15||0)/x.arrival_valid:100*(x.arrival_valid-(x.late6||0))/x.arrival_valid;
}
function metricLabel(){return {ontime6:'到站晚点不足6分钟的观测比例',late15:'到站晚点至少15分钟的观测比例',boundary:'到发停靠取消标记涉及比例（非整趟取消率）',drift:'下游到站与上游出站的晚点差值'}[chainMetric]}
function chainColor(leg){const v=metricValue(leg);if(v===null||!Number.isFinite(v))return '#637386';
 if(chainMetric==='ontime6')return v<40?'#d65a71':v<55?'#ee9375':v<70?'#efc36e':v<85?'#b7d48c':'#6bc6b1';
 if(chainMetric==='late15')return v<10?'#6bc6b1':v<20?'#b7d48c':v<30?'#efc36e':v<45?'#ee9375':'#d65a71';
 if(chainMetric==='boundary')return v<2?'#6bc6b1':v<5?'#e8c979':v<12?'#ee9375':'#d65a71';
 return v<0?'#7bd2ba':v<4?'#a6ce9a':v<10?'#eec779':v<20?'#e8936e':'#d65a71';
}
function labelForLeg(leg){const hint=['RE','RB','HLB','BRB','ERB','NWB','OE'].includes($('#linkTrainType').value)&&leg.label_hints?.length?leg.label_hints[0][0]+' · ':'';return hint+leg.from_station+' → '+leg.to_station}
function metricForLeg(leg){const v=metricValue(leg);return v===null||!Number.isFinite(v)?'无足够数据':chainMetric==='drift'?(v>0?'+':'')+v.toFixed(1)+'分':v.toFixed(1)+'%'}
function minLinkPairs(){return Number($('#linkMinPairs')?.value || 100)}
function eligibleLink(leg){return leg.planned_pairs>=minLinkPairs() && metricSample(leg)>=minLinkPairs() && metricValue(leg)!==null}
function refreshLinkLegend(){
 const box=$('#linkLegend');if(!box)return;
 const items=chainMetric==='ontime6'?[['<40%','#d65a71'],['40–54.9%','#ee9375'],['55–69.9%','#efc36e'],['70–84.9%','#b7d48c'],['≥85%','#6bc6b1']]:chainMetric==='late15'?[['<10%','#6bc6b1'],['10–19.9%','#b7d48c'],['20–29.9%','#efc36e'],['30–44.9%','#ee9375'],['≥45%','#d65a71']]:chainMetric==='boundary'?[['<2%','#6bc6b1'],['2–4.9%','#e8c979'],['5–11.9%','#ee9375'],['≥12%','#d65a71']]:[['改善','#7bd2ba'],['0–3.9分','#a6ce9a'],['4–9.9分','#eec779'],['10–19.9分','#e8936e'],['≥20分','#d65a71']];
 box.innerHTML=items.map(([l,c])=>'<span><i style="background:'+c+'"></i>'+l+'</span>').join('');
}
function renderLinks(){
  linkLayer.replaceChildren();
  if(perfView!=='links'||!chainData)return;
  const threshold=minLinkPairs(),frag=document.createDocumentFragment();
  for(let i=0;i<chainData.links.length;i++){
    const leg=chainData.links[i];
    if(!eligibleLink(leg)||!Array.isArray(leg.geometry))continue;
    const parts=[];
    for(const geometry of leg.geometry){
      if(!Array.isArray(geometry)||geometry.length<2)continue;
      let d='';
      for(let j=0;j<geometry.length;j++){
        const p=P(geometry[j]);if(!Number.isFinite(p[0])||!Number.isFinite(p[1])){d='';break}
        d+=(j?'L':'M')+p[0].toFixed(2)+' '+p[1].toFixed(2)+' ';
      }
      if(d)parts.push(d);
    }
    if(parts.length){
      const node=make('path',{d:parts.join(' '),'class':'chain-link'+(chainSelection===i?' highlight':''),stroke:chainColor(leg)},frag);
      const selectLeg=(ev)=>{ev.stopPropagation();chainSelection=i;trainSelection=null;selectedStation=null;selected=null;selectedRegion=null;renderLinks();showDetails();renderChainRanks();};
      node.addEventListener('click',selectLeg);const hit=make('path',{d:parts.join(' '),fill:'none',stroke:'transparent','stroke-width':12,'vector-effect':'non-scaling-stroke',style:'pointer-events:stroke;cursor:pointer'},frag);hit.addEventListener('click',selectLeg);
      const title=make('title',{},node);title.textContent=labelForLeg(leg)+' · '+metricForLeg(leg)+' · '+count(metricSample(leg))+'有效指标样本';
    }
  }
  linkLayer.appendChild(frag);
}
function showTrainDetail(){if(trainSelection===null)return false;
 const t=trainProfiles[trainSelection];$('#kvlist').replaceChildren();opsPane.replaceChildren();
 $('#detailTitle').textContent=t.name+' · 历史车次';$('#detailSub').textContent='2026年8—9月 · Deutsche Bahn Data · 实测列车编号聚合';
 $('#bigNum').textContent=t.delay.toFixed(1)+' 分';$('#bigCaption').textContent='该车次编号的历史平均晚点，不是逐段准点率';
 $('#aVal').textContent=count(t.n);$('#aLab').textContent='有效晚点停靠记录数';
 $('#bVal').textContent=t.cancel.toFixed(2)+'%';$('#bLab').textContent='同车次停靠取消记录比例';
 kv('ICE / IC 车次号',t.name);kv('平均晚点',t.delay.toFixed(2)+'分钟');kv('停靠取消记录比例',t.cancel.toFixed(2)+'%');kv('统计时间','2026年8—9月');
 kv('路线 / 轨道匹配','未获得逐车次完整停站链');
 opsPane.innerHTML='<div class="note"><b>与线路编号分离</b><br>ICE 车次号不是 DB InfraGO 的 Streckennummer，同一车次在不同日期也可能改道。来源车次表中的“Anzahl Fahrten”实际为有效晚点停靠记录数；取消比例为停靠记录口径。当前仅展示来源报告的聚合值，不把该车次随意画到真实轨道上。下载逐停靠历史数据并转换后，方可核查实际经过哪些相邻车站。</div>';
 return true}
function showChainDetail(){if(chainSelection===null||!chainData)return false;
 const c=chainData.links[chainSelection];if(!c)return false;$('#kvlist').replaceChildren();opsPane.replaceChildren();
 const typ=$('#linkTrainType').value,regional=['RE','RB','HLB','BRB','ERB','NWB','OE'].includes(typ);const v=c.v11||{};const a=(typ==='ALL'||regional)?v:(v.by_type||{})[typ]||{};
 $('#detailTitle').textContent=labelForLeg(c);$('#detailSub').textContent='2026年9月 · 官方 DB InfraGO 轨道编号 / 公里标匹配 · '+(regional?typ+' 区域列车':typ==='ALL'?'全部长途':typ);
 $('#bigNum').textContent=metricForLeg(c);$('#bigCaption').textContent=metricLabel();
 $('#aVal').textContent=count(c.planned_pairs);$('#aLab').textContent='计划相邻停站配对数';
 $('#bVal').textContent=count(metricSample(c));$('#bLab').textContent='当前指标有效样本数';
 kv('官方基础设施编号（不是运营线路标签）',c.route);kv('公里标范围',c.km_range.map(x=>x.toFixed(2)).join(' — ')+' km');
 if(regional){kv(typ+'运营线路标签（可能跨州重名）',c.label_hints?.map(x=>x[0]+' ('+count(x[1])+')').join('，')||'无');}
 kv('边界取消标记（非整趟取消）',count(a.boundary_cancel||0)+' / '+count(a.pairs||0));
 kv('有效下游到站时间',count(a.arrival_valid||0));kv('到站晚点不足6分钟',count(Math.max(0,(a.arrival_valid||0)-(a.late6||0))));
 kv('到站晚点≥15分钟',count(a.late15||0));kv('到站晚点≥30分钟',count(a.late30||0));
 kv('平均晚点变化',c.delay_drift_mean_min==null?'样本不足':c.delay_drift_mean_min.toFixed(2)+'分钟');
 kv('途中终止运行证据','未核实（不能由取消标记推断）');
 opsPane.innerHTML='<div class="note"><b>正确理解这条彩色区间</b><br>统计对象是已识别的地区运营品牌、RB、RE 或长途列车按时刻表连续相邻停站，在下游站的到站时间观测；API变更时间可能是预估。所绘制曲线来自该线路的官方基础设施 WGS84 几何和公里标，但不是逐车实际运行轨迹。无法证明晚点归因于这段轨道，也不能从停靠取消标记判断列车中途抛下乘客。</div>';
 return true}
function renderTrainRankings(){let q=$('#trainSearch').value.toUpperCase().replace(/\s+/g,' ').trim();let arr=trainProfiles.filter(p=>p.name.toUpperCase().includes(q));
 arr.sort(trainSort==='volume'?(a,b)=>b.n-a.n:trainSort==='delay'?(a,b)=>b.delay-a.delay:(a,b)=>b.cancel-a.cancel);
 const box=$('#trainRankings');box.replaceChildren();for(const p of arr.slice(0,9)){
  const b=document.createElement('button'),name=document.createElement('span'),value=document.createElement('b');name.textContent=p.name+' · '+count(p.n)+'条';
  value.textContent=trainSort==='cancel'?p.cancel.toFixed(1)+'%':p.delay.toFixed(1)+'分';b.append(name,value);b.onclick=()=>{
   trainSelection=p.i;chainSelection=null;selectedStation=null;selected=null;selectedRegion=null;$('#search').value='';
   updatePerf();renderLinks();redraw();showDetails();updateStops();setArea()};box.appendChild(b)}
 const footer=document.createElement('div');footer.className='train-meta';footer.textContent=`精选 ${arr.length} 个车次档案 · 来源包含 ${trainProfiles.length} 条车次编号聚合统计`;box.appendChild(footer)}
function renderChainRanks(){const box=$('#chainRanks');box.replaceChildren();if(!chainData)return;
 const sort=$('#linkRankMode')?.value||'worst';
 const list=chainData.links.map((leg,idx)=>({leg,idx})).filter(x=>eligibleLink(x.leg));
 list.sort(sort==='volume'?(a,b)=>metricSample(b.leg)-metricSample(a.leg):(a,b)=>
 chainMetric==='ontime6'?metricValue(a.leg)-metricValue(b.leg):metricValue(b.leg)-metricValue(a.leg));
 for(const item of list.slice(0,9)){const c=item.leg,b=document.createElement('button'),name=document.createElement('span'),value=document.createElement('b');
  name.textContent=labelForLeg(c)+' · '+count(metricSample(c))+'条';value.textContent=metricForLeg(c);
  b.append(name,value);b.onclick=()=>{chainSelection=item.idx;trainSelection=null;selectedStation=null;selected=null;selectedRegion=null;
   $('#perfView [data-view="links"]').click();renderLinks();showDetails();redraw();setArea();
   if(c.geometry?.length){let coords=c.geometry.flat();let arr=coords.map(p=>P(p));let minx=Math.min(...arr.map(x=>x[0])),maxx=Math.max(...arr.map(x=>x[0])),miny=Math.min(...arr.map(x=>x[1])),maxy=Math.max(...arr.map(x=>x[1]));if(Number.isFinite(minx)&&Number.isFinite(miny)){let s=Math.min(5,Math.max(.7,Math.min(vp.clientWidth/Math.max(100,maxx-minx+120),vp.clientHeight/Math.max(100,maxy-miny+170))));viewScale=s;tx=vp.clientWidth/2-(minx+maxx)/2*s;ty=vp.clientHeight/2-(miny+maxy)/2*s;applyCam()}}};box.appendChild(b)}
}
function chainSummary(){const e=$('#chainInfo');if(!chainData){e.textContent='未加载区间数据';return}
 const regional=['RE','RB','HLB','BRB','ERB','NWB','OE'].includes($('#linkTrainType').value),shown=chainData.links.filter(eligibleLink).length;
 const accessible=chainData.links.filter(c=>c.planned_pairs>=minLinkPairs()).length, routes=chainData.qa?.official_routes_covered||0;
 e.innerHTML=`<b>${regional?($('#linkTrainType').value+' 区域铁路'):'长途列车'}：${count(shown)}个区间达到当前指标样本门槛</b>（共 ${count(chainData.links.length)}个拥有官方线形的方向性区间，${count(routes)}个独立基础设施线路编号 / 全国1,546个编号）。<br>计划配对和当前指标有效样本均须达到 ${count(minLinkPairs())} 次。<b>没上色不代表准点。</b>`;
 refreshLinkLegend();}
function refreshLinkView(){if(chainSelection!==null&&!eligibleLink(chainData.links[chainSelection]))chainSelection=null;renderLinks();renderChainRanks();chainSummary();showDetails();window.__V09_REFRESH_AUDIT__?.()}
$('#linkMinPairs').addEventListener('change',refreshLinkView);
$('#linkTrainType').addEventListener('change',()=>{chainData=({'HLB':V14_HLB_EVIDENCE,'BRB':V14_BRB_EVIDENCE,'ERB':V14_ERB_EVIDENCE,'NWB':V14_NWB_EVIDENCE,'OE':V14_OE_EVIDENCE,'RB':V13_RB_EVIDENCE,'RE':V12_RE_EVIDENCE})[$('#linkTrainType').value]||V10_SEPTEMBER_EVIDENCE;chainSelection=null;trainSelection=null;selectedStation=null;selected=null;selectedRegion=null;refreshLinkView();});
$('#linkRankMode').addEventListener('change',renderChainRanks);
$('#trainSearch').addEventListener('input',renderTrainRankings);
$$('#trainSort button').forEach(b=>b.onclick=()=>{trainSort=b.dataset.sort;$$('#trainSort button').forEach(x=>x.classList.toggle('active',x===b));renderTrainRankings()});
$('#linkMetric').onchange=e=>{chainMetric=e.target.value;refreshLinkView()};
$('#linkFile').addEventListener('change',async e=>{const f=e.target.files?.[0];if(!f)return;
 try{if(f.size>55*1024*1024)throw Error('单个汇总 JSON 文件超过55MB，请先提高最低样本门槛重新转换。');
  const raw=JSON.parse(await f.text());if(!['bahnmonitor-v07-train-link-v1','bahnmonitor-v10-september-evidence-v1','bahnmonitor-v11-recomputed-arrival-obs'].includes(raw.schema)||!Array.isArray(raw.links)||!raw.qa)throw Error('数据格式不匹配：需要已核验的区间 JSON。');
  const good=raw.links.filter(x=>Array.isArray(x.geometry)&&x.geometry.length>0&&x.geometry_status?.startsWith('same_unique'));
  chainData={...raw,links:good};chainSelection=null;trainSelection=null;chainSummary();renderChainRanks();
  $('#perfView [data-view="links"]').click();showDetails();
 }catch(err){$('#chainInfo').textContent='导入失败：'+String(err.message||err)}
});
function showLinkOverview(){
 if(perfView!=='links'||selected!==null||selectedRegion!==null||selectedStation!==null||trainSelection!==null||chainSelection!==null)return false;
 const usable=chainData.links.filter(eligibleLink);let den=0,nom=0;
 for(const leg of usable){const v=metricValue(leg);const n=metricSample(leg);if(v!==null&&Number.isFinite(v)){den+=n;nom+=v*n}}
 $('#kvlist').replaceChildren();opsPane.replaceChildren();
 const regional=['RE','RB','HLB','BRB','ERB','NWB','OE'].includes($('#linkTrainType').value);
 $('#detailTitle').textContent='本月区间观测 · '+(regional?$('#linkTrainType').value+' 区域列车':'长途列车');
 $('#detailSub').textContent='2026年9月 · 仅对官方地理匹配且达到观测门槛的区间进行汇总';
 $('#bigNum').textContent=den?(chainMetric==='drift'?(nom/den).toFixed(1)+'分':(nom/den).toFixed(1)+'%'):'—';
 $('#bigCaption').textContent=metricLabel()+' · 当前上色区间加权观察值（非全国总体）';
 $('#aVal').textContent=count(usable.length);$('#aLab').textContent='当前可视区间数';
 $('#bVal').textContent=count(den);$('#bLab').textContent='有效站间指标样本累计';
 kv('拥有官方轨道几何的区间',count(chainData.links.length));
 kv('涉及官方基础设施编号',count(chainData.qa?.official_routes_covered||0)+' / 1,546');
 kv('选择车次类别',regional?$('#linkTrainType').value:'长途（'+$('#linkTrainType').value+'）');
 kv('统计性质','按相邻停站配对 · 无法归因为特定路轨故障');
 opsPane.innerHTML='<div class="note"><b>未上色 ≠ 表现良好</b><br>只有能核验官方路线编号及公里标、同时有足量观测的区间才被着色。不同列车类型的线路布局和停靠频率不同，不能只看地图红线多少评判 RE 与 ICE 谁更差；参见左侧全月停站同口径比较。到站时间包括可能的预估值，停靠取消标记也不等于整趟列车取消。</div>';
 return true}
const originalShowDetails=showDetails;
showDetails=function(){if(showTrainDetail())return;if(showChainDetail())return;if(showLinkOverview())return;originalShowDetails()};
const originalSelectRoute=selectRoute;
selectRoute=function(idx,zoom=true){trainSelection=null;chainSelection=null;originalSelectRoute(idx,zoom);renderLinks()};
const originalSelectStation=selectStation;
selectStation=function(i,focus=false){trainSelection=null;chainSelection=null;originalSelectStation(i,focus);renderLinks()};
const originalClearRoute=clearRoute;
clearRoute=function(){trainSelection=null;chainSelection=null;originalClearRoute();renderLinks()};
// Chain view only reveals actual imported, verified geometry, never train-number guesses.
const refreshChainView=()=>{renderLinks();chainSummary();$('#chainSection').style.borderColor=perfView==='links'?'#52798d':''};
$$('#perfView button').forEach(b=>b.addEventListener('click',()=>{requestAnimationFrame(refreshChainView)}));
renderTrainRankings();chainSummary();refreshLinkLegend();
$('#perfView [data-view="links"]').click();renderLinks();renderChainRanks();

renderLegend();setArea();redraw();updatePerf();showDetails();fit();
window.__V14_READY__=true;window.__V14_DATASETS__={HLB:518,BRB:251,ERB:240,NWB:231,OE:320};window.__V13_READY__=true;window.__V13_RB_LINKS__=V13_RB_EVIDENCE.links.length;window.__V12_READY__=true;window.__V12_RE_LINKS__=V12_RE_EVIDENCE.links.length;window.__V11_READY__=true;window.__V11_VALID_ARRIVAL__=V10_SEPTEMBER_EVIDENCE.qa.v11_recomputation.arrival_valid_sum;window.__V10_READY__=true;window.__V10_LINKS__=V10_SEPTEMBER_EVIDENCE.links.length;window.__V07_READY__=true;window.__V07_PROFILE_COUNT__=trainProfiles.length;window.__ATLAS_READY__=true;window.__ATLAS_STATS__={routes:DATA.routes.length,lines:lineCount,states:Object.keys(stateNodes).length,stationObservations:obsStations.length,visible:obsStations.filter(s=>currentObs(s)).length};
