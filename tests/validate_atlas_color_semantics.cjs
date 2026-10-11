'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const browser={};vm.runInNewContext(fs.readFileSync('js/core/atlas-color-semantics.js','utf8'),{window:browser});
const S=browser.AtlasColorSemantics;
assert.ok(S,'Policy registry is required');
const expected=['crime','drugs','immigration','environment','railway','finance','industry','infrastructure','housing'];
assert.deepEqual(Object.keys(S.registry).sort(),expected.sort(),'Missing topic registry');
const valid=new Set(Object.values(S.kinds));
for(const [topic,rows] of Object.entries(S.registry))
  for(const [key,type]of Object.entries(rows)){
    assert.ok(valid.has(type),topic+'/'+key+' unknown semantics '+type);
    assert.ok(S.legendText(topic,key).length>0,topic+'/'+key+' missing legend');
    if(type===S.kinds.HIGH||type===S.kinds.LOW||type===S.kinds.NEUTRAL)
      assert.equal(S.palette(topic,key).length,7);
  }
const src=fs.readFileSync('topics/housing/topic.js','utf8');
const block=src.match(/const metrics = \{([\s\S]*?)\n  \};/);
assert.ok(block,'Cannot parse housing indicator list');
const all=[...block[1].matchAll(/^\s+([a-z][a-z0-9_]+):\{label:/gm)].map(x=>x[1]);
assert.equal(all.length,15);
assert.deepEqual(Object.keys(S.registry.housing).sort(),all.sort(),'Undeclared housing metric');
assert.equal(S.get('housing','living_area_2022_m2_person'),S.kinds.LOW);
assert.equal(S.get('housing','asking_rent_2025_eur_m2'),S.kinds.HIGH);
for(const key of ['vacancy_2022_pct','owner_occupier_2022_pct','disposable_income_2023_keur_person','population_growth_2022_2025_pct','completed_dwellings_new_residential_buildings_2023','sheltered_homeless_2025'])
 assert.equal(S.get('housing',key),S.kinds.NEUTRAL,key);
const low=S.palette('housing','living_area_2022_m2_person');
const high=S.palette('housing','asking_rent_2025_eur_m2');
assert.equal(low[0],high[6]);
assert.equal(low[6],high[0]);
assert.equal(S.palette('housing','vacancy_2022_pct')[6],'#1b5278');
assert.equal(S.palette('finance','core-2023')[6],'#a52d37');
assert.equal(S.palette('finance','city-2024')[6],'#a52d37');
assert.throws(()=>S.get('housing','unknown'),/Undeclared/);
assert.throws(()=>S.palette('finance','balance-2025'),/domain-specific/);
assert.equal(S.indexFor(null,[1,2,3]),-1);
assert.equal(S.indexFor(0,[1,2,3]),0);
assert.equal(S.indexFor(2,[1,2,3]),1);
assert.equal(S.indexFor(99,[1,2,3]),3);
assert.ok(src.includes('semantics.palette(\'housing\',metric)'));
assert.ok(fs.readFileSync('topics/finance/topic.js','utf8').includes('semantics.palette(\'finance\',metric)'));
for(const topic of ['housing','finance']){
 const html=fs.readFileSync('topics/'+topic+'/index.html','utf8');
 const at=html.indexOf('atlas-color-semantics.js');
 assert.ok(at>=0&&at<html.indexOf('topic.js?v='),topic+' color semantics script must load before map');
}
console.log('PASS color semantics registry, 15 housing metrics, inverse/neutral ramp, debt and missing values');
