'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const r1=JSON.parse(fs.readFileSync(path.join(root,'research/r1-events.json'),'utf8'));
const r23=JSON.parse(fs.readFileSync(path.join(root,'research/r2-r3-events.json'),'utf8'));
const employment=JSON.parse(fs.readFileSync(path.join(root,'data/county-employment.json'),'utf8'));
assert.equal(r1.events.length,61,'R1 input count');
assert.equal(r23.events.length,38,'R2+R3 input count');
assert.equal(r23.events.filter(x=>x.batch==='R2').length,15);
assert.equal(r23.events.filter(x=>x.batch==='R3').length,23);
const rows=[...r1.events,...r23.events];
assert.equal(rows.length,99);
assert.equal(new Set(rows.map(e=>e.event_id)).size,99,'IDs unique');
const validStates=new Set(['DE-BB','DE-BE','DE-BW','DE-BY','DE-HB','DE-HE','DE-HH','DE-MV','DE-NI','DE-NW','DE-RP','DE-SH','DE-SL','DE-SN','DE-ST','DE-TH']);
for(const e of rows){
 assert.ok(validStates.has(e.state_iso),'state '+e.event_id);
 assert.ok(e.headline_zh&&e.company&&e.event_date&&e.implementation_status,'required fields '+e.event_id);
 assert.match(e.source_url||'',/^https:\/\//,'source URL '+e.event_id);
 assert.ok(!e.jobs_affected||e.jobs_affected>=0,'bad jobs '+e.event_id);
 if(e.lat!==undefined&&e.lat!==null)assert.ok(Number(e.lat)>=47&&Number(e.lat)<=56,'lat '+e.event_id);
 if(e.lon!==undefined&&e.lon!==null)assert.ok(Number(e.lon)>=5&&Number(e.lon)<=16,'lon '+e.event_id);
}
assert.equal(Object.keys(employment.records).length,0,'Do not publish manufactured county employment figures');
assert.equal(employment.status,'awaiting_verified_county_series');
const js=fs.readFileSync(path.join(root,'topic.js'),'utf8');
assert.match(js,/COUNTY_HINTS/);
assert.match(js,/isMajor/);
assert.match(js,/source_url/);
assert.match(js,/county-employment.json/);
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
for(const tag of ['industry-map','legend','eventList','eventDetail','showMarkers','areaName'])
 assert.match(html,new RegExp('id="'+tag+'"'));
console.log('industry staging validation passed: 99 unique source-linked records; 16-state codes; no fabricated employment series.');
