import { readFileSync } from "fs";
import { resolve } from "path";

const preview = readFileSync(resolve(__dirname, "ClassMasterPreview.jsx"), "utf8");
const routes = readFileSync(resolve(__dirname, "../App.js"), "utf8");

describe("isolated class preview", () => {
  it("offers the thirteen classes through the actual CardFront renderer", () => {
    const names = [
      "Barbaro","Bardo","Chierico","Druido","Guerriero","Monaco",
      "Paladino","Ranger","Ladro","Stregone","Warlock","Mago","Artefice"
    ];
    names.forEach(name => expect(preview).toContain('name:"' + name + '"'));
    expect(preview).toContain("<CardFront key={selected} card={card}");
    expect(preview).toContain('type:"class"');
    expect(preview).toContain('dado_vita:sample.die');
  });
  it("has a read-only preview route and local-only image tests", () => {
    expect(routes).toContain('path="/prova-classi"');
    expect(preview).toContain("URL.createObjectURL");
    expect(preview).toContain("URL.revokeObjectURL");
    expect(preview).not.toContain("api.post");
    expect(preview).not.toContain("api.put");
    expect(preview).not.toContain("api.patch");
  });
});



describe("one user master with no superimposed class ring",()=>{
 it("shares the same class inner motif slot across all 13 Class selections",()=>{
   const css=readFileSync(resolve(__dirname,"../frontMasterV17.css"),"utf8");
   const layouts=readFileSync(resolve(__dirname,"../lib/frontCategoryLayouts.js"),"utf8");
   expect(layouts).toContain("/card-art/class-master-user-reference-v1.webp");
   expect(css).toContain('data-emblem-sprite="class-inner-v1"');
   expect(css).toContain("left:6.25%!important;top:3.97135%!important;");
   expect(preview).not.toContain("tf-bardo-proof");
 });
});
