"""Exclude unused BibTeX database entries using reachable manuscript TeX sources."""
import concurrent.futures,json,posixpath,re,time,urllib.parse,urllib.request
from extract import ROOT

def main():
    data=json.loads((ROOT/'.cache/reference-records.json').read_text())
    manifest=json.loads((ROOT/'content/reference-source-manifest.json').read_text());assert manifest['commit']==data['commit']
    paths={p for p in manifest['paths'] if p.endswith('.tex')}
    roots={};contexts={}
    for directory,files in data['paperFiles'].items():
        candidates=sorted([p for p in paths if p.startswith(directory+'/') and re.search(r'/(main|paper|manuscript)\.tex$',p)],key=lambda p:(len(p),p))
        roots[directory]=candidates[:1] or [p for p in files if p.endswith('.tex')]
    contents={};failures=[]
    def read(path):
        file=ROOT/'.cache/literature-source'/path
        if file.exists():return path,file.read_text()
        for attempt in range(3):
            try:
                with urllib.request.urlopen('https://raw.githubusercontent.com/openai/math/'+data['commit']+'/preprints/'+urllib.parse.quote(path),timeout=35) as response:s=response.read().decode()
                file.parent.mkdir(parents=True,exist_ok=True);file.write_text(s);return path,s
            except Exception as e:
                if attempt==2:failures.append(path);return path,''
                time.sleep(attempt+1)
    pending={(p,posixpath.dirname(p)) for files in roots.values() for p in files};seen=set();edges={}
    while pending:
        batch=sorted({p for p,root in pending if p not in contents})
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:contents.update(pool.map(read,batch))
        next_round=set()
        for path,root in pending:
            if (path,root) in seen:continue
            seen.add((path,root));s=re.sub(r'(?<!\\)%[^\n]*','',contents[path]);children=[]
            for name in re.findall(r'\\(?:input|include|subfile)\s*\{([^}]+)\}',s):
                if not name.endswith('.tex'):name+='.tex'
                candidates=[posixpath.normpath(posixpath.join(root,name)),posixpath.normpath(posixpath.join(posixpath.dirname(path),name))]
                found=next((p for p in candidates if p in paths),None)
                if found:children.append(found);next_round.add((found,root))
            edges[(path,root)]=children
        pending=next_round-seen
        print('Citation source files read',len(contents),flush=True)
    if failures:raise SystemExit('Citation sources failed: '+str(failures))
    citation_keys={};unfiltered=[]
    for directory,start in roots.items():
        visited=set();todo=[(p,posixpath.dirname(p)) for p in start];keys=set()
        while todo:
            path,root=todo.pop()
            if (path,root) in visited:continue
            visited.add((path,root));text=re.sub(r'(?<!\\)%[^\n]*','',contents.get(path,''))
            for args in re.findall(r'\\(?:[A-Za-z]*cite[A-Za-z]*)(?:\*)?\s*(?:\[[^]]*\]\s*)*\{([^}]+)\}',text):keys.update(k.strip() for k in args.split(','))
            todo.extend((child,root) for child in edges.get((path,root),[]))
        citation_keys[directory]=keys
        if not keys:unfiltered.append(directory)
    kept=[];removed=0
    for record in data['records']:
        directory=record['source'].split('/')[1];keys=citation_keys[directory]
        if record['source'].endswith('.bib') and keys and '*' not in keys and record['key'] not in keys:removed+=1;continue
        kept.append(record)
    data['records']=kept;data['citationFiltering']={'sourceFiles':len(contents),'unusedBibEntriesRemoved':removed,'manuscriptsWithoutRecognizedCiteCommands':unfiltered,'policy':'Filter BibTeX entries by cited keys across reachable TeX inputs; retain nocite-star databases, explicit bibitems and no-command fallbacks.'}
    (ROOT/'.cache/reference-records.json').write_text(json.dumps(data,ensure_ascii=False))
    print('Unused BibTeX entries removed',removed,'fallback manuscripts',len(unfiltered),flush=True)
if __name__=='__main__':main()
