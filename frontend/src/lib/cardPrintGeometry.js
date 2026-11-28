// The physical card is the complete 5:7 canvas, with no synthetic border.
// The original master stays intact. Reposition only the engraved bottom
// rail: extend a blank parchment/vertical rail band, then move the complete
// bottom ornament down. Dynamic artwork, text and emblems are NOT scaled.
export function frontMasterSlices(type) {
  // Legacy Monster v17 is also the approved fallback for character/custom.
  const cut=type==="class"?.970:.934;
  const start=.785, end=.815, extra=1-cut;
  return [
    {sourceY:start,sourceH:end-start,y:start,h:end-start+extra},
    {sourceY:end,sourceH:cut-end,y:end+extra,h:cut-end},
  ];
}
export function frontMasterSliceStyle(src,s) {
 return {position:"absolute",left:0,right:0,top:s.y*100+"%",height:s.h*100+"%",
   backgroundImage:`url("${src}")`,backgroundRepeat:"no-repeat",
   backgroundSize:`100% ${100/s.sourceH}%`,
   backgroundPosition:`center ${100*s.sourceY/(1-s.sourceH)}%`,
   pointerEvents:"none",zIndex:0};
}
// Trim the photographed excess around the straight rectangular gold rail.
// Nine backs share the same 750x1050 geometry; Class has a distinct surround.
// Both crop windows are exactly 5:7. A projecting ornament is NOT a cut edge.
// No reflection, invented cap, letterboxing or nonuniform image scaling.
export function getBackCrop(file,width=750,height=1050) {
 const k=width/750;
 if(Math.abs(width/height-5/7)<.001) {
   const r=file==="classe"?{x:8,y:27,w:708,h:991.2}:{x:6,y:7,w:738,h:1033.2};
   return {x:r.x*k,y:r.y*k,w:r.w*k,h:r.h*k};
 }
 const w=Math.min(width,height*5/7),h=w*7/5;
 return {x:(width-w)/2,y:(height-h)/2,w,h};
}
export function backImageStyle(file) {
 const r=getBackCrop(file);
 return {position:"absolute",left:-100*r.x/r.w+"%",top:-100*r.y/r.h+"%",
   width:100*750/r.w+"%",height:100*1050/r.h+"%",maxWidth:"none",objectFit:"fill"};
}
// 1.05 mm crop ticks aligned with the true trim, in the waste between
// cards. With a 3 mm gap, 0.35+1.05 < 1.5 mm, so they cannot touch a neighbour.
export function getCutGuideLines({x,y,w,h}) {
 const o=.35,L=1.05,lines=[];
 for(const [cx,dx] of [[x,-1],[x+w,1]])for(const [cy,dy] of [[y,-1],[y+h,1]]){
   lines.push([cx+dx*o,cy,cx+dx*(o+L),cy],[cx,cy+dy*o,cx,cy+dy*(o+L)]);
 }
 return lines;
}
export function drawCutGuides(pdf,bounds) {
 pdf.setDrawColor(115,115,115);pdf.setLineWidth(.12);
 pdf.setLineDashPattern([.45,.25],0);
 getCutGuideLines(bounds).forEach(line=>pdf.line(...line));
 pdf.setLineDashPattern([],0);
}
