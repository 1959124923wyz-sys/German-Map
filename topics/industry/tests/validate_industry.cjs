'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const r1=JSON.parse(fs.readFileSync(path.join(root,'research/r1-events.json'),'utf8'));
const r23=JSON.parse(fs.readFileSync(path.join(root,'research/r2-r3-events.json'),'utf8'));
const r4=JSON.parse(fs.readFileSync(path.join(root,'research/r4-events-and-updates.json'),'utf8'));
const r5a=JSON.parse(fs.readFileSync(path.join(root,'research/r5a-eurofound-sites.json'),'utf8'));
const r5b=JSON.parse(fs.readFileSync(path.join(root,'research/r5b-manufacturing-cases.json'),'utf8'));
const employment=JSON.parse(fs.readFileSync(path.join(root,'data/county-employment.json'),'utf8'));
assert.equal(r1.events.length,61,'R1 input count');
assert.equal(r23.events.length,38,'R2+R3 input count');
assert.equal(r23.events.filter(x=>x.batch==='R2').length,15);
assert.equal(r23.events.filter(x=>x.batch==='R3').length,23);
assert.equal(r4.events.length,18,'R4 input count');
assert.equal(Object.keys(r4.updates).length,5,'R4 corrections');
assert.equal(r5a.events.length,10,'R5A source audit');
assert.equal(r5b.events.length,16,'R5B source audit');
assert.equal(r5b.events.filter(e=>e.eligible_factory_marker===false).length,2,'R5B groups are not map markers');
assert.equal(r5a.events.filter(e=>e.eligible_factory_marker===false).length,2,'Exclude operators/multi-site');
const rows=[...r1.events,...r23.events,...r4.events,...r5a.events,...r5b.events];
assert.equal(rows.length,143);
assert.equal(new Set(rows.map(e=>e.event_id)).size,143,'IDs unique');
for(const [id,fix] of Object.entries(r4.updates)){
 assert.ok(rows.some(e=>e.event_id===id),'patch target '+id);
 assert.ok((fix.source_url||rows.find(e=>e.event_id===id)?.source_url)?.startsWith('https://'),'patch citation '+id);
}
const r4Groups=r4.events.filter(e=>e.eligible_factory_marker===false);
assert.equal(r4Groups.length,5,'R4 research-only shared groups must not generate point markers');
for(const e of r4Groups)assert.equal(e.jobs_affected,null,'research-only multi-site jobs must not be distributed');
const validStates=new Set(['DE-BB','DE-BE','DE-BW','DE-BY','DE-HB','DE-HE','DE-HH','DE-MV','DE-NI','DE-NW','DE-RP','DE-SH','DE-SL','DE-SN','DE-ST','DE-TH']);
for(const e of rows){
 assert.ok(validStates.has(e.state_iso)||(e.state_iso===null&&e.eligible_factory_marker===false),'state '+e.event_id);
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
assert.match(js,/r4-events-and-updates.json/);
assert.match(js,/r5a-eurofound-sites.json/);
assert.match(js,/r5b-manufacturing-cases.json/);
const grouped=r5b.events.filter(e=>e.shared_program_id);
for(const e of grouped)assert.equal(e.jobs_affected,null,'group layoffs must not be distributed to sites');
assert.match(js,/Object.assign\(original,patch\)/);
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
for(const tag of ['industry-map','legend','eventList','eventDetail','showMarkers','areaName'])
 assert.match(html,new RegExp('id="'+tag+'"'));
console.log('industry staging validation passed: 143 unique source-linked records; 5 documented corrections; no fabricated employment series.');
