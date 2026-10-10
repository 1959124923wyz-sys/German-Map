#!/usr/bin/env node
'use strict';
/* Build the ONLY legitimate county-level employment layer:
   two dates, SAME WZ2008_C scope, SAME original statistical family, SAME place-of-work basis.
   The source CSV must be supplied separately; no values inferred from events or news.
   Usage:
      node topics/industry/scripts/build_county_employment.cjs \
        --input /path/to/verified-official.csv \
        --output topics/industry/data/county-employment.json

   CSV columns:
   ags,year,manufacturing_employees,industry_definition,workplace_basis,source_table,source_url
   Suppression marks '.' '/' '-' are treated as missing (never numeric zero).
*/
const fs=require('node:fs');
const path=require('node:path');
const args=process.argv.slice(2);
function getArg(k){const idx=args.indexOf(k);return idx<0?null:args[idx+1]}
function fail(msg){throw Error('INDUSTRY_EMPLOYMENT_IMPORT: '+msg)}
const input=getArg('--input'),output=getArg('--output');
if(!input||!output)fail('Both --input and --output are required');
const lines=fs.readFileSync(input,'utf8').replace(/^\uFEFF/,'').replace(/\r\n/g,'\n').trim().split('\n');
if(lines.length<3)fail('At least two year rows are needed');
function csvParse(line){
 const cells=[];let cur='',quoted=false;
 for(let i=0;i<line.length;i++){
  const ch=line[i];
  if(ch==='"'){if(quoted&&line[i+1]==='"'){cur+='"';i++}else quoted=!quoted}
  else if(ch===','&&!quoted){cells.push(cur);cur=''}else cur+=ch;
 }
 if(quoted)fail('Unclosed CSV quote');
 cells.push(cur);return cells.map(x=>x.trim());
}
const cols=csvParse(lines[0]);
const expected=['ags','year','manufacturing_employees','industry_definition','workplace_basis','source_table','source_url'];
if(expected.some(k=>!cols.includes(k)))fail('Missing columns '+expected.filter(k=>!cols.includes(k)).join(','));
const crosswalk=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/ags-crosswalk-402-to-400.json'),'utf8'));
const canonical=new Set(crosswalk.features.map(x=>x.canonical_ags));
if(canonical.size!==400)fail('Canonical district index must cover 400 modern districts');
const byAgs=new Map(),globalYears=new Set(),methodologies=new Set(),skipped=[];
for(let i=1;i<lines.length;i++){
 if(!lines[i].trim())continue;
 const values=csvParse(lines[i]);if(values.length!==cols.length)fail('Invalid CSV column count at line '+(i+1));
 const r=Object.fromEntries(cols.map((k,j)=>[k,values[j]]));
 if(!/^\d{5}$/.test(r.ags)||!canonical.has(r.ags))fail('Unknown/non-current AGS '+r.ags+' line '+(i+1));
 if(!/^20\d{2}$/.test(r.year))fail('Invalid year '+r.year);
 if(r.industry_definition!=='WZ2008_C')fail('Only pure WZ2008_C manufacturing, not B+C or all-industry series: '+r.ags);
 if(r.workplace_basis!=='workplace')fail('Only workplace-based counts are supported');
 if(!r.source_table||!r.source_url.startsWith('https://'))fail('Public official source identification missing');
 const key=r.ags+'|'+r.year;
 if(!byAgs.has(r.ags))byAgs.set(r.ags,new Map());
 if(byAgs.get(r.ags).has(r.year))fail('Duplicate AGS/year '+key);
 const m=r.manufacturing_employees;
 let jobs=null;
 if(['','.','/','-','—','x','X','..'].includes(m)){skipped.push(key)}
 else {
  if(!/^\d+$/.test(m))fail('Invalid employee count at '+key+': '+m);
  jobs=Number(m);if(!Number.isSafeInteger(jobs)||jobs<0)fail('Employee count overflow/negative at '+key);
 }
 byAgs.get(r.ags).set(r.year,{jobs,source_table:r.source_table,source_url:r.source_url});
 globalYears.add(r.year);
 methodologies.add(r.source_table);
}
const years=[...globalYears].sort();
if(years.length!==2||years[0]!=='2019'||Number(years[1])<2020)fail('Require 2019 baseline and exactly one latest comparison year');
if(methodologies.size!==1)fail('A single source table/methodology per build is required');
const result={schema_version:'2.0',metric:'manufacturing_employment_change_pct_2019_latest',
 source_class:'official_validated',series:'WZ2008_C_employees_at_workplace',
 status:'partially_or_fully_validated', years,source_table:[...methodologies][0],
 source_url:null,region_key:'5_digit_Kreis_AGS_canonical_current',records:{},
 exclusions:{suppressed_or_missing_cells:skipped,unmatched_or_missing_ags:[]},
 warning:'No data / suppressed cells are null, not zero; comparison describes sampled employers only to the extent defined by the official statistical source.'};
for(const ags of canonical){
 const rows=byAgs.get(ags),a=rows?.get(years[0]),b=rows?.get(years[1]);
 if(!a||!b||a.jobs===null||b.jobs===null||a.jobs===0){result.exclusions.unmatched_or_missing_ags.push(ags);continue}
 if(a.source_table!==b.source_table)
  fail('Source methodology changed across years for AGS '+ags+'; compare like for like only');
 result.records[ags]={change_pct:Math.round((b.jobs/a.jobs-1)*10000)/100,
  employees_2019:a.jobs,employees_latest:b.jobs,latest_year:Number(years[1]),
  source_url:b.source_url,source_url_2019:a.source_url,source_url_latest:b.source_url};
}
result.source_url=[...byAgs.values()].flatMap(x=>[...x.values()]).find(x=>x.source_url)?.source_url||null;
result.coverage={valid_districts:Object.keys(result.records).length,possible_districts:400};
if(!result.coverage.valid_districts)fail('No validated comparable districts; refuse to overwrite placeholder');
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');
console.log('Validated WZ2008_C county jobs '+years.join(' vs ')+': '+result.coverage.valid_districts+'/400. Remaining counties display missing, never news-count fallback.');
