import json,pathlib,re
root=pathlib.Path('next/explanations')
updates={
'001':{'question':'When an algebraic shape is translated into arithmetic modulo a prime, do different mathematical ways of measuring its special features agree on ordinary fractions?','idea':'The manuscript claims that, for the abelian varieties and good reductions it studies, pairing a specialized Hodge class with the specified divisor products gives the same rational number in several cohomology theories. Think of different measuring systems agreeing on one answer; that is an analogy, not the proof. A further algebraic-cycle claim uses a separate Hodge-theorem result.','why':'Agreement between these mathematical measuring systems helps connect geometry in characteristic zero with arithmetic modulo primes. The exact hypotheses and the dependency on the companion result matter.'},
'003':{'question':'How close to the right edge of the critical strip can zeros of the zeta function and related functions occur?','idea':'The manuscript claims there are no such zeros to the right of the seven-eighths line, with the stated exception for poles. A companion gives a weaker eleven-twelfths boundary. These functions are connected to the distribution of primes. This is not the full Riemann hypothesis, which concerns the one-half line.','why':'A zero-free region can strengthen what mathematicians can say about prime-number patterns. The exact boundary and which functions are covered are central to evaluating the claim.'},
'017':{'question':'How closely can fractions approximate pi as their denominators get larger?','idea':'The manuscript claims that pi has irrationality exponent exactly two. Roughly, fractions can approximate pi well, but improvements beyond the usual square-of-the-denominator scale cannot keep happening indefinitely. This is a claim about the best possible long-run approximation rate, not a new decimal expansion of pi.','why':'Irrational numbers differ in how easily fractions approximate them. Locating pi precisely on this scale would answer a sharp question about its arithmetic behavior; the manuscript also claims a consequence for the Flint–Hills series.'}}
for id,fields in updates.items():
 p=root/(id+'.json')
 if p.exists():
  d=json.load(open(p));d.update(fields);d['reviewStatus']='assistant-edited';p.write_text(json.dumps(d,ensure_ascii=False))
cat=json.load(open('dist/data/catalogue.json'));fm={f['id']:f for f in cat['families']}
for p in root.glob('*.json'):
 d=json.load(open(p));terms=set(re.findall(r'[a-z]{5,}',fm[d['familyId']]['title'].lower()))-{'theorem','conjecture','general','problem'}
 d['references'].sort(key=lambda r:-len(terms&set(re.findall(r'[a-z]{5,}',r['citation'].lower()))))
 p.write_text(json.dumps(d,ensure_ascii=False))
print('Edited important examples and ordered references by title-word overlap.')
