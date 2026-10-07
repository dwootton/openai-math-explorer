import {build} from 'esbuild';import fs from 'node:fs/promises';import {gzipSync,brotliCompressSync,constants} from 'node:zlib';import path from 'node:path';
const out=process.env.RELEASE_DIR||'dist';
await fs.mkdir(out,{recursive:true});for(const name of ['index.html','style.css','analytics-config.json','site-config.json'])await fs.copyFile('public-shell/'+name,out+'/'+name);
if(await fs.stat('public-data').catch(()=>null))await fs.cp('public-data',out,{recursive:true});
if(process.env.GITHUB_PAGES==='true'){const repositoryUrl=process.env.GITHUB_REPOSITORY?'https://github.com/'+process.env.GITHUB_REPOSITORY:'';const backendBase=process.env.BACKEND_BASE_URL||'';if(backendBase&&!/^https:\/\//.test(backendBase))throw Error('Pages backend requires HTTPS');await fs.writeFile(out+'/site-config.json',JSON.stringify({hosting:'github-pages',repositoryUrl,backendBase}));await fs.writeFile(out+'/.nojekyll','');}
await fs.cp('public-shell/explore',out+'/explore',{recursive:true});
await fs.cp('public-shell/demo',out+'/demo',{recursive:true});
await fs.cp('public-shell/explanations',out+'/explanations',{recursive:true});
await build({entryPoints:['src/app.js','src/map-worker.js'],outdir:out,bundle:true,splitting:true,chunkNames:'assets/[name]-[hash]',format:'esm',minify:true,sourcemap:false});
await build({entryPoints:['public-shell/explore/focus.js'],outfile:out+'/explore/focus.js',bundle:true,format:'esm',minify:true});
await fs.mkdir(out+'/vendor',{recursive:true});await fs.copyFile('node_modules/pdfjs-dist/build/pdf.worker.min.mjs',out+'/vendor/pdf.worker.min.mjs');await fs.copyFile('node_modules/katex/dist/katex.min.css',out+'/vendor/katex.min.css');await fs.cp('node_modules/katex/dist/fonts',out+'/vendor/fonts',{recursive:true});
async function compress(dir){for(const ent of await fs.readdir(dir,{withFileTypes:true})){const p=path.join(dir,ent.name);if(ent.isDirectory())await compress(p);else if(/\.(json|js|mjs|css|html|txt)$/.test(p)){const b=await fs.readFile(p);await fs.writeFile(p+'.gz',gzipSync(b,{level:9}));await fs.writeFile(p+'.br',brotliCompressSync(b,{params:{[constants.BROTLI_PARAM_QUALITY]:6}}));}}}
await compress(out);console.log('Built split, precompressed release');
