"""Recompute every vector from its cached chunks and record comparable ranks."""
import json,pathlib,os,numpy as np
root=pathlib.Path(__file__).resolve().parents[1]
data_root=pathlib.Path(os.environ.get('DATA_DIR',str(root/'next-direct/data')))
audit=json.load(open(os.environ.get('AGGREGATION_AUDIT_PATH',str(root/'.cache/direct-aggregation.json'))))
for kind,name in [('topics','semantic'),('proofs','proof-semantic'),('leanFamilies','lean-family-semantic')]:
 data=json.load(open(data_root/f'{name}.json'))
 for d in data['docs']:
  keys=audit[kind][d['id']];v=np.mean([np.load(root/'.cache/direct-chunks'/f'{k}.npy') for k in keys],axis=0,dtype=np.float64);v/=np.linalg.norm(v)
  assert np.allclose(v,d['vector'],rtol=0,atol=1e-12),d['id']
 print('Verified',kind,len(data['docs']),flush=True)
t=json.load(open(data_root/'semantic.json'));l=json.load(open(data_root/'lean-family-semantic.json'));ids=[d['id'] for d in l['docs']];tb={d['id']:d['vector'] for d in t['docs']};a=np.array([tb[id] for id in ids]);b=np.array([d['vector'] for d in l['docs']]);ta=a@a.T;la=b@b.T;pairs=[]
for i,id in enumerate(ids):
 tr=sorted((j for j in range(len(ids)) if j!=i),key=lambda j:(-ta[i,j],ids[j]));lr=sorted((j for j in range(len(ids)) if j!=i),key=lambda j:(-la[i,j],ids[j]));
 if not lr:continue
 j=lr[0]
 pairs.append({'family':id,'leanNearest':ids[j],'topicRankWithinLeanCoveredFamilies':tr.index(j)+1,'leanRank':1,'topicCosine':float(ta[i,j]),'leanCosine':float(la[i,j])})
pairs.sort(key=lambda p:-p['topicRankWithinLeanCoveredFamilies'])
pathlib.Path(os.environ.get('COMPARISON_AUDIT_PATH',str(root/'public-shell/explore/comparison-audit.json'))).write_text(json.dumps({'candidateFamilies':ids,'comparison':'cosine, same candidate pool for both rankings','pairs':pairs}))
print('Comparable-rank audit written',len(ids),'families')
