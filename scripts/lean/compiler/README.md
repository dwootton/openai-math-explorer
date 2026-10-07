# Compiler-resolved Lean inputs

The previous resolver inferred names from source and stopped after two reference
hops. This pipeline imports the pinned project's compiled Lean environment and
walks the constants used by each catalogue target's elaborated type and body.
It follows repository-local dependencies transitively, including implicit
instances and dependencies introduced by macros. Merely importing a module does
not put all of its declarations into the embedding.

## Reproducibility and boundaries

- The checkout must match the catalogue's source commit and `lean-toolchain`.
  External packages must match `lake-manifest.json`. The upstream compatibility
  patches are retained and their actual diffs hashed in provenance.
- Entry roots are the catalogue config's `theorem_names` and `definition_names`.
  An entry without roots is excluded, never replaced by a guessed whole file.
- Only bodies from `OAI` modules are expanded. External constants are recorded;
  common Mathlib/Lean infrastructure is not embedded wholesale. Axiom collection
  nevertheless follows the complete dependency closure across that boundary.
- Missing declarations, compilation failures, `sorryAx`, and axioms outside each
  entry's permitted list are failures. No old heuristic output is substituted.
- Compiler declaration ranges select source blocks. Generated declarations reuse
  a reachable parent's compiler range where available; otherwise their elaborated
  expressions are retained. This source-block deduplication does not infer edges.
  Pretty-printer omissions in retained fallback expressions cause a failure.
- Embeddings use the same pinned model, task, chunking, aggregation, and cosine
  comparison as Topics. No ELI5 text is used. The numeric audit reconstructs every
  family and entry vector from the cached source-chunk vectors.
- `compilerVerified` in data means compiler-resolved, not a claim that the paper's
  informal claim was independently checked against the Lean statement. This also
  does not independently kernel-recheck downloaded external library caches.
- No source declaration is excluded merely for being older: an older lemma that
  the target actually uses is relevant. Unused declarations are excluded.

## Running

Provide a full pinned `lean/` checkout, its Lake dependencies/cache, and the exact
Lean toolchain. On GB10 these live under `.cache/compiler-source/lean` and
`.cache/lean-toolchains/lean-4.34.1-linux_aarch64`.

```sh
python3 scripts/lean/compiler/run.py \
  --source .cache/compiler-source/lean \
  --toolchain .cache/lean-toolchains/lean-4.34.1-linux_aarch64 \
  --output .cache/compiler-results
```

`run.py` builds each catalogue solution module and extracts every entry. Successful
results are reusable only under the same provenance identity. Failures are retried
on the next run. The optional `.cache/compiler-build-order.json` affects scheduling
only, never dependency discovery. Do not edit the extractor during a run; restart
if it changes so output cannot mix extractor versions.

```sh
python3 scripts/lean/compiler/prepare_candidate.py \
  --results .cache/compiler-results \
  --source .cache/compiler-source/lean \
  --output .cache/compiler-candidate \
  --python /home/dwootton/Projects/openai-math-explorer/.venv/bin/python \
  --wait-service math-lean-compiler.service
```

The second command waits for the complete pass, then materializes inputs, embeds,
audits, and computes maps into an **offline candidate directory**. It never writes
published data or deploys. Raw graphs/source manifests can be large and stay in
`.cache`; publish only compact data/provenance after inspecting exclusions,
coverage, ranks, UI source explanations, and payload sizes. Do not describe the
live map as compiler-resolved until the candidate is actually deployed.

```sh
python3 -m unittest discover -s scripts/lean/compiler -p 'test_*.py'
```

The compiler fixture checks macro and implicit-instance dependencies, exclusion of
an unused theorem in the same module, and explicit failure on an unknown target.
The materializer rejects incomplete corpus runs and mixed provenance.
