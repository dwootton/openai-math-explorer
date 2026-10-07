import {createPageCounter} from './page-counts.mjs';
import Fastify from 'fastify';import staticFiles from '@fastify/static';import rateLimit from '@fastify/rate-limit';import path from 'node:path';
const root=path.resolve(process.env.PUBLIC_DIR||'dist');const port=Number(process.env.PORT||4318);
const app=Fastify({logger:false,bodyLimit:32768,requestTimeout:85000,connectionTimeout:90000,keepAliveTimeout:10000});
const allowedOrigins=new Set((process.env.ALLOWED_ORIGINS||'').split(',').map(s=>s.trim()).filter(Boolean));
app.addHook('onRequest',async(req,reply)=>{if(!req.url.startsWith('/api/'))return;const origin=req.headers.origin;if(!origin)return;let same=false;try{same=new URL(origin).host===req.headers.host;}catch{}if(!same&&!allowedOrigins.has(origin))return reply.code(403).send({error:'Origin not allowed'});if(allowedOrigins.has(origin)){reply.header('Access-Control-Allow-Origin',origin);reply.header('Vary','Origin');}});
app.options('/api/embed',async(req,reply)=>reply.header('Access-Control-Allow-Methods','POST').header('Access-Control-Allow-Headers','Content-Type').header('Access-Control-Max-Age','600').code(204).send());
const countsFile=path.resolve(process.env.PAGE_COUNTS_FILE||'var/page-counts.json');
if(countsFile===root||countsFile.startsWith(root+path.sep))throw Error('Page counts must be outside the public directory');
const pageCounter=await createPageCounter(countsFile);
app.addHook('onResponse',async(req,reply)=>pageCounter.record(req,reply));
app.addHook('onClose',async()=>pageCounter.close());
let inferenceActive=0,inferenceTokens=8,inferenceRefill=Date.now();
await app.register(rateLimit,{global:false,max:20,timeWindow:'1 minute',keyGenerator:req=>req.headers['cf-connecting-ip']||req.ip,cache:10000,errorResponseBuilder:()=>({statusCode:429,error:'Too many semantic requests. Please wait a minute. Browsing and preset lenses remain available.'})});
app.addHook('onSend',async(req,reply,payload)=>{reply.header('X-Content-Type-Options','nosniff');reply.header('Referrer-Policy','strict-origin-when-cross-origin');reply.header('Permissions-Policy','camera=(), microphone=(), geolocation=()');if(req.url.startsWith('/api/'))reply.header('Cache-Control','no-store');return payload;});
app.post('/api/embed',{config:{rateLimit:{max:20,timeWindow:'1 minute'}}},async(req,reply)=>{
 const b=req.body;if(!b||!Array.isArray(b.texts)||b.texts.length<1||b.texts.length>32||!['similarity','search','code'].includes(b.task)||b.texts.some(t=>typeof t!=='string'||!t.trim()||t.length>2048)||b.texts.reduce((s,t)=>s+t.length,0)>16000)return reply.code(400).send({error:'Provide 1–32 nonempty texts (2048 characters each, 16000 total) and a valid task.'});
 const now=Date.now();inferenceTokens=Math.min(8,inferenceTokens+(now-inferenceRefill)/1000);inferenceRefill=now;if(inferenceActive>=8||inferenceTokens<1)return reply.code(503).header('Retry-After','2').send({error:'Semantic search is busy. Try again shortly.'});inferenceTokens--;inferenceActive++;
 try{const response=await fetch('http://127.0.0.1:4319/embed',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b),signal:AbortSignal.timeout(80000)});if(response.headers.get('retry-after'))reply.header('Retry-After',response.headers.get('retry-after'));reply.code(response.status);return await response.json();}catch{return reply.code(503).send({error:'Semantic search is temporarily unavailable. Keyword search and preset lenses still work.'});}finally{inferenceActive--;}
});
app.get('/api/health',async(req,reply)=>{try{const r=await fetch('http://127.0.0.1:4319/health',{signal:AbortSignal.timeout(1500)});return await r.json();}catch{return reply.code(503).send({ready:false});}});
app.get('/download/math-explorer-demo.mp4',async(req,reply)=>{reply.header('Content-Disposition','attachment; filename="math-explorer-demo.mp4"');reply.header('Cache-Control','no-store');return reply.type('application/octet-stream').sendFile('demo/math-explorer-demo-v5.mp4');});
await app.register(staticFiles,{root,preCompressed:true,cacheControl:false,etag:true,lastModified:true,dotfiles:'deny',index:['index.html'],setHeaders(res,file){const rel=path.relative(root,file).replace(/\.(br|gz)$/, '');if(/\.(html|js|css)$/.test(rel)&&!rel.startsWith('assets/'))res.header('Cache-Control','no-cache');else if(rel.startsWith('assets/'))res.header('Cache-Control','public, max-age=31536000, immutable');else res.header('Cache-Control','public, max-age=3600, stale-while-revalidate=86400');res.header('Vary','Accept-Encoding');}});
app.setErrorHandler((err,req,reply)=>{reply.code(err.statusCode||500).send({error:err.statusCode===413?'Request too large.':err.statusCode===429?'Too many semantic requests. Please wait a minute; browsing remains available.':'Request could not be completed.'});});
await app.listen({host:'127.0.0.1',port});console.log(`Explorer serving on http://127.0.0.1:${port}`);
for(const signal of ['SIGTERM','SIGINT'])process.on(signal,async()=>{await app.close();process.exit(0)});
