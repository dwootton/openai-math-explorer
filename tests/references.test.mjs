import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {referenceSimilarity} from '../src/reference-similarity.mjs';
test('shared rare works outweigh widely cited works and duplicate citations do not inflate similarity',()=>{
 const families={a:['common','rare'],b:['common','other'],c:['rare','else'],d:['common'],e:['common'],f:['common']};
 const out=referenceSimilarity(families),at=id=>out.ids.indexOf(id);
 assert.ok(out.matrix[at('a')][at('c')]>out.matrix[at('a')][at('b')]);
 assert.deepEqual(referenceSimilarity({...families,a:['common','rare','rare']}).matrix,out.matrix);
});
test('no overlap produces no neighbor, self-neighbors are excluded, and one shared work receives less support',()=>{
 const out=referenceSimilarity({a:['one'],b:['one'],c:['x','y','z'],d:['x','y','z'],e:[],f:['unshared']});
 assert.equal(out.matrix[0][1],1/3);assert.ok(out.matrix[2][3]>out.matrix[0][1]);
 assert.deepEqual(out.neighbors[4],[]);assert.deepEqual(out.neighbors[5],[]);
 out.neighbors.forEach((row,i)=>assert.ok(row.every(n=>n.id!==out.ids[i]&&n.shared.length>0&&n.score>0)));
});
test('published reference neighbors reproduce the evidence-based scores and have no invented edges',()=>{
 const root=process.env.RELEASE_DIR||'dist';
 const data=JSON.parse(fs.readFileSync(`${root}/explore/reference-data.json`));
 const map=JSON.parse(fs.readFileSync(`${root}/explore/map-data.json`));
 const result=referenceSimilarity(data.families),mode=map.modes.references;
 assert.equal(result.ids.length,372);assert.equal(data.extraction.manuscripts,722);assert.deepEqual(data.extraction.failedFiles,[]);
 map.docs.forEach((doc,i)=>{
  assert.equal(doc.id,result.ids[i]);assert.ok(mode.points[i].every(Number.isFinite));
  assert.equal(mode.counts[i],new Set(data.families[doc.id]).size);
  const expected=result.neighbors[i].slice(0,8);assert.deepEqual(mode.neighbors[i].map(n=>n.id),expected.map(n=>n.id));
  mode.neighbors[i].forEach((n,j)=>{assert.equal(n.shared,expected[j].shared.length);assert.ok(Math.abs(n.score-expected[j].score)<1e-7);expected[j].shared.forEach(key=>assert.ok(data.works[key].families.includes(doc.id)&&data.works[key].families.includes(n.id)));});
 });
});
