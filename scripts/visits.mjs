import fs from 'node:fs/promises';
const file=new URL('../var/page-counts.json',import.meta.url);
let data;try{data=JSON.parse(await fs.readFile(file,'utf8'));}catch(e){if(e.code==='ENOENT'){console.log('No page counts saved yet.');process.exit(0);}throw e;}
console.log('Daily page requests (UTC). Reloads and bots included; not unique visitors.');
console.table(Object.entries(data.days).sort(([a],[b])=>b.localeCompare(a)).map(([date,c])=>({date,app:c.app,demo:c.demo,total:c.app+c.demo})));
console.log('Retained total:',Object.values(data.days).reduce((n,c)=>n+c.app+c.demo,0));
