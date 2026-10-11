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
// Detailed source values add 2,001 previously UI-inaccessible fields to the
// original 804 district-year value slots: 2,805 observations, not 2,805 counties.
const tableFields={
 nrw:['new_dwellings_in_residential_buildings','new_residential_buildings','rooms_in_new_residential_buildings','floor_area_new_residential_sqm'],
 by:['completed_dwellings_new_residential_buildings_2025','completed_new_residential_buildings_2025','completed_dwellings_all_measures_2025'],
 bb:['completed_dwellings_all_measures_','completed_new_build_all_types_'],
 be:['completed_dwellings_all_measures_','completed_dwellings_new_build_all_types_']
};
const available=n=>typeof n==='number'&&Number.isFinite(n)&&n>=0;
for(const r of nrw.counties)for(const y of years)for(const key of tableFields.nrw)
 assert.ok(available(r.values_by_year?.[y]?.[key]),'NRW '+r.id+' '+y+' '+key);
for(const r of by.counties)for(const key of tableFields.by)
 assert.ok(available(r[key]),'Bavaria '+r.id+' '+key);
for(const r of bb.counties)for(const y of ['2024','2025'])for(const key of tableFields.bb)
 assert.ok(available(r[key+y]),'Brandenburg '+r.id+' '+y+' '+key);
for(const r of be.boroughs)for(const y of ['2024','2025'])for(const key of tableFields.be)
 assert.ok(available(r[key+y]),'Berlin borough '+r.name+' '+key+y);
const n=53*11*4+96*3+18*2*2+12*2*2+13*5;
assert.equal(n,2805);
assert.equal(nrw.counties.find(x=>x.id==='05111').values_by_year['2025'].new_residential_buildings,136);
assert.equal(by.counties.find(x=>x.id==='09162').completed_new_residential_buildings_2025,593);
assert.equal(bb.counties.find(x=>x.id==='12054').completed_new_build_all_types_2025,908);
assert.equal(be.boroughs.find(x=>x.name==='Mitte').completed_dwellings_new_build_all_types_2025,927);
assert.equal(bb.counties.reduce((n,r)=>n+r.completed_new_build_all_types_2025,0),6489);
assert.equal(be.boroughs.reduce((n,r)=>n+r.completed_dwellings_new_build_all_types_2025,0),9524);
assert.ok(html.includes('id="housingLocalMetric"'));
assert.ok(app.includes('function localSourceMetrics(src)'));
console.log('PASS housing: 192 source regions, 2,805 year × source-indicator values; original 2015–2026 scopes and construction categories preserved');
