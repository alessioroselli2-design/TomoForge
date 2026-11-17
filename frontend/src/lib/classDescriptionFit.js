// Maximum complete sentences for a fixed class well. Never truncate a word.
// If the first sentence cannot fit, prefer its last comma/semicolon break.
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
 if(best)return best;
 const firstSentence=value.slice(0,ends[0]||value.length);
 const commas=[...firstSentence.matchAll(/[,;](?=\s|$)/g)]
  .map(m=>m.index).reverse();
 for(const stop of commas){
   const candidate=firstSentence.slice(0,stop).replace(/[,;\s.]+$/,"").trim()+".";
   if(candidate.length>1&&fits(candidate))return candidate;
 }
 return fits("Descrizione completa nel QR.")?"Descrizione completa nel QR.":"";
};
