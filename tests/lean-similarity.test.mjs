import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {leanFamilyVectors,leanNeighbors} from '../src/lean-similarity.mjs';
test('family Lean vectors deduplicate solution files and give unique modules equal weight',()=>{
 const a={id:'a',familyId:'001',solutionPath:'a.lean',vector:[1,0],chunks:10},b={id:'b',familyId:'001',solutionPath:'b.lean',vector:[0,1],chunks:1};
 const [family]=leanFamilyVectors([a,{...a,id:'alias'},b]);assert.equal(family.modules.length,2);assert.ok(Math.abs(family.vector[0]-Math.SQRT1_2)<1e-12);assert.equal(family.vector[0],family.vector[1]);
});
test('published Lean ranks use solution vectors only and never rank families without Lean',()=>{
 const root=process.env.RELEASE_DIR||'dist',proofs=JSON.parse(fs.readFileSync(`${root}/data/proof-semantic.json`)),map=JSON.parse(fs.readFileSync(`${root}/explore/map-data.json`));
 const families=leanFamilyVectors(proofs.docs),expected=leanNeighbors(families);assert.equal(families.length,235);assert.equal(map.modes.lean.coverage,235);assert.equal(map.modes.methods,undefined);
 map.docs.forEach((d,i)=>{const list=map.modes.lean.neighbors[i];assert.deepEqual(list,expected.get(d.id)||[]);assert.equal(map.modes.lean.counts[i]>0,expected.has(d.id));for(const n of list)assert.ok(expected.has(n.id)&&n.id!==d.id);});
 const kakeya=map.docs.findIndex(d=>d.id==='074');assert.equal(map.modes.lean.counts[kakeya],0);assert.deepEqual(map.modes.lean.neighbors[kakeya],[]);
});
