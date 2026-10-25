#!/usr/bin/env python3
"""Vrisama Fashion PDF Studio. Runs locally on 127.0.0.1 only."""
import argparse
import json
import re
import uuid
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "exports"
OUT.mkdir(exist_ok=True)
WEB = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fashion PDF Studio | Vrisama</title><style>
*{box-sizing:border-box}body{margin:0;font-family:system-ui,'Segoe UI',sans-serif;color:#1e3343;background:radial-gradient(circle at 90% 0%,#d4f6f1,transparent 40%),#f6fbfc}
main{max-width:870px;margin:35px auto;padding:20px}header{padding:24px 7%;font-size:18px;font-weight:750}
small,p{color:#667e88}h1{font-size:clamp(37px,6vw,60px);letter-spacing:-2px;line-height:1.1;margin:12px 0}h1 span{color:#078d9a}
p{line-height:1.7}.card{padding:35px;background:white;border-radius:25px;border:1px solid #deebef;margin:30px 0;box-shadow:0 20px 75px #14557712}
label{display:block;font-size:13px;font-weight:700;margin:20px 0 9px}input,select{width:100%;padding:15px 14px;border:1px solid #d1e0e5;border-radius:10px;font:inherit;color:#143342}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}button,.download{display:inline-block;margin:17px 0 0;padding:15px 19px;background:linear-gradient(115deg,#079e9e,#125d91);border:none;border-radius:12px;color:white;font:inherit;text-decoration:none;cursor:pointer}
button:disabled{opacity:.6;cursor:wait}#status{font-weight:700;padding-top:12px}.intro{max-width:690px;font-size:17px}
@media(max-width:620px){.grid{grid-template-columns:1fr}.card{padding:20px}}
</style>
<header>✦ VRISAMA <span style="color:#079e9e">AI CAREERS</span></header>
<main><small>FREE • LOCAL • NO API KEY</small><h1>Make the whole web<br><span>your reference library.</span></h1>
<p class="intro">Save tutorials, trend reports, supplier references, and multi-section guides as PDF files. This tool runs privately on your computer.</p>
<div class="card"><h2>Convert a website to PDF</h2><form id="form">
<label>Website URL</label><input type="url" id="url" required placeholder="https://example.com/guide">
<div class="grid"><div><label>Capture method</label><select id="mode">
<option value="smart">Smart — expand all steps</option><option value="full">Full page</option><option value="sections">All sections (hash links)</option><option value="linked">Linked pages (same website)</option></select></div>
<div><label>Maximum sections / pages</label><input type="number" id="max" min="1" max="20" value="12"></div></div>
<div class="grid"><div><label>Extra rendering time</label><select id="wait"><option value="1">1 second</option><option value="2.5" selected>2.5 seconds</option><option value="5">5 seconds</option></select></div>
<div><label>Offline archive</label><select id="archive"><option value="1">PDF + ZIP snapshots</option><option value="0">PDF only</option></select></div></div>
<p><small>For websites that print only one visible step, choose Smart first; then try All sections. Login-only or blocked content cannot be bypassed.</small></p>
<button id="go">✦ Create my PDF</button><div id="status" role="status" aria-live="polite"></div><div id="links"></div></form></div>
<p><small>For educational reference and content you have permission to save. Complex sites may need manual adjustments. Close the terminal to stop this local app.</small></p></main>
<script>
document.getElementById('form').onsubmit=async(e)=>{
e.preventDefault();const go=document.getElementById('go'),status=document.getElementById('status'),links=document.getElementById('links');
go.disabled=true;status.textContent='Capturing website…';links.textContent='';
try{const r=await fetch('/convert',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({url:document.getElementById('url').value,mode:document.getElementById('mode').value,max:Number(document.getElementById('max').value),wait:Number(document.getElementById('wait').value),archive:document.getElementById('archive').value==='1'})});
const j=await r.json();if(!r.ok)throw Error(j.error||'Failed');status.textContent='Saved '+j.pages+' capture(s).';
j.files.forEach(f=>{const a=document.createElement('a');a.className='download';a.href=f.url;a.textContent='↓ '+f.label;a.style.marginRight='10px';links.appendChild(a)})}
catch(err){status.textContent='Conversion failed: '+err.message}finally{go.disabled=false}};
</script></html>"""

def check_url(url):
    if not isinstance(url,str) or len(url)>2048:
        raise ValueError("Invalid URL length")
    parsed=urlsplit(url.strip())
    if parsed.scheme not in ("http","https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Enter a public HTTP or HTTPS URL")
    if parsed.hostname.lower() in ("localhost","127.0.0.1","::1"):
        raise ValueError("Cannot capture localhost")
    return url.strip()

def browser_launch(p):
    for opts in ({"channel":"chrome"},{"channel":"msedge"},{}):
        try:return p.chromium.launch(headless=True,**opts)
        except Exception:pass
    raise RuntimeError("Browser missing. Install Chrome/Edge or run python -m playwright install chromium")

def scroll(page):
    try:
        page.evaluate("""async()=>{const step=Math.max(innerHeight,650),end=Math.min(document.body.scrollHeight,150000);
        for(let y=0;y<end;y+=step){scrollTo(0,y);await new Promise(r=>setTimeout(r,55))}scrollTo(0,0)}""")
    except Exception:pass

def expand(page):
    try:
        page.evaluate("""()=>{const words=['show all steps on one page','show all steps','expand all','show all sections'];
        for(const e of document.querySelectorAll('button,a,label,[role=button]')){
        const t=(e.innerText||'').toLowerCase();if(words.some(w=>t.includes(w))){e.click();break}}}""")
    except Exception:pass

def links(page,url,mode,n):
    if mode not in ("sections","linked"):return [url]
    base=urlsplit(url);found=[url]
    hrefs=page.eval_on_selector_all('a[href]','nodes=>nodes.map(n=>n.href)')
    for item in hrefs:
        u=urlsplit(item)
        if u.scheme not in ("https","http") or u.netloc!=base.netloc:continue
        if mode=="sections":
            if u.path!=base.path or not re.fullmatch(r'(s\d+|step[-_]?\d+|section[-_]?\d+|slide[-_]?\d+)',u.fragment,re.I):continue
        elif u.path==base.path or re.search(r'\.(pdf|zip|png|jpg|svg|mp4)$',u.path,re.I):continue
        address=item if mode=="sections" else item.split('#')[0]
        if address not in found:found.append(address)
        if len(found)>=n:break
    if mode=="sections" and len(found)==1:raise ValueError("No hash steps found. Try Smart mode.")
    return found[:n]

def convert(req):
    url=check_url(req.get('url',''));mode=req.get('mode','smart')
    if mode not in ('smart','full','sections','linked'):raise ValueError("Unknown mode")
    n=max(1,min(20,int(req.get('max',12))));wait=max(0,min(8,float(req.get('wait',2.5))))
    archive=bool(req.get('archive',True));job=uuid.uuid4().hex[:12];folder=OUT/job;folder.mkdir()
    host=re.sub('[^a-zA-Z0-9_-]','_',urlsplit(url).hostname or 'guide')[:50]
    pdf=folder/(host+'_complete.pdf');pieces=[];snapshots=[]
    with sync_playwright() as p:
        browser=browser_launch(p);context=browser.new_context(viewport={"width":1366,"height":900})
        page=context.new_page()
        try:
            page.goto(url,wait_until="domcontentloaded",timeout=45000);page.wait_for_timeout(int(wait*1000))
            if mode=="smart":expand(page);page.wait_for_timeout(600)
            urls=links(page,url,mode,n)
            for i,target in enumerate(urls):
                if i>0 or mode=="sections":
                    page.goto(target,wait_until="domcontentloaded",timeout=45000)
                    page.wait_for_timeout(int(wait*1000))
                if mode=="smart":expand(page)
                scroll(page);page.emulate_media(media="screen")
                part=folder/('section_%02d.pdf'%(i+1))
                page.pdf(path=str(part),format="A4",print_background=True,margin={"top":"8mm","bottom":"8mm","left":"8mm","right":"8mm"})
                pieces.append(part)
                if archive:
                    try:
                        cdp=context.new_cdp_session(page);snapshot=cdp.send('Page.captureSnapshot',{"format":"mhtml"})['data'];cdp.detach()
                        offline=folder/('section_%02d.mhtml'%(i+1));offline.write_text(snapshot,encoding='utf-8')
                        snapshots.append(offline)
                    except Exception:pass
        finally:browser.close()
    writer=PdfWriter()
    for part in pieces:
        for page in PdfReader(str(part)).pages:writer.add_page(page)
    with pdf.open('wb') as f:writer.write(f)
    files=[{"label":"Complete PDF","url":"/download/"+job+"/"+pdf.name}]
    if archive:
        zpath=folder/(host+'_offline.zip')
        with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
            z.write(pdf,pdf.name)
            for snapshot in snapshots:z.write(snapshot,snapshot.name)
        files.append({"label":"Offline ZIP","url":"/download/"+job+"/"+zpath.name})
    return {"pages":len(pieces),"files":files}

class Server(BaseHTTPRequestHandler):
    def json(self,code,body):
        data=json.dumps(body).encode();self.send_response(code);self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if self.path=='/':
            data=WEB.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
        match=re.fullmatch(r'/download/([a-f0-9]{12})/([a-zA-Z0-9_.-]+)',unquote(self.path))
        if match:
            path=OUT/match.group(1)/match.group(2)
            if path.is_file() and path.suffix in ('.pdf','.zip'):
                data=path.read_bytes();self.send_response(200)
                self.send_header('Content-Type','application/pdf' if path.suffix=='.pdf' else 'application/zip')
                self.send_header('Content-Disposition','attachment; filename="'+path.name+'"')
                self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
        self.send_error(404)
    def do_POST(self):
        if self.path!='/convert':return self.json(404,{"error":"Not found"})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<1 or length>20000:raise ValueError("Invalid request length")
            request=json.loads(self.rfile.read(length))
            if not isinstance(request,dict):raise ValueError("Invalid request")
            self.json(200,convert(request))
        except Exception as exc:self.json(400,{"error":str(exc)[:450]})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args();address='http://127.0.0.1:'+str(args.port)
    print("Fashion PDF Studio:",address,flush=True);webbrowser.open(address)
    try:ThreadingHTTPServer(('127.0.0.1',args.port),Server).serve_forever()
    except KeyboardInterrupt:pass
