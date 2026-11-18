import { getClassPrimaryAbilityIcons } from "./classPrimaryAbilityIcons";
describe("class primary ability files",()=>{
 test.each([
 ["Forza",["forza"]],["DESTREZZA",["destrezza"]],
 ["Costituzione",["costituzione"]],["Intelligenza",["intelligenza"]],
 ["Saggezza",["saggezza"]],["Carisma",["carisma"]],
 ["Forza o Destrezza",["forza","destrezza"]],
 ["Saggezza e Carisma",["saggezza","carisma"]],
 ["saggézza / CÀRISMA",["saggezza","carisma"]],
 ["Forza e forza",["forza"]],["non specificata",[]],
 ])("%s",(input,expected)=>expect(getClassPrimaryAbilityIcons(input).map(x=>x.name)).toEqual(expected));
});
