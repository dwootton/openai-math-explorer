import fs from 'node:fs/promises';
import {UMAP} from 'umap-js';
import {referenceSimilarity} from '../src/reference-similarity.mjs';
const input=JSON.parse(await fs.readFile('.cache/references-matched.json','utf8'));
const map=JSON.parse(await fs.readFile('public-shell/explore/map-data.json','utf8'));
const {ids,matrix,neighbors,frequency,idf}=referenceSimilarity(input.families);
if(ids.join()!==map.docs.map(d=>d.id).join())throw Error('Reference IDs must align with map docs');
const active=ids.map((id,i)=>i).filter(i=>neighbors[i].length),isolated=ids.map((id,i)=>i).filter(i=>!neighbors[i].length);
let seed=42;const random=()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296};
const k=Math.min(15,active.length-1),knn=active.map(i=>active.map((j,index)=>({index,distance:i===j?0:1-matrix[i][j]})).sort((a,b)=>a.distance-b.distance||a.index-b.index).slice(0,k));
const umap=new UMAP({nNeighbors:k,minDist:.12,nEpochs:350,random,distanceFn:(a,b)=>a[0]===b[0]?0:1-matrix[a[0]][b[0]]});
umap.setPrecomputedKNN(knn.map(row=>row.map(x=>x.index)),knn.map(row=>row.map(x=>x.distance)));
let points=umap.fit(active.map(i=>[i]));
const mx=points.reduce((s,p)=>s+p[0],0)/points.length,my=points.reduce((s,p)=>s+p[1],0)/points.length;
const scale=Math.sqrt(points.reduce((s,p)=>s+(p[0]-mx)**2+(p[1]-my)**2,0)/points.length);
points=points.map(p=>[(p[0]-mx)/scale,(p[1]-my)/scale]);
// Rotate/reflection-align to the existing view without changing distances or rankings.
const reference=map.modes.none.points;let best;
for(const flip of [1,-1]){const ps=points.map(([x,y])=>[x,y*flip]);let a=0,b=0;ps.forEach((p,i)=>{const r=reference[active[i]];a+=p[0]*r[0]+p[1]*r[1];b+=p[0]*r[1]-p[1]*r[0]});const angle=Math.atan2(b,a),c=Math.cos(angle),s=Math.sin(angle);const out=ps.map(([x,y])=>[x*c-y*s,x*s+y*c]);const error=out.reduce((sum,p,i)=>sum+(p[0]-reference[active[i]][0])**2+(p[1]-reference[active[i]][1])**2,0);if(!best||error<best.error)best={out,error}}
const coords=ids.map(()=>[0,0]);active.forEach((i,j)=>coords[i]=best.out[j]);
// Isolates have no evidence-based location: put them on a separate bottom row.
const bottom=Math.max(...best.out.map(p=>p[1]))+.3;
isolated.forEach((i,j)=>coords[i]=[(j-(isolated.length-1)/2)*.13,bottom]);
const top=neighbors.map(list=>list.slice(0,8).map(n=>({id:n.id,score:+n.score.toFixed(7),shared:n.shared.length})));
map.modes.references={points:coords,neighbors:top,counts:ids.map(id=>input.families[id].length),isolated:isolated.map(i=>ids[i]),method:'idf-cosine-shared-shrinkage-v1'};
await fs.writeFile('public-shell/explore/map-data.json',JSON.stringify(map));
const works=Object.fromEntries(Object.entries(input.works).map(([id,w])=>[id,{...w,idf:+idf.get(id).toFixed(6)}]));
await fs.writeFile('public-shell/explore/reference-data.json',JSON.stringify({commit:input.commit,method:map.modes.references.method,extraction:input.extraction,families:input.families,works:Object.fromEntries(Object.entries(works).filter(([,w])=>w.families.length>1))}));
const report={...input.extraction,families:ids.length,withSharedWorks:active.length,isolated:isolated.map(i=>ids[i]),totalPairs:neighbors.reduce((n,row)=>n+row.length,0)/2,largestLists:ids.map(id=>({id,count:input.families[id].length})).sort((a,b)=>b.count-a.count).slice(0,10),examples:['001','003','074','196','197','073','166'].map(id=>({id,neighbors:neighbors[ids.indexOf(id)].slice(0,3).map(n=>({...n,shared:n.shared.map(key=>works[key].title)}))}))};
await fs.writeFile('public-shell/explore/reference-analysis.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
