import fs from 'node:fs/promises';
import {UMAP} from 'umap-js';
import {lensBasis,project,rankNeighbors} from '../src/lenses.mjs';
const read=async n=>JSON.parse(await fs.readFile('dist/data/'+n+'.json','utf8'));
const [catalogue,semantic,presets,base]=await Promise.all(['catalogue','semantic','presets','map'].map(read));
const families=new Map(catalogue.families.map(f=>[f.id,f]));
function center(points){const mean=[0,1].map(j=>points.reduce((s,p)=>s+p[j],0)/points.length);const a=points.map(p=>p.map((v,j)=>v-mean[j]));const scale=Math.sqrt(a.reduce((s,p)=>s+p[0]**2+p[1]**2,0)/a.length);return a.map(p=>p.map(v=>v/scale));}
const reference=center(semantic.docs.map(d=>{const p=base.find(p=>p.id===d.id);return[p.x,p.y]}));
function align(points){let best;for(const flip of [1,-1]){const p=center(points).map(([x,y])=>[x,y*flip]);let a=0,b=0;for(let i=0;i<p.length;i++){a+=p[i][0]*reference[i][0]+p[i][1]*reference[i][1];b+=p[i][0]*reference[i][1]-p[i][1]*reference[i][0];}const theta=Math.atan2(b,a),c=Math.cos(theta),s=Math.sin(theta);const out=p.map(([x,y])=>[x*c-y*s,x*s+y*c]);const error=out.reduce((sum,v,i)=>sum+(v[0]-reference[i][0])**2+(v[1]-reference[i][1])**2,0);if(!best||error<best.error)best={out,error};}return best.out;}
const previous=await fs.readFile('public-shell/explore/map-data.json','utf8').then(JSON.parse).catch(()=>null);
const modes={};if(previous?.modes.references)modes.references=previous.modes.references;
for(const key of ['none','topics','methods']){
 const basis=key==='none'?null:lensBasis(presets[key].vectors,8).basis;
 const docs=semantic.docs.map(d=>({id:d.id,vector:basis?project(d.vector,basis):d.vector}));
 let coords=reference;
 if(basis){let seed=42;const random=()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296};coords=align(new UMAP({nNeighbors:15,minDist:.12,nEpochs:250,random}).fit(docs.map(d=>d.vector)));}
 modes[key]={points:coords,neighbors:docs.map(d=>rankNeighbors(d.vector,docs,d.id).slice(0,8).map(n=>({id:n.id,score:n.score})))};
 console.log('Computed',key);
}
const docs=await Promise.all(semantic.docs.map(async d=>{const f=families.get(d.id);const guide=JSON.parse(await fs.readFile('dist/explanations/'+d.id+'.json','utf8'));return{id:f.id,title:f.title,subject:f.subject,question:guide.question,idea:guide.idea,abstracts:f.papers.map(p=>p.abstract||'').join(' '),summary:f.summary,lean:!!f.leanDoc}}));
await fs.writeFile('public-shell/explore/map-data.json',JSON.stringify({subjects:catalogue.subjects,docs,modes,commit:catalogue.commit}));
