# Reference similarity

This view measures **shared literature**, also called bibliographic coupling. It is separate from the text-embedding and prompted-subspace views: two references are not treated as the same work merely because they sound alike.

## Source and matching

Bibliographies are extracted across the 722 manuscripts in the pinned catalogue. TeX inputs are followed to collect citation keys; uncited BibTeX database entries are removed. Explicit `bibitem` entries and `nocite{*}` lists are retained. Source coverage and any no-command fallbacks are recorded in `explore/reference-analysis.json`. A manuscript provided only through included PDFs may have no extractable bibliography, even when its family has references from other manuscripts.

DOIs are case-normalized and arXiv version suffixes removed. A record containing both identifiers bridges its preprint and published versions. Other merges require an exact normalized title and first-author surname, with compatible years for structured records; plain citations can match a distinctive exact known title plus surname. Conflicting DOI/arXiv identities block title-based merges. Compound references containing multiple different identifiers do not create identifier bridges. These conservative rules can miss legitimate matches. Bibliographic identity and mathematical validity have not been independently verified against publishers.

References to the OpenAI release itself are excluded so companion-paper links do not dominate the view. Each canonical work counts once per family, across all its manuscripts. Extracted source variants and rejected conflicts are available in the local build audit. Every displayed shared work links both to the work and to the pinned source bibliography in each family.

## Score

For N families, let df(r) be the number citing work r. The binary reference vector has weight

`w(r) = 1 + log((N + 1) / (df(r) + 1))`.

We compute cosine similarity between these weighted vectors, then multiply by `shared / (shared + 2)`. This last factor is an explicit evidence-strength heuristic: a one-reference coincidence receives less support than several shared works. It has not been fitted to expert relevance judgments. Normalization prevents raw bibliography length from determining the rank; IDF reduces the influence of widely shared works. Duplicates, author names alone, reference order and journal names do not create similarity.

Only positive-overlap neighbors are shown. UMAP uses distances `1 - score`, seed 42, 15 neighbors, minDist 0.12 and 350 epochs. Coordinates are rotation/reflection-aligned with the original view; rankings come from the full score matrix, not 2D proximity. Families with no matched overlap are placed on a separate bottom row and have no edges. Their row positions do not encode similarity.

This detects shared background or methods worth examining; it does not establish that two proofs use a reference for the same purpose. Citation context, importance within a proof, or disagreement with a cited work is not inferred.

## Rebuild

After `npm run build`, run:

```sh
python3 scripts/references/extract.py
python3 scripts/references/filter_cited.py
python3 scripts/references/match.py
node scripts/build-reference-map.mjs
npm run build
npm test
python3 scripts/references/test_extract.py
```

The checked-in source manifest pins paths and commit. Extraction downloads public sources into `.cache/`; subsequent runs reuse them. Publishing uses the checked-in precomputed data, with no inference server or query API. Detailed shared-work metadata loads only when its disclosure is opened.

Background: [Weighted bibliographic coupling](https://doi.org/10.1016/j.joi.2019.01.012). The exact scoring and matching choices above are specific to this explorer.
