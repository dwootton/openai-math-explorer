import unittest
from resolve import imports,resolve_closure
from resolve_declarations import declarations
class ResolutionTests(unittest.TestCase):
 def test_imports_and_nested_comments(self):
  self.assertEqual(imports('import OAI.A OAI.B -- trailing\n/- import OAI.Bad /- nested -/ -/\npublic import Mathlib.Data.Nat.Basic\n'),['Mathlib.Data.Nat.Basic','OAI.A','OAI.B'])
 def test_transitive_shared_and_cycles(self):
  sources={'A':{'imports':['B','C']},'B':{'imports':['C','Mathlib.X']},'C':{'imports':['A']}}
  self.assertEqual(resolve_closure('A',sources),(['A','B','C'],['Mathlib.X']))
 def test_declarations_preserve_namespace_source_lines_and_body(self):
  ds=declarations("/- comment\n nested /- x -/ -/\nnamespace A\nsection\nlemma foo : True := by trivial\nend\ntheorem bar : True := foo\nend A\n",'OAI.Test')
  self.assertEqual([(d['name'],d['line']) for d in ds],[('A.foo',5),('A.bar',7)])
  self.assertIn('by trivial',ds[0]['text'])
 def test_noncomputable_sections_and_universe_names(self):
  ds=declarations("namespace OAI\nnamespace A.B\nnoncomputable section\ndef x : Nat := 1\nend\nend A.B\nnamespace A\ntheorem target.{u} : True := by trivial\nend A\nend OAI\n",'Test')
  self.assertEqual([d['name'] for d in ds],['OAI.A.B.x','OAI.A.target'])
if __name__=='__main__':unittest.main()
