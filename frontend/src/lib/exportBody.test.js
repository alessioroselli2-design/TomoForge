import {fitBodyText,paintExportBody} from "./exportBody";
function context(){return {font:"",measureText(s){return {width:s.length*Number(this.font.match(/([\d.]+)px/)[1])*.52};},save:jest.fn(),restore:jest.fn(),setTransform:jest.fn(),fillText:jest.fn()};}
it.each(["+1 Forza o Destrezza","Intelligenza, Saggezza","Armature e scudi","Concentrazione, fino a 1 minuto","8d6 fuoco"])("fits full short data: %s",value=>{
 const ctx=context(),fit=fitBodyText(ctx,value,64,25,"Georgia","700",9,5,3);
 expect(fit.lines.join(" ")).toBe(value);
 expect(fit.lines.length*fit.lineHeight).toBeLessThanOrEqual(25);
 expect(fit.lines.every(x=>ctx.measureText(x).width<=64)).toBe(true);
});
it("paints every word of the feat value inside the native print cell",()=>{
 const ctx=context(),canvas={width:1020,height:1428,getContext:()=>ctx};
 paintExportBody(canvas,[{text:"+1 Forza o Destrezza",x:.733,y:.489,w:.201,h:.049,family:"Georgia",weight:"700",color:"#29170e",max:9,min:5,maxLines:3,align:"center"}]);
 expect(ctx.fillText.mock.calls.map(x=>x[0]).join(" ")).toBe("+1 Forza o Destrezza");
 expect(ctx.fillText.mock.calls.every(x=>x[2]>.489*1428&&x[2]<.538*1428)).toBe(true);
});
