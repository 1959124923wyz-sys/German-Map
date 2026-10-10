/* Public railway city-to-city overview.
 * Group real passenger stop observations along one named train service into
 * corridors between hubs, major cities or genuine branch terminals.
 * The 33,547 official infrastructure parts stay in the research model but
 * must NOT become stray green routes on this public map.
 * Never create geometry or impute observations. All percentages use counts.
 */
(()=>{
'use strict';
const {actualBounds}=window.Railway07Geometry;
const {grade}=window.Railway07Analysis;
const {dominantLabel}=window.Railway07ServiceGroups;
// Names supplement the shared official German place-name dictionary. Values
// are station/city names, not manually invented paths.
const HUBS=[
 'Erfurt','Jena','Gera','Weimar','Arnstadt','Ilmenau','Saalfeld','Rudolstadt',
 'Coburg','Suhl','Meiningen','Eisenach','Gotha','Apolda','Naumburg','Nordhausen',
 'Zwickau','Plauen','Altenburg','Döbeln','Riesa','Pirna','Hoyerswerda',
 'Cottbus','Frankfurt (Oder)','Eberswalde','Oranienburg','Bernau','Nauen',
 'Falkensee','Wustermark','Brandenburg','Luckenwalde','Ludwigsfelde',
 'Wittenberge','Neuruppin','Rathenow','Senftenberg','Elsterwerda','Fürstenwalde',
 'Görlitz','Bautzen','Dessau','Halberstadt','Stendal','Bitterfeld',
 'Hildburghausen','Lichtenfels','Forchheim','Bayreuth','Hof','Kulmbach',
 'Bamberg','Erlangen','Fürth','Ansbach','Schweinfurt','Aschaffenburg',
 'Würzburg','Regensburg','Passau','Landshut','Ingolstadt','Augsburg',
 'Memmingen','Kempten','Rosenheim','Traunstein','Freilassing',
 'Ulm','Heilbronn','Offenburg','Pforzheim','Tübingen','Reutlingen',
 'Freiburg','Karlsruhe','Mannheim','Heidelberg','Ludwigshafen',
 'Mainz','Wiesbaden','Darmstadt','Hanau','Fulda','Gießen','Marburg',
 'Koblenz','Bonn','Köln','Düsseldorf','Duisburg','Essen','Dortmund',
 'Wuppertal','Bochum','Hagen','Hamm','Münster','Bielefeld','Paderborn',
 'Osnabrück','Lingen','Oldenburg','Bremen','Bremerhaven','Hamburg',
 'Lübeck','Kiel','Flensburg','Neumünster','Itzehoe','Elmshorn',
 'Hannover','Celle','Hildesheim','Braunschweig','Wolfsburg',
 'Göttingen','Kassel','Magdeburg','Halle','Leipzig','Dresden',
 'Chemnitz','Rostock','Schwerin','Stralsund','Greifswald','Neubrandenburg',
 'Berlin','München','Stuttgart','Nürnberg','Frankfurt am Main','Frankfurt (Main)'
];
const KNOWN=Array.from(new Set([...HUBS,...Object.keys(window.GermanRailStations?.city||{})]))
 .sort((a,b)=>b.length-a.length);
const MAX_EDGES=45, MAX_PATH_KM=115, MIN_VISIBLE_KM=8;
const stationKey=name=>String(name||'').trim().replace(/\s+/g,' ').toLowerCase();
function cityName(raw){
 const name=String(raw||'').trim();
 if(!name)return '';
 for(const city of KNOWN){
  if(name===city||name.startsWith(city+' ')||name.startsWith(city+'-')||
    name.startsWith(city+'('))return city;
 }
 return name.replace(/\s+(?:Hbf|Hauptbahnhof|Bf|Pbf)$/i,'')
   .replace(/\s*\((?:Saale|Thür|Oberfr|Bay|Sachs|Brbg|Westf)\)$/,'');
}
const isHub=name=>{
 const city=cityName(name),full=String(name||'');
 return KNOWN.some(c=>c===city)||/\b(?:Hbf|Hauptbahnhof)\b/.test(full);
};
function legLabel(item){
 const direct=dominantLabel({members:[item]});
 return direct||'DB '+item.leg.route;
}
function keyOf(item,label){
 const leg=item.leg,km=leg.km_range||[];
 const names=[stationKey(leg.from_station),stationKey(leg.to_station)].sort();
 const range=km.length===2?km.map(Number).sort((a,b)=>a-b).map(x=>x.toFixed(2)).join(':'):'?';
 return [label,leg.route,...names,range].join('|');
}
function measuredKm(edge){
 const r=edge.members[0].leg.km_range;
 if(Array.isArray(r)&&r.length===2&&r.every(Number.isFinite))
  return Math.abs(r[1]-r[0]);
 return 0;
}
function summarise(edgeChain,label,metric,from,to){
 const members=edgeChain.flatMap(edge=>edge.members);
 const parts=members.flatMap(item=>item.parts);
 const nArrival=members.reduce((n,x)=>n+x.m.nArrival,0);
 const nPlanned=members.reduce((n,x)=>n+x.m.nPlanned,0);
 const lateCount=members.reduce((n,x)=>n+Number(x.leg.v11?.late6||0),0);
 const cancelCount=members.reduce((n,x)=>n+Number(x.leg.v11?.boundary_cancel||0),0);
 const late=nArrival?100*lateCount/nArrival:null;
 const cancel=nPlanned?100*cancelCount/nPlanned:null;
 const m={nArrival,nPlanned,late,cancel,onTime:late===null?null:100-late};
 const km=edgeChain.reduce((n,e)=>n+measuredKm(e),0);
 return {members,parts,bounds:actualBounds(parts),grade:grade(m,metric),m,
  cityFrom:cityName(from),cityTo:cityName(to),
  startStation:from,endStation:to,serviceName:label,km,
  observedEdges:edgeChain.length,
  coveredEdges:edgeChain,bridgeParts:[],bridges:0};
}
function buildCityCorridors(items,metric='both'){
 const physical=new Map();
 for(const item of items){
  const label=legLabel(item),leg=item.leg;
  if(!leg.from_station||!leg.to_station||
     stationKey(leg.from_station)===stationKey(leg.to_station))continue;
  const id=keyOf(item,label);
  let edge=physical.get(id);
  if(!edge){
   edge={label,a:stationKey(leg.from_station),b:stationKey(leg.to_station),
    aName:leg.from_station,bName:leg.to_station,members:[]};
   physical.set(id,edge);
  }
  edge.members.push(item);
 }
 const byService=new Map();
 for(const edge of physical.values()){
  if(!byService.has(edge.label))byService.set(edge.label,[]);
  byService.get(edge.label).push(edge);
 }
 const corridors=[],byItem=new Map(),covered=new Set();
 for(const [label,edges] of byService){
  const adjacent=new Map(),names=new Map();
  for(const edge of edges){
   for(const [id,name] of [[edge.a,edge.aName],[edge.b,edge.bName]]){
    if(!adjacent.has(id))adjacent.set(id,[]);
    names.set(id,name);adjacent.get(id).push(edge);
   }
  }
  const important=node=>{
   const degree=adjacent.get(node)?.length||0;
   return degree!==2||isHub(names.get(node));
  };
  function trace(start,node){
   const chain=[];let current=node,edge=start,km=0,finish=node;
   while(edge&&!covered.has(edge)&&chain.length<MAX_EDGES){
    covered.add(edge);chain.push(edge);km+=measuredKm(edge);
    const next=edge.a===current?edge.b:edge.a;finish=next;
    if(important(next)||km>=MAX_PATH_KM)break;
    const rest=adjacent.get(next).filter(e=>e!==edge&&!covered.has(e));
    if(rest.length!==1)break;
    current=next;edge=rest[0];
   }
   if(chain.length)return summarise(chain,label,metric,names.get(node),names.get(finish));
   return null;
  }
  // Begin at hubs, termini and junctions; degree-2 stretches become internal
  // stop details rather than hundreds of separately selectable decorations.
  for(const [node] of adjacent){
   if(!important(node))continue;
   for(const edge of adjacent.get(node)){
    if(covered.has(edge))continue;
    const group=trace(edge,node);
    if(group)corridors.push(group);
   }
  }
  // Rare loops with no hub: remain traceable, but never loop indefinitely.
  for(const edge of edges){
   if(covered.has(edge))continue;
   const group=trace(edge,edge.a);
   if(group)corridors.push(group);
  }
 }
 // Main-map display rules: don't clutter the map with little station leads
 // or duplicated same-city local track geometry. Keep all source observations
 // in memory for later analysis.
 const visibleGroups=corridors.filter(g=>g.km>=MIN_VISIBLE_KM ||
   (g.cityFrom!==g.cityTo&&g.km>=3.5&&
     (isHub(g.startStation)||isHub(g.endStation))));
 const visibleSet=new Set(visibleGroups);
 for(const group of corridors)for(const member of group.members){
  if(visibleSet.has(group))byItem.set(member,group);
 }
 return {corridors:visibleGroups,allCorridors:corridors,byItem,
  physicalEdges:physical.size,hidden:corridors.length-visibleGroups.length};
}
window.Railway07Cities=Object.freeze({cityName,isHub,legLabel,buildCityCorridors});
})();