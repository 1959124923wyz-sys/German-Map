#!/usr/bin/env node
// Export the *complete derived* railway line index from the browser dataset.
// This index is generated from an authored prototype; it does NOT establish
// independent official source provenance or data licensing.
const path=require('node:path');
const fs=require('node:fs');
global.window={};
require(path.join(__dirname,'../data/network.js'));
const data=global.window.GermanRailway07Data;
if(!data||data.routes.length!==1546||data.sections.length!==33547)
  throw Error('07 dataset QA mismatch; update the reference baseline first');
const csv=(v)=>{
  const s=String(v??'');
  return /[",\r\n]/.test(s) ? '"'+s.replace(/"/g,'""')+'"' : s;
};
const cols=['Streckennummer','Streckenkurzname','中文常用名','境内原始区段数',
  '几何部件数','方向线段累计km(非营业里程)','电气化累计km','≥200速度线段累计km',
  '速度未知线段累计km','涉及联邦州','方向属性','运营点采样数'];
const all=new Set(),rows=[cols.join(',')];
for(const r of data.routes){
  if(all.has(r[0]))throw Error('duplicate route ID '+r[0]);
  all.add(r[0]);
  const row=[r[0],r[1],r[2],r[4],r[11],r[3],r[5],r[6],r[7],
    r[8].join(';'),Object.entries(r[10]).map(([k,v])=>k+'='+v).join('; '),r[12].length];
  rows.push(row.map(csv).join(','));
}
const out=path.join(__dirname,'../data/route-index.csv');
fs.writeFileSync(out,rows.join('\n')+'\n','utf8');
if(rows.length!==1547)throw Error('expected 1546 routes, got '+(rows.length-1));
console.log('PASS complete *derived* railway line index: '+(rows.length-1)+' routes, '+out);
