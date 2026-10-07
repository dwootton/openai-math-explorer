import unittest,json,pathlib,re,html,sys,hashlib
from topic_source import topic_text
ROOT=pathlib.Path(__file__).resolve().parents[1]
class TopicSourceTests(unittest.TestCase):
 def test_eli5_and_display_fields_do_not_enter_input(self):
  f={'title':'Source title','summary':'Source description','papers':[{'title':'Paper title','abstract':'Original abstract','question':'ELI5 paper text'}],'question':'ELI5 question','idea':'ELI5 idea','explanation':'ELI5 explanation'}
  self.assertEqual(topic_text(f),'Source title\n\nSource description\n\nPaper title\n\nOriginal abstract')
 def test_all_catalogue_inputs_match_upstream_snapshot(self):
  s=(ROOT/'content/source-CONTENTS.md').read_text();entries=list(re.finditer(r'\*\*(\d{3})\. (.*?)\*\*',s));cat=json.loads((ROOT/'public-data/data/catalogue.json').read_text());by={f['id']:f for f in cat['families']}
  def clean(t):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',t)).replace('$`','$').replace('`$','$')).strip()
  count=0
  for i,m in enumerate(entries):
   block=s[m.end():entries[i+1].start() if i+1<len(entries) else len(s)];head=block.split('&emsp;')[0];f=by[m[1]]
   self.assertEqual(f['title'],clean(m[2]).rstrip('.'));self.assertEqual(f['summary'],clean(re.sub(r'\(\[Lean\].*?\)','',head)))
   papers=[]
   for piece in block.split('&emsp;')[1:]:
    pm=re.match(r'\s*\[(.*?)\]\((preprints/.*?\.pdf)\)',piece,re.S)
    if pm:papers.append({'title':clean(pm[1]),'path':pm[2],'abstract':clean(piece[pm.end():])})
   self.assertEqual(papers,f['papers'],f['id']);count+=len(papers)
  self.assertEqual(len(entries),372);self.assertEqual(count,722)
 def test_published_embeddings_identify_exact_source_input(self):
  cat=json.loads((ROOT/'public-data/data/catalogue.json').read_text());data=json.loads((ROOT/'public-data/data/semantic.json').read_text());by={f['id']:f for f in cat['families']}
  self.assertFalse(data['usesELI5']);self.assertEqual(data['sourcePath'],'CONTENTS.md');self.assertEqual(data['sourceCommit'],cat['commit'])
  for d in data['docs']:
   f=by[d['id']];self.assertEqual(d['inputSha256'],hashlib.sha256(topic_text(f).encode()).hexdigest());self.assertEqual(d['paperPaths'],[p['path'] for p in f['papers']])
if __name__=='__main__':unittest.main()
