import os,torch,numpy as np
from sentence_transformers import SentenceTransformer
MODEL='google/embeddinggemma-2'
# The immutable model revision is populated from the inspected Hugging Face metadata.
import json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
REVISION=json.load(open(ROOT/'server/model-config.json'))['revision']
class Embedder:
 def __init__(self):
  torch.set_num_threads(8)
  self.model=SentenceTransformer(MODEL,revision=REVISION,device='cuda' if torch.cuda.is_available() else 'cpu',config_kwargs={'vision_config':None,'audio_config':None},model_kwargs={'dtype':torch.bfloat16 if torch.cuda.is_available() else torch.float32},cache_folder=str(ROOT/'.cache/hf'))
  self.model.max_seq_length=8192
  self.tokenizer=self.model.tokenizer
 def encode(self,texts,task='similarity',batch_size=8):
  prompt={'similarity':'SentenceSimilarity','search':'SearchQuery','code':'CodeRetrieval','document':None}[task]
  kwargs={'normalize_embeddings':True,'batch_size':batch_size,'show_progress_bar':False,'convert_to_numpy':True}
  if prompt:kwargs['prompt_name']=prompt
  else:kwargs['prompt']=''
  x=self.model.encode(texts,**kwargs).astype(np.float32)
  if x.shape[1]!=768 or not np.isfinite(x).all():raise ValueError('Invalid embedding output')
  return x
 def chunks(self,text,limit=1024,overlap=96):
  ids=self.tokenizer.encode(text,add_special_tokens=False)
  return [self.tokenizer.decode(ids[i:i+limit],skip_special_tokens=True) for i in range(0,max(1,len(ids)),limit-overlap)]
