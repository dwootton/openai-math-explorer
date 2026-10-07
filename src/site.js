export const assetUrl=path=>new URL(path.replace(/^\//,''),document.baseURI).href;
let settings={backendBase:'',repositoryUrl:'',hosting:'gb10'};
try{const r=await fetch(assetUrl('site-config.json'),{cache:'no-store'});if(r.ok)settings={...settings,...await r.json()};}catch{}
export const siteConfig=settings;
export const hasEmbeddingBackend=()=>siteConfig.hosting!=='github-pages'||!!siteConfig.backendBase;
export const apiUrl=path=>siteConfig.backendBase?new URL(path.replace(/^\//,''),siteConfig.backendBase.replace(/\/$/,'')+'/').href:assetUrl(path);
