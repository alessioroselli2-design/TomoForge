import {fitExportHeading,paintExportHeading} from "./exportHeading";
function context(){return {font:"",measureText(s){return {width:s.length*Number(this.font.match(/([\d.]+)px/)[1])*.52};},save:jest.fn(),restore:jest.fn(),setTransform:jest.fn(),fillText:jest.fn()};}
it.each(["Bastone dei Boschi","Spada del Sole della Fiamma Eterna","Maestro d’Armi","Spada Lunga","Cotta di Maglia","Palla di Fuoco","Forma Selvatica","Elfo delle Foreste"])("preserves the entire name %s within the header",name=>{
 const ctx=context(),fit=fitExportHeading(ctx,name,138,31,"Georgia","700",20,2);
 expect(fit.lines.join(" ")).toBe(name);
 expect(fit.lines.length).toBeLessThanOrEqual(2);
 expect(fit.lines.length*fit.lineHeight).toBeLessThanOrEqual(31);
 expect(fit.lines.every(s=>ctx.measureText(s).width<=138)).toBe(true);
});
it("draws all title words and the subtitle into the real raster",()=>{
 const ctx=context(),canvas={width:1020,height:1428,getContext:()=>ctx};
 paintExportHeading(canvas,{x:.291,y:.039,w:.435,h:.098,title:{text:"Bastone dei Boschi",family:"Georgia",weight:"700",color:"#29170e"},subtitle:{text:"Oggetto Magico",family:"Georgia",weight:"500",color:"#29170e"}});
 expect(ctx.fillText.mock.calls.slice(0,-1).map(x=>x[0]).join(" ")).toBe("Bastone dei Boschi");
 expect(ctx.fillText.mock.calls.at(-1)[0]).toBe("Oggetto Magico");
 expect(canvas.exportHeading.title).toBe("Bastone dei Boschi");
});