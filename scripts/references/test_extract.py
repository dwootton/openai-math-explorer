import unittest
from extract import records, plain
from match import identifiers
class ExtractionTests(unittest.TestCase):
    def test_nested_bibtex_and_math(self):
        refs=list(records(r'@article{key, author={Smith, A. and Doe, B.}, title={The {Kakeya} problem in $\mathbb{R}^3$}, year={2020}, doi={10.1234/ABC}}','references.bib'))
        self.assertEqual(len(refs),1)
        self.assertEqual(refs[0]['title'],r'The Kakeya problem in $\mathbb{R}^3$')
        self.assertEqual(identifiers(refs[0]),{'doi:10.1234/abc'})
    def test_arxiv_versions_and_doi_alias(self):
        base={'doi':'10.1234/ABC','arxiv':'2102.11818v4','raw':'','title':''}
        a=identifiers(base)
        b=identifiers({'doi':'','arxiv':'','raw':r'\url{https://doi.org/10.1234/abc} \url{https://arxiv.org/pdf/2102.11818v1.pdf}'})
        self.assertEqual(a,b)
    def test_compound_citation_does_not_create_false_identifier_bridge(self):
        self.assertEqual(identifiers({'raw':'doi:10.1234/one and doi:10.1234/two'}),set())
    def test_commented_bibitems_excluded(self):
        rs=list(records('% \\bibitem{bad} Not a real citation.\n\\bibitem{good} A. Smith. A real bibliography entry.\\end{thebibliography}','paper.tex'))
        self.assertEqual([r['key'] for r in rs],['good'])
if __name__=='__main__':unittest.main()
