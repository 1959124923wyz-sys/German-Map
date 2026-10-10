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
const r6=JSON.parse(fs.readFileSync(path.join(root,'research/r6-events.json'),'utf8'));
const r7a=JSON.parse(fs.readFileSync(path.join(root,'research/r7a-screened-2026-events.json'),'utf8'));
const r7b=JSON.parse(fs.readFileSync(path.join(root,'research/r7b-2025-retrospective.json'),'utf8'));
const r7c=JSON.parse(fs.readFileSync(path.join(root,'research/r7c-plant-closures-offshoring.json'),'utf8'));
const r7d=JSON.parse(fs.readFileSync(path.join(root,'research/r7d-2024-company-primary-audited.json'),'utf8'));
const r7e=JSON.parse(fs.readFileSync(path.join(root,'research/r7e-2025-undercovered-sites.json'),'utf8'));
const r8a=JSON.parse(fs.readFileSync(path.join(root,'research/r8a-2024-industry-backfill.json'),'utf8'));
assert.equal(r8a.events.length,10,'R8A source-backed factory and exclusion records');
assert.equal(r8a.events.filter(e=>e.eligible_factory_marker).length,7);
assert.equal(r8a.events.filter(e=>e.shared_program_id==='putzmeister_2024_two_german_factories_280' && e.eligible_factory_marker && e.jobs_affected!==null).length,0,'Putzmeister cross-site total never assigned to sites');
assert.equal(r8a.events.find(e=>e.event_id==='R8A_UPM_DOR').event_type,'production_line_closure','Dörpen PM3-only not entire plant');
assert.equal(r7e.events.length,5,'R7E five documented factory restructuring cases');
assert.equal(r7e.events.find(e=>e.event_id==='R7E_KUS_HAL').implementation_status,'confirmed_by_subsequent_report','Kusch operation actually ended 2025 per 2026 media');
assert.equal(r7d.events.length,13,'R7D source-backed factory history and research-only notes');
assert.equal(r7d.events.filter(e=>e.eligible_factory_marker).length,11,'11 R7D site reference candidates');
const feintool=r7d.events.find(e=>e.event_id==='R7D_FEI_SAC');
assert.equal(feintool.jobs_affected,null,'200 shared jobs must NOT be assigned to Sachsenheim');
assert.equal(feintool.event_type,'production_relocation','Feintool 2025 accord prevents incorrect whole factory closure');
for(const e of r7d.events.filter(x=>x.shared_program_id==='neveon_de_2024_240_3sites')){
 if(e.eligible_factory_marker)assert.equal(e.jobs_affected,null,'240 cannot be assigned to Neveon factory');
}
assert.equal(r7c.events.length,7,'R7C source-backed industrial sites');
const r7audit=JSON.parse(fs.readFileSync(path.join(root,'research/r7-legacy-identity-audit.json'),'utf8'));
assert.equal(r7audit.updates.DEEB26_BB_EBER.city,'Britz (Barnim)','EWN Britz plant location not Eberswalde trade name');
assert.equal(r7audit.reviewed_nonadditions.length,2,'EWN/Varta duplicates explicitly audited');
const r6Audit=JSON.parse(fs.readFileSync(path.join(root,'research/r6-dedup-audit.json'),'utf8'));
assert.equal(r6.events.length,1,'R6 only genuinely new site');
assert.equal(r7a.events.length,10,'R7A individually screened cases');
assert.equal(r7b.events.length,11,'R7B retrospective events');
for(const b of [r7a,r7b,r7c,r7d,r7e,r8a])for(const e of b.events){
 if(e.eligible_factory_marker){
  assert.match(e.county_ags||'',/^\d{5}$/,'R7 site must have current AGS: '+e.event_id);
 }
}
assert.equal(r7a.events.filter(e=>e.eligible_factory_marker===true).length,3);
assert.equal(r7b.events.filter(e=>e.eligible_factory_marker===true).length,9);
assert.equal(r7b.events.filter(e=>e.shared_program_id==='musashi_2025_de_457').reduce((s,e)=>s+e.jobs_affected,0),457,'Musashi updated 457 only once across 3 site figures');
assert.equal(r6Audit.excluded_duplicates,10,'Ten already represented factsheets rejected');
const employment=JSON.parse(fs.readFileSync(path.join(root,'data/county-employment.json'),'utf8'));
const crosswalk=JSON.parse(fs.readFileSync(path.join(root,'data/county_ags_crosswalk.json'),'utf8'));
assert.equal(crosswalk.records.length,402,'402 county AGS source geometry crosswalk');
assert.equal(new Set(crosswalk.records.map(x=>x.ags5)).size,402,'402 AGS must be unique');
for(const x of crosswalk.records)assert.match(x.ags5,/^[0-9]{5}$/,'invalid AGS');
const ags=JSON.parse(fs.readFileSync(path.join(root,'data/ags-crosswalk-402-to-400.json'),'utf8'));
assert.equal(ags.features.length,402);
assert.equal(new Set(ags.features.map(e=>e.canonical_ags)).size,400);
assert.equal(ags.canonical_remaps['03152'],'03159','historic Goettingen remapped to new 2016 AGS');
assert.equal(ags.canonical_remaps['03156'],'03159','Osterode remapped to modern Goettingen');
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
const rows=[...r1.events,...r23.events,...r4.events,...r5a.events,...r5b.events,...r5c.events,...r5d.events,...r6.events,...r7a.events,...r7b.events,...r7c.events,...r7d.events,...r7e.events,...r8a.events];
assert.equal(rows.length,230);
assert.equal(new Set(rows.map(e=>e.event_id)).size,230,'IDs unique');
for(const [id,fix] of Object.entries({...r4.updates,...r7audit.updates})){
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
assert.match(js,/String\(stateKey\(feature\)\|\|''\)/,'Official employment must use canonical AGS after historical mergers');
assert.match(js,/r4-events-and-updates.json/);
assert.match(js,/r5a-eurofound-sites.json/);
assert.match(js,/r5b-manufacturing-cases.json/);
assert.match(js,/r5c-screened-manufacturing.json/);
assert.match(js,/r5d-2025-factory-closures.json/);
assert.match(js,/r7a-screened-2026-events.json/);
assert.match(js,/r7b-2025-retrospective.json/);
assert.match(js,/r7c-plant-closures-offshoring.json/);
assert.match(js,/r7d-2024-company-primary-audited.json/);
assert.match(js,/r7e-2025-undercovered-sites.json/);
assert.match(js,/r8a-2024-industry-backfill.json/);
assert.match(js,/r7-legacy-identity-audit.json/);
assert.match(js,/ags-crosswalk-402-to-400.json/);
assert.match(js,/bkg_vg250_counties_2025_candidate.geojson/);
const geo=JSON.parse(fs.readFileSync(path.join(root,'data/bkg_vg250_counties_2025_candidate.geojson'),'utf8'));
assert.equal(geo.features.length,400,'BKG map polygons exactly 400 modern Kreise');
assert.equal(new Set(geo.features.map(e=>e.id)).size,400,'BKG map unique canonical AGS');
assert.deepEqual([...new Set(geo.features.map(e=>e.id))].sort(),[...new Set(ags.features.map(e=>e.canonical_ags))].sort(),'Official geodata codes match 402->400 reference');
assert.equal(geo._provenance.publisher,'Bundesamt für Kartographie und Geodäsie');
assert.equal(geo._provenance.effective_date,'2024-12-31');
assert.ok(geo.features.every(f=>['Polygon','MultiPolygon'].includes(f.geometry?.type)),'BKG valid polygon type');
assert.equal(geo.features.find(f=>f.id==='03159').properties.name,'Göttingen');
assert.equal(geo.features.find(f=>f.id==='16063').properties.name,'Wartburgkreis');
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
 '03159,2019,1111,WZ2008_C,workplace,fixture_v1,https://example.invalid/2019',
 '03159,2025,.,WZ2008_C,workplace,fixture_v1,https://example.invalid/2025'
].join('\n');
try{
 fs.writeFileSync(csv,fixture);
 const importer=path.join(root,'scripts/build_county_employment.cjs');
 execFileSync(process.execPath,[importer,'--input',csv,'--output',out],{stdio:'pipe'});
 const result=JSON.parse(fs.readFileSync(out,'utf8'));
 assert.equal(result.coverage.valid_districts,1);
 assert.equal(result.coverage.possible_districts,400);
 assert.equal(result.records['08425'].change_pct,-20);
 assert.equal(result.records['03159'],undefined,'suppressed official cells remain missing');
 assert.equal(result.records['08425'].source_url_2019,'https://example.invalid/2019');
 // Refuse any series that mixes mining and manufacturing.
 fs.writeFileSync(csv,fixture.replace('WZ2008_C','WZ2008_BC'));
 assert.throws(()=>execFileSync(process.execPath,[importer,'--input',csv,'--output',out],{stdio:'pipe'}));
}finally{fs.rmSync(tmp,{recursive:true,force:true})}
console.log('industry staging validation passed: 230 unique events; 400 canonical districts; official-CSV guardrail fixture.');
