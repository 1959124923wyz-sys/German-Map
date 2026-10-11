'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const read=name=>JSON.parse(fs.readFileSync(path.join(root,'data',name),'utf8'));
const nrw=read('nrw-new-home-completions.json'),
 by=read('bavaria-new-home-completions-2025.json'),
 bb=read('brandenburg-completions-2024-2025.json'),
 be=read('berlin-2024-2025-borough-completions.json'),
 sn=read('saxony-homeless-counties.json');
const groups=[['05',nrw.counties,53],['09',by.counties,96],['12',bb.counties,18],['14',sn.counties,13]];
for(const [prefix,rows,count] of groups){
 assert.equal(rows.length,count,prefix);
 assert.equal(new Set(rows.map(r=>r.id)).size,count);
 assert.ok(rows.every(r=>/^\d{5}$/.test(r.id)&&r.id.startsWith(prefix)&&typeof r.name==='string'&&r.name.length>0),prefix);
}
assert.equal(be.boroughs.length,12);
assert.equal(new Set(be.boroughs.map(r=>r.borough_index)).size,12);
assert.equal(groups.reduce((n,g)=>n+g[2],0)+be.boroughs.length,192);
const is=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
const years=[...Array(11)].map((_,i)=>String(2015+i));
assert.ok(nrw.counties.every(r=>years.every(y=>is(r.values_by_year?.[y]?.new_dwellings_in_residential_buildings))));
assert.ok(by.counties.every(r=>is(r.completed_dwellings_new_residential_buildings_2025)));
for(const r of bb.counties)for(const y of ['2024','2025'])
 assert.ok(is(r['completed_dwellings_all_measures_'+y]));
for(const r of be.boroughs)for(const y of ['2024','2025'])
 assert.ok(is(r['completed_dwellings_all_measures_'+y]));
for(const r of sn.counties)for(const y of ['2022','2023','2024','2025','2026'])
 assert.ok(is(r.annual_counts?.[y]));
// Distinct 2025 *scope* totals guard, without joining incomparable measures.
assert.equal(nrw.counties.reduce((a,r)=>a+r.values_by_year['2025'].new_dwellings_in_residential_buildings,0),31237);
assert.equal(bb.counties.reduce((a,r)=>a+r.completed_dwellings_all_measures_2025,0),7379);
assert.equal(be.boroughs.reduce((a,r)=>a+r.completed_dwellings_all_measures_2025,0),11027);
assert.equal(sn.meta.state_total_2026,5590);
// Confidentiality rounding: do not demand sum of districts equals official total.
assert.equal(sn.counties.length,13);
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const app=fs.readFileSync(path.join(root,'topic.js'),'utf8');
for(const id of ['housingStateArchive','housingLocalYear','housingLocalRows','housingLocalSource'])
 assert.ok(html.includes('id="'+id+'"'));
assert.ok(app.includes('function localStateSource()'));
assert.ok(app.includes('function renderLocalStateArchive()'));
assert.ok(app.includes('const prev=src.years.includes(priorYear)')||app.includes('src.years.includes(priorYear)?'));
console.log('PASS housing: 192 independently sourced state/county/borough rows, 11y NRW, 2y BB/BE, 5y Sachsen; no cross-source national totals');
