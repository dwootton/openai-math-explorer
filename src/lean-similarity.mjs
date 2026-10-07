import {normalize,rankNeighbors} from './lenses.mjs';
export function leanFamilyVectors(proofs){
 const families=new Map();
 for(const proof of proofs){if(!proof.solutionPath||!proof.vector?.length)throw Error('Missing solution embedding');if(!families.has(proof.familyId))families.set(proof.familyId,new Map());families.get(proof.familyId).set(proof.solutionPath,proof);}
 return [...families].sort(([a],[b])=>a.localeCompare(b)).map(([id,byPath])=>{const modules=[...byPath.values()].sort((a,b)=>a.solutionPath.localeCompare(b.solutionPath));const dimensions=modules[0].vector.length;if(modules.some(m=>m.vector.length!==dimensions||!m.vector.every(Number.isFinite)))throw Error('Invalid Lean vector');const vector=normalize(Array.from({length:dimensions},(_,j)=>modules.reduce((s,m)=>s+m.vector[j],0)/modules.length));if(!vector)throw Error('Degenerate Lean vector');return{id,vector,modules:modules.map(({id,solutionPath,chunks})=>({id,solutionPath,chunks}))}});
}
export function leanNeighbors(families){return new Map(families.map(f=>[f.id,rankNeighbors(f.vector,families,f.id).slice(0,8).map(n=>({id:n.id,score:n.score}))]));}
