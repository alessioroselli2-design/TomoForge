import { execFileSync } from "child_process";

test("class master staging: report source branch git tree for exact raster reuse",()=>{
  const rev=(ref)=>{
    try {return execFileSync("git",["rev-parse",ref],{encoding:"utf8",stdio:["ignore","pipe","pipe"]}).trim();}
    catch {return null;}
  };
  const branch=process.env.GITHUB_HEAD_REF;
  if(branch) {
    try {execFileSync("git",["fetch","--no-tags","--depth=1","origin",branch],{stdio:["ignore","pipe","pipe"]});}
    catch {}
  }
  console.log("TOMOFORGE_TREE_PROBE "+JSON.stringify({
    branch,fetchHead:rev("FETCH_HEAD"),fetchTree:rev("FETCH_HEAD^{tree}"),
    head:rev("HEAD"),headTree:rev("HEAD^{tree}"),parent2:rev("HEAD^2"),
    parent2Tree:rev("HEAD^2^{tree}")
  }));
});
