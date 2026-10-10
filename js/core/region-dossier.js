/* Shared, dependency-free accessible dossier tabs. No external APIs or storage. */
(function(g){
 'use strict';
 const mount=function(root){
  if(typeof root==='string')root=document.getElementById(root);
  if(!root)throw Error('Missing regional dossier root');
  const buttons=[...root.querySelectorAll('[data-dossier-tab]')];
  const panes=[...root.querySelectorAll('[data-dossier-pane]')];
  const names=panes.map(x=>x.dataset.dossierPane);
  if(!buttons.length||names.length!==buttons.length||new Set(names).size!==names.length)
   throw Error('Dossier tabs mismatch');
  const id=root.id||'dossier';
  const nav=root.querySelector('.dossier-tabs');
  if(!nav)throw Error('Dossier tab list missing');
  nav.setAttribute('role','tablist');nav.setAttribute('aria-label','地区档案分页');
  let active=names[0];
  function choose(name,focus=false){
   if(!names.includes(name))return;
   active=name;
   buttons.forEach((b,i)=>{
    const on=b.dataset.dossierTab===name;
    b.id=id+'-tab-'+i;
    b.setAttribute('role','tab');b.setAttribute('aria-selected',String(on));
    b.setAttribute('aria-controls',id+'-pane-'+i);
    b.tabIndex=on?0:-1;
    if(on&&focus)b.focus();
   });
   panes.forEach((p,i)=>{
    p.id=id+'-pane-'+i;
    p.setAttribute('role','tabpanel');
    p.setAttribute('aria-labelledby',id+'-tab-'+i);
    p.hidden=p.dataset.dossierPane!==name;
   });
  }
  buttons.forEach((b,i)=>{
   b.type='button';
   b.addEventListener('click',()=>choose(b.dataset.dossierTab));
   b.addEventListener('keydown',e=>{
    if(!['ArrowRight','ArrowLeft','Home','End'].includes(e.key))return;
    e.preventDefault();
    const delta=e.key==='ArrowRight'?1:-1;
    const next=e.key==='Home'?0:e.key==='End'?buttons.length-1:(names.indexOf(active)+delta+buttons.length)%buttons.length;
    choose(names[next],true);
   });
  });
  choose(active);
  return Object.freeze({
   choose,
   show:show=>{root.hidden=!show;if(show)choose(names[0]);},
   active:()=>active
  });
 };
 g.GermanRegionDossier=Object.freeze({mount});
})(window);
