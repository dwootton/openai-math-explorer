let evidencePromise;
function loadEvidence(){return evidencePromise??=fetch('./reference-data.json?v=references-v1').then(r=>{if(!r.ok)throw Error('References could not be loaded. Try again.');return r.json()}).catch(e=>{evidencePromise=null;throw e})}
export function renderReferenceNeighbors(root,{selected,neighbors,byId,select,math,count}){
 const heading=document.createElement('small');heading.textContent='Nearest by shared references';root.append(heading);
 const context=document.createElement('p');context.className='reference-context';context.textContent=`${count} distinct works in this family’s extracted bibliographies.`;root.append(context);
 if(!neighbors.length){const p=document.createElement('p');p.className='reference-context';p.textContent='No shared works matched with another family. Citation variants may remain unmatched.';root.append(p);return;}
 for(const neighbor of neighbors){
  const row=document.createElement('div');row.className='reference-neighbor';
  const button=document.createElement('button');button.textContent=neighbor.id+' · '+byId.get(neighbor.id).title;button.onclick=e=>select(neighbor.id,e.shiftKey);row.append(button);math(button);
  const details=document.createElement('details'),summary=document.createElement('summary'),body=document.createElement('div');
  summary.textContent=neighbor.shared+' shared '+(neighbor.shared===1?'work':'works')+(neighbor.shared===1?' · limited evidence':'');details.append(summary,body);row.append(details);root.append(row);
  details.addEventListener('toggle',async()=>{
   if(!details.open||details.dataset.loaded)return;
   body.textContent='Loading shared works…';
   try{
    const data=await loadEvidence(),other=new Set(data.families[neighbor.id]);
    const shared=data.families[selected].filter(id=>other.has(id)).sort((a,b)=>data.works[b].idf-data.works[a].idf||a.localeCompare(b));
    body.replaceChildren();const list=document.createElement('ul');
    for(const id of shared){const work=data.works[id],item=document.createElement('li'),link=document.createElement('a');link.textContent=work.title;link.href=work.url;link.target='_blank';link.rel='noreferrer';item.append(link);if(work.authors){const meta=document.createElement('span');meta.textContent=[work.authors,work.year].filter(Boolean).join(' · ');item.append(meta)}const sources=document.createElement('span');sources.className='reference-sources';for(const family of [selected,neighbor.id]){const source=work.sources?.[family];if(!source)continue;const a=document.createElement('a');a.textContent=family+' bibliography ↗';a.href='https://github.com/openai/math/blob/'+data.commit+'/'+source.split('/').map(encodeURIComponent).join('/');a.target='_blank';a.rel='noreferrer';sources.append(a)}item.append(sources);list.append(item)}
    body.append(list);math(body);details.dataset.loaded='true';
   }catch(e){body.textContent=e.message}
  });
 }
}
