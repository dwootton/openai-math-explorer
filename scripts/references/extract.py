"""Extract bibliography records across all family manuscripts from the pinned source tree."""
import concurrent.futures, json, pathlib, re, time, urllib.parse, urllib.request, unicodedata
ROOT=pathlib.Path(__file__).resolve().parents[2]

def plain(text):
    math=[]
    def keep(m):
        math.append(m[0]);return ' MATHPLACEHOLDER'+str(len(math)-1)+'TOKEN '
    text=re.sub(r'(?<!\\)\$[^$]+(?<!\\)\$',keep,text)
    text=re.sub(r'\\(?:href|url)\{[^}]*\}', '', text)
    text=re.sub(r'\\[\'"`^~=.uvHckbr]\s*\{?([A-Za-z])\}?',r'\1',text)
    text=re.sub(r'\\(?:begin|end)\{[^}]*\}',' ',text)
    text=re.sub(r'\\(?:newblock|textit|textbf|emph|it|bf|sc|rm)\b',' ',text)
    text=re.sub(r'\\([A-Za-z]+)',r'\1',text)
    text=re.sub(r'\s+',' ',text.replace('{','').replace('}','').replace('~',' ').replace('\\','').replace('--','–')).strip(' ,\n')
    for i,value in enumerate(math):text=text.replace('MATHPLACEHOLDER'+str(i)+'TOKEN',value)
    return text

def balanced(s,start):
    depth=1;i=start+1
    while i<len(s) and depth:
        if s[i]=='\\':i+=2;continue
        if s[i]=='{':depth+=1
        if s[i]=='}':depth-=1
        i+=1
    return s[start+1:i-1],i

def bib_entries(s):
    pos=0
    while m:=re.search(r'@(\w+)\s*\{',s[pos:]):
        start=pos+m.end()-1;body,pos=balanced(s,start)
        if m[1].lower() in ['comment','preamble','string']:continue
        key,sep,tail=body.partition(',')
        if not sep:continue
        fields={};i=0
        while f:=re.search(r'\b([\w-]+)\s*=\s*',tail[i:]):
            name=f[1].lower();i+=f.end()
            if i>=len(tail):break
            if tail[i]=='{':value,i=balanced(tail,i)
            elif tail[i]=='"':
                end=re.search(r'(?<!\\)"',tail[i+1:]);j=i+1+end.start() if end else len(tail);value=tail[i+1:j];i=j+1
            else:
                j=tail.find(',',i);j=len(tail) if j<0 else j;value=tail[i:j].strip();i=j+1
            fields[name]=value
        yield key.strip(),fields

def records(s,path):
    # Ignore commented-out bibliography entries.
    s=re.sub(r'(?<!\\)%[^\n]*','',s)
    if path.endswith('.bib'):
        for key,f in bib_entries(s):
            if not f.get('title'):continue
            title=plain(f['title']);authors=plain(f.get('author',f.get('editor','')));year=f.get('year','')
            citation='. '.join(x for x in [authors,title,plain(f.get('journal',f.get('booktitle',f.get('publisher','')))),year] if x)
            yield {'key':key,'title':title,'authors':authors,'year':year,'citation':citation,'raw':json.dumps(f,ensure_ascii=False),'doi':f.get('doi',''),'arxiv':f.get('eprint','') if 'arxiv' in (f.get('archiveprefix','')+f.get('url','')).lower() else '', 'url':f.get('url',''),'source':'preprints/'+path}
    else:
        for m in re.finditer(r'\\bibitem(?:\[[^]]*\])?\{([^}]+)\}([\s\S]*?)(?=\\bibitem|\\end\{thebibliography\}|\Z)',s):
            raw=m[2];citation=plain(raw)
            if len(citation)<20:continue
            urls=re.findall(r'\\(?:href|url)\{(https?://[^}]+)\}',raw)
            yield {'key':m[1],'title':'','authors':'','year':'','citation':citation,'raw':raw,'doi':'','arxiv':'','url':urls[0] if urls else '', 'source':'preprints/'+path}

def main():
    cat=json.loads((ROOT/'dist/data/catalogue.json').read_text());manifest=json.loads((ROOT/'content/reference-source-manifest.json').read_text())
    assert manifest['commit']==cat['commit'], 'Source manifest must match catalogue snapshot'
    paths=manifest['paths']
    bydir={}
    for p in paths:bydir.setdefault(p.split('/')[0],[]).append(p)
    selected={};paper_paths={}
    for f in cat['families']:
        for paper in f['papers']:
            directory=paper['path'].split('/')[1]
            if directory not in bydir:
                matches=[d for d in bydir if d.startswith(directory)]
                if len(matches)==1:directory=matches[0]
                else:raise ValueError('Cannot resolve manuscript directory: '+paper['path'])
            candidates=bydir.get(directory,[])
            preferred=[p for p in candidates if p.endswith('.bib') or re.search(r'(referenc|bibliograph|refs)[^/]*\.tex$',p,re.I)]
            # Inspect the main file too: some manuscripts use inline bibitems alongside external files.
            mains=sorted([p for p in candidates if re.search(r'/(main|paper|manuscript)\.tex$',p)],key=len)
            preferred+=mains[:1] if mains else ([] if preferred else sorted(candidates,key=len)[:1])
            paper_paths[directory]=sorted(set(preferred))
            for p in preferred:selected.setdefault(p,set()).add(f['id'])
    failed=[]
    def read(path):
        file=ROOT/'.cache/literature-source'/path
        if file.exists():return path,file.read_text()
        for attempt in range(3):
            try:
                url='https://raw.githubusercontent.com/openai/math/'+cat['commit']+'/preprints/'+urllib.parse.quote(path)
                with urllib.request.urlopen(url,timeout=35) as response:s=response.read().decode()
                file.parent.mkdir(parents=True,exist_ok=True);file.write_text(s);return path,s
            except Exception as e:
                if attempt==2:failed.append({'path':path,'error':str(e)});return path,''
                time.sleep(attempt+1)
    result=[];done=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for path,s in pool.map(read,selected):
            for r in records(s,path):
                r['families']=sorted(selected[path]);result.append(r)
            done+=1
            if done%100==0:print('Read',done,'/',len(selected),flush=True)
    out={'commit':cat['commit'],'records':result,'failures':failed,'files':len(selected),'manuscripts':len(paper_paths),'paperFiles':paper_paths}
    (ROOT/'.cache/reference-records.json').write_text(json.dumps(out,ensure_ascii=False))
    print('Records',len(result),'failures',len(failed),'manuscripts',len(paper_paths),flush=True)
    if failed:raise SystemExit('Source downloads incomplete; do not publish partial data.')
if __name__=='__main__':main()
