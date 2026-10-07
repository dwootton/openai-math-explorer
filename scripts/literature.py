import json,re,pathlib,urllib.request,urllib.parse,concurrent.futures,time
ROOT=pathlib.Path(__file__).resolve().parents[1];cat=json.load(open(ROOT/'dist/data/catalogue.json'));tree=json.load(open(ROOT/'.cache/preprints-tree.json'))['tree'];SHA=cat['commit']
paths=[x['path'] for x in tree if x['type']=='blob' and x['path'].endswith(('.tex','.bib'))]
def read(p):
 file=ROOT/'.cache/literature-source'/p;file.parent.mkdir(parents=True,exist_ok=True)
 if file.exists():return file.read_text()
 for attempt in range(3):
  try:
   text=urllib.request.urlopen('https://raw.githubusercontent.com/openai/math/'+SHA+'/preprints/'+urllib.parse.quote(p),timeout=40).read().decode();file.write_text(text);return text
  except Exception:
   if attempt==2:return ''
   time.sleep(1)
def plain(s):
 s=re.sub(r'\\(?:href|url)\{[^}]+\}(?:\{[^}]+\})?','',s)
 s=re.sub(r'\\(?:begin|end)\{[^}]+\}','',s)
 s=re.sub(r'\\[a-zA-Z]+\*?(?:\[[^]]+\])?','',s)
 return re.sub(r'\s+',' ',s.replace('{','').replace('}','').replace('~',' ').replace('\\','').replace('--','–')).strip()
def process(f):
 directory=f['papers'][0]['path'].split('/')[1]+'/'
 candidates=[p for p in paths if p.startswith(directory)]
 preferred=[p for p in candidates if re.search(r'(?:referenc|bibliograph|refs)[^/]*\.(tex|bib)$',p,re.I)]
 if not preferred:preferred=sorted([p for p in candidates if re.search(r'/(?:main|paper|manuscript)\.tex$',p)],key=len)[:1]
 if not preferred:preferred=sorted(candidates,key=len)[:1]
 refs=[]
 for p in preferred:
  s=read(p)
  parts=re.split(r'\\bibitem(?:\[[^]]*\])?\{[^}]*\}',s)[1:]
  if not parts and p.endswith('.bib'):parts=re.split(r'@\w+\{',s)[1:]
  for part in parts:
   part=part.split('\\end{thebibliography}')[0]
   urls=re.findall(r'\\(?:href|url)\{(https?://[^}]+)\}',part)
   urls+=re.findall(r'url\s*=\s*\{(https?://[^}]+)\}',part,re.I)
   doi=re.search(r'doi\s*=\s*\{([^}]+)\}',part,re.I)
   if doi:urls.insert(0,'https://doi.org/'+doi[1])
   urls=[u.replace('\\_','_').replace('\\%','%') for u in urls if 'openai/math' not in u and 'javascript:' not in u]
   title=plain(part)
   if len(title)<20 or 'OpenAI' in title[:150]:continue
   url=next((u for u in urls if 'doi.org' in u),urls[0] if urls else 'https://scholar.google.com/scholar?q='+urllib.parse.quote(title[:220]))
   refs.append({'citation':title[:700],'url':url,'linkType':'source-link' if urls else 'literature-search','source':'preprints/'+p})
 # Store all extracted references, display a selected subset and allow expansion.
 return f['id'],{'references':refs,'sourceFiles':['preprints/'+p for p in preferred]}
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:result=dict(ex.map(process,cat['families']))
(ROOT/'next/data/literature.json').write_text(json.dumps(result,ensure_ascii=False))
print('Families with references',sum(bool(x['references']) for x in result.values()),'References',sum(len(x['references']) for x in result.values()))
