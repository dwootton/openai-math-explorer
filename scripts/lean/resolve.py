"""Resolve complete repository-local Lean import closures at a pinned commit.
Includes whole imported modules; this is conservative module-level resolution,
not compiler-level declaration dependency analysis. External libraries are listed.
"""
import json,pathlib,re,urllib.request,urllib.parse,concurrent.futures,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
def strip_comments(s):
 out=[];i=0;depth=0;string=False
 while i<len(s):
  if depth:
   if s[i:i+2]=='/-':depth+=1;i+=2
   elif s[i:i+2]=='-/':depth-=1;i+=2
   else:out.append('\n' if s[i]=='\n' else ' ');i+=1
  elif not string and s[i:i+2]=='/-':depth=1;out.append(' ');i+=2
  elif not string and s[i:i+2]=='--':
   j=s.find('\n',i);i=len(s) if j<0 else j
  else:
   c=s[i];out.append(c)
   if c=='"' and (i==0 or s[i-1]!='\\'):string=not string
   i+=1
 return ''.join(out)
def imports(s):
 lines=re.findall(r'^\s*(?:public\s+)?import[ \t]+([^\n]+)',strip_comments(s),re.M)
 return sorted(set(name for line in lines for name in re.findall(r"[A-Za-z_][\w.']*",line)))
def resolve_closure(start,sources):
 found=set();outside=set();todo=[start]
 while todo:
  name=todo.pop()
  if name in found or name in outside:continue
  if name not in sources:outside.add(name);continue
  found.add(name);todo.extend(sources[name]['imports'])
 return sorted(found),sorted(outside)
def main():
 catalogue=json.load(open(ROOT/'dist/data/catalogue.json'));commit=catalogue['commit'];cache=ROOT/'.cache/lean-expanded'/commit;cache.mkdir(parents=True,exist_ok=True)
 def request(url):
  for trial in range(4):
   try:return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'math-explorer-source-index'}),timeout=40).read()
   except Exception:
    if trial==3:raise
    time.sleep(1+trial)
 local_roots={'OAI','ComparatorChallenges'}
 def local(name):return name.split('.')[0] in local_roots
 entries=[json.load(open(p)) for p in sorted((ROOT/'dist/proofs').glob('*.json'))];sources={};pending={d['solutionPath'][5:-5].replace('/','.') for d in entries};external=set()
 def fetch(module):
  path='lean/'+module.replace('.','/')+'.lean';file=cache/path
  if not file.exists():file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(request('https://raw.githubusercontent.com/openai/math/'+commit+'/'+urllib.parse.quote(path)))
  s=file.read_text();return module,{'path':path,'imports':imports(s),'characters':len(s)}
 while pending:
  missing={x for x in pending if not local(x)};external.update(missing);todo=sorted(x for x in pending if local(x) and x not in sources);pending=set()
  with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
   for name,value in pool.map(fetch,todo):sources[name]=value;pending.update(value['imports'])
  pending-=sources.keys();print('Resolved',len(sources),'pending',len(pending),flush=True)
 docs=[]
 for d in entries:
  included,outside=resolve_closure(d['solutionPath'][5:-5].replace('/','.'),sources);docs.append({'id':d['id'],'familyId':d['familyId'],'solutionPath':d['solutionPath'],'modules':included,'externalImports':outside})
 report={'commit':commit,'resolution':'complete-repository-local-import-closure','includesWholeModules':True,'externalLibrariesExpanded':False,'modules':sources,'docs':docs}
 (ROOT/'content/lean-source-manifest.json').write_text(json.dumps(report));print('COMPLETE',len(sources),'modules',len(docs),'entries','largest closure',max(len(d['modules']) for d in docs),flush=True)
if __name__=='__main__':main()
