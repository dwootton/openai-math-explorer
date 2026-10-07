# Direct source comparisons

Topics embeds each catalogue family's title, description, paper titles and abstracts. Lean embeds actual named target declarations and supporting source blocks, selected with the same bounded static expansion policy for every linked entry. Neither text view uses the former prompt/SVD projection. Topic fields are verified against the upstream `CONTENTS.md` snapshot, including all 722 paper abstracts. ELI5 guides never enter embedding inputs. Each topic vector records a SHA-256 of its exact input text and the included paper paths. The concept atlas compares these source vectors against authored concept prompts; those prompts are not ELI5 guides.

Both use google/embeddinggemma-2 revision 914f7f89142e33e77833254d9c9b90c3cef7303b, the SentenceSimilarity task, normalized 768-dimensional chunk vectors, 1,024-token chunks with 96-token overlap, and the normalized mean of unique chunk embeddings. Exact duplicate chunks count once within an entry or family. Nearest neighbors are ranked by cosine in the original 768 dimensions. UMAP is only a display, with the same cosine metric and settings for both text views.

## Lean scope

`scripts/lean/resolve_declarations.py` starts with catalogue target names and follows two explicit name-reference hops within cached imported source modules at the pinned repository commit. It resolves unique names, preferring the current file. Unqualified references shorter than eight characters are skipped to reduce accidental matches to local variables. This heuristic can miss real dependencies and can still select false matches. This is not Lean elaboration or verified dependency analysis.

Implicit instances, macros, ambiguous names, external libraries (including Mathlib), and imports absent from the pinned source cache are not expanded. The selected declaration manifest records unresolved target names, ambiguous references, and uncached imports. An entry with no resolved named target falls back to its actual entry source, without imports or comments. The UI exposes exact source declaration links and coverage per family. Do not describe this as a complete proof or complete dependency closure.

The original attempt to collect the full import closure encountered GitHub rate limiting after tens of thousands of modules. Expanding every imported module would also include large quantities of unrelated generated declarations. The bounded declaration manifest is the frozen input for this release; rebuilding the source cache later can change resolution and requires regeneration and a new audit.

## Coverage and interpretation

Topics includes 372 families; Lean includes the 235 with catalogue-linked Lean solutions, encompassing 405 catalogue entries. Two import-only entries have no resolved source and are excluded from the entry map (403 embedded entries); their families still have other available entries. Missing Lean families receive no invented source vector or neighbor ranking. A rank change between the tabs can partly reflect the changed candidate population; claims comparing ranks should restrict both rankings to their common covered families. Code similarity can reflect notation and formalization choices, not necessarily mathematical proof strategy.

References is deliberately separate: inverse-frequency weighted shared citations, normalized for bibliography length and discounted for very small overlaps. It is not an embedding cosine comparison. Existing reference evidence and rankings are unchanged.

## Reproduction

The selected input is `content/lean-declaration-manifest.json`. `scripts/index-direct.py` writes the topic, proof-entry, and Lean-family vectors plus public source provenance. `scripts/build-direct-maps.mjs` builds maps and neighbor lists from those vectors. Set DATA_DIR to the output data directory. The public site uses precomputed artifacts and requires no inference service.

The legacy analysis is retained as historical data but is no longer presented as current findings. Search retrieval vectors are separate from map comparisons and are not used in map ranks; GitHub Pages search remains lexical.
