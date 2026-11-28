import {displayClasses,displaySources,displayText,searchRecords} from "./librarySearchView";
test("accepts legacy string classes and normal arrays without losing labels",()=>{
 expect(displayClasses("Mago, Stregone")).toBe("Mago, Stregone");
 expect(displayClasses(["Mago","Stregone"])).toBe("Mago, Stregone");
 expect(displayClasses([{nome:"Druido"},null])).toBe("Druido");
 expect(displayText({unexpected:true})).toBe("");
});
test("guards missing or malformed source and search arrays",()=>{
 expect(displaySources(null)).toBe("");
 expect(displaySources("bad")).toBe("");
 expect(displaySources([null,{filename:"Manuale",page:42}])).toBe("Manuale p.42");
 expect(searchRecords({})).toEqual([]);
 expect(searchRecords([null,{id:"valid"}])).toEqual([{id:"valid"}]);
});
