/* Railway 07 observation maths and corridor grouping (no UI or network).
   Rates are always computed from counts, never averaged percentages. */
(()=>{
'use strict';
const {actualBounds}=window.Railway07Geometry;

function mergeObserved(groupData){
 const byKey=new Map();
 for(const [kind,data] of groupData){
  for(const leg of data.links||[]){
   const range=leg.km_range||[];
   const key=[leg.route,leg.from_station,leg.to_station,
    range.map(x=>Number(x).toFixed(2)).join(':')].join('|');
   let dest=byKey.get(key);
   if(!dest){
    dest={...leg,v11:{pairs:0,arrival_valid:0,late6:0,late15:0,boundary_cancel:0},
      brands:[],label_hints:leg.label_hints||[]};
    byKey.set(key,dest);
   }
   const a=leg.v11||{};
   for(const field of ['pairs','arrival_valid','late6','late15','boundary_cancel'])
    dest.v11[field]+=Number(a[field]||0);
   if(!dest.brands.includes(kind))dest.brands.push(kind);
  }
 }
 return [...byKey.values()];
}
function metrics(leg,metric,minimum=100){
 const a=leg.v11||{},nArrival=Number(a.arrival_valid||0),nPlanned=Number(a.pairs||0);
 const late=nArrival?100*Number(a.late6||0)/nArrival:null;
 const cancel=nPlanned?100*Number(a.boundary_cancel||0)/nPlanned:null;
 const enough=metric==='both'?nArrival>=minimum&&nPlanned>=minimum:
  metric==='late'?nArrival>=minimum:nPlanned>=minimum;
 return {late,cancel,nArrival,nPlanned,sufficient:enough};
}
function grade(m,metric){
 if(metric==='late')return m.late>=40?2:m.late>=25?1:0;
 if(metric==='cancel')return m.cancel>=8?2:m.cancel>=4?1:0;
 return m.late>=40||m.cancel>=8?2:m.late>=25||m.cancel>=4?1:0;
}
function attention(m,metric){
 const a=(m.late??0)/40,b=(m.cancel??0)/8;
 return metric==='late'?a:metric==='cancel'?b:Math.max(a,b);
}

// Build straight-through, same-colour directional runs only.  Branches,
// grade changes and gaps stay separate: no fabricated line continuity.
function canJoin(a,b){
 if(a===b||a.leg.route!==b.leg.route||a.grade!==b.grade)return false;
 if(a.leg.to_station!==b.leg.from_station)return false;
 const x=a.leg.km_range,y=b.leg.km_range;
 if(!Array.isArray(x)||!Array.isArray(y)||x.length!==2||y.length!==2)return false;
 if(![...x,...y].every(Number.isFinite))return false;
 const loX=Math.min(...x),hiX=Math.max(...x),loY=Math.min(...y),hiY=Math.max(...y);
 // Prevent chaining the same km interval in opposite directions.
 if(Math.min(hiX,hiY)-Math.max(loX,loY)>.15)return false;
 return Math.min(...x.flatMap(v=>y.map(w=>Math.abs(v-w))))<=.15;
}
function buildCorridors(items){
 const outgoing=new Map(),incoming=new Map();
 const key=(o,station)=>o.leg.route+'|'+o.grade+'|'+station;
 for(const o of items){
  const a=key(o,o.leg.from_station),b=key(o,o.leg.to_station);
  if(!outgoing.has(a))outgoing.set(a,[]);
  if(!incoming.has(b))incoming.set(b,[]);
  outgoing.get(a).push(o);incoming.get(b).push(o);
 }
 const next=new Map(),prev=new Map();
 for(const o of items){
  const tails=(outgoing.get(key(o,o.leg.to_station))||[]).filter(q=>canJoin(o,q));
  if(tails.length!==1)continue;
  const q=tails[0];
  const heads=(incoming.get(key(q,q.leg.from_station))||[]).filter(p=>canJoin(p,q));
  if(heads.length===1){next.set(o,q);prev.set(q,o);}
 }
 const seen=new Set(),groups=[];
 for(const o of items){
  if(seen.has(o))continue;
  let first=o,walked=new Set();
  while(prev.has(first)&&!walked.has(first)){
   walked.add(first);first=prev.get(first);
  }
  const members=[];
  let cursor=first;
  while(cursor&&!seen.has(cursor)){
   seen.add(cursor);members.push(cursor);cursor=next.get(cursor);
  }
  if(!members.length)continue;
  const nArrival=members.reduce((n,x)=>n+x.m.nArrival,0);
  const nPlanned=members.reduce((n,x)=>n+x.m.nPlanned,0);
  const lateCount=members.reduce((n,x)=>n+Number(x.leg.v11?.late6||0),0);
  const cancelledCount=members.reduce((n,x)=>n+Number(x.leg.v11?.boundary_cancel||0),0);
  const late=nArrival?100*lateCount/nArrival:null;
  const cancel=nPlanned?100*cancelledCount/nPlanned:null;
  const parts=members.flatMap(x=>x.parts);
  const group={members,parts,bounds:actualBounds(parts),grade:o.grade,
   m:{late,onTime:late===null?null:100-late,cancel,nArrival,nPlanned}};
  for(const x of members)x.group=group;
  groups.push(group);
 }
 return groups;
}

window.Railway07Analysis=Object.freeze({
 mergeObserved,metrics,grade,attention,canJoin,buildCorridors
});
})();
