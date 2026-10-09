
(function(){
  function adapt(){
    const b=document.querySelector('#perfView button.active');const links=b?.dataset.view==='links';
    for(const id of ['perfType','perfMetric','minSample']){
      const n=document.getElementById(id)?.closest('.field');if(n)n.style.display=links?'none':'';
    }
    for(const id of ['perfCoverage','perfLegend']){
      const n=document.getElementById(id);if(n)n.style.display=links?'none':'';
    }
    const c=document.getElementById('chainSection');if(c)c.style.display=links?'':'none';
    const label=document.querySelector('#perfControl .subhead');
    if(label)label.textContent=links?'运行质量 · 2026年9月 · 地方运营商 / RB / RE / ICE 区间':'历史车站观测 · 2026年8—9月';
  }
  document.querySelectorAll('#perfView button').forEach(b=>b.addEventListener('click',()=>requestAnimationFrame(adapt)));
  document.getElementById('linkMinPairs')?.addEventListener('change',()=>requestAnimationFrame(()=>window.__V09_REFRESH_AUDIT__?.()));
  adapt();
})();
