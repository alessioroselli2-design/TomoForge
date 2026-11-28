export function isTemporaryAuthError(error){
 const status=error?.response?.status;
 return !error?.response || [408,429,502,503,504].includes(status);
}
export async function readAuth(api,path,config={},pause=ms=>new Promise(resolve=>setTimeout(resolve,ms))){
 const options={...config,timeout:config.timeout??12000};
 try{return await api.get(path,options);}
 catch(error){
  if(!isTemporaryAuthError(error)||error?.response?.status===429||error?.code==="ERR_CANCELED")throw error;
  await pause(450);
  return api.get(path,options);
 }
}
