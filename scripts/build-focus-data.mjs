// Direct comparisons share one reproducible map builder; no prompt projections.
process.env.DATA_DIR??='dist/data';
await import('./build-direct-maps.mjs');
