"""Bounded static expansion of named declarations; not Lean elaboration.
Two reference hops, same policy for every entry. Ambiguous names, implicit
instances, macros, and uncached/external declarations are not expanded.
"""
import json,pathlib,re,collections,time,bisect
from resolve import imports,strip_comments
ROOT=pathlib.Path(__file__).resolve().parents[2];DEPTH=2
DECL=re.compile(r'(?m)^[ \t]*(?:(?:@\[[^\n]*?\]|private|protected|noncomputable|unsafe|partial)\s+)*(?:theorem|lemma|def|abbrev|opaque|axiom|structure|class|inductive)\s+([\w\u0080-\uffff][\w.\u0080-\uffff\']*)')
SCOPE=re.compile(r'(?m)^[ \t]*(?:noncomputable[ \t]+)?(namespace|section|end)(?:[ \t]+([\w.\']+))?[^\n]*')
TOKEN=re.compile(r"[A-Za-z_][A-Za-z0-9_'.]*")
def declarations(text,module,clean=False):
 code=text if clean else strip_comments(text);ds=list(DECL.finditer(code));events=iter(SCOPE.finditer(code));event=next(events,None);stack=[];out=[];newlines=[m.start() for m in re.finditer("\n",code)]
 for i,m in enumerate(ds):
  while event and event.start()<m.start():
   kind,name=event.group(1,2)
   if kind in ['namespace','section']:stack.append((kind,name or ''))
   elif stack:
    if name:
     while stack:
      _,last=stack.pop()
      if last==name:break
    else:stack.pop()
   event=next(events,None)
  name=m.group(1).rstrip('.');prefix='.'.join(n for k,n in stack if k=='namespace');full=name[7:] if name.startswith('_root_.') else '.'.join(x for x in [prefix,name] if x)
  end=ds[i+1].start() if i+1<len(ds) else len(code);body=code[m.start():end].strip();line=bisect.bisect_left(newlines,m.start())+1
  out.append({'name':full,'module':module,'line':line,'text':body})
 return out

def main():
 cat=json.load(open(ROOT/'dist/data/catalogue.json'));commit=cat['commit'];cache=ROOT/'.cache/lean-expanded'/commit/'lean';index={};by_module={};graph={};print('Indexing cached pinned sources',flush=True)
 for i,p in enumerate(sorted(cache.rglob('*.lean'))):
  module=str(p.relative_to(cache))[:-5].replace('/','.');text=strip_comments(p.read_text());graph[module]=sorted(set(n for line in re.findall(r'^\s*(?:public\s+)?import[ \t]+([^\n]+)',text,re.M) for n in re.findall(r"[A-Za-z_][\w.']*",line)));decls=declarations(text,module,clean=True);by_module[module]=[]
  for d in decls:
   key=module+':'+str(d['line']);index[key]=d;by_module[module].append(key)
  if i%5000==0:print('FILES',i,'DECLARATIONS',len(index),flush=True)
 suffix=collections.defaultdict(set)
 for key,d in index.items():
  parts=d['name'].split('.')
  for n in range(1,len(parts)+1):suffix['.'.join(parts[-n:])].add(key)
 roots=[json.load(open(p)) for p in sorted((ROOT/'dist/proofs').glob('*.json'))];selected={};docs=[];reach_cache={}
 def reachable(module):
  if module in reach_cache:return reach_cache[module]
  seen=set();todo=[module];outside=set()
  while todo:
   n=todo.pop()
   if n in seen:continue
   seen.add(n)
   if n not in graph:outside.add(n);continue
   todo.extend(graph[n])
  reach_cache[module]=(seen,outside);return seen,outside
 def choose(token,scope,module):
  candidates=suffix.get(token.replace('_root_.',''),set());local=[k for k in candidates if index[k]['module']==module]
  if len(local)==1:return local
  hits=[k for k in candidates if index[k]['module'] in scope]
  return hits if len(hits)==1 else []
 for i,d in enumerate(roots):
  module=d['solutionPath'][5:-5].replace('/','.');scope,outside=reachable(module);targets=d['config'].get('theorem_names',[])+d['config'].get('definition_names',[]);seeds=set();unresolved=[]
  for t in targets:
   found=choose(t,scope,module)
   if found:seeds.update(found)
   else:unresolved.append(t)
  if not seeds:
   # Preserve entry text rather than invent a target resolution.
   key=module+':entry';index[key]={'name':module,'module':module,'line':1,'text':re.sub(r'^\s*import[^\n]*','',strip_comments(d['source']),flags=re.M).strip()};seeds.add(key)
  included=set(seeds);frontier=set(seeds);ambiguous=set()
  for depth in range(DEPTH):
   nxt=set()
   for key in frontier:
    block=index[key]
    for token in set(TOKEN.findall(block['text'])):
     if token==block['name'] or ('.' not in token and len(token)<8):continue
     found=choose(token,scope,block['module'])
     if found:nxt.update(found)
     elif token in suffix and '.' in token:ambiguous.add(token)
   frontier=nxt-included;included.update(frontier)
  for key in included:selected[key]=index[key]
  docs.append({'id':d['id'],'familyId':d['familyId'],'solutionPath':d['solutionPath'],'declarations':sorted(included),'targetDeclarations':targets,'unresolvedTargets':unresolved,'ambiguousReferences':sorted(ambiguous),'externalImports':sorted(n for n in outside if not n.startswith('OAI.')),'uncachedImports':sorted(n for n in outside if n.startswith('OAI.'))})
  if i%50==0:print('ENTRIES',i,'SELECTED',len(selected),flush=True)
 out={'commit':commit,'resolution':'static-named-declaration-references','maxReferenceDepth':DEPTH,'indexedModuleCount':len(graph),'compilerVerified':False,'externalLibrariesExpanded':False,'declarations':selected,'docs':docs}
 (ROOT/'content/lean-declaration-manifest.json').write_text(json.dumps(out));print('COMPLETE',len(docs),len(selected),'declarations',sum(len(v['text']) for v in selected.values()),'characters','unresolved targets',sum(len(d['unresolvedTargets']) for d in docs),flush=True)
if __name__=='__main__':main()
