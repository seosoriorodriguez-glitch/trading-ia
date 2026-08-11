# -*- coding: utf-8 -*-
"""
Lee el JSON de bt_visual (velas M5 + zonas OB + trades) y escribe un HTML
autocontenido (canvas) con candlestick + zonas + trades, para validar visualmente
contra TradingView. Uso: python make_chart.py <in.json> <out.html>
"""
import sys, json
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out = Path(sys.argv[2])
payload = json.dumps(data)

HTML = """<title>Validacion visual — %(name)s</title>
<style>
  :root{--bg:#0e1420;--panel:#151d2b;--border:#243247;--text:#d7e0ec;--dim:#8794a8;
    --up:#26a69a;--dn:#ef5350;--mono:ui-monospace,"SF Mono",Consolas,monospace;--sans:"Segoe UI",system-ui,sans-serif}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);padding:clamp(14px,3vw,32px)}
  .wrap{max-width:1120px;margin:0 auto}
  h1{font-size:clamp(19px,3vw,26px);margin:0 0 4px;font-weight:650;letter-spacing:-.01em}
  .sub{color:var(--dim);font-size:14px;margin:0 0 18px}
  .bar{display:flex;flex-wrap:wrap;gap:10px 22px;margin:0 0 16px;font-family:var(--mono);font-size:12.5px;color:var(--dim)}
  .bar b{color:var(--text)}
  .chartbox{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:10px 6px 6px;position:relative}
  canvas{width:100%;display:block;border-radius:8px}
  .legend{display:flex;flex-wrap:wrap;gap:16px;margin:14px 2px 0;font-size:12.5px;color:var(--dim);font-family:var(--mono)}
  .legend span{display:inline-flex;align-items:center;gap:6px}
  .sw{width:14px;height:10px;border-radius:2px;display:inline-block}
  .trade{margin-top:22px;background:var(--panel);border:1px solid var(--border);border-left:3px solid var(--dn);
    border-radius:10px;padding:14px 18px;font-family:var(--mono);font-size:13px}
  .trade .h{color:var(--dim);text-transform:uppercase;letter-spacing:.08em;font-size:10.5px;margin-bottom:8px}
  .kv{display:flex;flex-wrap:wrap;gap:6px 20px}
  .kv span b{color:var(--text)}
  .note{color:var(--dim);font-size:13px;margin-top:18px;line-height:1.6;font-family:var(--mono)}
  #tip{position:absolute;pointer-events:none;background:#0b1018;border:1px solid var(--border);border-radius:6px;
    padding:6px 9px;font-family:var(--mono);font-size:11px;color:var(--text);opacity:0;transition:opacity .1s;white-space:nowrap}
</style>
<div class="wrap">
  <h1>%(name)s — validación visual</h1>
  <p class="sub" id="sub"></p>
  <div class="bar" id="bar"></div>
  <div class="chartbox"><canvas id="c"></canvas><div id="tip"></div></div>
  <div class="legend">
    <span><i class="sw" style="background:rgba(38,166,154,.28);border:1px solid #26a69a"></i> zona alcista (OB bull)</span>
    <span><i class="sw" style="background:rgba(239,83,80,.24);border:1px solid #ef5350"></i> zona bajista (OB bear)</span>
    <span><i class="sw" style="background:var(--up)"></i> vela alcista</span>
    <span><i class="sw" style="background:var(--dn)"></i> vela bajista</span>
    <span>▼ entrada &nbsp; ✕ salida &nbsp; — SL/TP</span>
  </div>
  <div class="trade" id="tradebox"></div>
  <div class="note">Compara zona por zona con tu TradingView: cada rectángulo es un Order Block que el bot detectó (mismo M5). La entrada STOP se dispara en el borde de la zona. Ventana corta (hoy) → 1 trade; sirve para confirmar que las <b>zonas y la mecánica calzan</b> con lo que ves en pantalla.</div>
</div>
<script>
const D = %(payload)s;
const cv = document.getElementById('c'), ctx = cv.getContext('2d'), tip = document.getElementById('tip');
const C = D.candles, Z = D.zones, T = D.trades, dec = D.dec;
const fmt = v => v.toLocaleString('en-US',{minimumFractionDigits:dec,maximumFractionDigits:dec});
const tISO = s => s.slice(5,16).replace('T',' ');
document.getElementById('sub').textContent = `Order Block · M5 · ${C[0].t.slice(0,16)} → ${C[C.length-1].t.slice(0,16)} (hora servidor)`;
document.getElementById('bar').innerHTML =
  `<span>velas <b>${C.length}</b></span><span>zonas OB <b>${Z.length}</b></span>`+
  `<span>trades <b>${T.length}</b></span><span>rango <b>${fmt(Math.min(...C.map(c=>c.l)))}–${fmt(Math.max(...C.map(c=>c.h)))}</b></span>`;
if(T.length){const t=T[0];const w=t.r>0;
  document.getElementById('tradebox').innerHTML=`<div class="h">operación</div><div class="kv">`+
  `<span>${t.dir==='short'?'▼ SHORT':'▲ LONG'}</span><span>entrada <b>${tISO(t.entry_time)}</b></span>`+
  `<span>entry <b>${fmt(t.entry)}</b></span><span>SL <b>${fmt(t.sl)}</b></span><span>TP <b>${fmt(t.tp)}</b></span>`+
  `<span>salida <b>${tISO(t.exit_time)}</b> (${t.reason.toUpperCase()})</span>`+
  `<span style="color:${w?'#26a69a':'#ef5350'}">R <b style="color:inherit">${t.r>0?'+':''}${t.r.toFixed(2)}</b> ${w?'GANA':'PIERDE'}</span></div>`;
} else { document.getElementById('tradebox').style.display='none'; }

const idxOf = iso => { let b=0; for(let i=0;i<C.length;i++){ if(C[i].t<=iso) b=i; else break; } return b; };
let W,H,PL=10,PR=64,PT=14,PB=26,lo,hi;
function scale(){
  const dpr=Math.min(devicePixelRatio||1,2);
  W=cv.clientWidth; H=Math.round(Math.min(560,Math.max(380,W*0.5)));
  cv.width=W*dpr; cv.height=H*dpr; cv.style.height=H+'px'; ctx.setTransform(dpr,0,0,dpr,0,0);
  lo=Math.min(...C.map(c=>c.l)); hi=Math.max(...C.map(c=>c.h));
  T.forEach(t=>{lo=Math.min(lo,t.sl,t.tp); hi=Math.max(hi,t.sl,t.tp);});
  const pad=(hi-lo)*0.04; lo-=pad; hi+=pad;
}
const X = i => PL + (i+0.5)*((W-PL-PR)/C.length);
const Y = p => PT + (hi-p)/(hi-lo)*(H-PT-PB);
function draw(){
  ctx.clearRect(0,0,W,H);
  // grid + price axis
  ctx.font='11px ui-monospace,monospace'; ctx.textBaseline='middle';
  const steps=6;
  for(let s=0;s<=steps;s++){const p=lo+(hi-lo)*s/steps; const y=Y(p);
    ctx.strokeStyle='rgba(255,255,255,.05)'; ctx.beginPath(); ctx.moveTo(PL,y); ctx.lineTo(W-PR,y); ctx.stroke();
    ctx.fillStyle='#8794a8'; ctx.textAlign='left'; ctx.fillText(fmt(p),W-PR+6,y);}
  // time axis
  ctx.textAlign='center';
  for(let i=0;i<C.length;i+=Math.ceil(C.length/8)){ctx.fillStyle='#8794a8'; ctx.fillText(C[i].t.slice(11,16),X(i),H-10);}
  // zones
  Z.forEach(z=>{const x0=X(idxOf(z.conf)); const bull=z.type==='bullish';
    ctx.fillStyle=bull?'rgba(38,166,154,.16)':'rgba(239,83,80,.14)';
    ctx.fillRect(x0,Y(z.high),(W-PR)-x0,Y(z.low)-Y(z.high));
    ctx.strokeStyle=bull?'rgba(38,166,154,.5)':'rgba(239,83,80,.45)'; ctx.lineWidth=1;
    ctx.strokeRect(x0,Y(z.high),(W-PR)-x0,Y(z.low)-Y(z.high));});
  // candles
  const cw=Math.max(1.5,Math.min(7,(W-PL-PR)/C.length*0.62));
  C.forEach((c,i)=>{const up=c.c>=c.o; ctx.strokeStyle=ctx.fillStyle=up?'#26a69a':'#ef5350';
    const x=X(i); ctx.lineWidth=1; ctx.beginPath(); ctx.moveTo(x,Y(c.h)); ctx.lineTo(x,Y(c.l)); ctx.stroke();
    const yo=Y(c.o),yc=Y(c.c); ctx.fillRect(x-cw/2,Math.min(yo,yc),cw,Math.max(1,Math.abs(yc-yo)));});
  // trades
  T.forEach(t=>{const xi=X(idxOf(t.entry_time)), xe=X(idxOf(t.exit_time));
    const line=(p,col,dash)=>{ctx.strokeStyle=col;ctx.setLineDash(dash);ctx.lineWidth=1.2;
      ctx.beginPath();ctx.moveTo(xi,Y(p));ctx.lineTo(xe,Y(p));ctx.stroke();ctx.setLineDash([]);};
    line(t.tp,'#26a69a',[5,3]); line(t.sl,'#ef5350',[5,3]); line(t.entry,'#cfd8e6',[2,3]);
    ctx.fillStyle=t.dir==='short'?'#ef5350':'#26a69a'; const ey=Y(t.entry);
    ctx.beginPath();
    if(t.dir==='short'){ctx.moveTo(xi,ey-9);ctx.lineTo(xi-5,ey-17);ctx.lineTo(xi+5,ey-17);}
    else{ctx.moveTo(xi,ey+9);ctx.lineTo(xi-5,ey+17);ctx.lineTo(xi+5,ey+17);}
    ctx.closePath();ctx.fill();
    ctx.strokeStyle='#cfd8e6';ctx.lineWidth=1.6;const xy=Y(t.reason==='tp'?t.tp:t.sl);
    ctx.beginPath();ctx.moveTo(xe-4,xy-4);ctx.lineTo(xe+4,xy+4);ctx.moveTo(xe+4,xy-4);ctx.lineTo(xe-4,xy+4);ctx.stroke();});
}
cv.addEventListener('mousemove',e=>{const r=cv.getBoundingClientRect();const mx=e.clientX-r.left;
  const i=Math.round((mx-PL)/((W-PL-PR)/C.length)-0.5);
  if(i<0||i>=C.length){tip.style.opacity=0;return;}const c=C[i];
  tip.innerHTML=`${c.t.slice(11,16)}  O ${fmt(c.o)}  H ${fmt(c.h)}  L ${fmt(c.l)}  C ${fmt(c.c)}`;
  tip.style.opacity=1;tip.style.left=Math.min(mx+12,W-180)+'px';tip.style.top='16px';});
cv.addEventListener('mouseleave',()=>tip.style.opacity=0);
function all(){scale();draw();} addEventListener('resize',all); all();
</script>
"""
html = HTML.replace("%(name)s", data["name"]).replace("%(payload)s", payload)
out.write_text(html, encoding="utf-8")
print(f"OK -> {out}")
