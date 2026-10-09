(() => {
'use strict';
const $=id=>document.getElementById(id);
const fmt=x=>Number(x).toLocaleString('zh-CN',{maximumFractionDigits:1});
let data=null,pending=null,selected='';
function item(tag,text,cls){
 const e=document.createElement(tag);e.textContent=String(text||'');if(cls)e.className=cls;return e;
}
function sourceLink(title,url){
 const e=item('a',title);e.href=url;e.target='_blank';e.rel='noopener noreferrer';return e;
}
function validate(d){
 if(d?.meta?.year!==2025||!d.mortality_by_state||!d.selected_offence_codes_by_state||!d.other_health_indicators_by_state)throw Error('州级数据缺失');
 if(Object.keys(d.mortality_by_state).length<9)throw Error('死亡数据覆盖数异常');
 for(const [state,r]of Object.entries(d.mortality_by_state)){
  if(!state||!Number.isInteger(r.cases)||r.cases<0||!/^https:\/\//.test(r.source_url))throw Error('死亡来源校验失败');
 }
 for(const record of Object.values(d.other_health_indicators_by_state)){
  if(!/^https:\/\//.test(record.source_url)||!Array.isArray(record.metrics))throw Error('健康数据来源失效');
  for(const row of record.metrics)
   if(!row.name||!Number.isInteger(row.cases)||!Number.isInteger(row.previous_2024)||row.cases<0||row.previous_2024<0)
    throw Error('医院记录非法');
 }
 for(const [state,trend] of Object.entries(d.long_term_trends_by_state||{})){
  if(!state||!/^https:\\/\\//.test(trend.source_url)||
    !Array.isArray(trend.records)||trend.records.length!==5||
    trend.break_year!==2024||!trend.break_label||
    !trend.records.every((r,i)=>r.year===2021+i&&Number.isInteger(r.cases)&&r.cases>=0))
   throw Error('年度趋势来源、年份或法律断点异常');
 }
 for(const o of Object.values(d.selected_offence_codes_by_state)){
  if(!/^https:\/\//.test(o.source_url)||!Array.isArray(o.groups))throw Error('州案件来源格式错误');
  for(const row of o.groups)
   if(!row.name||!Number.isInteger(row.general)||!Number.isInteger(row.trade)||row.general<0||row.trade<0)
     throw Error('州分类数字异常');
  for(const row of o.additional_metrics||[])
   if(!row.name||!Number.isInteger(row.cases)||row.cases<0||!row.code||
      (row.previous_2024!==undefined&&(!Number.isInteger(row.previous_2024)||row.previous_2024<0)))
     throw Error('州新增分项缺失或无效');
 }
}
async function load(){
 if(data)return data;
 if(!pending)pending=fetch('data/state_health_offences_2025.json',{cache:'no-store'})
   .then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()})
   .then(d=>{validate(d);data=d;return d})
   .finally(()=>pending=null);
 return pending;
}
function render(state,d){
 if(selected!==state)return;
 const head=$('region-evidence-head'),body=$('region-evidence-body');
 if(!head||!body)return;
 const death=d.mortality_by_state[state],off=d.selected_offence_codes_by_state[state],health=d.other_health_indicators_by_state[state];
 const tags=[];
 if(death)tags.push('死亡 '+fmt(death.cases)+' 人');
 if(off)tags.push('毒品罪名细分');
 if(health)tags.push('健康诊断数据');
 head.textContent=tags.length?'州级补充：'+tags.join(' · '):'州级补充：暂无核实数字';
 body.replaceChildren();
 if(death){
  const sect=item('div','','evidence-group');
  sect.append(item('h5','2025年毒品相关死亡 · 全州'),item('strong',fmt(death.cases)+' 人','evidence-mortality-number'));
  if(death.previous_2024!==null){
   const delta=death.cases-death.previous_2024;
   sect.append(item('p','2024年：'+fmt(death.previous_2024)+' 人 · 较上年'+(delta>0?'增加':delta<0?'减少':'持平')+' '+fmt(Math.abs(delta))+' 人','evidence-trend'));
  } else sect.append(item('p','2024年可比死亡人数：未核实','evidence-trend'));
  if(Number.isFinite(death.rate_per_100k))
   sect.append(item('p','官方每10万人死亡率：'+fmt(death.rate_per_100k)+'（2024年 '+fmt(death.rate_previous_2024)+'）','evidence-trend'));
  sect.append(item('p',death.note,'note'));
  const src=item('div','','evidence-source');
  src.append(sourceLink('查看来源：'+death.source_title+' ↗',death.source_url));
  sect.append(src);
  if(!['state_police','state_government'].includes(death.source_type))
   sect.append(item('p','此数值由公共媒体或专业机构引述，尚待独立官方原表交叉核验。','note'));
  body.append(sect);
 }else body.append(item('p','本州2025年死亡人数尚未取得可靠的对应统计；不表示死亡人数为零。','note'));
 if(off){
  const sect=item('div','','evidence-group');
  sect.append(item('h5','2025年按物质统计的指定警方案件'));
  if(off.groups.length) {
   const table=document.createElement('table');table.className='evidence-offence-table';
   const header=document.createElement('thead'),line=document.createElement('tr');
   for(const t of ['物质','一般违法','贩卖/走私'])line.append(item('th',t));
   header.append(line);table.append(header);
   const tbody=document.createElement('tbody');
   for(const cat of off.groups){
    const tr=document.createElement('tr');
    tr.append(item('th',cat.name),item('td',fmt(cat.general)),item('td',fmt(cat.trade)));
    const codeRow=document.createElement('tr');codeRow.className='evidence-code-row';
    const td=item('td',cat.law+' · PKS '+(cat.general_code||'州局报告')+' / '+(cat.trade_code||'州局报告'));
    td.colSpan=3;codeRow.append(td);tbody.append(tr,codeRow);
   }
   table.append(tbody);
   sect.append(table);
  }
  if(off.additional_metrics?.length){
   sect.append(item('h5','其他已核实分项 · 口径各异','evidence-subheading'));
   const table=document.createElement('table');table.className='evidence-offence-table';
   const tbody=document.createElement('tbody');
   for(const row of off.additional_metrics){
     const line=document.createElement('tr');
     line.append(item('th',row.name),item('td',fmt(row.cases)));
     tbody.append(line);
     const note=document.createElement('tr');note.className='evidence-code-row';
     const td=item('td',row.code+
       (Number.isInteger(row.previous_2024)?' · 2024年 '+fmt(row.previous_2024)+' 起':'')+
       (row.note?' · '+row.note:''));
     td.colSpan=2;note.append(td);tbody.append(note);
   }
   table.append(tbody);sect.append(table);
  }
  sect.append(item('p',off.notes,'note'));
  const src=item('div','','evidence-source');src.append(sourceLink('警察统计原表：'+off.source_title+' ↗',off.source_url));sect.append(src);
  body.append(sect);
 } else body.append(item('p','本州大麻、可卡因、冰毒、海洛因罪名细分原表尚未核实，不依据全国比例估算。','note'));
 const trend=d.long_term_trends_by_state?.[state];
 if(trend){
  const section=item('div','','evidence-group');
  section.append(item('h5','2021—2025年毒品案件趋势 · 全州'));
  // Two line segments rather than a continuous line: 2024 KCanG is a
  // legal/statistical break, not evidence of declining drug consumption.
  const NS='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(NS,'svg');
  svg.classList.add('evidence-mini-trend');
  svg.setAttribute('viewBox','0 0 310 82');
  svg.setAttribute('role','img');
  svg.setAttribute('aria-label','警方登记毒品案件五年序列；2024年存在法定统计断点，不能跨断点直接比较');
  svg.style.cssText='display:block;width:100%;max-width:350px;height:auto;margin:8px 0 4px';
  const points=trend.records, vals=points.map(x=>x.cases);
  const lo=Math.min(...vals),hi=Math.max(...vals),span=Math.max(1,hi-lo);
  const xy=points.map((p,i)=>({x:20+i*66,y:15+33*(hi-p.cases)/span,p}));
  function node(tag,attrs,text){
   const n=document.createElementNS(NS,tag);
   for(const [k,v]of Object.entries(attrs))n.setAttribute(k,String(v));
   if(text!==undefined)n.textContent=String(text);
   return n;
  }
  svg.append(node('line',{x1:185,y1:4,x2:185,y2:64,stroke:'#8b949d','stroke-dasharray':'3 4','stroke-width':1}));
  for(const segment of [xy.filter(x=>x.p.year<2024),xy.filter(x=>x.p.year>=2024)])
   svg.append(node('polyline',{points:segment.map(a=>a.x+','+a.y).join(' '),fill:'none',stroke:'#8ab9a0','stroke-width':2.4,'stroke-linecap':'round','stroke-linejoin':'round'}));
  for(const a of xy){
   svg.append(node('circle',{cx:a.x,cy:a.y,r:3.2,fill:'#c6dfcc'}));
   svg.append(node('text',{x:a.x,y:a.y-7,'text-anchor':'middle',fill:'#dbe6df','font-size':10},fmt(a.p.cases)));
   svg.append(node('text',{x:a.x,y:76,'text-anchor':'middle',fill:'#b5c5cc','font-size':10},a.p.year));
  }
  section.append(svg);
  section.append(item('p','2024年法律统计断点 · 两段折线故意不连接','note'));
  section.append(item('p',trend.break_label+' '+trend.note,'note'));
  const source=item('div','','evidence-source');
  source.append(sourceLink('趋势原表：'+trend.source_title+' ↗',trend.source_url));
  section.append(source);
  body.append(section);
 }
 if(health){
  const sect=item('div','','evidence-group');
  sect.append(item('h5','2025年大麻相关健康诊断 · 全州'));
  const table=document.createElement('table');table.className='evidence-offence-table';
  const headRow=document.createElement('tr');
  for(const v of ['诊断项目','2025','2024'])headRow.append(item('th',v));
  const thead=document.createElement('thead');thead.append(headRow);table.append(thead);
  const tbody=document.createElement('tbody');
  for(const metric of health.metrics){
    const line=document.createElement('tr');
    line.append(item('th',metric.name),item('td',fmt(metric.cases)),item('td',fmt(metric.previous_2024)));
    tbody.append(line);
  }
  table.append(tbody);
  sect.append(table,item('p',health.note,'note'));
  const src=item('div','','evidence-source');
  src.append(sourceLink('查看资料来源：'+health.source_title+' ↗',health.source_url));sect.append(src);
  body.append(sect);
 }
 body.append(item('p','不同指标不可相加：死亡记录、警方案件、医院诊断与污水残留不等于吸毒人口。','evidence-caveat'));
}
function show(state){
 selected=state;
 const box=$('region-evidence'),head=$('region-evidence-head'),body=$('region-evidence-body');
 if(!box||!head||!body)return;
 box.open=false;head.textContent='州级补充资料 · 加载中';
 body.replaceChildren(item('p','读取带来源的2025年补充统计…','note'));
 load().then(d=>render(state,d)).catch(err=>{
  if(selected!==state)return;
  head.textContent='州级补充资料 · 暂不可用';
  body.replaceChildren(item('p','数据加载失败：'+err.message,'note'));
 });
}
window.GermanMapDrugEvidence=Object.freeze({show});
})();