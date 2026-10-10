'use strict';
const fs=require('fs');
const path=require('path');
const root=path.resolve(__dirname,'..');
const load=n=>JSON.parse(fs.readFileSync(path.join(root,'data',n),'utf8'));
const scores=load('state_scores_2025.json');
const evidence=load('condition_evidence.json');
const events=load('events.json');
function assert(p,msg){if(!p)throw Error(msg);}
assert(scores.states.length===16,'must have 16 states');
const ids=new Set(scores.states.map(r=>r.iso));
assert(ids.size===16,'duplicate ISO');
assert(scores.weights.rail_track===.35 && scores.weights.rail_station===.15 && scores.weights.fiber===.3 && scores.weights.power===.2,'pilot weights unexpectedly changed');
function approx(a,b,tol=.0007){return Math.abs(a-b)<tol;}
const ranks=[...scores.states].sort((a,b)=>b.score-a.score);
scores.states.forEach(r=>{
  assert(/^DE-[A-Z]{2}$/.test(r.iso),'invalid ISO '+r.iso);
  assert(approx(r.indicators.rail_track,100-20*(r.rail_track_grade_2025-1)),'rail grade transform '+r.iso);
  assert(approx(r.indicators.rail_station,100-20*(r.rail_station_grade_2025-1)),'station grade '+r.iso);
  assert(approx(r.indicators.fiber,r.fiber_fttbh_pct_2025),'fiber '+r.iso);
  assert(approx(r.indicators.power,100*(1-r.power_saidi_two_year_mean/30)),'power '+r.iso);
  const a=r.indicators,w=scores.weights;
  const computed=a.rail_track*w.rail_track+a.rail_station*w.rail_station+a.fiber*w.fiber+a.power*w.power;
  assert(approx(r.score,computed),'score '+r.iso);
  assert(ranks[r.rank-1].iso===r.iso,'rank '+r.iso);
});
assert(evidence.tli_motorway_2025.states.length===6,'partial TLI data must contain six states');
for(const r of evidence.tli_motorway_2025.states) {
  assert(ids.has(r.iso)&&r.bad>0&&r.total>r.bad,'TLI denominator '+r.iso);
  assert(approx(r.percent,Math.round(1000*r.bad/r.total)/10),'TLI percent '+r.iso);
}
assert(!evidence.tli_motorway_2025.states.some(r=>r.iso==='DE-HH'),'unknown TLI must stay missing');
for(const r of evidence.din_bridge_samples){
  assert(ids.has(r.iso)&&r.bad>=0&&r.bad<=r.total,'DIN count '+r.iso);
  assert(r.inspection==='DIN_1076','must not relabel TLI as DIN');
}
for(const r of evidence.road_state_samples){
  assert(ids.has(r.iso)&&r.year>=2018&&r.value_pct>=0&&r.value_pct<=100,'road metric');
}
assert(events.events.length>=10,'event coverage unexpectedly too small');
const seen=new Set();
for(const e of events.events){
 assert(e.id&&!seen.has(e.id),'duplicate event ID');seen.add(e.id);
 assert(ids.has(e.state_iso),'unknown event state');
 assert(e.event_date<='2026-10-10','future event');
 assert(e.coordinates&&Number.isFinite(e.coordinates.lat)&&Number.isFinite(e.coordinates.lon),'missing coords');
 assert(e.coordinates.lat>=47&&e.coordinates.lat<=56&&e.coordinates.lon>=5&&e.coordinates.lon<=16,'bad approximate locator');
 assert(['locality_approx','facility_approx'].includes(e.coordinates.precision),'location precision missing');
 assert(e.sources.length>0&&e.sources.every(s=>/^https:\/\//.test(s.url)),'source URL missing');
}
const page=fs.readFileSync(path.join(root,'index.html'),'utf8');
assert(page.includes('id="infra-map"'),'map HTML missing');
assert(page.includes('id="showEvents"'),'event toggle missing');
console.log('PASS infrastructure pilot: 16 state scores, six-state TLI, partial evidence, sourced events and layout');
