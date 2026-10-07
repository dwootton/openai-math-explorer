const seenKey='math-explorer:eli5-hint-seen';
export function initELI5Hint(){
 try{if(localStorage.getItem(seenKey)==='true')return;}catch{}
 const selector='#eli5, [data-eli5] [role="switch"], .subject-explain summary';
 const observed=new WeakSet();let shown=false;
 const observer=new IntersectionObserver(entries=>{for(const entry of entries){if(shown||!entry.isIntersecting||entry.intersectionRatio<.8||document.visibilityState!=='visible')continue;const target=entry.target,r=target.getBoundingClientRect();if(!r.width||!r.height)continue;shown=true;observer.disconnect();mutations.disconnect();try{localStorage.setItem(seenKey,'true')}catch{}showHint(target);break;}},{threshold:.8});
 function scan(){document.querySelectorAll(selector).forEach(el=>{if(!observed.has(el)){observed.add(el);observer.observe(el);}});}
 const mutations=new MutationObserver(scan);mutations.observe(document.body,{childList:true,subtree:true});scan();
 document.addEventListener('visibilitychange',()=>{if(!shown&&document.visibilityState==='visible'){observer.disconnect();document.querySelectorAll(selector).forEach(el=>observer.observe(el));}});
}
function showHint(target){
 const style=document.createElement('style');style.textContent='#eli5-hint{position:fixed;z-index:1000;max-width:250px;width:max-content;padding:10px 13px;border:1px solid #527566;border-radius:8px;background:#193d33;color:#e4fff3;box-shadow:0 5px 18px #0003;font:12px/1.5 system-ui;pointer-events:none}:root[data-theme="light"] #eli5-hint{background:#e8f3ef;color:#123e32;border-color:#789c8e}';document.head.append(style);
 const tip=document.createElement('div');tip.id='eli5-hint';tip.role='tooltip';tip.textContent='Want a simpler explanation? Try ELI5.';document.body.append(tip);const previous=target.getAttribute('aria-describedby');target.setAttribute('aria-describedby',[previous,tip.id].filter(Boolean).join(' '));
 function position(){const r=target.getBoundingClientRect();if(!target.isConnected||!r.width||!r.height||r.bottom<0||r.top>innerHeight){dismiss();return;}tip.style.maxWidth=Math.min(250,innerWidth-24)+'px';const t=tip.getBoundingClientRect();tip.style.left=Math.max(12,Math.min(innerWidth-t.width-12,r.right-t.width))+'px';tip.style.top=(r.bottom+t.height+8<innerHeight?r.bottom+8:Math.max(8,r.top-t.height-8))+'px';}
 function key(e){if(e.key==='Escape')dismiss();}
 function dismiss(){clearTimeout(timer);tip.remove();style.remove();if(previous)target.setAttribute('aria-describedby',previous);else target.removeAttribute('aria-describedby');removeEventListener('scroll',position,true);removeEventListener('resize',position);document.removeEventListener('pointerdown',dismiss,true);document.removeEventListener('keydown',key);visibility.disconnect();}
 const visibility=new IntersectionObserver(entries=>{if(entries.some(e=>!e.isIntersecting))dismiss();});visibility.observe(target);const timer=setTimeout(dismiss,10000);position();addEventListener('scroll',position,true);addEventListener('resize',position);document.addEventListener('pointerdown',dismiss,true);document.addEventListener('keydown',key);
}
