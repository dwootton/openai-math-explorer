import json,pathlib,numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score,adjusted_rand_score
from sklearn.feature_extraction.text import TfidfVectorizer
ROOT=pathlib.Path(__file__).resolve().parents[1];out=ROOT/'next/data'
c=json.load(open(out/'catalogue.json'));new=json.load(open(out/'semantic.json'));old=json.load(open(ROOT/'.cache/minilm-baseline.json'));proof=json.load(open(out/'proof-semantic.json'))
fs=c['families'];ids=[d['id'] for d in new['docs']];fm={f['id']:f for f in fs};X=np.array([d['vector'] for d in new['docs']]);Old=np.array([d['vector'] for d in old['docs']]);scores=X@X.T;np.fill_diagonal(scores,-2);oldscores=Old@Old.T;np.fill_diagonal(oldscores,-2)
trials=[];fits={}
for k in [6,8,10,12,14,17,20]:
 model=KMeans(n_clusters=k,n_init=20,random_state=42).fit(X);value=float(silhouette_score(X,model.labels_,metric='cosine'));trials.append({'k':k,'silhouette':value});fits[k]=model
best=max(trials,key=lambda x:x['silhouette']);fit=fits[best['k']];labs=fit.labels_
other=KMeans(n_clusters=best['k'],n_init=20,random_state=97).fit(X)
stability=float(adjusted_rand_score(labs,other.labels_))
texts=[fm[i]['title']+' '+fm[i]['summary'] for i in ids];tf=TfidfVectorizer(stop_words='english',ngram_range=(1,2),max_features=4000,min_df=2);T=tf.fit_transform(texts);terms=tf.get_feature_names_out();clusters=[]
for label in range(best['k']):
 indices=np.where(labs==label)[0];centroid=fit.cluster_centers_[label];sim=X[indices]@centroid/np.linalg.norm(centroid);representative=indices[np.argsort(-sim)[:4]];keywords=terms[np.argsort(-np.asarray(T[indices].mean(axis=0)).ravel())[:6]].tolist();subjects={}
 for i in indices:subjects[fm[ids[i]]['subject']]=subjects.get(fm[ids[i]]['subject'],0)+1
 clusters.append({'id':int(label),'size':len(indices),'keywords':keywords,'subjects':dict(sorted(subjects.items(),key=lambda x:-x[1])),'representatives':[ids[i] for i in representative],'families':[ids[i] for i in indices]})
cross=[]
for i,id in enumerate(ids):
 for j in np.argsort(-scores[i]):
  if fm[id]['subject']!=fm[ids[j]]['subject']:
   if i<j:cross.append({'a':id,'b':ids[j],'similarity':float(scores[i,j]),'sameCluster':bool(labs[i]==labs[j])})
   break
cross=sorted(cross,key=lambda p:-p['similarity'])[:12]
def evaluate(vs,docs):
 results=[];mat=np.array(docs);qs=json.load(open(ROOT/'scripts/eval-queries.json'))
 for q,v in zip(qs,vs):
  order=np.argsort(-(mat@np.array(v)));ranks=[int(np.where(order==ids.index(e))[0][0])+1 for e in q['expected'] if e in ids];rank=min(ranks)
  results.append({**q,'rank':rank,'top':[ids[i] for i in order[:3]]})
 return {'top1':sum(r['rank']==1 for r in results),'top3':sum(r['rank']<=3 for r in results),'mrr':sum(1/r['rank'] for r in results)/len(results),'count':len(results),'results':results}
evnew=evaluate(json.load(open(ROOT/'.cache/gemma2/eval-vectors.json')),[d['searchVector'] for d in new['docs']]);evold=evaluate(json.load(open(ROOT/'.cache/minilm-query-vectors.json')),[d['vector'] for d in old['docs']])
shared=np.mean([len(set(np.argsort(-scores[i])[:5])&set(np.argsort(-oldscores[i])[:5]))/5 for i in range(len(ids))]);sameSubject=np.mean([np.mean([fm[ids[j]]['subject']==fm[id]['subject'] for j in np.argsort(-scores[i])[:5]]) for i,id in enumerate(ids)])
result={'model':new['model'],'revision':new['revision'],'method':'K-means on unit-normalized 768D SentenceSimilarity vectors; cosine silhouette for k selection. Not clustering the 2D map.','selectedK':best['k'],'silhouette':best['silhouette'],'trials':trials,'seedStabilityARI':stability,'clusters':clusters,'assignments':{id:int(labs[i]) for i,id in enumerate(ids)},'crossSubjectPairs':cross,'neighborOverlapWithMiniLM':float(shared),'sameSubjectNeighborShare':float(sameSubject),'evaluation':{'gemma2':evnew,'minilm':evold,'limitations':'12 hand-picked, known-item queries; a smoke test chosen before embedding, not an unbiased mathematical relevance benchmark. No OpenAI embedding model was evaluated.'},'coverage':c['coverage'],'proofCoverage':{'entries':len(proof['docs']),'uniqueSourceModules':len(set(d['solutionPath'] for d in proof['docs'])),'chunks':proof['chunkCount']}}
(out/'analysis.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:result[k] for k in ['selectedK','silhouette','seedStabilityARI','neighborOverlapWithMiniLM','sameSubjectNeighborShare','proofCoverage']},indent=2));print('New evaluation',evnew['top1'],evnew['top3'],'Old',evold['top1'],evold['top3']);print('Clusters',[(cl['id'],cl['size'],cl['keywords'][:4]) for cl in clusters]);print('Cross subject',[(fm[p['a']]['title'],fm[p['b']]['title'],p['similarity']) for p in cross[:4]])
