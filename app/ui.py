"""Single-page UI for GREP AI: service map, ingestion and root cause analysis."""

INDEX_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GREP AI</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#0b0d12;--pn:#11141b;--pn2:#161a23;--ln:#222733;--ln2:#2e3544;--t:#e7eaf0;--m:#8d95a8;--m2:#6a728a;--ac:#6c8cff;--ok:#4cc38a;--wn:#e8b04a;--er:#f26d6d;--mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--t);font:13.5px/1.5 Inter,system-ui,-apple-system,"Segoe UI",sans-serif;display:flex;flex-direction:column;overflow:hidden;-webkit-font-smoothing:antialiased}
.top{height:52px;flex:none;display:flex;align-items:center;gap:12px;padding:0 16px;border-bottom:1px solid var(--ln);background:var(--pn)}
.brand{display:flex;align-items:center;gap:10px}
.brand b{display:block;font-size:14px;font-weight:600;letter-spacing:.02em;line-height:1.1}
.brand span{display:block;font-size:11.5px;color:var(--m)}
.sp{flex:1}
.status{display:inline-flex;align-items:center;gap:7px;font-size:12px;color:var(--m);padding:4px 10px;border:1px solid var(--ln);border-radius:999px;background:var(--pn2)}
.status i{width:7px;height:7px;border-radius:50%;background:var(--m2)}
.status.ok i{background:var(--ok)}.status.bad i{background:var(--er)}
main{flex:1;min-height:0;display:grid;grid-template-columns:290px minmax(0,1fr) 420px;gap:12px;padding:12px}
.pn{background:var(--pn);border:1px solid var(--ln);border-radius:10px;min-height:0;min-width:0;display:flex;flex-direction:column;overflow:hidden}
.sc{flex:1;min-height:0;overflow:auto;padding:16px}
.sc::-webkit-scrollbar{width:8px}.sc::-webkit-scrollbar-thumb{background:var(--ln2);border-radius:4px}
h3{margin:18px 0 8px;font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--m)}
h3:first-child{margin-top:0}
h4{margin:14px 0 6px;font-size:11px;font-weight:600;color:var(--m);letter-spacing:.05em;text-transform:uppercase}
.drop{border:1.5px dashed var(--ln2);border-radius:8px;padding:20px 12px;text-align:center;cursor:pointer;transition:.15s;background:var(--pn2)}
.drop:hover,.drop.over{border-color:var(--ac);background:rgba(108,140,255,.07)}
.drop b{display:block;font-weight:500}.drop span{font-size:12px;color:var(--m)}
.row2{display:flex;align-items:center;justify-content:space-between;gap:8px}
.fn{font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.badge{display:inline-flex;align-items:center;font-size:11px;font-weight:500;padding:1px 8px;border-radius:999px;border:1px solid var(--ln2);color:var(--m);text-transform:capitalize;white-space:nowrap}
.badge.completed{color:var(--ok);border-color:rgba(76,195,138,.4)}.badge.failed{color:var(--er);border-color:rgba(242,109,109,.4)}
.badge.processing,.badge.queued{color:var(--ac);border-color:rgba(108,140,255,.45)}
.prog{height:4px;border-radius:3px;background:var(--ln);overflow:hidden;margin:10px 0;position:relative}
.prog i{position:absolute;inset:0 auto 0 0;width:0;background:var(--ok);border-radius:3px;transition:width .3s}
.prog.completed i{width:100%}.prog.failed i{width:100%;background:var(--er)}
.prog.queued i,.prog.processing i{width:35%;background:var(--ac);animation:ind 1.1s ease-in-out infinite alternate}
@keyframes ind{from{left:0}to{left:65%}}
.kp{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.kp div{background:var(--pn2);border:1px solid var(--ln);border-radius:8px;padding:8px 10px}
.kp small{display:block;font-size:11px;color:var(--m)}
.kp b{font-size:19px;font-weight:600;font-variant-numeric:tabular-nums}
.err{color:var(--er);font-size:12px;margin-top:8px;word-break:break-word}
.leg{display:grid;grid-template-columns:1fr 1fr;gap:5px 8px;font-size:12px;color:var(--m)}
.leg i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px}
#act{list-style:none;margin:0;padding:0;font-size:12px}
#act li{display:flex;gap:8px;padding:4px 0;border-bottom:1px solid var(--ln);color:var(--m)}
#act time{font:11px var(--mono);color:var(--m2);flex:none;padding-top:1px}
#act li.ok{color:var(--ok)}#act li.er{color:var(--er)}#act li.in{color:var(--t)}
/* graph */
.gt{display:flex;align-items:center;gap:8px;padding:11px 14px;border-bottom:1px solid var(--ln);flex:none}
.gt>div{min-width:0}
.gt b{font-size:13.5px;font-weight:600;display:block}
.gt small{font-size:12px;color:var(--m);display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.live{width:8px;height:8px;border-radius:50%;background:var(--ln2);flex:none}
.live.on{background:var(--ok);animation:pg 1.4s infinite}
@keyframes pg{0%{box-shadow:0 0 0 0 rgba(76,195,138,.6)}100%{box-shadow:0 0 0 8px rgba(76,195,138,0)}}
.btn{font:500 12.5px Inter,sans-serif;cursor:pointer;border:1px solid var(--ln2);background:var(--pn2);color:var(--t);border-radius:7px;padding:7px 12px;white-space:nowrap;transition:.15s}
.btn:hover{border-color:var(--m2)}.btn:disabled{opacity:.55;cursor:wait}
.btn.sm{padding:5px 10px;font-size:12px}.btn.on{background:rgba(108,140,255,.14);border-color:var(--ac);color:#c9d6ff}
.btn.pri{background:var(--ac);border-color:var(--ac);color:#fff;width:100%;margin-top:14px;padding:10px;font-size:13px}
.btn.pri:hover{filter:brightness(1.08)}
#gwrap{flex:1;min-height:0;position:relative;background-image:radial-gradient(var(--ln) 1px,transparent 1px);background-size:22px 22px}
#graph{position:absolute;inset:0;width:100%;height:100%;cursor:grab}
#graph:active{cursor:grabbing}
#empty{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;color:var(--m);text-align:center;padding:24px;pointer-events:none}
#empty b{color:var(--t);font-size:15px;font-weight:600}
#gleg{position:absolute;left:14px;bottom:12px;right:14px;display:flex;flex-wrap:wrap;gap:4px 16px;font-size:11.5px;color:var(--m);pointer-events:none}
#gleg i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}
#insp{position:absolute;right:14px;top:14px;width:262px;max-height:calc(100% - 70px);overflow:auto;background:rgba(17,20,27,.96);border:1px solid var(--ln2);border-radius:10px;padding:14px;display:none;box-shadow:0 12px 36px rgba(0,0,0,.45)}
.ih{display:flex;align-items:center;gap:8px;margin-bottom:10px}
.ih b{font-weight:600;word-break:break-all;flex:1;min-width:0}
.ih .x{background:none;border:0;color:var(--m);cursor:pointer;font:12px Inter;padding:0}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.kpis div{background:var(--pn2);border:1px solid var(--ln);border-radius:7px;padding:6px 8px}
.kpis small{display:block;font-size:10.5px;color:var(--m)}.kpis b{font-size:15px;font-variant-numeric:tabular-nums}
.rate{height:4px;background:var(--ln);border-radius:2px;margin:10px 0 4px;overflow:hidden}.rate i{display:block;height:100%;background:var(--er)}
.mut{color:var(--m);font-size:11.5px}
#insp .row{display:flex;justify-content:space-between;gap:8px;padding:5px 8px;border-radius:6px;cursor:pointer;font-size:12.5px}
#insp .row:hover{background:var(--pn2)}#insp .row em{font-style:normal;color:var(--m);font-variant-numeric:tabular-nums}#insp .row s{text-decoration:none;color:var(--er)}
#insp .none{color:var(--m2);font-size:12px;padding:2px 8px}
.smp{font:11px var(--mono);color:var(--m);word-break:break-all;margin-top:4px}
.edge{fill:none;stroke-linecap:round;stroke-dasharray:5 6;animation:fl 1.4s linear infinite;transition:opacity .2s}
@keyframes fl{to{stroke-dashoffset:-11}}
.hit{fill:none;stroke:transparent;stroke-width:14;cursor:pointer}
.edge.dim,.node.dim,.elab.dim{opacity:.12}
.elab{fill:#a9b1c6;font:500 10.5px Inter,sans-serif;text-anchor:middle;paint-order:stroke;stroke:#0b0d12;stroke-width:3px;pointer-events:none}
.node{cursor:pointer;transition:opacity .2s}
.node .core{stroke-width:1.8}.node.sel .core{stroke-width:3;stroke:#fff}
.node .ring{fill:none;stroke:#f26d6d;stroke-width:1.5;opacity:0}
.node.err .ring{animation:br 2.4s ease-in-out infinite}
@keyframes br{0%,100%{opacity:.2}50%{opacity:.75}}
.lbl{fill:#e7eaf0;font:600 12px Inter,sans-serif;text-anchor:middle;paint-order:stroke;stroke:#0b0d12;stroke-width:3px;pointer-events:none}
.sub{fill:#8d95a8;font:11px Inter,sans-serif;text-anchor:middle;paint-order:stroke;stroke:#0b0d12;stroke-width:3px;pointer-events:none}
/* query */
textarea,input{width:100%;min-width:0;background:#0d1017;border:1px solid var(--ln);border-radius:7px;color:var(--t);padding:8px 10px;font:13px Inter,sans-serif;outline:none;transition:.15s;color-scheme:dark}
textarea:focus,input:focus{border-color:var(--ac);box-shadow:0 0 0 3px rgba(108,140,255,.15)}
textarea{resize:vertical;min-height:84px}
.sug{margin-top:8px;display:flex;flex-direction:column;gap:3px}
.sug a{color:var(--m);font-size:12px;cursor:pointer}.sug a:hover{color:var(--ac)}
details.f{border:1px solid var(--ln);border-radius:8px;padding:10px 12px;margin-top:14px;background:var(--pn2)}
details.f>summary{font-weight:500;font-size:12.5px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
.chip{font-size:12px;border:1px solid var(--ln2);color:var(--m);padding:2px 10px;border-radius:999px;cursor:pointer;transition:.15s;user-select:none}
.chip:hover{color:var(--t)}.chip.on{color:#0b0d12;border-color:transparent;font-weight:600}
.g2{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:8px}
label.s{display:block;font-size:11px;color:var(--m);margin:0 0 3px}
.chk{display:flex;gap:8px;align-items:center;margin-top:10px;font-size:12.5px;color:var(--m)}.chk input{width:auto}
.res{margin-top:20px;border-top:1px solid var(--ln);padding-top:16px;animation:up .25s ease}
@keyframes up{from{opacity:0;transform:translateY(6px)}}
.rh{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px}
.rh h3{margin:0}
.meter{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;color:var(--m)}
.meter span{width:16px;height:5px;border-radius:2px;background:var(--ln2)}.meter span.f{background:var(--ac)}
.ans{font-size:14px;line-height:1.6}
.call{margin:12px 0;padding:10px 12px;border:1px solid var(--ln2);border-left:3px solid var(--ac);border-radius:6px;background:var(--pn2)}
.call small{display:block;font-size:11px;color:var(--m);margin-bottom:2px}
.tl{list-style:none;margin:0;padding:0 0 0 14px;border-left:1px solid var(--ln2)}
.tl li{position:relative;padding:0 0 10px 10px;font-size:12.8px}
.tl li:before{content:"";position:absolute;left:-18px;top:6px;width:7px;height:7px;border-radius:50%;background:var(--ac)}
.tl time{display:block;font:11px var(--mono);color:var(--m2)}
.lim{font-size:12.5px;color:var(--wn);padding:2px 0 2px 10px;border-left:2px solid var(--wn);margin:5px 0}
details.e{border:1px solid var(--ln);border-radius:8px;padding:8px 10px;margin-top:7px;background:var(--pn2)}
details.e summary{cursor:pointer;font-size:12.5px}
pre{margin:8px 0 0;white-space:pre-wrap;word-break:break-word;font:11.5px/1.55 var(--mono);color:#b5bdd0;max-height:260px;overflow:auto}
.ts{color:#6a728a}.rid{color:#7fb2ff}.sv{color:#c3a6ff}.se{color:var(--er);font-weight:500}.sw{color:var(--wn);font-weight:500}.si{color:var(--ok)}
.fc{display:inline-block;margin:2px 4px 2px 0;padding:1px 8px;border:1px solid var(--ln2);border-radius:5px;font:11.5px var(--mono);color:#9db4ff}
.sk{height:11px;border-radius:3px;margin:10px 0;background:linear-gradient(90deg,var(--ln),var(--ln2),var(--ln));background-size:200% 100%;animation:sh 1.1s infinite}
@keyframes sh{to{background-position:-200% 0}}
@media(max-width:1200px){body{overflow:auto}main{grid-template-columns:1fr}#gcard{height:70vh}}
</style></head><body>
<header class="top">
  <div class="brand">
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none"><rect width="28" height="28" rx="7" fill="#161a23" stroke="#2e3544"/><path d="M9 18l5-8 5 8" stroke="#6c8cff" stroke-width="1.5"/><circle cx="9" cy="18" r="2.4" fill="#6c8cff"/><circle cx="14" cy="10" r="2.4" fill="#6c8cff"/><circle cx="19" cy="18" r="2.4" fill="#6c8cff"/></svg>
    <div><b>GREP AI</b><span>From log search to root cause</span></div>
  </div>
  <div class="sp"></div>
  <span class="status" id="llm"><i></i><em style="font-style:normal">Checking</em></span>
</header>
<main>
  <aside class="pn"><div class="sc">
    <h3>Upload</h3>
    <div class="drop" id="drop"><b>Drop a .log file</b><span>or click to browse</span></div>
    <input type="file" id="file" accept=".log" hidden>
    <h3>Current job</h3>
    <div class="row2"><span class="fn" id="jname">No job</span><span class="badge" id="jstate">idle</span></div>
    <div class="prog" id="prog"><i></i></div>
    <div class="kp"><div><small>Lines</small><b id="jlines">0</b></div><div><small>Chunks</small><b id="jchunks">0</b></div></div>
    <div class="err" id="jerr"></div>
    <h3>Severity</h3><div class="leg" id="legend"></div>
    <h3>Activity (UTC)</h3><ul id="act"></ul>
  </div></aside>

  <section class="pn" id="gcard">
    <div class="gt"><span class="live" id="live"></span>
      <div><b>Service map</b><small id="gstats">No data yet</small></div><span class="sp"></span>
      <button class="btn sm" id="errOnly">Errors only</button><button class="btn sm" id="fit">Fit</button><button class="btn sm" id="reload">Refresh</button></div>
    <div id="gwrap">
      <svg id="graph"></svg>
      <div id="empty"><b>No service data yet</b><span>Upload a log file to map its services and how events flow between them.</span></div>
      <div id="insp"></div>
      <div id="gleg"><span id="basis"></span></div>
    </div>
  </section>

  <aside class="pn"><div class="sc">
    <h3>Question</h3>
    <textarea id="q" placeholder="Ask about errors, services or time ranges"></textarea>
    <div class="sug" id="sug"></div>
    <details class="f" open><summary>Filters</summary>
      <div class="chips" id="chips"></div>
      <div class="g2">
        <div><label class="s">Service</label><input id="fsvc" placeholder="database-service"></div>
        <div><label class="s">Error code</label><input id="fcode" placeholder="HTTP_500"></div>
        <div><label class="s">From (UTC)</label><input id="fstart" type="datetime-local"></div>
        <div><label class="s">To (UTC)</label><input id="fend" type="datetime-local"></div>
      </div>
      <label class="chk"><input type="checkbox" id="scope" checked> Limit to the current upload</label>
    </details>
    <button class="btn pri" id="go">Analyze</button>
    <div id="out"></div>
  </div></aside>
</main>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script>
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const SEV={CRITICAL:'#e5484d',ERROR:'#f26d6d',WARNING:'#e8b04a',NOTICE:'#5ab0e8',INFO:'#4cc38a',DEBUG:'#7b8394'};
const sevc=s=>SEV[s]||'#7b8394';
let jobId=null,timer=null,hl=[],gdata=null,lastState='',userZoom=false,onlyErr=false,busy=false,tickN=0;
let hov=null,sel=null,selE=null,gmax=1,emax=1;
try{jobId=localStorage.getItem('grep_job')}catch(e){}

function logLine(msg,cls){const ul=$('#act'),li=document.createElement('li');li.className=cls||'';
  li.innerHTML='<time>'+new Date().toISOString().slice(11,19)+'</time><span></span>';li.lastChild.textContent=msg;ul.prepend(li);
  while(ul.children.length>30)ul.removeChild(ul.lastChild)}
async function api(path,opts){const r=await fetch(path,opts);let d=null;try{d=await r.json()}catch(e){}
  if(!r.ok){let m=d&&d.detail;if(Array.isArray(m))m=m.map(x=>(x.loc||[]).slice(1).join('.')+': '+x.msg).join('; ');throw new Error(m||('HTTP '+r.status))}return d}

$('#legend').innerHTML=Object.keys(SEV).map(k=>`<div><i style="background:${SEV[k]}"></i>${k}</div>`).join('');
$('#chips').innerHTML=['INFO','WARNING','ERROR','CRITICAL'].map(s=>`<span class="chip" data-s="${s}">${s}</span>`).join('');
document.querySelectorAll('#chips .chip').forEach(c=>c.onclick=()=>{const on=c.classList.toggle('on');c.style.background=on?SEV[c.dataset.s]:''});
const SUG=['Why did requests fail?','What errors occurred and in which services?','Summarize the failures and the likely cause'];
$('#sug').innerHTML=SUG.map(q=>`<a>${esc(q)}</a>`).join('');
document.querySelectorAll('#sug a').forEach(a=>a.onclick=()=>{$('#q').value=a.textContent;$('#q').focus()});

/* ---------------- graph ---------------- */
const wrap=$('#gwrap'),svg=d3.select('#graph');let W=800,H=600;
const defs=svg.append('defs');
[['neu','#5b6683'],['err','#f26d6d'],['hot','#6c8cff']].forEach(([k,c])=>defs.append('marker').attr('id','ar-'+k).attr('viewBox','0 0 10 10').attr('refX',9).attr('refY',5).attr('markerWidth',6).attr('markerHeight',6).attr('orient','auto').append('path').attr('d','M0,0L10,5L0,10z').attr('fill',c));
const root=svg.append('g'),linkG=root.append('g'),labG=root.append('g'),nodeG=root.append('g');
const zoom=d3.zoom().scaleExtent([.25,4]).on('zoom',e=>{root.attr('transform',e.transform);if(e.sourceEvent)userZoom=true});
svg.call(zoom).on('dblclick.zoom',null);
svg.on('click',ev=>{if(ev.target===svg.node()){sel=null;selE=null;showInsp();restyle()}});
let link=linkG.selectAll('path.edge'),hit=linkG.selectAll('path.hit'),elab=labG.selectAll('text'),node=nodeG.selectAll('g.node');
const eid=(e,k)=>e[k].id||e[k];
const ekey=e=>eid(e,'source')+'>'+eid(e,'target');
const radius=c=>9+19*Math.log(c+1)/Math.log(gmax+1);
const sim=d3.forceSimulation()
  .force('link',d3.forceLink().id(d=>d.id).distance(d=>130+d.source.r+d.target.r).strength(.35))
  .force('charge',d3.forceManyBody().strength(-520))
  .force('x',d3.forceX(0).strength(.05)).force('y',d3.forceY(0).strength(.05))
  .force('collide',d3.forceCollide(d=>d.r+34))
  .on('tick',ticked).on('end',()=>{if(!userZoom)fit()});
const drag=d3.drag().on('start',(e,d)=>{if(!e.active)sim.alphaTarget(.25).restart();d.fx=d.x;d.fy=d.y}).on('drag',(e,d)=>{d.fx=e.x;d.fy=e.y}).on('end',(e,d)=>{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null});
function pathFor(d){const s=d.source,t=d.target;if(!s||!t||s.x==null||t.x==null)return'';
  const dx=t.x-s.x,dy=t.y-s.y,l=Math.hypot(dx,dy)||1,ux=dx/l,uy=dy/l,k=.18;
  const x1=s.x+ux*s.r,y1=s.y+uy*s.r,x2=t.x-ux*(t.r+6),y2=t.y-uy*(t.r+6);
  const cx=(x1+x2)/2-uy*l*k,cy=(y1+y2)/2+ux*l*k;
  d.mx=.25*x1+.5*cx+.25*x2;d.my=.25*y1+.5*cy+.25*y2;
  return `M${x1},${y1}Q${cx},${cy} ${x2},${y2}`}
function ticked(){link.attr('d',pathFor);hit.attr('d',pathFor);elab.attr('x',d=>d.mx||0).attr('y',d=>d.my||0);node.attr('transform',d=>`translate(${d.x},${d.y})`)}
function fit(){const ns=sim.nodes();if(!ns.length)return;userZoom=false;
  let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
  ns.forEach(n=>{x0=Math.min(x0,n.x-n.r-40);x1=Math.max(x1,n.x+n.r+40);y0=Math.min(y0,n.y-n.r-30);y1=Math.max(y1,n.y+n.r+50)});
  const k=Math.min(1.4,.92*Math.min(W/(x1-x0),H/(y1-y0)));
  svg.transition().duration(500).call(zoom.transform,d3.zoomIdentity.translate(W/2-k*(x0+x1)/2,H/2-k*(y0+y1)/2).scale(k))}
function resize(){W=wrap.clientWidth||800;H=wrap.clientHeight||600;svg.attr('viewBox',`0 0 ${W} ${H}`);
  if(sim.nodes().length){if(!userZoom)fit()}else svg.call(zoom.transform,d3.zoomIdentity.translate(W/2,H/2))}
new ResizeObserver(resize).observe(wrap);resize();

function restyle(){
  const act=hov||sel;let nb=null;
  if(act&&gdata){nb=new Set([act]);gdata.edges.forEach(e=>{if(e.source===act)nb.add(e.target);if(e.target===act)nb.add(e.source)})}
  const anyHot=gdata&&gdata.anyHot;
  node.classed('dim',d=>{
    if(selE){const p=selE.split('>');return d.id!==p[0]&&d.id!==p[1]}
    if(nb)return !nb.has(d.id);
    if(onlyErr&&!d.errors)return true;
    return !!(anyHot&&!d.hot)}).classed('sel',d=>d.id===sel);
  const edim=e=>{const a=eid(e,'source'),b=eid(e,'target');
    if(selE)return a+'>'+b!==selE;
    if(act)return a!==act&&b!==act;
    if(onlyErr&&!e.errors)return true;
    return !!(anyHot&&!e.hot)};
  const vis=e=>{const n=gdata?gdata.edges.length:0;if(n<=10||e.count>=emax*.3)return true;
    const a=eid(e,'source'),b=eid(e,'target');return a+'>'+b===selE||(act&&(a===act||b===act))};
  link.classed('dim',edim);hit.style('pointer-events',e=>edim(e)?'none':'stroke');
  elab.classed('dim',edim).style('display',e=>vis(e)?null:'none')}

function showInsp(){
  const el=$('#insp');if(!gdata||(!sel&&!selE)){el.style.display='none';return}
  let h='';
  if(sel){
    const d=gdata.nodes.find(n=>n.id===sel);if(!d){el.style.display='none';return}
    const ins=gdata.edges.filter(e=>e.target===sel).sort((a,b)=>b.count-a.count),outs=gdata.edges.filter(e=>e.source===sel).sort((a,b)=>b.count-a.count);
    const rate=d.count?Math.round(100*d.errors/d.count):0;
    const rows=(arr,k)=>arr.length?arr.map(e=>`<div class="row" data-n="${esc(e[k])}"><span>${esc(e[k])}</span><em>${e.count}${e.errors?` <s>${e.errors} err</s>`:''}</em></div>`).join(''):'<div class="none">None</div>';
    h=`<div class="ih"><b>${esc(d.id)}</b><span class="badge" style="color:${sevc(d.severity)};border-color:${sevc(d.severity)}66">${esc(d.severity||'n/a')}</span><button class="x" id="ix">Close</button></div>
    <div class="kpis"><div><small>Events</small><b>${d.count.toLocaleString()}</b></div><div><small>Errors</small><b>${d.errors.toLocaleString()}</b></div><div><small>Warnings</small><b>${d.warnings.toLocaleString()}</b></div></div>
    <div class="rate"><i style="width:${rate}%"></i></div><span class="mut">${rate}% of this service's events are errors</span>
    <h4>Receives from</h4>${rows(ins,'source')}<h4>Sends to</h4>${rows(outs,'target')}`}
  else{
    const p=selE.split('>'),e=gdata.edges.find(x=>x.source===p[0]&&x.target===p[1]);if(!e){el.style.display='none';return}
    const how=gdata.stats.edge_basis==='request_id'?'Seen when an event in the first service was followed by an event in the second within the same request ID.':'Seen when an event in the first service was directly followed by an event in the second in file order. No request IDs were available, so this is weaker evidence.';
    h=`<div class="ih"><b>${esc(p[0])} &rarr; ${esc(p[1])}</b><button class="x" id="ix">Close</button></div>
    <div class="kpis"><div><small>Times seen</small><b>${e.count}</b></div><div><small>Ended in error</small><b>${e.errors}</b></div><div><small>Worst</small><b style="font-size:12px;color:${sevc(e.severity)}">${esc(e.severity||'n/a')}</b></div></div>
    <p class="mut" style="margin:10px 0 0">${how}</p>${e.samples&&e.samples.length?`<h4>Sample request IDs</h4><div class="smp">${e.samples.map(esc).join('<br>')}</div>`:''}`}
  el.innerHTML=h;el.style.display='block';
  $('#ix').onclick=()=>{sel=null;selE=null;showInsp();restyle()};
  el.querySelectorAll('.row').forEach(r=>r.onclick=()=>{sel=r.dataset.n;selE=null;showInsp();restyle()})}

function update(g){
  g.anyHot=g.nodes.some(n=>n.hot);gdata=g;
  gmax=Math.max(1,...g.nodes.map(n=>n.count));emax=Math.max(1,...g.edges.map(e=>e.count));
  if(sel&&!g.nodes.some(n=>n.id===sel))sel=null;
  const old=new Map(sim.nodes().map(n=>[n.id,n]));
  const nodes=g.nodes.map(n=>Object.assign(old.get(n.id)||{x:(Math.random()-.5)*200,y:(Math.random()-.5)*200},n,{r:radius(n.count)}));
  const links=g.edges.map(e=>Object.assign({},e));
  link=linkG.selectAll('path.edge').data(links,ekey).join(en=>en.append('path').attr('class','edge'));
  link.attr('stroke',e=>e.hot?'#6c8cff':e.errors>0?'#f26d6d':'#5b6683').attr('stroke-width',e=>1+2*Math.log(e.count+1)/Math.log(emax+1))
      .attr('marker-end',e=>`url(#ar-${e.hot?'hot':e.errors>0?'err':'neu'})`);
  hit=linkG.selectAll('path.hit').data(links,ekey).join(en=>en.append('path').attr('class','hit'))
      .on('click',(ev,e)=>{ev.stopPropagation();selE=ekey(e);sel=null;showInsp();restyle()});
  elab=labG.selectAll('text').data(links,ekey).join(en=>en.append('text').attr('class','elab')).text(e=>e.count);
  node=nodeG.selectAll('g.node').data(nodes,d=>d.id).join(en=>{
    const x=en.append('g').attr('class','node').call(drag)
      .on('mouseenter',(ev,d)=>{hov=d.id;restyle()}).on('mouseleave',()=>{hov=null;restyle()})
      .on('click',(ev,d)=>{ev.stopPropagation();sel=d.id;selE=null;showInsp();restyle()});
    x.append('circle').attr('class','ring');x.append('circle').attr('class','core');x.append('text').attr('class','lbl');x.append('text').attr('class','sub');return x});
  node.classed('err',d=>d.errors>0);
  node.select('.ring').attr('r',d=>d.r+6);
  node.select('.core').attr('r',d=>d.r).attr('stroke',d=>sevc(d.severity)).attr('fill',d=>sevc(d.severity)+'26');
  node.select('.lbl').attr('dy',d=>d.r+16).text(d=>d.id.length>24?d.id.slice(0,23)+'.':d.id);
  node.select('.sub').attr('dy',d=>d.r+29).text(d=>d.count.toLocaleString()+' events'+(d.errors?', '+d.errors.toLocaleString()+' errors':''));
  sim.nodes(nodes);sim.force('link').links(links);sim.alpha(.7).restart();
  showInsp();restyle()}

async function refreshGraph(){
  if(!jobId||busy)return;busy=true;
  try{const g=await api('/api/v1/graph?job_id='+jobId+(hl.length?'&highlight='+encodeURIComponent(hl.join(',')):''));
    update(g);$('#empty').style.display=g.nodes.length?'none':'flex';
    $('#gstats').textContent=g.nodes.length?`${g.nodes.length} services, ${g.edges.length} links, ${g.stats.events.toLocaleString()} events`:'No service data in this job';
    const b=g.stats.edge_basis;
    $('#basis').textContent=!g.nodes.length?'':b==='request_id'?'Links: consecutive events that share a request ID (temporal order, not proven call direction).':b==='sequence'?'Links: consecutive events in file order. No request IDs found, so treat as weak evidence.':'No links could be inferred from this log.';
    if(g.stats.truncated)$('#basis').textContent+=' Large log: busiest services from a bounded sample.'}
  finally{busy=false}}
$('#reload').onclick=()=>refreshGraph().then(()=>logLine('graph refreshed')).catch(e=>logLine('graph error: '+e.message,'er'));
$('#fit').onclick=fit;
$('#errOnly').onclick=e=>{onlyErr=!onlyErr;e.target.classList.toggle('on',onlyErr);restyle()};

/* ---------------- ingestion ---------------- */
function renderJob(s){
  $('#jname').textContent=s.filename||s.job_id.slice(0,8);const st=$('#jstate');st.textContent=s.status;st.className='badge '+s.status;
  $('#prog').className='prog '+s.status;$('#jlines').textContent=s.lines_processed.toLocaleString();$('#jchunks').textContent=s.chunks_indexed.toLocaleString();
  $('#jerr').textContent=s.error||'';$('#live').classList.toggle('on',s.status==='queued'||s.status==='processing');
  if(s.status!==lastState){lastState=s.status;logLine(`${s.filename||'job'}: ${s.status}`+(s.status==='completed'?` (${s.chunks_indexed} chunks, ${s.lines_processed} lines)`:''),s.status==='failed'?'er':s.status==='completed'?'ok':'in')}}
async function tick(){
  try{const s=await api('/api/v1/ingestion/'+jobId);renderJob(s);const done=s.status==='completed'||s.status==='failed';
    tickN++;if(done||tickN%8===0)await refreshGraph();if(done)stopPolling()}
  catch(e){logLine(e.message,'er');$('#jerr').textContent=e.message;stopPolling()}}
function startPolling(){stopPolling();tickN=0;tick();timer=setInterval(tick,1500)}
function stopPolling(){if(timer){clearInterval(timer);timer=null}$('#live').classList.remove('on')}
async function upload(file){
  if(!file)return;$('#jerr').textContent='';hl=[];sel=null;selE=null;lastState='';userZoom=false;
  logLine('uploading '+file.name+' ('+Math.round(file.size/1024).toLocaleString()+' KB)');
  const fd=new FormData();fd.append('file',file);
  try{const d=await api('/api/v1/ingestion',{method:'POST',body:fd});jobId=d.job_id;logLine('accepted, job '+jobId.slice(0,8),'ok');
    try{localStorage.setItem('grep_job',jobId)}catch(e){}startPolling()}
  catch(e){$('#jerr').textContent=e.message;logLine('upload rejected: '+e.message,'er')}}
const drop=$('#drop'),fi=$('#file');
drop.onclick=()=>fi.click();fi.onchange=()=>{upload(fi.files[0]);fi.value=''};
['dragenter','dragover'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.add('over')}));
['dragleave','drop'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.remove('over')}));
drop.addEventListener('drop',e=>upload(e.dataTransfer.files[0]));

/* ---------------- query ---------------- */
function hlog(text){return text.split('\n').map(line=>{let s=esc(line);
  s=s.replace(/^(\d{4}-\d{2}-\d{2}[ T][\d:.,]+)/,'<span class="ts">$1</span>');
  s=s.replace(/\b(ERROR|CRITICAL|FATAL|SEVERE)\b/g,'<span class="se">$1</span>').replace(/\b(WARN|WARNING)\b/g,'<span class="sw">$1</span>').replace(/\bINFO\b/g,'<span class="si">INFO</span>');
  s=s.replace(/(req-[\w-]+)/g,'<span class="rid">$1</span>').replace(/(\[[^\]]+\])/g,'<span class="sv">$1</span>');return s}).join('\n')}
function renderRCA(r){
  const lvl={high:3,medium:2,low:1,undetermined:0}[r.confidence]||0;
  const meter=[0,1,2].map(i=>`<span class="${i<lvl?'f':''}"></span>`).join('');
  let h=`<div class="res"><div class="rh"><h3>Result</h3><span class="meter" title="Stated by the model, not calibrated">${meter} ${esc(r.confidence)} confidence (model stated)</span></div><div class="ans">${esc(r.answer)}</div>`;
  if(r.likely_root_cause)h+=`<div class="call"><small>Likely root cause (inferred, not proven)</small>${esc(r.likely_root_cause)}</div>`;
  if(r.timeline.length)h+=`<h3>Timeline</h3><ul class="tl">`+r.timeline.map(t=>`<li>${t.timestamp?`<time>${esc(t.timestamp)}</time>`:''}${esc(t.event)}${t.chunk_id?` <span class="badge">chunk ${esc(t.chunk_id.split(':').pop())}</span>`:''}</li>`).join('')+`</ul>`;
  if(r.limitations.length)h+=`<h3>Limitations</h3>`+r.limitations.map(l=>`<div class="lim">${esc(l)}</div>`).join('');
  if(r.evidence.length)h+=`<h3>Evidence (${r.evidence.length})</h3>`+r.evidence.map(e=>`<details class="e"><summary>Chunk ${esc(e.chunk_id.split(':').pop())} <span class="badge" style="color:${sevc(e.severity)};border-color:${sevc(e.severity)}66">${esc(e.severity||'n/a')}</span> lines ${e.start_line}-${e.end_line}, similarity ${e.score}</summary><pre>${hlog(e.excerpt)}</pre></details>`).join('');
  const fa=r.filters_applied,keys=['job_id','severity','service','error_code','start_time','end_time','source_file'];
  const chips=keys.filter(k=>fa[k]!=null).map(k=>`<span class="fc">${k}=${esc(Array.isArray(fa[k])?fa[k].join(','):fa[k])}</span>`).join('');
  h+=`<h3>Filters applied</h3>${chips||'<span class="fc">none: the whole index was searched</span>'}<details class="e"><summary>${fa.candidates_matched} chunks matched inside the vector query</summary><pre>${esc(fa.chroma_where?JSON.stringify(fa.chroma_where,null,2):'no database-side filter was sent')}</pre></details></div>`;
  $('#out').innerHTML=h}
async function analyze(){
  const q=$('#q').value.trim();if(q.length<3){$('#out').innerHTML='<div class="lim">Enter a question first.</div>';return}
  const f={},sev=[...document.querySelectorAll('#chips .chip.on')].map(c=>c.dataset.s);if(sev.length)f.severity=sev;
  [['fsvc','service'],['fcode','error_code'],['fstart','start_time'],['fend','end_time']].forEach(([i,k])=>{const v=$('#'+i).value.trim();if(v)f[k]=v});
  if($('#scope').checked&&jobId)f.job_id=jobId;
  const b=$('#go');b.disabled=true;b.textContent='Analyzing...';logLine('query: '+q.slice(0,60),'in');
  $('#out').innerHTML='<div class="res"><div class="sk"></div><div class="sk" style="width:80%"></div><div class="sk" style="width:55%"></div></div>';
  try{const r=await api('/api/v1/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,filters:f})});
    renderRCA(r);logLine(`analysis ready: ${r.filters_applied.candidates_matched} chunks, ${r.confidence} confidence`,'ok');
    hl=r.evidence.map(e=>e.chunk_id);if(jobId)await refreshGraph()}
  catch(e){$('#out').innerHTML=`<div class="res err">${esc(e.message)}</div>`;logLine('query failed: '+e.message,'er')}
  finally{b.disabled=false;b.textContent='Analyze'}}
$('#go').onclick=analyze;
$('#q').addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey))analyze()});

/* ---------------- boot ---------------- */
api('/health').then(h=>{const l=$('#llm');l.className='status '+(h.llm_key_configured?'ok':'bad');l.lastChild.textContent=h.llm_key_configured?'Nemotron connected':'API key missing'})
  .catch(()=>{const l=$('#llm');l.className='status bad';l.lastChild.textContent='API offline'});
if(jobId)api('/api/v1/ingestion/'+jobId).then(s=>{renderJob(s);return refreshGraph()}).catch(()=>{jobId=null;logLine('previous job expired','er')});
</script></body></html>
"""