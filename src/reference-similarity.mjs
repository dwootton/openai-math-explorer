// Weighted bibliographic coupling. Input lists contain canonical work IDs, not citation text.
export function referenceSimilarity(families){
 const ids=Object.keys(families).sort(),sets=ids.map(id=>new Set(families[id])),frequency=new Map();
 for(const refs of sets)for(const key of refs)frequency.set(key,(frequency.get(key)||0)+1);
 const idf=new Map([...frequency].map(([key,count])=>[key,1+Math.log((ids.length+1)/(count+1))]));
 const norm=sets.map(refs=>Math.sqrt([...refs].reduce((sum,key)=>sum+idf.get(key)**2,0)));
 const matrix=ids.map(()=>Array(ids.length).fill(0)),neighbors=ids.map(()=>[]);
 for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++){
  const shared=[...sets[i]].filter(key=>sets[j].has(key)).sort((a,b)=>idf.get(b)-idf.get(a)||a.localeCompare(b));
  if(!shared.length)continue;
  const cosine=shared.reduce((sum,key)=>sum+idf.get(key)**2,0)/(norm[i]*norm[j]);
  const score=cosine*shared.length/(shared.length+2);
  matrix[i][j]=matrix[j][i]=score;
  neighbors[i].push({id:ids[j],score,cosine,shared});neighbors[j].push({id:ids[i],score,cosine,shared});
 }
 for(const list of neighbors)list.sort((a,b)=>b.score-a.score||b.shared.length-a.shared.length||a.id.localeCompare(b.id));
 return{ids,sets,frequency,idf,matrix,neighbors};
}
