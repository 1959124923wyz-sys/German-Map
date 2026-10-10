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
const r5c=JSON.parse(fs.readFileSync(path.join(root,'research/r5c-screened-manufacturing.json'),'utf8'));
const r5d=JSON.parse(fs.readFileSync(path.join(root,'research/r5d-2025-factory-closures.json'),'utf8'));
const employment=JSON.parse(fs.readFileSync(path.join(root,'data/county-employment.json'),'utf8'));
const ags=JSON.parse(fs.readFileSync(path.join(root,'data/ags-crosswalk-402-to-400.json'),'utf8'));
assert.equal(ags.features.length,402);
assert.equal(new Set(ags.features.map(e=>e.canonical_ags)).size,400);
assert.equal(ags.canonical_remaps['03156'],'03152');
assert.equal(ags.canonical_remaps['16056'],'16063');
for(const batch of [r5a,r5b,r5c,r5d]){
 const siteRows=batch.events.filter(e=>e.eligible_factory_marker===true);
 assert.equal(batch.manifest.county_ags_assigned,siteRows.length,'site AGS audited');
 for(const e of siteRows){
  assert.match(e.county_ags||'',/^\d{5}$/,'AGS required for '+e.event_id);
  assert.ok(ags.features.some(g=>g.canonical_ags===e.county_ags),'county AGS belongs to current national crosswalk: '+e.event_id);
 }
}
const indexed=[...r5a.events,...r5b.events,...r5c.events,...r5d.events];
const byEvent=Object.fromEntries(indexed.map(e=>[e.event_id,e]));
assert.equal(byEvent.R5_PI_KAR.county_ags,'08212','Karlsruhe city, NOT Karlsruhe Landkreis');
assert.equal(byEvent.R5B_KRA_KAR.county_ags,'08212','Karlsruhe city not rural district');
assert.equal(byEvent.R5C_ENO_OBE.county_ags,'08215','Oberderdingen in Karlsruhe rural district');
assert.equal(byEvent.R5D_BSH_BRE.county_ags,'08215','Bretten in Karlsruhe rural district');
assert.equal(byEvent.R5C_OSR_SCH.county_ags,'09772','Schwabmünchen in Landkreis Augsburg, not Augsburg city');
assert.equal(byEvent.R5D_RW_POC.county_ags,'09275','Pocking in Landkreis Passau, not Passau city');
assert.equal(r1.events.length,61,'R1 input count');
assert.equal(r23.events.length,38,'R2+R3 input count');
assert.equal(r23.events.filter(x=>x.batch==='R2').length,15);
assert.equal(r23.events.filter(x=>x.batch==='R3').length,23);
assert.equal(r4.events.length,18,'R4 input count');
assert.equal(Object.keys(r4.updates).length,5,'R4 corrections');
assert.equal(r5a.events.length,10,'R5A source audit');
assert.equal(r5b.events.length,16,'R5B source audit');
assert.equal(r5c.events.length,12,'R5C source audit');
assert.equal(r5d.events.length,18,'R5D source audit');
assert.equal(r5d.events.filter(e=>e.eligible_factory_marker===false).length,1,'R5D DS Smith group memo hidden');
assert.equal(r5d.manifest.site_events,17);
assert.equal(r5c.manifest.sites,7);
assert.equal(r5c.events.filter(e=>e.eligible_factory_marker===false).length,5,'R5C undecided/group/nonfactory excluded');
assert.equal(r5b.events.filter(e=>e.eligible_factory_marker===false).length,2,'R5B groups are not map markers');
assert.equal(r5a.events.filter(e=>e.eligible_factory_marker===false).length,2,'Exclude operators/multi-site');
const rows=[...r1.events,...r23.events,...r4.events,...r5a.events,...r5b.events,...r5c.events,...r5d.events];
assert.equal(rows.length,173);
assert.equal(new Set(rows.map(e=>e.event_id)).size,173,'IDs unique');
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
assert.match(js,/r5c-screened-manufacturing.json/);
assert.match(js,/r5d-2025-factory-closures.json/);
assert.match(js,/ags-crosswalk-402-to-400.json/);
assert.match(js,/new Set\(counties.features.map\(stateKey\)\).size!==400/);
const grouped=r5b.events.filter(e=>e.shared_program_id);
for(const e of grouped){
 if(e.jobs_affected!==null)assert.equal(e.jobs_basis,'site_planned_or_reported_positions_non_additive','only independently allocated site figures allowed '+e.event_id);
}
assert.equal(r5b.events.filter(e=>e.shared_program_id==='thermo_fisher_2026_160_two_sites').reduce((sum,e)=>sum+e.jobs_affected,0),160,'Thermo Fisher combined figure only once');
assert.match(js,/Object.assign\(original,patch\)/);
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
for(const tag of ['industry-map','legend','eventList','eventDetail','showMarkers','areaName'])
 assert.match(html,new RegExp('id="'+tag+'"'));
const os=require('node:os');
const {execFileSync}=require('node:child_process');
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'industry-ags-test-'));
const csv=path.join(tmp,'fixture.csv'),out=path.join(tmp,'out.json');
const header='ags,year,manufacturing_employees,industry_definition,workplace_basis,source_table,source_url';
const fixture=[header,
 '08425,2019,1000,WZ2008_C,workplace,fixture_v1,https://example.invalid/2019',
 '08425,2025,800,WZ2008_C,workplace,fixture_v1,https://example.invalid/2025',
 '03152,2019,1111,WZ2008_C,workplace,fixture_v1,https://example.invalid/2019',
 '03152,2025,.,WZ2008_C,workplace,fixture_v1,https://example.invalid/2025'
].join('\n');
try{
 fs.writeFileSync(csv,fixture);
 const importer=path.join(root,'scripts/build_county_employment.cjs');
 execFileSync(process.execPath,[importer,'--input',csv,'--output',out],{stdio:'pipe'});
 const result=JSON.parse(fs.readFileSync(out,'utf8'));
 assert.equal(result.coverage.valid_districts,1);
 assert.equal(result.coverage.possible_districts,400);
 assert.equal(result.records['08425'].change_pct,-20);
 assert.equal(result.records['03152'],undefined,'suppressed official cells remain missing');
 assert.equal(result.records['08425'].source_url_2019,'https://example.invalid/2019');
 // Refuse any series that mixes mining and manufacturing.
 fs.writeFileSync(csv,fixture.replace('WZ2008_C','WZ2008_BC'));
 assert.throws(()=>execFileSync(process.execPath,[importer,'--input',csv,'--output',out],{stdio:'pipe'}));
}finally{fs.rmSync(tmp,{recursive:true,force:true})}
console.log('industry staging validation passed: 173 unique events; 400 canonical districts; official-CSV guardrail fixture.');
