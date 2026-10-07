import { Matrix, SingularValueDecomposition } from 'ml-matrix';
export const normalize=v=>{const n=Math.hypot(...v);return n>1e-9?v.map(x=>x/n):null};
export const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
export function lensBasis(prompts,k=8){
 if(prompts.length<3)throw Error('Use at least three distinct prompts for a meaningful lens.');
 const d=prompts[0].length;
 if(!d||prompts.some(v=>v.length!==d||v.some(x=>!Number.isFinite(x))))throw Error('Invalid prompt vectors.');
 const mean=Array.from({length:d},(_,j)=>prompts.reduce((s,v)=>s+v[j],0)/prompts.length);
 const centered=prompts.map(v=>v.map((x,j)=>x-mean[j]));
 const svd=new SingularValueDecomposition(new Matrix(centered),{autoTranspose:true});
 const singular=svd.diagonal;const rank=singular.filter(x=>x>Math.max(1e-8,singular[0]*1e-6)).length;
 if(rank<2)throw Error('These prompts collapse to fewer than two independent directions. Try more varied prompts.');
 const keep=Math.min(k,rank,prompts.length-1); const basis=Array.from({length:keep},(_,j)=>svd.rightSingularVectors.getColumn(j));
 return {basis,rank:keep,variance:singular.slice(0,keep).reduce((s,x)=>s+x*x,0)/singular.reduce((s,x)=>s+x*x,0)};
}
export function project(v,basis){return normalize(basis.map(b=>dot(v,b)))}
export function rankNeighbors(query,items,exclude){return items.filter(x=>x.id!==exclude&&x.vector).map(x=>({...x,score:dot(query,x.vector)})).sort((a,b)=>b.score-a.score)}
export const PRESETS={
 topics:{name:'Mathematical objects',prompts:['A result about prime numbers and multiplicative functions.','A result about elliptic curves and arithmetic geometry.','A result about graphs and combinatorial structures.','A result about smooth manifolds and curvature.','A result about partial differential equations and regularity.','A result about operators and Banach spaces.','A result about groups and their representations.','A result about probability distributions and random processes.','A result about algorithms and computational complexity.','A result about algebraic varieties and cohomology.','A result about dynamical systems and ergodic measures.','A result about mathematical logic and definability.']},
 methods:{name:'Proof techniques',prompts:['A mathematical proof using induction and recursive constructions.','A mathematical proof using contradiction and compactness.','A mathematical proof using Fourier analysis and harmonic estimates.','A mathematical proof using probabilistic methods and concentration.','A mathematical proof using algebraic geometry and cohomology.','A mathematical proof using combinatorial counting and extremal arguments.','A mathematical proof using functional analysis and operator theory.','A mathematical proof using energy estimates and differential inequalities.','A mathematical proof using reductions and computational complexity.','A mathematical proof using spectral theory and eigenvalue estimates.','A mathematical proof using topology and fixed point theorems.','A mathematical proof using explicit constructions and counterexamples.']},
 outcomes:{name:'Kinds of results',prompts:['A theorem establishing existence of a mathematical object.','A theorem establishing uniqueness of a solution.','A theorem classifying all objects with specified properties.','A theorem giving an asymptotic formula with an error estimate.','A theorem proving an upper bound.','A theorem proving a lower bound.','A theorem proving irrationality or transcendence.','A theorem proving convergence or stability.','A theorem proving impossibility or undecidability.','A theorem constructing a counterexample.','A theorem proving an equivalence between mathematical structures.','A theorem describing a limiting probability distribution.']}
};
