import fs from 'node:fs/promises';
import path from 'node:path';

// Aggregate origin requests only: no cookies, browser script, IDs, IPs or request logs.
export async function createPageCounter(file) {
  const days=Object.create(null);
  try {
    const saved=JSON.parse(await fs.readFile(file,'utf8'));
    for(const [day,counts] of Object.entries(saved.days||{})) {
      if(!/^\d{4}-\d{2}-\d{2}$/.test(day))continue;
      days[day]={app:Number.isSafeInteger(counts.app)&&counts.app>=0?counts.app:0,demo:Number.isSafeInteger(counts.demo)&&counts.demo>=0?counts.demo:0};
    }
  } catch(e) {if(e.code!=='ENOENT')throw e;}
  let dirty=false,writing=Promise.resolve();
  function prune(){const cutoff=new Date(Date.now()-89*86400000).toISOString().slice(0,10);for(const key of Object.keys(days))if(key<cutoff){delete days[key];dirty=true;}}
  function increment(page){
    const day=new Date().toISOString().slice(0,10);prune();
    days[day]??={app:0,demo:0};days[day][page]++;dirty=true;
  }
  function flush(){
    prune();
    if(!dirty)return writing;
    dirty=false;
    const body=JSON.stringify({version:1,timezone:'UTC',retentionDays:90,days},null,2)+'\n';
    writing=writing.then(async()=>{await fs.mkdir(path.dirname(file),{recursive:true,mode:0o700});await fs.writeFile(file+'.tmp',body,{mode:0o600});await fs.rename(file+'.tmp',file);}).catch(e=>{dirty=true;console.error('Aggregate page counts could not be saved:',e.code||'write error');});
    return writing;
  }
  const timer=setInterval(flush,5000);timer.unref();
  return {record(req,reply){
    if(req.method!=='GET'||![200,304].includes(reply.statusCode))return;
    if(/prefetch/i.test(String(req.headers.purpose||req.headers['sec-purpose']||'')))return;
    const url=req.url.split('?')[0];
    if(['/','/index.html','/explore/','/explore/index.html'].includes(url))increment('app');
    else if(url==='/demo/'||url==='/demo/index.html')increment('demo');
  },async close(){clearInterval(timer);await flush();}};
}
