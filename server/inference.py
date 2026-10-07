import asyncio,hashlib,time
from contextlib import asynccontextmanager
from collections import OrderedDict
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel,Field,field_validator
from typing import Literal
from embedding_model import Embedder,MODEL,REVISION
class Payload(BaseModel):
 texts:list[str]=Field(min_length=1,max_length=32)
 task:Literal['similarity','search','code']='similarity'
 @field_validator('texts')
 @classmethod
 def validate_texts(cls,v):
  if any(not s.strip() or len(s)>2048 for s in v) or sum(map(len,v))>16000:raise ValueError('Use nonempty texts, at most 2048 characters each and 16000 total.')
  return v
cache=OrderedDict();queue=asyncio.Queue(maxsize=8);stats={'requests':0,'cacheHits':0,'batches':0};model=None
async def inference_loop():
 while True:
  first=await queue.get();batch=[first];await asyncio.sleep(.008)
  while len(batch)<4 and not queue.empty():batch.append(queue.get_nowait())
  try:
   for task in ['similarity','search','code']:
    subset=[item for item in batch if item[0].task==task]
    if not subset:continue
    texts=[s for req,_,_ in subset for s in req.texts]
    vs=await asyncio.to_thread(model.encode,texts,task,8);stats['batches']+=1;offset=0
    for req,fut,key in subset:
     result=vs[offset:offset+len(req.texts)].tolist();offset+=len(req.texts)
     cache[key]=result;cache.move_to_end(key)
     while len(cache)>256:cache.popitem(last=False)
     if not fut.done():fut.set_result(result)
  except Exception as e:
   for _,fut,_ in batch:
    if not fut.done():fut.set_exception(RuntimeError('Embedding calculation failed. Please retry.'))
  finally:
   for _ in batch:queue.task_done()
@asynccontextmanager
async def lifespan(app):
 global model
 model=await asyncio.to_thread(Embedder)
 model.encode(['A mathematical theorem.'])
 task=asyncio.create_task(inference_loop());yield;task.cancel()
app=FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
@app.get('/health')
def health():return {'ready':model is not None,'model':MODEL,'revision':REVISION,'dimensions':768,'queue':queue.qsize()}
@app.post('/embed')
async def embed(req:Payload):
 import json
 stats['requests']+=1;key=hashlib.sha256((REVISION+json.dumps(req.model_dump(),sort_keys=True)).encode()).hexdigest()
 if key in cache:stats['cacheHits']+=1;cache.move_to_end(key);vectors=cache[key]
 else:
  if queue.full():return JSONResponse({'error':'Semantic search is busy. Please try again shortly.'},status_code=503,headers={'Retry-After':'5'})
  fut=asyncio.get_running_loop().create_future();queue.put_nowait((req,fut,key))
  try:vectors=await asyncio.wait_for(fut,75)
  except asyncio.TimeoutError:return JSONResponse({'error':'Search timed out. Try a shorter query.'},status_code=504)
  except RuntimeError as e:return JSONResponse({'error':str(e)},status_code=503)
 return {'model':MODEL,'revision':REVISION,'dimensions':768,'vectors':vectors}
