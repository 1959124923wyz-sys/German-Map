#!/usr/bin/env node
/* Pure-module smoke: no browser, no network, no DOM. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const context=vm.createContext({window:{}});
for(const name of ['rail-geometry.js','rail-analysis.js','rail-bridge.js']){
  const source=fs.readFileSync(path.join(root,'js',name),'utf8');
  vm.runInContext(source,context,{filename:name,timeout:10000});
}
const geom=context.window.Railway07Geometry;
const math=context.window.Railway07Analysis;
assert.ok(Object.isFrozen(geom)&&Object.isFrozen(math));
assert.deepEqual(Array.from(geom.decodePolyline('????')),[0,0,0,0]);
const shape=geom.shape([1,2,3,4]);
assert.equal(shape.minX,1);assert.equal(shape.maxY,4);
assert.equal(geom.segmentDist(1,0,0,0,2,0),0);
assert.equal(geom.segmentDist(3,0,0,0,2,0),1);
const p=geom.proj(8,50),back=geom.unproject(...p);
assert.ok(Math.abs(back[0]-50)<1e-7&&Math.abs(back[1]-8)<1e-7);
assert.equal(geom.observedParts({geometry:[[[8,50],[8.01,50.01]]]}).length,1);
const leg=(from,to,km,late,cancel,route='100')=>({
  route,from_station:from,to_station:to,km_range:km,
  v11:{pairs:100,arrival_valid:100,late6:late,boundary_cancel:cancel}
});
const a=leg('A','B',[0,10],45,5),b=leg('B','C',[10,20],42,7);
assert.equal(math.metrics(a,'both',100).sufficient,true);
assert.equal(math.metrics({...a,v11:{...a.v11,arrival_valid:99}},'both',100).sufficient,false);
assert.equal(math.grade(math.metrics(a,'both',100),'both'),2);
assert.equal(math.grade({late:24,cancel:3},'both'),0);
assert.equal(math.grade({late:24,cancel:5},'both'),1);
assert.equal(math.grade({late:41,cancel:0},'late'),2);
assert.equal(math.grade({late:0,cancel:9},'cancel'),2);
const parts=[geom.shape([10,10,11,11])];
const entry=leg=>({leg,grade:2,parts,m:math.metrics(leg,'both',100)});
const joined=math.buildCorridors([entry(a),entry(b)]);
assert.equal(joined.length,1);
assert.equal(joined[0].members.length,2);
assert.equal(joined[0].m.nArrival,200);
assert.equal(joined[0].m.nPlanned,200);
assert.equal(joined[0].m.late,43.5);
assert.equal(joined[0].m.onTime,56.5);
assert.equal(joined[0].m.cancel,6);
assert.equal(math.buildCorridors([entry(a),entry(leg('B','C',[21,30],45,5))]).length,2);
assert.equal(math.buildCorridors([entry(a),entry(leg('B','C',[10,20],45,5,'200'))]).length,2);
// A fork must not be collapsed as a unique straight-through corridor.
assert.equal(math.buildCorridors([entry(a),entry(b),entry(leg('B','D',[10,21],41,8))]).length,3);
const combined=math.mergeObserved([['RE',{links:[a]}],['RB',{links:[a]}]]);
assert.equal(combined.length,1);
assert.equal(combined[0].v11.pairs,200);
assert.equal(combined[0].v11.late6,90);
assert.equal(combined[0].brands.length,2);
assert.equal(math.metrics(combined[0],'late',100).late,45);

// Real WGS84-derived curve connections must never create fake observations.
const bridge=context.window.Railway07Bridge;
const net=new bridge.RouteGraph();
const baseY=45000;
const part=(from,to,dy=0)=>geom.shape([from,baseY+dy,to,baseY+dy]);
net.add('100',part(100,105));
net.add('100',part(105,110));
const connection=net.find('100',[104,baseY],[106,baseY],5);
assert.ok(connection&&connection.parts.length>=1,'official source route should bridge');
assert.ok(connection.km>0&&connection.km<2);
assert.equal(net.find('100',[104,baseY],[130,baseY],5),null,'no invented straight line');
assert.equal(net.find('200',[104,baseY],[106,baseY],5),null,'never cross route IDs');
const m1=leg('A','B',[0,5],45,5),m2=leg('C','D',[6,11],44,5);
const f=x=>({leg:x,grade:2,parts:[part(x===m1?100:106,x===m1?104:110)],m:math.metrics(x,'both')});
const observed=[f(m1),f(m2)];
const singles=math.buildCorridors(observed);
assert.equal(singles.length,2);
const merged=bridge.mergeGroups(singles,net,observed);
assert.equal(merged.bridged,1);
assert.equal(merged.groups.length,1);
assert.equal(merged.groups[0].bridges,1);
assert.ok(merged.groups[0].bridgeKm>0);
assert.equal(merged.groups[0].members.length,2);
assert.equal(merged.groups[0].m.late,44.5);
assert.equal(merged.groups[0].m.cancel,5);
// A higher-risk measured interval in the missing range cannot be hidden.
const conflicting={leg:leg('E','F',[5.2,5.8],3,1),grade:0,m:{},parts:[part(104,106)]};
assert.equal(bridge.mergeGroups(math.buildCorridors([f(m1),f(m2)]),net,[...observed,conflicting]).bridged,0);
const distant=leg('Q','R',[75,85],43,5);
assert.equal(bridge.mergeGroups(math.buildCorridors([f(m1),f(distant)]),net,observed).bridged,0);

console.log('PASS railway pure geometry, weighted rates, branches, km gaps and pooled counts');
