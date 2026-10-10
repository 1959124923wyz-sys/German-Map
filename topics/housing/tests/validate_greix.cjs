'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'data/greix-city-series.json'),'utf8'));
assert.equal(data.meta.city_count,38);
assert.equal(data.meta.observations,6612);
assert.equal(data.meta.time_frequency,'monthly');
assert.equal(data.meta.columns.length,6);
assert.equal(Object.keys(data.cities).length,38);
let total=0;
for(const [city,series] of Object.entries(data.cities)){
 assert.equal(series.length,174,city);
 let prev='';
 for(const row of series){
  assert.equal(row.length,6,city);
  assert.match(row[0],/^20\d{2}-(0[1-9]|1[0-2])$/);
  assert.ok(row[0]>prev,city+' duplicate/unsorted '+row[0]);
  prev=row[0];
  for(const v of row.slice(1))assert.ok(typeof v==='number'&&Number.isFinite(v)&&v>0,city+' invalid value');
 }
 assert.equal(series[0][0],'2012-01');
 assert.equal(series.at(-1)[0],'2026-06');
 total+=series.length;
}
assert.equal(total,6612);
const app=fs.readFileSync(path.join(root,'topic.js'),'utf8');
assert.ok(app.includes('GREIX_STATES'));
assert.ok(app.includes('data/greix-city-series.json'));
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
assert.ok(html.includes('data-dossier-tab="rent-series"'));
assert.ok(html.includes('id="greixChart"'));
assert.ok(html.includes('IfW Kiel GREIX公开数据原表'));
console.log('PASS GREIX: 38 series (37 state-located + noncounty aggregate), 6612 positive monthly rows, 2012-01 to 2026-06');
