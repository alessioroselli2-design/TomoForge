// Search summaries can contain arrays, strings and legacy objects. Do not
// render an object as a React child or call array methods on a scalar.
export function displayText(value){
 if(typeof value==="string"||typeof value==="number")return String(value);
 if(Array.isArray(value))return value.map(displayText).filter(Boolean).join(", ");
 if(value&&typeof value==="object")return displayText(value.name??value.nome??value.label??value.value??"");
 return "";
}
export function displayClasses(value){
 return displayText(value);
}
export function searchRecords(value){
 return Array.isArray(value)?value.filter(record=>record&&typeof record==="object"&&typeof record.id==="string"): [];
}
export function displaySources(value,privateLibrary=false){
 return Array.isArray(value)?value.filter(ref=>ref&&typeof ref==="object").map(ref=>{
  const filename=privateLibrary&&ref.language==="es"?"Fonte spagnola":displayText(ref.filename)||"Manuale";
  return filename+" p."+ (displayText(ref.page)||"?");
 }).join(privateLibrary?", ":" · "):"";
}
