
(function(){
  const msg=document.getElementById('v09AuditMessage');
  const panel=document.getElementById('v09AuditStats');
  const file=document.getElementById('linkFile');
  if(!msg||!panel||!file)return;
  function row(label,value){
    const p=document.createElement('div');p.className='station-rank';
    const a=document.createElement('span'),b=document.createElement('b');a.textContent=label;b.textContent=value;
    p.append(a,b);panel.appendChild(p);
  }
  function integer(n){return typeof n==='number'&&Number.isFinite(n)?n.toLocaleString('zh-CN'):'—'}
  function refresh(){
    panel.replaceChildren();
    const audit=(typeof chainData!=='undefined' && chainData && chainData.qa)?chainData.qa:null;
    if(!audit){
      msg.textContent='逐车次区间层：尚未加载真实逐停站记录；未计算或展示任何区间准点率。';
      row('官方基础设施','已接入');row('精选车站实测','已接入');row('逐车次相邻区间','待载入');
      row('最终取消原因','无足够证据');return;
    }
    const info=chainData.source||{};
    const eligible=(chainData.links||[]).filter(x=>x.planned_pairs >= (typeof minLinkPairs==='function'?minLinkPairs():100)).length;
    msg.textContent='已内置核验汇总；下列是 API 停靠记录匹配质量指标，禁止将它们解释为列车整趟取消率或铁路区间故障率。数据月份：'+(info.month||'2026-09')+'。';
    row('输入停靠记录',integer(audit.input_rows));
    row('计划停靠记录',integer(audit.planned_stop_rows));
    row('可识别相邻站配对',integer(audit.route_identified_adjacent_pairs));
    row('无法匹配或有歧义的配对',integer(audit.unmapped_or_ambiguous_pairs));
    row('拒绝站序断档',integer(audit.rejected_nonconsecutive_pairs));
    row('拒绝时间异常',integer(audit.rejected_nonchronological_pairs));
    row('拒绝重复站序',integer(audit.rejected_ambiguous_trip_groups));
    row('缺失官方轨道几何',integer(audit.missing_official_geometry_pairs));
    row('生成几何区间',integer((chainData.links||[]).length));
    row('当前门槛达标的方向性区间',integer(eligible));
    row('疑似后段取消线索',integer(audit.possible_partial_cancel_events));
  }
  file.addEventListener('change',()=>setTimeout(refresh,500));
  document.querySelectorAll('#perfView button').forEach(b=>b.addEventListener('click',()=>setTimeout(refresh,30)));
  refresh();window.__V09_REFRESH_AUDIT__=refresh;
})();
