/* Atlas navigation: reveal active topic without interfering with user scroll. */
(() => {
 'use strict';
 function initialize(){
  const bar=document.querySelector('.header-main .modebar, .topbar .toplinks');
  if(!bar)return;
  let pending=false;
  function reveal(){
   if(pending)return;
   pending=true;
   requestAnimationFrame(()=>{
    pending=false;
    const active=bar.querySelector('.modebtn.active');
    if(!active)return;
    const rect=bar.getBoundingClientRect(),target=active.getBoundingClientRect(),margin=8;
    if(target.left<rect.left+margin)
     bar.scrollLeft-=rect.left+margin-target.left;
    else if(target.right>rect.right-margin)
     bar.scrollLeft+=target.right-(rect.right-margin);
   });
  }
  reveal();
  new MutationObserver(records=>{
   if(records.some(r=>r.target.classList?.contains('modebtn')))reveal();
  }).observe(bar,{subtree:true,attributes:true,attributeFilter:['class']});
  window.addEventListener('resize',reveal,{passive:true});
  window.addEventListener('pageshow',reveal);
 }
 if(document.readyState==='loading')
  document.addEventListener('DOMContentLoaded',initialize,{once:true});
 else initialize();
})();
