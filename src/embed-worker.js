import {pipeline,env} from '/vendor/transformers.min.js';
env.allowLocalModels=true;env.allowRemoteModels=false;env.localModelPath='/models/';env.backends.onnx.wasm.numThreads=1;env.backends.onnx.wasm.wasmPaths='/vendor/';
let extractor;
self.onmessage=async({data})=>{try{
 extractor??=pipeline('feature-extraction','Xenova/all-MiniLM-L6-v2',{dtype:'q8',device:'wasm',progress_callback:p=>{if(p.status==='progress')self.postMessage({id:data.id,status:'progress',message:`Loading local model · ${Math.round(p.progress)}%`});}});
 const run=await extractor;const vectors=(await run(data.texts,{pooling:'mean',normalize:true,truncation:true,max_length:256})).tolist();self.postMessage({id:data.id,vectors});
 }catch(e){extractor=null;self.postMessage({id:data.id,error:e.message});}};
