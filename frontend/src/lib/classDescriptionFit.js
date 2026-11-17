// Shared preview/PNG/PDF rule for complete printed sentences. Source remains
// untouched in the record and on the QR page.
export const fitClassDescription=(source,fits)=>{
 const value=String(source||"").replace(/\s+/g," ").trim();
 if(!value)return "";
 if(fits(value))return value;
 const ends=[...value.matchAll(/[.!?](?=\s|$)/g)].map(m=>m.index+1);
 for(let i=ends.length-1;i>=0;i--){
   const candidate=value.slice(0,ends[i]).trim();
   if(fits(candidate))return candidate;
 }
 // Only when the first full sentence cannot fit: finish at the final
 // fitting comma or semicolon and add a full stop.
 const firstEnd=ends[0]??value.length;
 const first=value.slice(0,firstEnd);
 const clauses=[...first.matchAll(/[,;](?=\s|$)/g)].map(m=>m.index);
 for(let i=clauses.length-1;i>=0;i--){
   const candidate=first.slice(0,clauses[i]).trim().replace(/[,;]+$/,"")+".";
   if(fits(candidate))return candidate;
 }
 return fits("Descrizione completa nel QR.")?"Descrizione completa nel QR.":"";
};
