#!/usr/bin/env node
/* Pure-module smoke: no browser, no network, no DOM. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const context=vm.createContext({window:{}});
for(const name of ['rail-geometry.js','rail-analysis.js','rail-bridge.js','rail-service-groups.js','rail-city-corridors.js','rail-continuity.js','rail-picker.js','rail-color-runs.js']){
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
const highlighted=net.walk('100',[104,baseY],10);
assert.ok(highlighted);
assert.equal(highlighted.parts.length,2,'official same-route adjacent sections form one green highlight');
assert.equal(highlighted.route,'100');
assert.equal(net.walk('9999',[104,baseY]),null,'unknown line cannot be invented');
const connection=net.find('100',[104,baseY],[106,baseY],5);
assert.ok(connection&&connection.parts.length>=1,'official source route should bridge');
assert.ok(connection.km>0&&connection.km<2);
assert.equal(net.find('100',[104,baseY],[130,baseY],5),null,'no invented straight line');
assert.ok(net.find('200',[104,baseY],[106,baseY],5),'observed route alias must be reconciled by real geographic geometry');
const duplicate=new bridge.RouteGraph();duplicate.add('100',part(100,110));duplicate.add('200',part(100,110));
assert.equal(duplicate.find('300',[104,baseY],[106,baseY],5),null,'ambiguous coincident DB alignments must be rejected');
const crossNumber=new bridge.RouteGraph();
crossNumber.add('100',part(100,105));crossNumber.add('200',part(105,110));
const crossLink=crossNumber.find('999',[102,baseY],[108,baseY],5);
assert.ok(crossLink&&crossLink.crossRoute===true,
  'joined official geometries may traverse mismatched infrastructure route labels');

const m1=leg('A','B',[0,5],45,5),m2=leg('C','D',[6,11],44,5);
const reverse=leg('B','A',[0,5],20,1);
const f=x=>({leg:x,grade:2,parts:[part((x===m1||x===reverse)?100:106,(x===m1||x===reverse)?104:110)],m:math.metrics(x,'both')});
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
// Previously the old gap>=.12 rule dropped *exactly adjoining* km sections,
// leaving false breaks where the station labels did not match.
const touchA=leg('Station A','Station B',[0,5],45,5);
const touchB=leg('Station B variant','Station C',[5,10],44,5);
const touchRows=[
 {leg:touchA,grade:2,parts:[part(100,104)],m:math.metrics(touchA,'both')},
 {leg:touchB,grade:2,parts:[part(105,110)],m:math.metrics(touchB,'both')}
];
const touching=bridge.mergeGroups(math.buildCorridors(touchRows),net,touchRows);
assert.equal(touching.groups.length,1,'adjacent km chain remains one corridor');
assert.equal(touching.groups[0].members.length,2);
assert.equal(touching.groups[0].m.late,44.5);

// Two directions on the same physical km interval become one corridor with
// pooled *counted* arrivals, not an average of printed percentages.
const groupedOpposite=bridge.mergeGroups(
 math.buildCorridors([f(m1),f(reverse)]),net,[f(m1),f(reverse)]);
assert.equal(groupedOpposite.groups.length,1);
assert.equal(groupedOpposite.groups[0].members.length,2);
assert.equal(groupedOpposite.groups[0].m.late,32.5);
assert.equal(groupedOpposite.groups[0].m.cancel,3);

// A higher-risk measured interval in the missing range cannot be hidden.
const conflicting={leg:leg('E','F',[5.2,5.8],3,1),grade:0,m:{},parts:[part(104,106)]};
assert.equal(bridge.mergeGroups(math.buildCorridors([f(m1),f(m2)]),net,[...observed,conflicting]).bridged,0);
const distant=leg('Q','R',[75,85],43,5);
assert.equal(bridge.mergeGroups(math.buildCorridors([f(m1),f(distant)]),net,observed).bridged,0);


// Regress the former clickable-only-observations bug: even with no usable
// stop data, the official low-opacity green rail should select as no-data.
const select=context.window.Railway07Picker;
const locator=new select.RailwayPicker();
const virgin=geom.shape([100,baseY+10,110,baseY+10]);
locator.addNetwork('6081',virgin);
let result=locator.hit([105,baseY+10],9);
assert.equal(result.kind,'network');
assert.equal(result.route,'6081');
assert.equal(locator.network.items,1);
const measured=geom.shape([100,baseY,110,baseY]);
const measuredEntry={parts:[measured],group:{route:'6081',m:{onTime:83}}};
locator.replaceObserved([measuredEntry],[]);
result=locator.hit([105,baseY],9);
assert.equal(result.kind,'observed');
assert.equal(result.group.m.onTime,83);
result=locator.hit([105,baseY+10],9);
assert.equal(result.kind,'network','unobserved green section remains selectable');
locator.replaceObserved([],[]);
assert.equal(locator.observed.items,0);
assert.equal(locator.network.items,1,'switching a filter cannot erase official rail picking');
assert.equal(locator.hit([105,baseY+10],9).kind,'network');
assert.equal(locator.hit([105,baseY+100],9),null,'blank map must not trigger a rail');
const seen=new Set();
locator.network.nearest([105,baseY+10],2);
assert.equal(locator.network.items,1);


// The RE4 train service crosses DB infrastructure 6107 -> 6179 at Berlin:
// clicking either measured part must select the same longer *service* corridor.
const svc=context.window.Railway07ServiceGroups;
const makeLine=(route,from,to,start,end,hint,late)=>{
 const track=leg(from,to,[0,5],late,1,route);
 track.label_hints=[[hint,150]];
 return {leg:track,grade:math.grade(math.metrics(track,'both'),'both'),
  parts:[part(start,end)],m:math.metrics(track,'both')};
};
const west=makeLine('6107','Wustermark','Elstal',100,104,'RE4',32);
const east=makeLine('6179','Berlin-Staaken','Berlin-Spandau',106,110,'RE4',12);
const services=svc.joinServiceCorridors(math.buildCorridors([west,east]),net,'both');
assert.equal(services.joined,1);
assert.equal(services.corridors.length,1);
assert.equal(services.corridors[0].serviceName,'RE4');
assert.equal(services.corridors[0].members.length,2);
assert.equal(services.corridors[0].m.late,22);
assert.equal(services.corridors[0].gradeVariation,true);
assert.equal(services.map.get(services.corridors[0]),undefined);
const other=makeLine('6179','Berlin-Staaken','Berlin-Spandau',106,110,'RE6',12);
assert.equal(svc.joinServiceCorridors(math.buildCorridors([west,other]),net,'both').joined,0,
 'Different service labels must not be joined just for appearance');


// One click selects an entire city-to-city passenger chain while retaining
// exact raw counts and stopping at a named metropolitan railway hub.
const city=context.window.Railway07Cities;
const cityLeg=(from,to,lo,hi,late=30)=>{
 const x=leg(from,to,[lo,hi],late,2,'7000');
 x.label_hints=[['RE11',200]];return x;
};
const t1=cityLeg('Erfurt Hbf','Neudietendorf',0,15);
const t2=cityLeg('Neudietendorf','Arnstadt Hbf',15,27);
const t3=cityLeg('Arnstadt Hbf','Ilmenau',27,48,50);
const citem=x=>({leg:x,grade:math.grade(math.metrics(x,'both'),'both'),
 parts:[part(x.km_range[0]*3,x.km_range[1]*3)],m:math.metrics(x,'both')});
const input=[citem(t1),citem(t2),citem(t3)];
const resultCity=city.buildCityCorridors(input,'both');
assert.equal(resultCity.physicalEdges,3);
assert.equal(resultCity.corridors.length,2,'stop at Arnstadt city interchange');
const erToAr=resultCity.corridors.find(g=>g.cityFrom==='Erfurt'&&g.cityTo==='Arnstadt');
assert.ok(erToAr);
assert.equal(erToAr.members.length,2);
assert.equal(erToAr.m.onTime,70);
const arToIl=resultCity.corridors.find(g=>g.cityFrom==='Arnstadt'&&g.cityTo==='Ilmenau');
assert.ok(arToIl);assert.equal(arToIl.m.onTime,50);
// Reverse direction contributes counts, never a separate duplicate line.
const reverse2=cityLeg('Arnstadt Hbf','Neudietendorf',15,27,20);
const both=city.buildCityCorridors([...input,citem(reverse2)],'both');
const match=both.corridors.find(g=>g.cityFrom==='Erfurt'&&g.cityTo==='Arnstadt');
assert.equal(match.members.length,3);
assert.equal(match.m.onTime,100-(30+30+20)/3);
assert.equal(city.cityName('Berlin-Spandau'),'Berlin');


// User's A--green--red--green--B contract: original official geometry survives
// even without any timetable observations; no new fake measured segments.
const network=new context.window.Railway07Continuity.Backbone();
network.add('7000',part(100,104));
network.add('7000',part(104,108));
network.add('7000',part(108,112));
assert.equal(network.official,3);
assert.equal(network.all.length,3);
const trace=network.unobserved('7000',[105,baseY]);
assert.ok(trace.parts.length>=3,'green backbone must span the missing middle');
const active=network.setActive([{members:[{leg:{route:'7000'}}]}]);
assert.equal(active.sections,3);
assert.equal(active.all,3);
assert.equal(network.all.length,3,'changing observed categories cannot delete official track');
assert.equal(network.unobserved('7000',[110,baseY]).parts.length,3);
assert.equal(network.unobserved('UNKNOWN',[110,baseY]).parts.length,0);
const observedGap={
 startStation:'A Hbf',endStation:'B Hbf',
 members:[
  {leg:{route:'7000',from_station:'A Hbf',to_station:'Middle A'},
   parts:[part(100,104)]},
  {leg:{route:'7000',from_station:'Middle B',to_station:'B Hbf'},
   parts:[part(108,112)]}
 ]
};
const whole=network.full(observedGap);
assert.ok(whole&&whole.length>=3,'a city selection must follow all 3 official track sections');
const total=whole.reduce((n,p)=>n+(p.maxX-p.minX),0);
assert.ok(total>=11.9,'highlight must span from city A to city B, not only the green gap');
assert.equal(network.full(observedGap),whole,'verified full route cached per corridor');



// The user's two sketches: A--same RED--RED--GREEN--B must select the entire
// contiguous red stretch from either red piece, and ONLY green from green.
const shade=context.window.Railway07ColorRuns;
const colorObs=(from,to,start,end,late,gr)=>{
 const l=leg(from,to,[start,end],late,2,'7000');
 const m=math.metrics(l,'both',100);
 return {leg:l,m,grade:gr,parts:[part(start,end)]};
};
const sr1=colorObs('A','X',100,104,45,2);
const sr2=colorObs('X','Y',104,108,43,2);
const sg=colorObs('Y','B',108,112,8,0);
const colouredGroup={
 startStation:'A',endStation:'B',cityFrom:'A',cityTo:'B',
 serviceName:'RE7',members:[sr1,sr2,sg],grade:2
};
const fakeDB={full:()=>[part(100,104),part(104,108),part(108,112)]};
const runs=shade.forCorridor(colouredGroup,fakeDB);
assert.equal(runs.length,2,'adjacent identically coloured records are one clickable run');
assert.deepEqual(Array.from(runs,x=>x.grade),[2,0]);
const rA=shade.findRun(runs,[102,baseY],2,2.5);
const rX=shade.findRun(runs,[106,baseY],2,2.5);
const rB=shade.findRun(runs,[110,baseY],0,2.5);
assert.strictEqual(rA,rX,'either red section must highlight the same complete red run');
assert.notStrictEqual(rA,rB,'a differently coloured section must select separately');
assert.ok(rA.parts.reduce((n,p)=>n+p.maxX-p.minX,0)>7.5);
assert.ok(rB.parts.reduce((n,p)=>n+p.maxX-p.minX,0)>2.8);
assert.equal(rA.members.length,2);
assert.equal(rA.m.onTime,56);
assert.equal(rB.m.onTime,92);
assert.equal(colouredGroup.members.length,3,'original observed records unchanged');
// An unobserved middle GREEN gap cannot magically contribute two new samples.
const missingGroup={...colouredGroup,members:[sr1,sr2],_colorRuns:null};
const noDataRuns=shade.forCorridor(missingGroup,fakeDB);
assert.ok(noDataRuns.some(x=>x.grade===0&&x.m.onTime===null),
 'green without timetable samples stays selectable and numeric KPI missing');


// A railway siding joining at X must not truncate the A--B green selection
// when the straight physical continuation is unambiguous.
const switches=new context.window.Railway07Continuity.Backbone();
switches.add('8100',part(100,104));
switches.add('8100',part(104,108));
switches.add('8100',part(108,112));
switches.add('8100',geom.shape([104,baseY,104,baseY+4]));
const trunk=switches.walkPhysical('8100',[101,baseY],20);
assert.ok(trunk.parts.length>=3,'a minor turnout must not fragment the main track');
assert.equal(trunk.parts.includes(switches.perRoute.get('8100')[3]),false,
 'a siding must not be mistaken for the A--B trunk');
// Green A--RED middle--GREEN B must form 3 physical click regions.
const fakeRisk=[colorObs('X','Y',104,108,45,2)];
const sourceCut=shade.forOfficial(switches.unobserved('8100',[105,baseY]),fakeRisk);
const gA=shade.findRun(sourceCut,[101,baseY],0,3);
const gB=shade.findRun(sourceCut,[111,baseY],0,3);
assert.ok(gA&&gB&&gA!==gB,
 'green must be split into two separate runs by a measured red section');
assert.ok(gA.unobserved&&gB.unobserved&&gA.m.onTime===null,
 'missing-data green cannot inherit the red interval statistics');

console.log('PASS railway pure geometry, weighted rates, branches, km gaps and pooled counts');
