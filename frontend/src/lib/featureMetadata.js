// Presentation-only derivation for ALL class-feature cards. Never modify the
// original reference, translation, attributes or text saved in the database.
// Explicit structured attributes always win over recognisable prose patterns.
const asText=value=>{
 if(value===0)return "0";
 if(value===null||value===undefined||typeof value==="boolean")return "";
 if(typeof value==="string"||typeof value==="number")return String(value).trim();
 return "";
};
const first=(a,keys)=>keys.map(k=>asText(a?.[k])).find(Boolean)||"";
const NORMALIZED_NUMBER={un:1,uno:1,una:1,due:2,tre:3,quattro:4,cinque:5,sei:6,sette:7,otto:8,nove:9,dieci:10};
const countValue=value=>String(NORMALIZED_NUMBER[value.toLowerCase()]??value);
const NUM="(?:\\d+|un|uno|una|due|tre|quattro|cinque|sei|sette|otto|nove|dieci)";
const sentences=s=>String(s||"").replace(/\s+/g," ").trim().split(/(?<=[.!?])\s+/).filter(Boolean);
const introRemoved=s=>String(s||"")
 .replace(/^[^.:;]{1,80},\s*\d+\s*[°º]?\s*livello\s*:\s*/i,"")
 .replace(/^privilegio\s+(?:di|del|della)\s+[^.!?]{0,75}\blivello\s*[.!?]\s*/i,"");
const isOnlyCountAndRecovery=s=>new RegExp(
 "^\\s*"+NUM+"\\s+(?:usi|utilizzi)\\s+(?:per|tra)\\s+(?:un\\s+)?riposo\\s+(?:breve\\s+o\\s+lungo|lungo\\s+o\\s+breve|breve|lungo)\\.?\\s*$","i").test(s);
const isOnlyUseAndRecovery=s=>
 /^(?:puoi|può|puo)\s+(?:usare|utilizzare)\s+(?:questo privilegio|questa capacità)\s+(?:un|uno|una|due|tre|\d+)\s+volte?\s+e\s+recuper(?:a|i)\s+(?:tutti\s+)?(?:gli\s+)?utilizzi(?:\s+spesi)?\s+(?:(?:quando|dopo|al termine di|alla fine di)[^.!?]*)?\.?$/i.test(s);
