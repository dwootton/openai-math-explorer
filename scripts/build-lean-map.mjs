import fs from 'node:fs/promises';
import {UMAP} from 'umap-js';
import {dot} from '../src/lenses.mjs';
import {leanFamilyVectors,leanNeighbors} from '../src/lean-similarity.mjs';
const proofs=JSON.parse(await fs.readFile('dist/data/proof-semantic.json','utf8'));
const map=JSON.parse(await fs.readFile('public-shell/explore/map-data.json','utf8'));
const families=leanFamilyVectors(proofs.docs),byId=new Map(families.map(f=>[f.id,f])),neighbors=leanNeighbors(families);
let seed=42;const random=()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296};
let points=new UMAP({nNeighbors:15,minDist:.12,nEpochs:300,random,distanceFn:(a,b)=>Math.max(0,1-dot(a,b))}).fit(families.map(f=>f.vector));
const mean=[0,1].map(j=>points.reduce((s,p)=>s+p[j],0)/points.length);points=points.map(p=>p.map((v,j)=>v-mean[j]));const scale=Math.sqrt(points.reduce((s,p)=>s+p[0]**2+p[1]**2,0)/points.length);points=points.map(p=>p.map(v=>v/scale));
const reference=families.map(f=>map.modes.none.points[map.docs.findIndex(d=>d.id===f.id)]);let best;
for(const flip of [1,-1]){const ps=points.map(([x,y])=>[x,y*flip]);let a=0,b=0;ps.forEach((p,i)=>{a+=p[0]*reference[i][0]+p[1]*reference[i][1];b+=p[0]*reference[i][1]-p[1]*reference[i][0]});const theta=Math.atan2(b,a),c=Math.cos(theta),s=Math.sin(theta),out=ps.map(([x,y])=>[x*c-y*s,x*s+y*c]);const error=out.reduce((sum,p,i)=>sum+(p[0]-reference[i][0])**2+(p[1]-reference[i][1])**2,0);if(!best||error<best.error)best={out,error}}
const coordinates=new Map(families.map((f,i)=>[f.id,best.out[i]]));
map.modes.lean={points:map.docs.map((d,i)=>coordinates.get(d.id)||map.modes.none.points[i]),neighbors:map.docs.map(d=>neighbors.get(d.id)||[]),counts:map.docs.map(d=>byId.get(d.id)?.modules.length||0),modules:map.docs.map(d=>byId.get(d.id)?.modules||[]),method:'normalized-mean-of-unique-solution-module-embeddings',coverage:families.length};
delete map.modes.methods;
await fs.writeFile('public-shell/explore/map-data.json',JSON.stringify(map));
console.log(JSON.stringify({families:families.length,unavailable:map.docs.length-families.length,uniqueModules:new Set(proofs.docs.map(p=>p.solutionPath)).size,kakeya:neighbors.get('074')||null,quasiRiemann:neighbors.get('003')},null,2));
