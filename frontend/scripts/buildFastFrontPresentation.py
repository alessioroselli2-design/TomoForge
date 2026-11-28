"""Generate pixel-verified, lossless screen-size masters using the approved JS."""
import base64
import io
import json
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/"public"
LIB=ROOT/"src/lib"
DEST=PUBLIC/"card-art/screen-bronze-v1"
DEST.mkdir(parents=True,exist_ok=True)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(PUBLIC),**kwargs)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=="/__render":
            data=b"<!doctype html><title>Approved frame renderer</title>"
            self.send_response(200);self.send_header("Content-Type","text/html");self.end_headers();self.wfile.write(data)
            return
        if path.startswith("/lib/"):
            name=path.removeprefix("/lib/")
            if "/" in name or ".." in name:
                self.send_error(404);return
            p=LIB/name
            if not p.suffix:p=p.with_suffix(".js")
            if not p.is_file():self.send_error(404);return
            data=p.read_bytes()
            if p.suffix==".json":data=b"export default "+data
            self.send_response(200);self.send_header("Content-Type","text/javascript");self.end_headers();self.wfile.write(data)
            return
        super().do_GET()
    def log_message(self,*args):pass

server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
manifest={}
try:
    with sync_playwright() as p:
        chrome=shutil.which("google-chrome") or shutil.which("chromium")
        browser=p.chromium.launch(executable_path=chrome,headless=True,args=["--no-sandbox"])
        page=browser.new_page()
        page.goto(f"http://127.0.0.1:{server.server_port}/__render")
        types=page.evaluate("async()=> (await import('/lib/frameColorProof.js')).METAL_PROOF_TYPES")
        for kind in types:
            key=page.evaluate("async t=>(await import('/lib/frameColorProof.js')).metalProofUrl(t)",kind)
            if key in manifest:continue
            result=page.evaluate("""async type=>{
                const m=await import('/lib/frameColorProof.js');
                const layers=await m.getMetalProofLayers(type);
                const screen=document.createElement('canvas');
                screen.width=1020;screen.height=1428;
                const ctx=screen.getContext('2d');
                ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';
                ctx.drawImage(layers.background,0,0,1020,1428);
                return [screen.toDataURL('image/png'),layers.trim.toDataURL('image/png')];
            }""",kind)
            files={}
            for label,url in zip(("background","src"),result):
                im=Image.open(io.BytesIO(base64.b64decode(url.split(",",1)[1]))).convert("RGBA")
                assert im.size==(1020,1428)
                name=f"{kind}-{'master' if label=='background' else 'trim'}.webp"
                target=DEST/name
                im.save(target,format="WEBP",lossless=True,method=4,exact=True)
                decoded=Image.open(target).convert("RGBA")
                assert decoded.tobytes()==im.tobytes(),name
                files[label]="/card-art/screen-bronze-v1/"+name
            manifest[key]=files
            print(kind, sum((PUBLIC/v.lstrip("/")).stat().st_size for v in files.values()),flush=True)
        browser.close()
    assert len(manifest)==9
    (LIB/"fastFrontPresentation.json").write_text(json.dumps(manifest,indent=2)+"\n")
finally:
    server.shutdown()
