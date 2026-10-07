"""Same chunk encoder and aggregation for every semantic comparison."""
import sys,pathlib,json,hashlib,time
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from embedding_model import Embedder,MODEL,REVISION
out=ROOT/'next-direct/data';out.mkdir(parents=True,exist_ok=True);cache=ROOT/'.cache/direct-chunks';cache.mkdir(exist_ok=True)
model=Embedder();started=time.time();print('MODEL READY',flush=True)
meta={'model':MODEL,'revision':REVISION,'dimensions':768,'chunkTokens':1024,'overlapTokens':96,'prompt':'SentenceSimilarity','aggregation':'normalized-mean-of-unique-chunk-embeddings','comparison':'cosine','projection':None}
vectors={};texts={}
def register(text):
 if not text.strip():return []
 keys=[]
 for chunk in model.chunks(text):
  key=hashlib.sha256((REVISION+'SentenceSimilarity'+chunk).encode()).hexdigest();texts.setdefault(key,chunk);keys.append(key)
 return sorted(set(keys))
def encode_pending():
 pending=[]
 for k in texts:
  if k in vectors:continue
  p=cache/(k+'.npy')
  if p.exists():vectors[k]=np.load(p)
  else:pending.append(k)
 print('ENCODE',len(pending),'new chunks of',len(texts),flush=True)
 for i in range(0,len(pending),32):
  keys=pending[i:i+32];vs=model.encode([texts[k] for k in keys],'similarity',batch_size=32)
  for k,v in zip(keys,vs):vectors[k]=v;np.save(cache/(k+'.npy'),v)
  if i%320==0:print('CHUNKS',i+len(keys),'/',len(pending),'elapsed',round(time.time()-started),flush=True)
def vector(keys):
 if not keys:raise ValueError('No usable source chunks')
 v=np.mean([vectors[k] for k in sorted(set(keys))],axis=0,dtype=np.float64);v/=np.linalg.norm(v);return v.tolist()
catalogue=json.load(open(ROOT/'dist/data/catalogue.json'));old={d['id']:d for d in json.load(open(ROOT/'dist/data/semantic.json'))['docs']};family_keys={f['id']:register(f['title']+'\n'+f['summary']) for f in catalogue['families']};encode_pending()
(out/'semantic.json').write_text(json.dumps({**meta,'source':'family-title-and-description','docs':[{'id':f['id'],'vector':vector(family_keys[f['id']]),'searchVector':old[f['id']]['searchVector'],'chunks':len(family_keys[f['id']])} for f in catalogue['families']]}));print('TOPICS COMPLETE',flush=True)
source=json.load(open(ROOT/'content/lean-declaration-manifest.json'));declaration_keys={id:register(d['text']) for id,d in source['declarations'].items()};encode_pending();docs=[];families={};excluded=[];audit={'topics':family_keys,'proofs':{},'leanFamilies':{}}
for d in source['docs']:
 keys=sorted(set(k for name in d['declarations'] for k in declaration_keys[name]));
 if not keys:excluded.append({'id':d['id'],'familyId':d['familyId'],'reason':'No resolved target or usable entry source','unresolvedTargets':d['unresolvedTargets']});continue
 paths=sorted(set('lean/'+source['declarations'][n]['module'].replace('.','/')+'.lean' for n in d['declarations']));record={**d,'vector':vector(keys),'chunks':len(keys),'moduleCount':len(paths),'declarationCount':len(d['declarations'])};record.pop('declarations');record.pop('uncachedImports');docs.append(record);audit['proofs'][d['id']]=keys
 f=families.setdefault(d['familyId'],{'keys':set(),'paths':set(),'external':set(),'roots':set(),'declarations':set(),'unresolved':set(),'ambiguous':set(),'uncached':set()});f['keys'].update(keys);f['paths'].update(paths);f['external'].update(d['externalImports']);f['roots'].add(d['solutionPath']);f['declarations'].update(d['declarations']);f['unresolved'].update(d['unresolvedTargets']);f['ambiguous'].update(d['ambiguousReferences']);f['uncached'].update(d['uncachedImports'])
coverage='Named Lean targets plus two statically resolved reference hops. External libraries, implicit instances, macros, ambiguous names, short unqualified names and uncached imports are not expanded.'
(out/'proof-semantic.json').write_text(json.dumps({**meta,'excludedEntries':excluded,'coverage':coverage,'sourceCommit':source['commit'],'maxReferenceDepth':2,'compilerVerified':False,'chunkCount':sum(d['chunks'] for d in docs),'uniqueChunkCount':len(set(k for v in declaration_keys.values() for k in v)),'docs':docs}))
(out/'lean-family-semantic.json').write_text(json.dumps({**meta,'excludedEntries':excluded,'coverage':coverage,'sourceCommit':source['commit'],'maxReferenceDepth':2,'compilerVerified':False,'sourceModuleCount':len(set(p for f in families.values() for p in f['paths'])),'docs':[{'id':id,'vector':vector(f['keys']),'chunks':len(f['keys']),'sourcePaths':sorted(f['paths']),'solutionPaths':sorted(f['roots']),'declarationCount':len(f['declarations']),'unresolvedTargetCount':len(f['unresolved'])} for id,f in sorted(families.items())]}))
source_out=ROOT/'public-shell/explore/lean-sources';source_out.mkdir(exist_ok=True)
for id,f in families.items():
 declarations=[{'name':source['declarations'][k]['name'],'path':'lean/'+source['declarations'][k]['module'].replace('.','/')+'.lean','line':source['declarations'][k]['line']} for k in sorted(f['declarations'])]
 (source_out/(id+'.json')).write_text(json.dumps({'commit':source['commit'],'sourcePaths':sorted(f['paths']),'solutionPaths':sorted(f['roots']),'chunks':len(f['keys']),'externalImports':sorted(f['external']),'declarations':declarations,'unresolvedTargets':sorted(f['unresolved']),'ambiguousReferences':sorted(f['ambiguous']),'uncachedImports':sorted(f['uncached']),'maxReferenceDepth':2,'compilerVerified':False}));audit['leanFamilies'][id]=sorted(f['keys'])
report={**meta,'excludedEntries':excluded,'commit':source['commit'],'resolution':source['resolution'],'maxReferenceDepth':2,'compilerVerified':False,'families':{id:{'sourceModuleCount':len(f['paths']),'declarationCount':len(f['declarations']),'chunks':len(f['keys']),'unresolvedTargetCount':len(f['unresolved'])} for id,f in families.items()}}
(ROOT/'public-shell/explore/lean-source-data.json').write_text(json.dumps(report));(ROOT/'.cache/direct-aggregation.json').write_text(json.dumps(audit));print('COMPLETE',len(families),'families',len(source['declarations']),'declarations',round(time.time()-started),'seconds',flush=True)
