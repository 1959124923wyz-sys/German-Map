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
 if(d?.meta?.year!==2025||!d.mortality_by_state||!d.selected_offence_codes_by_state)throw Error('州级数据缺失');
 if(Object.keys(d.mortality_by_state).length<9)throw Error('死亡数据覆盖数异常');
 for(const [state,r]of Object.entries(d.mortality_by_state)){
  if(!state||!Number.isInteger(r.cases)||r.cases<0||!/^https:\/\//.test(r.source_url))throw Error('死亡来源校验失败');
 }
 for(const o of Object.values(d.selected_offence_codes_by_state)){
  if(!/^https:\/\//.test(o.source_url)||!Array.isArray(o.groups))throw Error('州案件来源格式错误');
  for(const row of o.groups)if(!row.name||!Number.isInteger(row.general)||!Number.isInteger(row.trade)||row.general<0||row.trade<0)throw Error('州分类数字异常');
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
 const death=d.mortality_by_state[state],off=d.selected_offence_codes_by_state[state];
 head.textContent=death||off
  ?'州级补充：'+(death?'死亡 '+fmt(death.cases)+' 人':'')+(death&&off?' · ':'')+(off?'毒品罪名细分':'')
  :'州级补充：暂无核实数字';
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
  sect.append(table,item('p',off.notes,'note'));
  const src=item('div','','evidence-source');src.append(sourceLink('警察统计原表：'+off.source_title+' ↗',off.source_url));sect.append(src);
  body.append(sect);
 } else body.append(item('p','本州大麻、可卡因、冰毒、海洛因罪名细分原表尚未核实，不依据全国比例估算。','note'));
 body.append(item('p','不同指标不可相加：死亡记录、警方案件、污水残留并不等于吸毒人口。','evidence-caveat'));
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