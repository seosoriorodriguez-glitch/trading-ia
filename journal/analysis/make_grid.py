# -*- coding: utf-8 -*-
"""Renderiza un JSON multi-panel (bt_trades_multi) como grilla de mini-graficos.
Uso: python make_grid.py <in.json> <out.html>"""
import sys, json
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out = Path(sys.argv[2]); payload = json.dumps(data)

HTML = r"""<title>Validación de sesgo — %(name)s</title>
<style>
  :root{--bg:#0e1420;--panel:#151d2b;--border:#243247;--text:#d7e0ec;--dim:#8794a8;
    --up:#26a69a;--dn:#ef5350;--mono:ui-monospace,"SF Mono",Consolas,monospace;--sans:"Segoe UI",system-ui,sans-serif}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);padding:clamp(14px,3vw,30px)}
  .wrap{max-width:1240px;margin:0 auto}
  h1{font-size:clamp(19px,3vw,26px);margin:0 0 4px;font-weight:650;letter-spacing:-.01em}
  .sub{color:var(--dim);font-size:14px;margin:0 0 6px}
  .tally{font-family:var(--mono);font-size:13px;margin:0 0 20px}
  .tally b{color:var(--text)}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px}
  .card{background:var(--panel);border:1px solid var(--border);border-radius:10px;overflow:hidden}
  .card.win{border-left:3px solid var(--up)} .card.lose{border-left:3px solid var(--dn)}
  .hd{display:flex;align-items:center;gap:8px;padding:9px 12px;font-family:var(--mono);font-size:11.5px;border-bottom:1px solid var(--border)}
  .hd .date{color:var(--dim)}
  .hd .dir{padding:1px 6px;border-radius:4px;font-size:10.5px}
  .hd .dir.long{color:var(--up);background:rgba(38,166,154,.15)} .hd .dir.short{color:var(--dn);background:rgba(239,83,80,.14)}
  .hd .r{margin-left:auto;font-weight:700}
  .hd .r.p{color:var(--up)} .hd .r.n{color:var(--dn)}
  canvas{width:100%;display:block}
  .legend{display:flex;flex-wrap:wrap;gap:16px;margin:20px 2px 0;font-size:12.5px;color:var(--dim);font-family:var(--mono)}
  .legend i{width:14px;height:10px;border-radius:2px;display:inline-block;vertical-align:middle;margin-right:5px}
  .note{color:var(--dim);font-size:13px;margin-top:16px;line-height:1.6;font-family:var(--mono)}
</style>
<div class="wrap">
  <h1>%(name)s — validación de sesgo</h1>
  <p class="sub">Order Block · M5 · entrada STOP en el borde de la zona (= tu live). Operaciones repartidas parejo en la muestra, sin cherry-pick.</p>
  <p class="tally" id="tally"></p>
  <div class="grid" id="grid"></div>
  <div class="legend">
    <span><i style="background:rgba(38,166,154,.28);border:1px solid #26a69a"></i>zona alcista</span>
    <span><i style="background:rgba(239,83,80,.24);border:1px solid #ef5350"></i>zona bajista</span>
    <span>▼▲ entrada &nbsp; ✕ salida &nbsp; — SL/TP</span>
  </div>
  <div class="note">Revisa cada panel: la entrada debe caer SIEMPRE en el borde de la zona, el SL al otro extremo + buffer, y el resultado (TP/SL) coincidir con el recorrido de las velas. Ganadoras y perdedoras se ven con la MISMA lógica → sin sesgo.</div>
</div>
<script>
const D = %(payload)s; const dec = D.dec;
const fmt = v => v.toLocaleString('en-US',{minimumFractionDigits:dec,maximumFractionDigits:dec});
document.getElementById('tally').innerHTML =
  `<b>${D.panels.length}</b> operaciones mostradas &nbsp;·&nbsp; <span style="color:#26a69a"><b>${D.wins}</b> ganan</span> / <span style="color:#ef5350"><b>${D.losses}</b> pierden</span> &nbsp;·&nbsp; de <b>${D.total}</b> totales`;
const grid = document.getElementById('grid');
D.panels.forEach((pn,ix)=>{
  const t = pn.trade, win = t.r>0;
  const card = document.createElement('div'); card.className='card '+(win?'win':'lose');
  card.innerHTML = `<div class="hd"><span class="date">${t.entry_time.slice(5,16)}</span>`+
    `<span class="dir ${t.dir}">${t.dir==='short'?'▼ short':'▲ long'}</span>`+
    `<span class="r ${win?'p':'n'}">${t.r>0?'+':''}${t.r.toFixed(2)}R ${win?'GANA':'PIERDE'}</span></div>`+
    `<canvas id="cv${ix}"></canvas>`;
  grid.appendChild(card);
  drawPanel('cv'+ix, pn);
});
function drawPanel(id, pn){
  const cv=document.getElementById(id), ctx=cv.getContext('2d');
  const C=pn.candles, Z=pn.zone, t=pn.trade;
  const dpr=Math.min(devicePixelRatio||1,2), W=cv.clientWidth, H=190;
  cv.width=W*dpr; cv.height=H*dpr; cv.style.height=H+'px'; ctx.setTransform(dpr,0,0,dpr,0,0);
  const PL=6,PR=52,PT=8,PB=16;
  let lo=Math.min(...C.map(c=>c.l),t.sl,t.tp), hi=Math.max(...C.map(c=>c.h),t.sl,t.tp);
  const pad=(hi-lo)*0.06; lo-=pad; hi+=pad;
  const X=i=>PL+(i+0.5)*((W-PL-PR)/C.length), Y=p=>PT+(hi-p)/(hi-lo)*(H-PT-PB);
  const idxOf=iso=>{let b=0;for(let i=0;i<C.length;i++){if(C[i].t<=iso)b=i;else break;}return b;};
  ctx.clearRect(0,0,W,H);
  ctx.font='10px ui-monospace,monospace'; ctx.textBaseline='middle';
  for(let s=0;s<=3;s++){const p=lo+(hi-lo)*s/3,y=Y(p);
    ctx.strokeStyle='rgba(255,255,255,.05)';ctx.beginPath();ctx.moveTo(PL,y);ctx.lineTo(W-PR,y);ctx.stroke();
    ctx.fillStyle='#8794a8';ctx.textAlign='left';ctx.fillText(fmt(p),W-PR+5,y);}
  // zona
  const x0=X(idxOf(Z.conf)), bull=Z.type==='bullish';
  ctx.fillStyle=bull?'rgba(38,166,154,.16)':'rgba(239,83,80,.14)';
  ctx.fillRect(x0,Y(Z.high),(W-PR)-x0,Y(Z.low)-Y(Z.high));
  ctx.strokeStyle=bull?'rgba(38,166,154,.5)':'rgba(239,83,80,.45)';ctx.lineWidth=1;ctx.strokeRect(x0,Y(Z.high),(W-PR)-x0,Y(Z.low)-Y(Z.high));
  // velas
  const cw=Math.max(1.2,Math.min(6,(W-PL-PR)/C.length*0.6));
  C.forEach((c,i)=>{const up=c.c>=c.o;ctx.strokeStyle=ctx.fillStyle=up?'#26a69a':'#ef5350';
    const x=X(i);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,Y(c.h));ctx.lineTo(x,Y(c.l));ctx.stroke();
    const yo=Y(c.o),yc=Y(c.c);ctx.fillRect(x-cw/2,Math.min(yo,yc),cw,Math.max(1,Math.abs(yc-yo)));});
  // trade
  const xi=X(idxOf(t.entry_time)), xe=X(idxOf(t.exit_time));
  const line=(p,col)=>{ctx.strokeStyle=col;ctx.setLineDash([4,3]);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(xi,Y(p));ctx.lineTo(xe,Y(p));ctx.stroke();ctx.setLineDash([]);};
  line(t.tp,'#26a69a');line(t.sl,'#ef5350');line(t.entry,'#cfd8e6');
  ctx.fillStyle=t.dir==='short'?'#ef5350':'#26a69a';const ey=Y(t.entry);ctx.beginPath();
  if(t.dir==='short'){ctx.moveTo(xi,ey-7);ctx.lineTo(xi-4,ey-14);ctx.lineTo(xi+4,ey-14);}
  else{ctx.moveTo(xi,ey+7);ctx.lineTo(xi-4,ey+14);ctx.lineTo(xi+4,ey+14);}
  ctx.closePath();ctx.fill();
  ctx.strokeStyle='#cfd8e6';ctx.lineWidth=1.4;const xy=Y(t.reason==='tp'?t.tp:t.sl);
  ctx.beginPath();ctx.moveTo(xe-3,xy-3);ctx.lineTo(xe+3,xy+3);ctx.moveTo(xe+3,xy-3);ctx.lineTo(xe-3,xy+3);ctx.stroke();
}
addEventListener('resize',()=>D.panels.forEach((pn,ix)=>drawPanel('cv'+ix,pn)));
</script>
"""
out.write_text(HTML.replace("%(name)s", data["name"]).replace("%(payload)s", payload), encoding="utf-8")
print(f"OK -> {out}")
