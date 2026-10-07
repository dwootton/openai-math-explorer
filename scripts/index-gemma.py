import sys,pathlib,json,numpy as np,hashlib,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from embedding_model import Embedder,MODEL,REVISION
out=ROOT/'next/data';cache=ROOT/'.cache/gemma2';cache.mkdir(exist_ok=True)
c=json.load(open(ROOT/'dist/data/catalogue.json'));m=Embedder();print('MODEL READY',MODEL,REVISION,flush=True)
def cached(text,task):
 key=hashlib.sha256((REVISION+task+('titled-chunks-v2' if task=='document' else '')+text).encode()).hexdigest();p=cache/(key+'.npy')
 if p.exists():return np.load(p)
 chunks=m.chunks(text)
 if task=='document':
  title,body=text.split(' | text: ',1);chunks=[title+' | text: '+part for part in m.chunks(body)]
 v=m.encode(chunks,task).mean(axis=0);v/=np.linalg.norm(v);np.save(p,v);return v
families=[];start=time.time()
for i,f in enumerate(c['families']):
 text=f['title']+'. '+f['summary']+'\n'+'\n'.join(p['title']+'. '+p['abstract'] for p in f['papers'])
 vector=cached(text,'similarity');search=cached('title: '+f['title']+' | text: '+text,'document')
 families.append({'id':f['id'],'vector':vector.tolist(),'searchVector':search.tolist()})
 if i%25==0:print('Families',i+1,'seconds',round(time.time()-start),flush=True)
meta={'model':MODEL,'revision':REVISION,'dimensions':768,'chunkTokens':1024,'overlapTokens':96,'prompt':'SentenceSimilarity'}
(out/'semantic.json').write_text(json.dumps({**meta,'docs':families}))
presets=json.load(open(ROOT/'.cache/lens-prompts.json'))
for p in presets.values():p['vectors']=m.encode(p['prompts'],'similarity').tolist()
(out/'presets.json').write_text(json.dumps(presets))
queries=json.load(open(ROOT/'scripts/eval-queries.json'));qvs=m.encode([q['query'] for q in queries],'search');(cache/'eval-vectors.json').write_text(json.dumps(qvs.tolist()))
proofs=[];chunks=0
for i,p in enumerate(sorted((ROOT/'dist/proofs').glob('*.json'))):
 d=json.load(open(p));text=d['source'];n=len(m.chunks(text));v=cached(text,'similarity');chunks+=n
 proofs.append({'id':d['id'],'familyId':d['familyId'],'solutionPath':d['solutionPath'],'vector':v.tolist(),'chunks':n})
 if i%25==0:print('Proofs',i+1,'chunks',chunks,'seconds',round(time.time()-start),flush=True)
(out/'proof-semantic.json').write_text(json.dumps({**meta,'chunkCount':chunks,'coverage':'Catalogue-linked solution modules, excluding imported dependencies.','docs':proofs}))
print('EMBEDDINGS COMPLETE',len(families),len(proofs),chunks,flush=True)
