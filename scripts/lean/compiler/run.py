"""Resumable, pinned compiler dependency extraction. Never publishes partial output."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,time,collections,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[3]
def read(p):return json.loads(p.read_text())
def write(p,data):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(data));tmp.replace(p)
def run(args):
 source=args.source.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
 catalogue=read(ROOT/'public-data/data/catalogue.json');commit=catalogue['commit'];toolchain=(source/'lean-toolchain').read_text().strip()
 actual=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
 if actual!=commit:raise RuntimeError('Source revision differs from catalogue')
 if subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],text=True).strip():raise RuntimeError('Pinned source checkout has tracked modifications')
 env=dict(os.environ);env['PATH']=str(args.toolchain.resolve()/'bin')+os.pathsep+env['PATH'];env['LEAN_NUM_THREADS']='12'
 lean=str(args.toolchain.resolve()/'bin/lean');lake=str(args.toolchain.resolve()/'bin/lake')
 version=subprocess.check_output([lean,'--version'],text=True).strip()
 if 'version '+toolchain.split(':v')[-1]+',' not in version:raise RuntimeError('Toolchain mismatch')
 manifest=read(source/'lake-manifest.json');packages=[]
 for p in manifest['packages']:
  name=p['name'].strip('«»');directory=source/'.lake/packages'/name
  head=subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip()
  if head!=p['rev']:raise RuntimeError('Dependency revision mismatch: '+name)
  diff=subprocess.check_output(['git','-C',str(directory),'diff','HEAD','--binary','--no-ext-diff','--no-textconv','--no-color'])
  if diff:
   patch=source/'patches'/f'{name}-lean4341.patch'
   if not patch.exists():raise RuntimeError('Unapproved dependency modifications: '+name)
   # Build the expected patched index in isolation, including staged changes
   # in the actual diff. Never change the package's real index or worktree.
   with tempfile.TemporaryDirectory() as temporary:
    patch_env=dict(os.environ,GIT_INDEX_FILE=str(pathlib.Path(temporary)/'index'))
    git=['git','-C',str(directory)]
    subprocess.run(git+['read-tree','HEAD'],env=patch_env,check=True,capture_output=True)
    subprocess.run(git+['apply','--cached',str(patch)],env=patch_env,check=True,capture_output=True)
    expected=subprocess.check_output(git+['diff','--cached','HEAD','--binary','--no-ext-diff','--no-textconv','--no-color'],env=patch_env)
    if expected!=diff:raise RuntimeError('Dependency modifications differ from pinned upstream patch: '+name)
  packages.append({'name':name,'revision':head,'patchSha256':hashlib.sha256(diff).hexdigest() if diff else None})
 extractor=ROOT/'scripts/lean/compiler/Extract.lean';identity={'sourceCommit':commit,'toolchain':toolchain,'leanVersion':version,'packages':packages,'extractorSha256':hashlib.sha256(extractor.read_bytes()).hexdigest(),'libraryBoundary':'Only OAI module bodies are expanded; external constant names are recorded; axiom closure includes external libraries.'}
 identity_hash=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();write(out/'provenance.json',{**identity,'identityHash':identity_hash})
 entries=[]
 for f in catalogue['families']:
  for p in f['proofs']:entries.append({**p,'familyId':f['id']})
 order_file=ROOT/'.cache/compiler-build-order.json';order={x[2]:x[0] for x in read(order_file)} if order_file.exists() else {}
 grouped=collections.defaultdict(list)
 for p in entries:grouped[p['config']['solution_module']].append(p)
 modules=sorted(grouped,key=lambda m:(order.get(m,10**9),m))
 started=time.time();status={'state':'running','identityHash':identity_hash,'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'totalEntries':len(entries),'entries':{}}
 def report():
  status['updatedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat();status['elapsedSeconds']=round(time.time()-started);status['completedEntries']=len(status['entries']);status['compilerResolvedEntries']=sum(v['state']=='resolved' for v in status['entries'].values());write(out/'status.json',status)
 report()
 for module in modules:
  group=grouped[module];cached=[]
  for p in group:
   f=out/'entries'/f"{p['id']}.json"
   if f.exists() and (r:=read(f)).get('identityHash')==identity_hash and r['state']=='resolved':cached.append(r)
  if len(cached)==len(group):
   for r in cached:status['entries'][r['id']]={k:r[k] for k in ['state','familyId','moduleName']}
   report();continue
  status['currentModule']=module;status['phase']='build';report();print('BUILD',module,flush=True)
  log=out/'logs'/f'{module}.build.log';log.parent.mkdir(exist_ok=True)
  with log.open('w') as f:built=subprocess.run([lake,'build','+'+module+':olean'],cwd=source,env=env,stdout=f,stderr=subprocess.STDOUT)
  for p in group:
   result={'id':p['id'],'familyId':p['familyId'],'moduleName':module,'solutionPath':p['solutionPath'],'identityHash':identity_hash}
   if built.returncode:result.update(state='build-failed',exitCode=built.returncode,log=str(log.relative_to(out)))
   else:
    status['phase']='extract';report();request=out/'requests'/f"{p['id']}.json";raw=out/'raw'/f"{p['id']}.json";raw.parent.mkdir(exist_ok=True)
    targets=p['config'].get('theorem_names',[])+p['config'].get('definition_names',[]);write(request,{'moduleName':module,'targets':targets,'localModules':['OAI']})
    elog=out/'logs'/f"{p['id']}.extract.log"
    with elog.open('w') as f:extracted=subprocess.run([lake,'env',lean,'--run',str(extractor),str(request),str(raw)],cwd=source,env=env,stdout=f,stderr=subprocess.STDOUT)
    if extracted.returncode or not raw.exists():result.update(state='extraction-failed',exitCode=extracted.returncode,log=str(elog.relative_to(out)))
    else:
     data=read(raw);unexpected=sorted(set(data['axioms'])-set(p['config'].get('permitted_axioms',[])))
     if not targets or data['missingDeclarations'] or data['containsSorry'] or unexpected:result.update(state='rejected',unexpectedAxioms=unexpected,extraction=data)
     else:result.update(state='resolved',extraction=data)
   write(out/'entries'/f"{p['id']}.json",result);status['entries'][p['id']]={k:result[k] for k in ['state','familyId','moduleName']};report();print('ENTRY',p['id'],result['state'],status['completedEntries'],'/',len(entries),flush=True)
 status['state']='complete';status['phase']='review';report()
 print('COMPLETE',status['compilerResolvedEntries'],'of',len(entries),'compiler-resolved; review failures before rebuilding maps',flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--source',type=pathlib.Path,required=True);parser.add_argument('--toolchain',type=pathlib.Path,required=True);parser.add_argument('--output',type=pathlib.Path,required=True);run(parser.parse_args())
