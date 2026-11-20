"""Dependency-free local web demo for the course planning assistant."""

from __future__ import annotations

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src.workflow import run


HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Catalog-grounded course planner</title>
<style>
:root{--ink:#16202a;--muted:#617083;--line:#d9e0e8;--paper:#fff;--wash:#f3f6f8;--blue:#1457d9;--navy:#102a43;--good:#087f5b}
*{box-sizing:border-box}body{margin:0;background:var(--wash);color:var(--ink);font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}
header{background:var(--navy);color:white;padding:28px max(24px,calc((100vw - 1180px)/2))}header h1{margin:0 0 4px;font-size:28px}header p{margin:0;color:#c9d8e7}
main{max-width:1180px;margin:24px auto;padding:0 20px;display:grid;grid-template-columns:340px 1fr;gap:20px}.card{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:0 4px 18px #102a4310}h2{font-size:18px;margin:0 0 16px}h3{font-size:15px;margin:20px 0 8px;color:var(--navy)}label{display:block;font-weight:650;margin:12px 0 5px}input,select,textarea{width:100%;border:1px solid #b8c4d1;border-radius:8px;padding:10px;background:white;color:var(--ink);font:inherit}textarea{min-height:90px;resize:vertical}.check{display:flex;gap:9px;align-items:center;font-weight:500}.check input{width:auto}.hint,.empty{color:var(--muted);font-size:13px}button{margin-top:16px;width:100%;border:0;border-radius:9px;padding:11px 16px;background:var(--blue);color:white;font-weight:750;cursor:pointer}button:disabled{opacity:.55;cursor:wait}.answer{border-left:4px solid var(--good);padding:12px 14px;background:#ebfbee;border-radius:6px;margin-bottom:18px}.decision{font-weight:800;color:var(--good);text-transform:capitalize}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.section{border-top:1px solid var(--line)}ul{padding-left:20px;margin:8px 0}a{color:var(--blue);overflow-wrap:anywhere}.pill{display:inline-block;background:#e8eef9;color:#254c91;border-radius:999px;padding:2px 8px;font-size:12px;margin-left:5px}table{width:100%;border-collapse:collapse;margin:8px 0 18px}th,td{text-align:left;border-bottom:1px solid var(--line);padding:8px}.error{color:#b42318;background:#fff1f0;padding:10px;border-radius:8px}.hidden{display:none}@media(max-width:820px){main{grid-template-columns:1fr}.grid{grid-template-columns:1fr}}
</style></head><body>
<header><h1>Catalog-grounded course planning assistant</h1><p>Oregon State University · CS Computer Systems · 2026–27 catalog pilot</p></header>
<main><section class="card"><h2>Student profile</h2>
<label>Catalog year</label><select id="year"><option>2026-2027</option></select>
<label>Program</label><select id="program"><option>CS Computer Systems</option></select>
<label>Target term</label><select id="term"><option>Fall</option><option>Winter</option><option>Spring</option></select>
<label>Maximum credits</label><input id="credits" type="number" min="1" max="19" value="12">
<label>Completed courses and grades</label><textarea id="completed">CS162:C, CS225:B, CS261:B</textarea><div class="hint">Use COURSE:GRADE, separated by commas.</div>
<label class="check"><input id="complete" type="checkbox" checked> Completed-course list is complete</label>
<label class="check"><input id="gpt" type="checkbox"> Use GPT wording <span class="pill">gpt-5-mini</span></label>
</section><section class="card"><h2>Ask the catalog</h2>
<label>Eligibility, program requirement, or term-plan question</label><input id="question" value="Can I take CS374?">
<button id="submit">Check catalog</button><p id="error" class="error hidden"></p>
<div id="result" class="hidden"><h3>Answer / Plan</h3><div class="answer"><span id="decision" class="decision"></span><div id="answer"></div></div><div id="plan"></div>
<div class="grid"><div><div class="section"><h3>Why</h3><div id="why"></div></div><div class="section"><h3>Clarifying questions</h3><div id="questions"></div></div><div class="section"><h3>Next steps</h3><div id="next"></div></div></div>
<div><div class="section"><h3>Citations</h3><div id="citations"></div></div><div class="section"><h3>Assumptions / Not in catalog</h3><div id="assumptions"></div></div><div class="section"><h3>Workflow</h3><div id="trace" class="hint"></div></div></div></div></div>
</section></main><script>
const el=id=>document.getElementById(id);function list(id,items,empty='None'){const host=el(id);host.replaceChildren();if(!items?.length){const p=document.createElement('p');p.className='empty';p.textContent=empty;host.append(p);return}const ul=document.createElement('ul');items.forEach(x=>{const li=document.createElement('li');li.textContent=x;ul.append(li)});host.append(ul)}
function citations(items){const host=el('citations');host.replaceChildren();if(!items?.length){host.textContent='No catalog claim was made.';host.className='empty';return}const ul=document.createElement('ul');items.forEach(c=>{const li=document.createElement('li'),a=document.createElement('a'),code=document.createElement('code');a.href=c.url;a.target='_blank';a.rel='noopener';a.textContent=c.section;code.textContent=' '+c.passage_id;li.append(a,document.createTextNode(' · '),code);ul.append(li)});host.append(ul)}
function plan(items){const host=el('plan');host.replaceChildren();if(!items?.length)return;const table=document.createElement('table'),head=document.createElement('tr');['Course','Credits','Why'].forEach(v=>{const th=document.createElement('th');th.textContent=v;head.append(th)});table.append(head);items.forEach(x=>{const tr=document.createElement('tr');[x.course,x.credits,x.why].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td)});table.append(tr)});host.append(table)}
el('submit').onclick=async()=>{el('submit').disabled=true;el('submit').textContent='Checking…';el('error').classList.add('hidden');try{const body={question:el('question').value,profile:{catalog_year:el('year').value,target_program:el('program').value,target_term:el('term').value,max_credits:Number(el('credits').value),transcript_complete:el('complete').checked,completed_courses_text:el('completed').value},use_gpt:el('gpt').checked};const response=await fetch('/api/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw new Error(data.error||'Request failed');el('decision').textContent=data.decision.replaceAll('_',' ')+' · ';el('answer').textContent=data.answer;plan(data.plan);list('why',data.why);list('questions',data.clarifying_questions);list('next',data.next_steps);citations(data.citations);list('assumptions',data.assumptions_not_in_catalog);el('trace').textContent=(data.workflow_trace||[]).join(' → ');el('result').classList.remove('hidden')}catch(e){el('error').textContent=e.message;el('error').classList.remove('hidden')}finally{el('submit').disabled=false;el('submit').textContent='Check catalog'}};
</script></body></html>"""


def parse_completed(value: str) -> dict[str, str]:
    completed: dict[str, str] = {}
    invalid = []
    for raw in filter(None, (item.strip() for item in value.split(","))):
        match = re.fullmatch(r"([A-Za-z]{2,5})\s*(\d{3}[A-Za-z]?)\s*:\s*([A-F][+-]?)", raw)
        if not match:
            invalid.append(raw)
        else:
            completed[f"{match.group(1).upper()}{match.group(2).upper()}"] = match.group(3).upper()
    if invalid:
        raise ValueError("Could not parse: " + ", ".join(invalid) + ". Use COURSE:GRADE format.")
    return completed


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(404)
            return
        body = HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/api/query":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            profile = dict(payload["profile"])
            profile["completed_courses"] = parse_completed(profile.pop("completed_courses_text", ""))
            profile.setdefault("in_progress_courses", [])
            profile.setdefault("placement_scores", {})
            result = run(str(payload["question"]), profile, model="gpt-5-mini",
                         use_gpt=bool(payload.get("use_gpt", False)))
            self._json(200, result)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:  # Keep local demo errors readable without exposing secrets.
            self._json(500, {"error": f"Assistant failed: {type(exc).__name__}"})

    def _json(self, status: int, value: dict) -> None:
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    print(f"Course planner running at http://{args.host}:{args.port}")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
