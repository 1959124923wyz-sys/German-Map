/* Source-scoped 400-county PKS archive; not a national blended crime score.
 * Both independent data sources are already in memory. No extra fetches. */
(()=>{'use strict';
const el=id=>document.getElementById(id);
const root=el('crimeCountyDossier');
if(!root||!window.GermanRegionDossier)return;
const tabs=window.GermanRegionDossier.mount(root);
const specs=Object.freeze({
 violence:[
  ['violence','暴力犯罪总体'],
  ['serious_injury','严重及危险伤害'],
  ['robbery','抢劫'],
  ['sexual','性犯罪'],
  ['homicide','凶杀犯罪']
 ],
 property:[
  ['property_total','盗窃犯罪总体'],
  ['burglary','住宅入室盗窃'],
  ['bicycle_theft','自行车盗窃'],
  ['vehicle_theft','机动车盗窃'],
  ['theft_from_vehicle','车内／车上盗窃']
 ]
});
let selected=null,renderCount=0;
const fmt=x=>Number(x).toLocaleString('zh-CN',{maximumFractionDigits:1});
const resolved=(data,ags)=>{
 const value=data?.records?.[ags];
 const alias=data?.meta?.geometry_aliases?.[ags];
 return value||data?.records?.[alias]||null;
};
function metricRows(target,rec,group){
 target.replaceChildren();
 for(const [key,label] of specs[group]){
  const m=rec?.[key];
  const row=document.createElement('div');
  row.className='crime-county-metric';
  row.dataset.metric=key;
  const title=document.createElement('strong'),values=document.createElement('div'),details=document.createElement('small');
  title.textContent=label;
  values.className='crime-county-facts';
  const cases=document.createElement('b'),rate=document.createElement('b');
  cases.textContent=Number.isFinite(m?.cases)?fmt(m.cases)+' 起':'未公布';
  rate.textContent=Number.isFinite(m?.rate)?fmt(m.rate)+' /10万人':'未公布';
  values.append(cases,rate);
  details.textContent='较2024年：'+(m?.change||'未公布');
  row.append(title,values,details);target.append(row);
 }
}
function source(target,rec){
 const a=el(target);
 const url=rec?.source_url;
 const valid=typeof url==='string'&&/^https:\/\//i.test(url);
 a.hidden=!valid;
 if(valid)a.href=url;else a.removeAttribute('href');
}
function hide(){
 if(!root.hidden)tabs.show(false);
 selected=null;
}
function render(detail){
 const kind=detail?.kind,ags=detail?.ags;
 if(!['violence-county','property-county'].includes(kind)||!/^\d{5}$/.test(String(ags||''))){
  hide();return;
 }
 const api=window.__CRIME_MAP__;
 const v=resolved(api?.getPksData(),ags),p=resolved(api?.getPropertyData(),ags);
 if(!v&&!p){hide();return;}
 const mode=detail?.mode==='property'?'property':'violence';
 const key=ags+'|'+mode;
 if(selected===key&&!root.hidden)return;
 selected=key;renderCount++;
 const name=window.GermanPlaceNames?.byAGS(ags,v?.name||p?.name) ||v?.name||p?.name||ags;
 el('crimeCountyTitle').textContent=name+' · 2025年县级犯罪档案';
 metricRows(el('crimeCountyViolence'),v,'violence');
 metricRows(el('crimeCountyProperty'),p,'property');
 source('crimeCountyViolenceSource',v);
 source('crimeCountyPropertySource',p);
 tabs.show(true);
 if(mode==='property')tabs.choose('property');
}
document.addEventListener('crime:area-pinned',event=>render(event.detail));
window.__CRIME_COUNTY_DOSSIER__=Object.freeze({
 selected:()=>selected,
 visible:()=>!root.hidden,
 entries:group=>el(group==='property'?'crimeCountyProperty':'crimeCountyViolence').children.length,
 renders:()=>renderCount,
 active:()=>tabs.active()
});
})();
