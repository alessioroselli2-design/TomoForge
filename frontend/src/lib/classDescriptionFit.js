// Shared printable-text rule: use the maximum number of complete sentences.
// The complete source is preserved for the QR/details page.
export const fitClassDescription=(source,fits)=>{
 const value=String(source||"").replace(/\s+/g," ").trim();
 if(!value)return "";
 if(fits(value))return value;
 const ends=[...value.matchAll(/[.!?](?=\s|$)/g)].map(match=>match.index+1);
 let lo=0,hi=ends.length-1,best="";
 while(lo<=hi){
   const mid=Math.floor((lo+hi)/2);
   const candidate=value.slice(0,ends[mid]).trim();
   if(fits(candidate)){best=candidate;lo=mid+1;}
   else hi=mid-1;
 }
 return best||"Descrizione completa disponibile tramite QR.";
};
