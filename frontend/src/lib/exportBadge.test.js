import {paintExportBadge} from "./exportBadge";
function context(){return {font:"",measureText(s){return {width:s.length*Number(this.font.match(/([\d.]+)px/)[1])*.52};},save:jest.fn(),restore:jest.fn(),setTransform:jest.fn(),fillText:jest.fn()};}
it.each([["Media","TAGLIA",false],["Molto raro","",false],["Leggendario","",false],["2","LIV.",true],["3","LIV.",true],["1d8","DANNO",false],["16","CA",false]])("draws the full badge %s within the safe text area",(value,label,level)=>{
 const ctx=context(),canvas={width:1020,height:1428,getContext:()=>ctx},entry=text=>({text,family:"Georgia",weight:"700",color:"#fff"});
 paintExportBadge(canvas,{x:.846,y:.10,w:.17,h:.1214,level,value:entry(value),label:entry(label)});
 expect(canvas.exportBadge.lines.join(" ")).toBe(value);
 expect(canvas.exportBadge.label).toBe(label);
 const calls=ctx.fillText.mock.calls;
 expect(calls.every(([,x,y,max])=>x===.846*1020&&Math.abs(y-(.10*1428-6))<54&&max<=125)).toBe(true);
 if(label)expect(calls[level?calls.length-1:0][0]).toBe(label);
});