const rawEvidence=(description,a)=>{
 const benefits=Array.isArray(a?.benefici)?a.benefici.map(asText).filter(Boolean):[];
 return [asText(description),...benefits].filter(Boolean);
};
// Only an action clearly describing the feature's use. Don't read a later
// bonus action used to END Wild Shape as its activation.
const parseActivation=source=>{
 const parts=sentences(source).filter(s=>!isOnlyCountAndRecovery(s));
 for(const part of parts.slice(0,3)){
  const s=introRemoved(part);
  if(/^(?:privilegio\s+(?:di|del)\s+\d+\s*[°º]?\s+livello)\.?$/i.test(s))continue;
  const bonus=/\bcome\s+(?:un['’]?\s*)?azione bonus\b|\bcon\s+(?:un['’]?\s*)?azione bonus\b|\b(?:può|puo|puoi)\s+usare\s+(?:(?:la\s+)?(?:sua|propria)\s+|un['’]?\s*|una\s+)?azione bonus\s+per\b/i;
  const reaction=/\bcome\s+reazione\b|\b(?:usa|usare|utilizzare|pu[oò]\s+usare)\s+(?:la\s+)?reazione\s+(?:per|quando)\b/i;
  const regular=/\bcome\s+(?:un['’]?\s*)?azione\b|\bcon\s+(?:un['’]?\s*)?azione\b|\b(?:usa|usare|utilizzare|pu[oò]\s+usare|puoi\s+usare)\s+(?:(?:la\s+)?(?:sua|propria)\s+|un['’]?\s*|una\s+)?azione\s+per\b/i;
  // The primary feature may be phrased with the action AFTER its name.
  if(bonus.test(s))return "Azione bonus";
  if(reaction.test(s))return "Reazione";
  if(regular.test(s))return "Azione";
  if(/\bpassiv[ao]\b|\bsempre\s+attiv[ao]\b/i.test(s))return "Passivo";
  // Only inspect the first meaningful effect sentence, not later abilities
  // or ways to end the transformation.
  if(!/^\s*(?:privilegio di|livello|dal\s+\d+)/i.test(s))break;
 }
 return "";
};
const parseUses=source=>{
 // Do not confuse the COST of another feature ("spendendo due utilizzi")
 // with the number of uses actually available for the selected privilege.
 const mod=source.match(/\b(?:usi|utilizzi)\s+pari\s+al\s+(?:tuo\s+)?modificatore\s+di\s+(Forza|Destrezza|Costituzione|Intelligenza|Saggezza|Carisma)(\s*\(minimo\s+\d+\))?/i);
 if(mod)return "Mod. "+mod[1]+(mod[2]?mod[2].replace("minimo","min."):"");
 if(/\b(?:un\s+numero\s+di\s+)(?:usi|utilizzi|volte)\s+pari\s+al\s+(?:tuo\s+)?bonus\s+di\s+competenza\b|\b(?:usi|utilizzi)\s+pari\s+al\s+(?:tuo\s+)?bonus\s+di\s+competenza\b/i.test(source))
  return "Bonus competenza";
 const per=source.match(new RegExp("\\b("+NUM+")\\s+(?:usi|utilizzi)\\s+(?:per|tra)\\s+(?:un\\s+)?riposo\\b","i"));
 if(per)return countValue(per[1]);
 // E.g. "Può utilizzare questo privilegio due volte", without treating
 // later level increases as the base amount.
 const clauses=sentences(source);
 for(const clause of clauses){
  if(/(?:a\s+partire\s+dal|dal)\s+\d+\s*[°º]?\s+livello/i.test(clause))continue;
  const m=clause.match(new RegExp("\\b(?:pu[oò]|puoi)\\s+(?:utilizzare|usare)\\s+(?:questo\\s+privilegio|questa\\s+capacit[aà]|questo\\s+tratto)\\s+("+NUM+")\\s+volte?\\b","i"));
  if(m)return countValue(m[1]);
 }
 const v=source.match(/\b(?:usi|utilizzi)\s+pari\s+al\s+(?:tuo\s+)?bonus\s+di\s+competenza\b/i);
 if(v)return "Bonus competenza";
 const one=source.match(/\b(?:una|un)\s+volta\s+per\s+(?:un\s+)?riposo\s+(?:breve|lungo)\b/i);
 if(one)return "1";
 return "";
};
const restLabel=clause=>{
 if(/\briposo\s+breve\s+(?:o|oppure)\s+lungo\b|\briposo\s+lungo\s+(?:o|oppure)\s+breve\b/i.test(clause))return "Riposo breve o lungo";
 if(/\briposo\s+breve\b/i.test(clause))return "Riposo breve";
 if(/\briposo\s+lungo\b/i.test(clause))return "Riposo lungo";
 return "";
};
const parseRecovery=source=>{
 for(const clause of String(source).replace(/\s+/g," ").split(/[.!?;](?=\s|$)/)){
  const rest=restLabel(clause);if(!rest)continue;
  const hasUses=/\b(?:usi|utilizzi|cariche|volte|privilegio|capacità)\b/i.test(clause);
  const recovers=/\b(?:recuper(?:a|i|ano|ati|are|o|erai|erà)|ripristin(?:a|i|ati|are)|riotten(?:gono|ere|i)|ricaric(?:a|hi|ano|are))\b/i.test(clause);
  const perRest=/\b(?:usi|utilizzi|volte)\s+(?:(?:pari\s+[^;,.]{1,80})?\s*)?per\s+(?:un\s+)?riposo\b/i.test(clause);
  const untilRest=/\b(?:non\s+pu[oò]|non\s+puoi|nuovamente|di\s+nuovo)\b[^;,.]{0,120}\b(?:finch[eé]|prima\s+di)\b/i.test(clause);
  if((hasUses&&recovers)||perRest||(hasUses&&untilRest))return rest;
  // Self-contained abbreviated entries: "Due usi per riposo breve o lungo."
  if(isOnlyCountAndRecovery(clause))return rest;
 }
 return "";
};
const capitalization=s=>s ? s[0].toLocaleUpperCase("it-IT")+s.slice(1):s;
export const featureEffectOnly=(description,{activation="",uses="",recovery=""}={})=>{
 let source=asText(description).replace(/\s+/g," ").trim();
 if(!source)return "";
 source=introRemoved(source);
 // Only delete self-contained metadata sentences, NEVER a whole sentence
 // which also describes an effect, benefit, condition or consequence.
 const pieces=sentences(source).filter(s=>
  !(uses&&recovery&&isOnlyCountAndRecovery(s)) &&
  !(uses&&recovery&&isOnlyUseAndRecovery(s))
 );
 source=pieces.join(" ");
 if(activation){
  source=source.replace(/^(?:come|con)\s+(?:un['’]?\s*)?azione(?:\s+bonus)?\s*,?\s*/i,"");
  source=source.replace(/^(?:come|con)\s+reazione\s*,?\s*/i,"");
  if(activation==="Azione"){
   source=source.replace(/\b(si\s+trasforma)\s+con\s+un['’]azione\s+(in)\b/i,"$1 $2");
   source=source.replace(/\b(pu[oò]|puoi)\s+usare\s+(?:la\s+sua\s+|una\s+|un['’]?)azione\s+per\s+/i,"$1 ");
  }
 }
 return capitalization(source.replace(/\s{2,}/g," ").trim());
};
export const extractFeatureMetadata=(a={},description="")=>{
 const evidence=rawEvidence(description,a);
 const activation=first(a,["tipo_attivazione","attivazione","tempo_attivazione","action_type",
    "tipo_azione","activation","activation_type","azione"])
    ||evidence.map(parseActivation).find(Boolean)||"";
 const uses=first(a,["utilizzi_disponibili","numero_utilizzi","numero_di_utilizzi",
    "utilizzi_per_riposo","utilizzi","usi","uses","cariche","charges"])
    ||evidence.map(parseUses).find(Boolean)||"";
 const recovery=first(a,["recupero_utilizzi","recupero_degli_utilizzi","recupero",
    "ricarica","ripristino_utilizzi","ripristino","recharge","recovery"])
    ||evidence.map(parseRecovery).find(Boolean)||"";
 const normalizedActivation=/^passiv[ao]$/i.test(activation)?"Passivo":activation;
 return {activation:normalizedActivation,uses,recovery,
  cleanDescription:featureEffectOnly(description,{activation:normalizedActivation,uses,recovery})};
};
