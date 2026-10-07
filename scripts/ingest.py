import re,json,urllib.request,concurrent.futures,pathlib,posixpath,html,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
CACHE=ROOT/'.cache'; CACHE.mkdir(exist_ok=True)
SHA='adc7f1241b42e322a6451854ab7e4b4c146bf78a'
BASE=f'https://raw.githubusercontent.com/openai/math/{SHA}/'
def get(path):
 p=CACHE/path;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():return p.read_text()
 for retry in range(3):
  try:
   s=urllib.request.urlopen(BASE+urllib.parse.quote(path),timeout=60).read().decode();p.write_text(s);return s
  except Exception:
   if retry==2:raise
   time.sleep(1+retry)
def clean(s):
 s=re.sub(r'<[^>]+>','',s);s=html.unescape(s).replace('$`','$').replace('`$','$')
 return re.sub(r'\s+',' ',s).strip()
s=get('overview.tex'); subject=None; sm={};subjects=[]
for m in re.finditer(r'\\cataloguesection\{([^}]+)\}\{\d+\}|\\resultentry\{(\d+)\}',s):
 if m[1]:subject=m[1];subjects.append(subject)
 else:sm[m[2]]=subject
s=get('CONTENTS.md');entries=list(re.finditer(r'\*\*(\d{3})\. (.*?)\*\*',s)); families=[]
for i,m in enumerate(entries):
 block=s[m.end():entries[i+1].start() if i+1<len(entries) else len(s)]
 head=block.split('&emsp;')[0]
 lean=re.search(r'\[Lean\]\(([^)]+)\)',head)
 papers=[]
 for piece in block.split('&emsp;')[1:]:
  pm=re.match(r'\s*\[(.*?)\]\((preprints/[^)]+)\)',piece,re.S)
  if pm: papers.append({'title':clean(pm[1]),'path':pm[2],'abstract':clean(piece[pm.end():])})
 families.append({'id':m[1],'title':clean(m[2]).rstrip('.'),'subject':sm[m[1]],'summary':clean(re.sub(r'\(\[Lean\].*?\)','',head)),'papers':papers,'leanDoc':lean[1] if lean else None,'proofs':[]})
assert len(families)==372,len(families)
print('families',len(families),'papers',sum(len(f['papers']) for f in families),flush=True)
readme=get('README.md')
for f in families:
 mt=re.search(r'\|\s*'+f['id']+r'\s*\|.*?\]\((reasoning_traces/[^)]+)\)',readme)
 if mt:f['trace']=mt[1]
def proof_family(f):
 if not f['leanDoc']:return
 doc=get(f['leanDoc']);f['leanScope']=doc
 links=list(dict.fromkeys(re.findall(r'\]\(([^)]+\.lean)\)',doc)))
 for link in links:
  challenge=posixpath.normpath(posixpath.join(posixpath.dirname(f['leanDoc']),link))
  if not challenge.startswith('lean/ComparatorChallenges/'):continue
  try:
   config=json.loads(get(challenge[:-5]+'.json'))
   solution='lean/'+config['solution_module'].replace('.','/')+'.lean'
   source=get(solution); target=get(challenge)
   ident=challenge.split('/')[-1][:-5]
   entry={'id':ident,'familyId':f['id'],'challengePath':challenge,'solutionPath':solution,'config':config,'target':target,'source':source}
   out=ROOT/'dist/proofs'/f'{ident}.json';out.write_text(json.dumps(entry,ensure_ascii=False))
   f['proofs'].append({k:entry[k] for k in ['id','challengePath','solutionPath','config']})
  except Exception as e:print('PROOF ERROR',f['id'],challenge,str(e),flush=True);f.setdefault('proofErrors',[]).append(challenge)
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:list(ex.map(proof_family,families))
meta={'commit':SHA,'date':'2026-10-06','subjects':subjects,'families':families,'coverage':{'families':len(families),'papers':sum(len(f['papers']) for f in families),'leanFamilies':sum(bool(f['leanDoc']) for f in families),'proofModules':sum(len(f['proofs']) for f in families)}}
(ROOT/'dist/data/catalogue.json').write_text(json.dumps(meta,ensure_ascii=False))
print(meta['coverage'],flush=True)
