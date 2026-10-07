"""Conservative citation identity matching; no external metadata or semantic guesses."""
import collections, hashlib, json, pathlib, re, unicodedata, urllib.parse
from extract import ROOT, plain

def norm(s):
    return ' '.join(re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',plain(s)).encode('ascii','ignore').decode().lower()))
def doi(s):
    return urllib.parse.unquote(s).strip().lower().rstrip('.,;"}\u2019').removeprefix('https://doi.org/').removeprefix('http://dx.doi.org/').removeprefix('doi:').strip()
def arxiv(s):
    m=re.search(r'(\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z]{2})?/\d{7})(?:v\d+)?',s,re.I)
    return m[1].lower() if m else ''
def surname(s):
    first=re.split(r'\s+and\s+|;',s)[0]
    words=norm(first.split(',')[0] if ',' in first else first).split()
    return next((w for w in reversed(words) if len(w)>1),'')
def identifiers(r):
    raw=r['raw'];ids=set()
    for s in ([r.get('doi','')] if r.get('doi') else re.findall(r'10\.\d{4,9}/[^\s{}"<>\\]+',raw)):
        d=doi(s)
        if re.fullmatch(r'10\.\d{4,9}/\S+',d):ids.add('doi:'+d)
    aa=[r.get('arxiv','')]+re.findall(r'(?:arxiv\.org/(?:abs|pdf|html)/|arxiv\s*:\s*)([^\s{}"<>\\]+)',raw,re.I)
    for s in aa:
        if a:=arxiv(s):ids.add('arxiv:'+a)
    # Multiple different IDs in a bibitem may describe a collection, not one work.
    if len([i for i in ids if i.startswith('doi:')])>1 or len([i for i in ids if i.startswith('arxiv:')])>1:return set()
    return ids

def main():
    data=json.loads((ROOT/'.cache/reference-records.json').read_text());rs=[];excluded=0
    for r in data['records']:
        if re.search(r'\bopenai\b',r['authors'] or r['citation'][:100],re.I) or 'github.com/openai/math' in r['raw']:
            excluded+=1;continue
        r['ids']=identifiers(r);r['titleNorm']=norm(r['title']);r['surname']=surname(r['authors']);rs.append(r)
    parent=list(range(len(rs)));method=collections.Counter();conflicts=[]
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    root_ids=[set(r['ids']) for r in rs]
    def union(i,j,reason):
        a,b=find(i),find(j)
        if a==b:return
        if reason != 'identifier':
            for prefix in ['doi:','arxiv:']:
                x={k for k in root_ids[a] if k.startswith(prefix)};y={k for k in root_ids[b] if k.startswith(prefix)}
                if x and y and x.isdisjoint(y):
                    conflicts.append([i,j,reason]);return
        parent[b]=a;root_ids[a]|=root_ids[b];method[reason]+=1
    strong={};exact={};titles=collections.defaultdict(list)
    for i,r in enumerate(rs):
        for key in sorted(r['ids']):
            if key in strong:union(i,strong[key],'identifier')
            else:strong[key]=i
        key=norm(r['citation'])
        if key in exact:union(i,exact[key],'identical citation')
        else:exact[key]=i
        if len(r['titleNorm'].split())>=3 and len(r['titleNorm'])>=20 and r['surname']:
            key=(r['titleNorm'],r['surname'])
            years=re.findall(r'\b(?:18|19|20)\d{2}\b',r['year'])
            for j in titles[key]:
                yy=re.findall(r'\b(?:18|19|20)\d{2}\b',rs[j]['year'])
                if not years or not yy or abs(int(years[0])-int(yy[0]))<=3:union(i,j,'title and author')
            titles[key].append(i)
    # Match plain TeX bibitems against exact known titles + first-author surname.
    # Require a distinctive title, not general topic words or author name alone.
    title_rows={}
    for i,r in enumerate(rs):
        if len(r['titleNorm'].split())>=4 and len(r['titleNorm'])>=28 and r['surname']:
            title_rows.setdefault((r['titleNorm'],r['surname']),i)
    freq=collections.Counter(w for t,a in title_rows for w in set(t.split()) if len(w)>3)
    index=collections.defaultdict(list)
    for (t,a),j in title_rows.items():
        tokens=[w for w in t.split() if len(w)>3]
        if tokens:index[min(tokens,key=lambda w:freq[w])].append((t,a,j))
    for i,r in enumerate(rs):
        if r['title']:continue
        text=norm(r['citation']);matches=set()
        for token in set(text.split()):
            for title,author,j in index.get(token,[]):
                if ' '+title+' ' in ' '+text+' ' and author in text.split():matches.add(find(j))
        if len(matches)==1:
            j=next(iter(matches));union(i,j,'exact title in citation')
    groups=collections.defaultdict(list)
    for i,r in enumerate(rs):groups[find(i)].append(r)
    works={};families=collections.defaultdict(set);audit=[]
    for group in groups.values():
        ids=set().union(*(r['ids'] for r in group));best=max(group,key=lambda r:(bool(r['title']),bool(r['ids']),bool(r['authors']),len(r['citation'])))
        canonical=next(iter(sorted(k for k in ids if k.startswith('doi:'))),next(iter(sorted(ids)), 'text:'+norm(best['citation'])))
        key=hashlib.sha256(canonical.encode()).hexdigest()[:16]
        title=best['title'] or best['citation'];url=''
        if canonical.startswith('doi:'):url='https://doi.org/'+canonical[4:]
        elif canonical.startswith('arxiv:'):url='https://arxiv.org/abs/'+canonical[6:]
        else:url=next((r['url'].replace('\\_','_').replace('\\%','%') for r in group if r['url'].startswith(('https://','http://'))),'')
        if not url:url='https://scholar.google.com/scholar?q='+urllib.parse.quote(title[:220])
        family_ids=sorted(set(f for r in group for f in r['families']))
        works[key]={'title':title,'authors':best['authors'],'year':best['year'],'url':url,'families':family_ids,'identifiers':sorted(ids),'sources':{f:next(r['source'] for r in group if f in r['families']) for f in family_ids}}
        for f in family_ids:families[f].add(key)
        audit.append({'id':key,'variants':[{'citation':r['citation'],'source':r['source'],'families':r['families']} for r in group]})
    cat=json.loads((ROOT/'dist/data/catalogue.json').read_text())
    result={'commit':data['commit'],'works':works,'families':{f['id']:sorted(families[f['id']]) for f in cat['families']},'extraction':{'manuscripts':data['manuscripts'],'sourceFiles':data['files'],'records':len(data['records']),'excludedReleaseReferences':excluded,'distinctWorks':len(works),'mergeCounts':dict(method),'conflictingTextMatchesRejected':len(conflicts),'failedFiles':data['failures'],'citationFiltering':data.get('citationFiltering',{})}}
    (ROOT/'.cache/references-matched.json').write_text(json.dumps(result,ensure_ascii=False))
    (ROOT/'.cache/reference-match-audit.json').write_text(json.dumps({'groups':audit,'conflicts':conflicts},ensure_ascii=False))
    print(json.dumps(result['extraction'],indent=2));print('Missing families',[f for f,refs in result['families'].items() if not refs])
if __name__=='__main__':main()
