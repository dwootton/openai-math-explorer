"""Wait for the corpus pass, then build and audit an offline candidate.
This command never writes into published data or deploys the site.
"""
import argparse,datetime,json,os,pathlib,subprocess,sys,time
from materialize import materialize
ROOT=pathlib.Path(__file__).resolve().parents[3]
def read(p):return json.loads(p.read_text())
def prepare(args):
 out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
 def status(phase,**extra):
  p=out/'status.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps({'phase':phase,'updatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),**extra}));tmp.replace(p);print(phase,flush=True)
 status('waiting-for-corpus')
 while True:
  corpus=read(args.results/'status.json')
  if corpus['state']=='complete':break
  if not args.wait_service:raise RuntimeError('Corpus pass is incomplete')
  active=subprocess.run(['systemctl','--user','is-active','--quiet',args.wait_service]).returncode==0
  if not active:raise RuntimeError('Compiler service stopped before completing the corpus')
  time.sleep(30)
 provenance=read(args.results/'provenance.json');status('materializing',identityHash=provenance['identityHash'])
 manifest=out/'lean-declaration-manifest.json';materialize(args.results,args.source,manifest)
 env=dict(os.environ);data=out/'data';public=out/'explore';data.mkdir(exist_ok=True);public.mkdir(exist_ok=True)
 env.update(LEAN_MANIFEST_PATH=str(manifest),EMBEDDING_OUTPUT_DIR=str(data),PROVENANCE_OUTPUT_DIR=str(public),AGGREGATION_AUDIT_PATH=str(out/'aggregation.json'),DATA_DIR=str(data),COMPARISON_AUDIT_PATH=str(public/'comparison-audit.json'),MAP_OUTPUT=str(public/'map-data.json'))
 def run(phase,command):
  status(phase,identityHash=provenance['identityHash'])
  with (out/(phase+'.log')).open('w') as log:subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 run('embedding',[str(args.python),'scripts/index-direct.py'])
 run('auditing',[str(args.python),'scripts/audit-direct.py'])
 lean=read(data/'lean-family-semantic.json');proof=read(data/'proof-semantic.json')
 if len(lean['docs'])<=15 or len(proof['docs'])<=15:raise RuntimeError('Insufficient coverage for the configured UMAP; review exclusions')
 run('mapping',['node','scripts/build-direct-maps.mjs'])
 status('ready-for-review',identityHash=provenance['identityHash'],sourceCommit=provenance['sourceCommit'],compilerResolvedEntries=len(proof['docs']),families=len(lean['docs']),excludedEntries=proof['excludedEntries'],deployed=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--results',type=pathlib.Path,required=True);p.add_argument('--source',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--python',type=pathlib.Path,default=pathlib.Path(sys.executable));p.add_argument('--wait-service');a=p.parse_args()
 try:prepare(a)
 except Exception as e:
  a.output.mkdir(parents=True,exist_ok=True);(a.output/'status.json').write_text(json.dumps({'phase':'failed','error':str(e),'deployed':False}));raise
