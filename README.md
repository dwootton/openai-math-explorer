# OpenAI Math Explorer

A map and reader for the [OpenAI math repository](https://github.com/openai/math): 372 research families, 722 manuscripts, and 17 subjects. Independent project, not an official OpenAI product.

[Open the explorer](https://dwootton.github.io/openai-math-explorer/) · [Watch or download the demo](https://dwootton.github.io/openai-math-explorer/demo/)

Select a subject to dim other points, or Shift-click to keep multiple families highlighted. Compare paper summaries, linked Lean source, or shared references. Search titles, subjects, abstracts and family IDs locally in your browser. Read the original manuscripts and linked Lean scope/source. All 372 families have plain-language introductions. These summarize the manuscript claims and retain source references; they are not independent proof reviews.

## Run locally

```sh
npm ci
npm run build
npm run dev
```

Open http://127.0.0.1:4318 . The precomputed research data is included; no embedding model is needed for browsing, keyword search, or preset lenses. `npm test` validates corpus coverage and projection math.

## GitHub Pages

Set Settings → Pages → Build and deployment → Source to **GitHub Actions**. Push to main to run the included deployment workflow. Project paths such as `/openai-math-explorer/` are supported. The app's GitHub link is generated from the repository running the workflow.

GitHub Pages hosts static files. Maps, preset lenses, keyword search, ELI5, PDFs and Lean source reading work without a server. Semantic search and custom concepts require the separate embedding service. The published workflow intentionally supplies no backend URL: semantic query search and custom concepts are disabled, and no requests go to the GB10. To enable a backend in a separate deployment, explicitly pass `BACKEND_BASE_URL` at build time and set the server’s `ALLOWED_ORIGINS` to the exact frontend origin. Never put API secrets in this variable or in the client.

The backend includes a Fastify gateway and a private Python embedding service. Bind both to loopback, serve only dist, and expose the web gateway through an appropriate HTTPS reverse proxy. Google EmbeddingGemma 2 is pinned in server/model-config.json. The model needs a suitable Python/CUDA environment; requirements-lock.txt records the development environment. Use a dedicated account/container for a public backend rather than running it with access to personal files. Request limits reduce abuse but are not a substitute for edge protection.

## Data and interpretation

Source snapshot: adc7f1241b42e322a6451854ab7e4b4c146bf78a. Linked Lean material covers 235 of 372 families. There are 405 comparator-linked entries referencing 402 distinct solution modules. Imported Lean dependencies are not embedded. A linked family is not necessarily fully formalized; the app does not compile or verify proofs.

Actual normalized 768D EmbeddingGemma 2 vectors represent family titles/summaries/abstracts and linked Lean modules. Lines show eight cosine neighbors in the active full or projected space; UMAP is the 2D layout. Prompt lenses use centered PCA/SVD and projection, inspired by [Jasper Lu](https://jasperlu.com/blog/prompted-similarity-search/). Layout inspiration: [NeurIPS 2024 explorer](https://neurips2024.vizhub.ai).

Six exploratory clusters were selected by cosine silhouette (0.0902, weak separation). About 58% of top-five neighbors share the source subject label. Gemma and the earlier MiniLM pipeline both scored 9/12 first-place matches in a small known-item check. This is not a comprehensive mathematical similarity benchmark. ELI5 guides and extracted references are reading aids, not independent validation of manuscript claims.

## Privacy and counts

Google Analytics is disabled by default. Optional opt-in controls require a completed operator notice and deployment configuration; enabling a tag alone does not establish legal compliance. Search strings and custom concept text are excluded from analytics events. Any embedding requests are sent to the configured backend, so describe that provider in your privacy notice.

When self-hosted, the server keeps private UTC daily page-request totals for 90 days, without counter cookies or visitor-level records. `npm run visits` reads those totals. GitHub Pages traffic never reaches this server, so that counter does not measure the Pages site. GitHub itself processes visitor connection information for hosting/security.

## Attribution

Research artifacts remain subject to the upstream licenses retained in public-data/data/SOURCE-LICENSE.txt and LEAN-LICENSE.txt. PDFs and source links point at the pinned upstream repository. Third-party libraries retain their respective licenses. No claim of independent mathematical verification is made.

## References view

The References tab compares deduplicated cited works across each family’s manuscripts using rarity-weighted cosine similarity and an evidence-count adjustment. Expand a neighbor’s shared works to inspect links and both source bibliographies. The calculation is fully precomputed. [Matching, formula, caveats and rebuild instructions](content/reference-method.md).

## Lean source similarity

The Lean proofs view uses existing embeddings of actual linked solution modules, including code and comments. Chunk embeddings are averaged per module; unique modules are then equally weighted and normalized per family. Neighbors use cosine similarity before UMAP projection. There are 402 distinct modules covering 235 families; the 137 families without linked solutions are not plotted or ranked in this view. The details panel links the exact files used.

Imported dependencies are not expanded. Some entry modules are short wrappers around imported results, so source similarity is not a verified classification of proof techniques. Family 074 (Kakeya) has no linked Lean source; the former 250th-to-first example came from summary embeddings projected using technique prompts, not Lean proof comparison. The advanced explorer retains that experiment under “Technique prompts.”

Rebuild this view with `node scripts/build-lean-map.mjs` after building the app data, then rebuild the site.

## Map styling and poster exports

The default summary layout uses cosine UMAP with 12 neighbors, min_dist 0.32, 400 epochs and seed 42. Nine candidate layouts were rendered and visually reviewed. At k=10, the selected layout has trustworthiness 0.9192 (previously 0.9224) and neighbor recall 0.4478 (previously 0.4398). This is a spacing/readability tradeoff, not evidence of improved mathematical understanding. High-dimensional neighbor rankings and the other projections are unchanged. Details are in `public-shell/explore/layout-study.json`.

Run `node scripts/study-layouts.mjs` and `node scripts/render-layout-study.mjs` to compare candidates. `node scripts/apply-poster-layout.mjs` applies the selected layout. `node scripts/render-posters.mjs` produces the two default posters. The map’s Poster button exports the current full comparison and theme as SVG or a 2400 × 3000 PNG. SVG preserves vector geometry for printing. Colors represent repository subjects; coordinates and labels are derived from the catalogue, with no generated illustration.
