"""Turn a completed compiler graph into exact source blocks for embedding.
Dependency discovery is exclusively the Lean extractor. Source-owner reuse only
avoids counting a generated auxiliary proof twice when its source is already
included; unresolved source ranges retain the actual elaborated expression.
"""
import argparse,hashlib,json,pathlib,sys,subprocess
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from resolve import strip_comments

def read(p):return json.loads(p.read_text())
def source_slice(text,r):
 # Lean Position.column counts Unicode codepoints (not UTF-16 display units).
 lines=text.splitlines(keepends=True);a=r['startLine']-1;b=r['endLine']-1
 if a<0 or b>=len(lines) or a>b:raise ValueError('Invalid compiler source range')
 if a==b:return lines[a][r['startColumn']:r['endColumn']]
 return lines[a][r['startColumn']:]+''.join(lines[a+1:b])+lines[b][:r['endColumn']]
def blocks_for_entry(extraction,source):
 by={d['name']:d for d in extraction['declarations']};texts={};mapping={};generated=0;source_cache={};block_cache={}
 for d in extraction['declarations']:
  owner=d
  if not d['sourceRange']:
   name=d['name']
   while '.' in name:
    name=name.rsplit('.',1)[0];candidate=by.get(name)
    if candidate and candidate['sourceRange'] and candidate['moduleName']==d['moduleName']:
     owner=candidate;generated+=1;break
  owner_key=(owner['moduleName'],owner['name'])
  if owner_key in block_cache:mapping[d['name']]=block_cache[owner_key];continue
  path=source/(owner['moduleName'].replace('.','/')+'.lean')
  if owner['sourceRange']:
   source_cache.setdefault(path,None)
   if source_cache[path] is None:source_cache[path]=path.read_text()
   snippet=strip_comments(source_slice(source_cache[path],owner['sourceRange'])).strip();line=owner['sourceRange']['startLine'];representation='source'
  else:
   snippet=d['canonicalText'];line=None;representation='elaborated-expression'
  if not snippet:raise ValueError('No compiler-backed text for '+d['name'])
  if representation=='elaborated-expression' and '⋯' in snippet:raise ValueError('Pretty-printer omitted a term in '+d['name'])
  key=hashlib.sha256((owner['moduleName']+'\0'+snippet).encode()).hexdigest()
  texts[key]={'name':owner['name'],'module':owner['moduleName'],'line':line,'text':snippet,'representation':representation}
  mapping[d['name']]=key;block_cache[owner_key]=key
 return texts,mapping,generated

def materialize(results,source,output):
 status=read(results/'status.json');provenance=read(results/'provenance.json')
 if status['state']!='complete' or status['completedEntries']!=status['totalEntries']:raise ValueError('Corpus pass is incomplete; refusing a release manifest')
 if status['identityHash']!=provenance['identityHash']:raise ValueError('Mixed status provenance')
 if len(status['entries'])!=status['totalEntries']:raise ValueError('Missing entry records')
 actual=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
 if actual!=provenance['sourceCommit']:raise ValueError('Source checkout differs from compiler provenance')
 if subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],text=True).strip():raise ValueError('Source changed after compilation')
 declarations={};docs=[];excluded=[]
 for id,state in sorted(status['entries'].items()):
  r=read(results/'entries'/f'{id}.json')
  if r['identityHash']!=provenance['identityHash']:raise ValueError('Mixed build provenance')
  if r['state']!='resolved':excluded.append({k:v for k,v in r.items() if k!='extraction'});continue
  x=r['extraction']
  if x['missingDeclarations'] or x['containsSorry']:raise ValueError('Invalid resolved entry')
  blocks,mapping,reused=blocks_for_entry(x,source);declarations.update(blocks)
  docs.append({'id':id,'familyId':r['familyId'],'solutionPath':r['solutionPath'],'declarations':sorted(blocks),'resolvedDeclarationCount':len(x['declarations']),'generatedDeclarationsReusingSource':reused,'targetDeclarations':x['targets'],'unresolvedTargets':[],'ambiguousReferences':[],'uncachedImports':[],'externalImports':sorted({module for _,module in x['externalDependencies']}),'externalConstants':[name for name,_ in x['externalDependencies']],'axioms':x['axioms'],'dependencyEdges':{d['name']:d['dependencies'] for d in x['declarations']},'declarationBlocks':mapping})
 report={'commit':provenance['sourceCommit'],'resolution':'lean-elaborated-transitive-local-dependencies','compilerVerified':True,'maxReferenceDepth':None,'externalLibrariesExpanded':False,'provenance':provenance,'excludedEntries':excluded,'declarations':declarations,'docs':docs}
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report));print('MATERIALIZED',len(docs),'entries',len(declarations),'source blocks;',len(excluded),'excluded')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--results',type=pathlib.Path,required=True);p.add_argument('--source',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();materialize(a.results,a.source,a.output)
