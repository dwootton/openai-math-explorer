import json,os,pathlib,subprocess,tempfile,unittest
from materialize import source_slice,materialize,blocks_for_entry
ROOT=pathlib.Path(__file__).resolve().parents[3]
TOOLCHAIN=pathlib.Path(os.environ.get('LEAN_TOOLCHAIN_DIR',ROOT/'.cache/lean-toolchains/lean-4.34.1-linux_aarch64'))
class MaterializerTests(unittest.TestCase):
 def test_unicode_range(self):
  self.assertEqual(source_slice('αβγ\nδεζη\n',{'startLine':1,'startColumn':1,'endLine':2,'endColumn':2}),'βγ\nδε')
 def test_partial_corpus_cannot_be_published(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'status.json').write_text(json.dumps({'state':'running','completedEntries':1,'totalEntries':405}));(p/'provenance.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'incomplete'):materialize(p,p,p/'manifest.json')
 def test_mixed_provenance_cannot_be_materialized(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'status.json').write_text(json.dumps({'state':'complete','completedEntries':0,'totalEntries':0,'entries':{},'identityHash':'a'}));(p/'provenance.json').write_text(json.dumps({'identityHash':'b'}))
   with self.assertRaisesRegex(ValueError,'provenance'):materialize(p,p,p/'manifest.json')
 def test_omitted_expression_is_not_embedded(self):
  x={'declarations':[{'name':'generated','moduleName':'Fixture','sourceRange':None,'canonicalText':'generated := ⋯'}]}
  with self.assertRaisesRegex(ValueError,'omitted'):blocks_for_entry(x,pathlib.Path('/unused'))
 def test_reachable_source_owner_deduplicates_generated_declaration(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'Fixture.lean').write_text('theorem target : True := by trivial\n')
   r={'startLine':1,'startColumn':0,'endLine':1,'endColumn':34}
   x={'declarations':[{'name':'target','moduleName':'Fixture','sourceRange':r,'canonicalText':None},{'name':'target.match_1','moduleName':'Fixture','sourceRange':None,'canonicalText':None},{'name':'other.match_1','moduleName':'Fixture','sourceRange':None,'canonicalText':'actual elaborated expression'}]}
   blocks,mapping,reused=blocks_for_entry(x,p);self.assertEqual(mapping['target'],mapping['target.match_1']);self.assertNotEqual(mapping['target'],mapping['other.match_1']);self.assertEqual(reused,1);self.assertEqual(len(blocks),2)
@unittest.skipUnless((TOOLCHAIN/'bin/lean').exists(),'Pinned Lean toolchain is required')
class CompilerTests(unittest.TestCase):
 def test_resolved_dependencies_and_missing_target(self):
  lean=str(TOOLCHAIN/'bin/lean');env=dict(os.environ);env['PATH']=str(TOOLCHAIN/'bin')+os.pathsep+env['PATH']
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);env['LEAN_PATH']=str(p);src=p/'DependencyFixture.lean';src.write_text((ROOT/'scripts/lean/compiler/fixtures/DependencyFixture.lean').read_text());subprocess.run([lean,'-o',str(p/'DependencyFixture.olean'),str(src)],cwd=p,env=env,check=True,capture_output=True)
   request=p/'request.json';out=p/'out.json';request.write_text(json.dumps({'moduleName':'DependencyFixture','targets':['DifferentNamespace.target'],'localModules':['DependencyFixture']}))
   subprocess.run([lean,'--run',str(ROOT/'scripts/lean/compiler/Extract.lean'),str(request),str(out)],env=env,check=True,capture_output=True)
   result=json.loads(out.read_text());names={v['name'] for v in result['declarations']};self.assertTrue({'DifferentNamespace.target','DifferentNamespace.helper','DifferentNamespace.actualInstance'}<=names);self.assertNotIn('DifferentNamespace.unused',names);self.assertFalse(result['containsSorry']);self.assertFalse(result['missingDeclarations']);blocks,mapping,_=blocks_for_entry(result,p);self.assertEqual(set(mapping),names);self.assertTrue(all(v['text'] for v in blocks.values()))
   request.write_text(json.dumps({'moduleName':'DependencyFixture','targets':['DifferentNamespace.nonexistent'],'localModules':['DependencyFixture']}));r=subprocess.run([lean,'--run',str(ROOT/'scripts/lean/compiler/Extract.lean'),str(request),str(out)],env=env,capture_output=True);self.assertEqual(r.returncode,2);self.assertEqual(json.loads(out.read_text())['missingDeclarations'],['DifferentNamespace.nonexistent'])
if __name__=='__main__':unittest.main()
