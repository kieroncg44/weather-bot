"""Build dashboard.html from the bot's log files. Opens in any browser, works offline.

Run:  python3 dashboard.py      (scan.py and report.py also run this automatically)
"""

import csv
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))


def _csv(name):
    path = os.path.join(HERE, name)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _json(name):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except ValueError:
        return None


def build():
    trades = _csv("paper_trades.csv")
    forecasts = _csv("forecasts.csv")
    actuals = _csv("actuals.csv")
    latest = _json("latest_scan.json") or {}

    # Last forecast made for each city/day, to compare with what actually happened.
    last_fc = {}
    for r in forecasts:
        last_fc[(r["city"], r["date"])] = r.get("mean_high")
    errors = []
    for a in actuals:
        fc = last_fc.get((a["city"], a["date"]))
        if fc not in (None, ""):
            try:
                errors.append({"city": a["city"], "date": a["date"],
                               "forecast": float(fc), "actual": float(a["actual"])})
            except ValueError:
                pass

    try:
        import config
        freeze = getattr(config, "FREEZE_START", None)
    except Exception:
        freeze = None
    data = {
        "freeze_start": freeze,
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scanned_at": latest.get("scanned_at"),
        "new_trades": latest.get("new_trades"),
        "board": latest.get("board", []),
        "trades": trades,
        "errors": errors,
    }
    html = TEMPLATE.replace("/*DATA*/null", json.dumps(data).replace("</", "<\\/"))
    out = os.path.join(HERE, "dashboard.html")
    with open(out, "w") as f:
        f.write(html)
    return out


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>Weather Bot</title>
<style>
:root{
  --bg:#f6f5f2; --panel:#ffffff; --ink:#1d1d1b; --muted:#6b6a66; --line:#e4e2dc;
  --accent:#2f6fde; --accent-soft:#dbe6fb; --market:#b9b6ad;
  --win:#1f8a4c; --win-soft:#dcf1e4; --loss:#c2412d; --loss-soft:#f8e1dc;
  --low:#7a4fd0; --low-soft:#ebe3fa;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#141413; --panel:#1e1e1c; --ink:#ecebe6; --muted:#9a988f; --line:#2f2e2b;
    --accent:#6c9cf0; --accent-soft:#22324f; --market:#5d5b55;
    --win:#4cc27e; --win-soft:#17321f; --loss:#ee7a64; --loss-soft:#3a1e18;
    --low:#a88af0; --low-soft:#2c2342;
  }
}
:root[data-theme="dark"]{
  --bg:#141413; --panel:#1e1e1c; --ink:#ecebe6; --muted:#9a988f; --line:#2f2e2b;
  --accent:#6c9cf0; --accent-soft:#22324f; --market:#5d5b55;
  --win:#4cc27e; --win-soft:#17321f; --loss:#ee7a64; --loss-soft:#3a1e18;
  --low:#a88af0; --low-soft:#2c2342;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.45 -apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",sans-serif;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:28px 16px 64px}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:22px}
h1{font-size:26px;margin:0;letter-spacing:-.02em}
.sub{color:var(--muted);font-size:13px;margin-top:4px}
.badge{display:inline-block;font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  padding:3px 8px;border-radius:99px;background:var(--accent-soft);color:var(--accent);vertical-align:middle;margin-left:8px}
h2{font-size:17px;margin:34px 0 12px;letter-spacing:-.01em}
h2 small{font-weight:400;color:var(--muted);font-size:13px;margin-left:6px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.kpi .l{font-size:12px;color:var(--muted)}
.kpi .v{font-size:26px;font-weight:650;letter-spacing:-.02em;margin-top:2px;font-variant-numeric:tabular-nums}
.kpi .n{font-size:12px;color:var(--muted);margin-top:2px}
.pos{color:var(--win)} .neg{color:var(--loss)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px}
.empty{color:var(--muted);text-align:center;padding:26px 10px;font-size:14px}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.chip{border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:99px;
  padding:5px 12px;font-size:13px;cursor:pointer}
.chip.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.card.hot{border-color:var(--accent)}
.ch{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:2px}
.cn{font-weight:650;font-size:15px}
.kind{font-size:11px;font-weight:600;padding:2px 7px;border-radius:99px;margin-left:6px;text-transform:uppercase;letter-spacing:.05em}
.kind.high{background:var(--accent-soft);color:var(--accent)}
.kind.low{background:var(--low-soft);color:var(--low)}
.fc{font-size:13px;color:var(--muted);margin-bottom:10px}
.fc b{color:var(--ink);font-size:15px}
.row{display:grid;grid-template-columns:86px 1fr 104px;align-items:center;gap:8px;padding:3px 0;font-size:13px}
.lbl{font-variant-numeric:tabular-nums}
.bars{position:relative;height:16px;background:var(--bg);border-radius:4px;overflow:hidden}
.bar{position:absolute;left:0;top:0;bottom:0;background:var(--accent);opacity:.85;border-radius:4px}
.card .low-k .bar{background:var(--low)}
.mk{position:absolute;top:-1px;bottom:-1px;width:3px;background:var(--ink);border-radius:2px}
.nums{font-size:11px;color:var(--muted);text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.sig{grid-column:2 / 4;font-size:12px;font-weight:600;color:var(--accent);margin:-1px 0 3px}
.legend{display:flex;gap:16px;font-size:12px;color:var(--muted);margin:-4px 0 12px;flex-wrap:wrap}
.legend i{display:inline-block;width:14px;height:10px;border-radius:2px;background:var(--accent);margin-right:5px;vertical-align:-1px}
.legend i.m{width:3px;background:var(--ink)}
table{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}
th{text-align:left;color:var(--muted);font-weight:500;font-size:12px;padding:6px 8px;border-bottom:1px solid var(--line)}
td{padding:7px 8px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:none}
.scroll{overflow-x:auto}
.pill{font-size:11px;font-weight:650;padding:2px 8px;border-radius:99px}
.pill.win{background:var(--win-soft);color:var(--win)} .pill.loss{background:var(--loss-soft);color:var(--loss)}
.pill.open{background:var(--bg);color:var(--muted)}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
.help{font-size:13px;color:var(--muted);line-height:1.55}
.help b{color:var(--ink)}
svg text{fill:var(--muted);font-size:11px}
.toggle{border:1px solid var(--line);background:var(--panel);color:var(--muted);border-radius:8px;padding:5px 10px;font-size:12px;cursor:pointer}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>Weather Bot <span class="badge">Paper trading</span></h1>
      <div class="sub" id="stamp"></div>
    </div>
    <button class="toggle" id="theme">Light / dark</button>
  </header>

  <div class="chips" id="version"></div>
  <div class="kpis" id="kpis"></div>

  <h2>Profit over time <small>settled paper trades only</small></h2>
  <div class="panel" id="chart"></div>

  <h2>Market board <small>from the latest scan</small></h2>
  <div class="legend"><span><i></i>Model's chance</span><span><i class="m"></i>Market's price</span>
    <span>A gap between them = possible mispricing</span></div>
  <div class="chips" id="filters"></div>
  <div class="grid" id="board"></div>

  <h2>Open paper trades <small id="opencount"></small></h2>
  <div class="panel scroll" id="open"></div>

  <h2>Results</h2>
  <div class="two">
    <div class="panel"><div style="font-weight:600;margin-bottom:8px">By city</div><div id="bycity"></div></div>
    <div class="panel"><div style="font-weight:600;margin-bottom:8px">Is the model honest?</div><div id="calib"></div></div>
  </div>

  <h2>Settled trades</h2>
  <div class="panel scroll" id="settled"></div>

  <h2>Forecast error <small>actual minus forecast, °F</small></h2>
  <div class="panel scroll" id="errors"></div>

  <h2>How to read this</h2>
  <div class="panel help">
    <p><b>Model's chance</b> is the forecast's probability that the temperature lands in that range.
    <b>Market's price</b> is what Kalshi traders are paying, in cents per $1. A contract at 30¢ means the market thinks there's about a 30% chance.</p>
    <p>A <b>signal</b> appears when the model's chance beats the price by at least 6¢ after fees. <b>BUY YES</b> bets the temperature lands in that range; <b>BUY NO</b> bets it doesn't.</p>
    <p><b>Is the model honest?</b> compares how often trades actually won with how often the model expected them to. If those drift far apart over 100+ trades, the model needs tuning, whatever the profit says.</p>
    <p>This page rebuilds every time the bot runs and refreshes itself every 5 minutes. Nothing here uses real money.</p>
  </div>
</div>

<script>
const D = /*DATA*/null;
const $ = id => document.getElementById(id);
const money = v => (v < 0 ? "−$" : "+$") + Math.abs(v).toFixed(2);
const pct = v => Math.round(v * 100) + "%";
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmtDate = s => { const d = new Date(s + "T12:00:00"); return d.toLocaleDateString(undefined,{weekday:"short",month:"short",day:"numeric"}); };

// theme toggle (remembered per browser)
(function(){
  try { const t = localStorage.getItem("wb-theme"); if (t) document.documentElement.dataset.theme = t; } catch(e){}
  $("theme").onclick = () => {
    const dark = matchMedia("(prefers-color-scheme: dark)").matches;
    const cur = document.documentElement.dataset.theme || (dark ? "dark" : "light");
    const nxt = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = nxt;
    try { localStorage.setItem("wb-theme", nxt); } catch(e){}
  };
})();

// header
(function(){
  let s = "No scan yet";
  if (D.scanned_at) {
    const t = new Date(D.scanned_at.replace(" UTC","Z").replace(" ","T"));
    s = "Last scan " + t.toLocaleString(undefined,{weekday:"short",hour:"numeric",minute:"2-digit"}) +
        (D.new_trades != null ? " · " + D.new_trades + " new trade" + (D.new_trades === 1 ? "" : "s") : "");
  }
  $("stamp").textContent = s;
})();

const ALL = D.trades.map(r => ({...r, pnl: r.pnl === "" ? null : +r.pnl,
  price: +r.price_cents, n: +r.contracts, p: +r.model_prob_win, edge: +r.edge,
  isLow: / low$/.test(r.city)}));
let trades = ALL, settled = [], open = [];
const FREEZE = D.freeze_start;  // "YYYY-MM-DD HH:MM" UTC, same format as logged_at
let view = "frozen";
try { const v = localStorage.getItem("wb-view"); if (v) view = v; } catch(e){}
if (!FREEZE) view = "all";


// market board
(function(){
  const board = D.board || [];
  if (!board.length) { $("board").innerHTML = '<div class="empty panel">Run a full scan to fill the board.</div>'; return; }
  const dates = [...new Set(board.map(c => c.date))].sort();
  const state = {view: "signals", date: dates[0]};
  const views = [["signals","With signals"],["all","All cities"],["high","Highs"],["low","Lows"]];
  function chips(){
    $("filters").innerHTML = views.map(([k,l]) => `<button class="chip ${state.view===k?"on":""}" data-v="${k}">${l}</button>`).join("") +
      (dates.length > 1 ? '<span style="width:10px"></span>' + dates.map(d => `<button class="chip ${state.date===d?"on":""}" data-d="${d}">${fmtDate(d)}</button>`).join("") : "");
    $("filters").querySelectorAll("[data-v]").forEach(b => b.onclick = () => { state.view = b.dataset.v; render(); });
    $("filters").querySelectorAll("[data-d]").forEach(b => b.onclick = () => { state.date = b.dataset.d; render(); });
  }
  function render(){
    chips();
    let cards = board.filter(c => c.date === state.date);
    if (state.view === "signals") cards = cards.filter(c => c.rows.some(r => r.side));
    if (state.view === "high" || state.view === "low") cards = cards.filter(c => c.kind === state.view);
    if (!cards.length) { $("board").innerHTML = '<div class="empty panel">No signals on this day. That\'s fine: the bot only flags clear mispricings.</div>'; return; }
    $("board").innerHTML = cards.map(c => {
      const hot = c.rows.some(r => r.side);
      const rows = c.rows.map(r => {
        const mkt = r.yes_ask != null && r.no_ask != null ? (r.yes_ask + (100 - r.no_ask)) / 2 : (r.yes_ask ?? null);
        const mk = mkt == null ? "" : `<div class="mk" style="left:calc(${Math.min(mkt,99.5)}% - 1px)" title="market ${Math.round(mkt)}¢"></div>`;
        const sig = r.side ? `<div></div><div class="sig">BUY ${r.side} at ${r.price}¢ · edge +${Math.round(r.edge*100)}¢</div>` : "";
        return `<div class="row"><div class="lbl">${esc(r.label)}</div>
          <div class="bars"><div class="bar" style="width:${(r.model*100).toFixed(1)}%"></div>${mk}</div>
          <div class="nums">${pct(r.model)} vs ${mkt == null ? "–" : Math.round(mkt) + "¢"}</div></div>${sig}`;
      }).join("");
      return `<div class="card ${hot?"hot":""} ${c.kind==="low"?"low-k":""}">
        <div class="ch"><div class="cn">${esc(c.city)}<span class="kind ${c.kind}">${c.kind}</span></div>
        <div class="nums">${fmtDate(c.date)}</div></div>
        <div class="fc">Forecast ${c.kind} <b>${c.forecast.toFixed(1)}°</b> · likely ${Math.round(c.low)}–${Math.round(c.high)}°</div>
        ${rows}</div>`;
    }).join("");
  }
  render();
})();

function renderTrades(){
  trades = view === "frozen" && FREEZE ? ALL.filter(t => t.logged_at >= FREEZE) : ALL;
  settled = trades.filter(t => t.status === "settled");
  open = trades.filter(t => t.status === "open");
  const vs = [["frozen", FREEZE ? "Current version (since " + fmtDate(FREEZE.slice(0,10)) + ")" : ""], ["all", "All trades"]].filter(v => v[1]);
  $("version").innerHTML = vs.map(([k,l]) => `<button class="chip ${view===k?"on":""}" data-view="${k}">${l}</button>`).join("");
  $("version").querySelectorAll("[data-view]").forEach(b => b.onclick = () => {
    view = b.dataset.view; try { localStorage.setItem("wb-view", view); } catch(e){}
    renderTrades();
  });
// KPIs
(function(){
  const pnl = settled.reduce((a,t) => a + t.pnl, 0);
  const risked = settled.reduce((a,t) => a + t.n * t.price / 100, 0);
  const wins = settled.filter(t => t.result === "win").length;
  const exp = settled.reduce((a,t) => a + t.p, 0);
  const atRisk = open.reduce((a,t) => a + t.n * t.price / 100, 0);
  const k = (l, v, n, cls) => `<div class="kpi"><div class="l">${l}</div><div class="v ${cls||""}">${v}</div><div class="n">${n}</div></div>`;
  $("kpis").innerHTML =
    k("Paper profit", settled.length ? money(pnl) : "—", settled.length ? settled.length + " settled trades" : "nothing settled yet", settled.length ? (pnl >= 0 ? "pos" : "neg") : "") +
    k("Return on money risked", risked ? (pnl/risked*100).toFixed(1) + "%" : "—", risked ? "on $" + risked.toFixed(2) + " risked" : "", risked ? (pnl >= 0 ? "pos" : "neg") : "") +
    k("Win rate", settled.length ? pct(wins/settled.length) : "—", settled.length ? "model expected " + pct(exp/settled.length) : "") +
    k("Open trades", open.length, "$" + atRisk.toFixed(2) + " (paper) at stake");
})();

// cumulative P&L chart
(function(){
  if (!settled.length) { $("chart").innerHTML = '<div class="empty">First results land the morning after each trading day.</div>'; return; }
  const byDay = {};
  settled.forEach(t => byDay[t.date] = (byDay[t.date] || 0) + t.pnl);
  const days = Object.keys(byDay).sort();
  let c = 0; const pts = days.map(d => (c += byDay[d], {d, v: c}));
  const W = 1000, H = 220, P = 40;
  const vs = pts.map(p => p.v).concat([0]);
  const lo = Math.min(...vs), hi = Math.max(...vs), rng = (hi - lo) || 1;
  const x = i => P + (pts.length === 1 ? (W - 2*P)/2 : i * (W - 2*P) / (pts.length - 1));
  const y = v => H - 24 - (v - lo) / rng * (H - 48);
  const line = pts.map((p,i) => (i ? "L" : "M") + x(i).toFixed(1) + "," + y(p.v).toFixed(1)).join("");
  const last = pts[pts.length-1].v;
  const col = last >= 0 ? "var(--win)" : "var(--loss)";
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Cumulative paper profit">`;
  svg += `<line x1="${P}" x2="${W-P}" y1="${y(0)}" y2="${y(0)}" stroke="var(--line)" stroke-dasharray="4 4"/>`;
  svg += `<text x="4" y="${y(0)+4}">$0</text><text x="4" y="${y(hi)+4}">${money(hi)}</text>`;
  if (lo < 0) svg += `<text x="4" y="${y(lo)+4}">${money(lo)}</text>`;
  svg += `<path d="${line}" fill="none" stroke="${col}" stroke-width="2.5" stroke-linejoin="round"/>`;
  pts.forEach((p,i) => { svg += `<circle cx="${x(i)}" cy="${y(p.v)}" r="3.5" fill="${col}"><title>${p.d}: ${money(p.v)}</title></circle>`; });
  [0, pts.length-1].filter((v,i,a) => a.indexOf(v) === i).forEach(i => {
    svg += `<text x="${x(i)}" y="${H-4}" text-anchor="middle">${fmtDate(pts[i].d)}</text>`; });
  $("chart").innerHTML = svg + "</svg>";
})();

// tables
function tradeTable(list, withResult){
  if (!list.length) return '<div class="empty">' + (withResult ? "Nothing settled yet." : "No open trades.") + "</div>";
  const head = `<tr><th>City</th><th>Day</th><th>Range</th><th>Bet</th><th>Price</th><th>Model</th><th>Edge</th>${withResult?"<th>Result</th><th>Profit</th>":""}</tr>`;
  const body = list.map(t => `<tr><td>${esc(t.city)}</td><td>${fmtDate(t.date)}</td><td>${esc(t.bracket)}</td>
    <td>${t.side}</td><td>${t.price}¢</td><td>${pct(t.p)}</td><td>+${Math.round(t.edge*100)}¢</td>
    ${withResult ? `<td><span class="pill ${t.result}">${t.result}</span></td><td class="${t.pnl>=0?"pos":"neg"}">${money(t.pnl)}</td>` : ""}</tr>`).join("");
  return `<table>${head}${body}</table>`;
}
$("opencount").textContent = open.length ? open.length + " waiting to settle" : "";
$("open").innerHTML = tradeTable(open.slice().sort((a,b) => a.date.localeCompare(b.date) || a.city.localeCompare(b.city)), false);
$("settled").innerHTML = tradeTable(settled.slice().sort((a,b) => b.date.localeCompare(a.date) || a.city.localeCompare(b.city)), true);

// by city
(function(){
  if (!settled.length) { $("bycity").innerHTML = '<div class="empty">Waiting for results.</div>'; return; }
  const m = {};
  settled.forEach(t => { const k = t.city; (m[k] = m[k] || {n:0,w:0,p:0}); m[k].n++; m[k].p += t.pnl; if (t.result === "win") m[k].w++; });
  const rows = Object.entries(m).sort((a,b) => b[1].p - a[1].p);
  $("bycity").innerHTML = "<table><tr><th>City</th><th>Trades</th><th>Won</th><th>Profit</th></tr>" +
    rows.map(([c,v]) => `<tr><td>${esc(c)}</td><td>${v.n}</td><td>${v.w}</td><td class="${v.p>=0?"pos":"neg"}">${money(v.p)}</td></tr>`).join("") + "</table>";
})();

// calibration: bucket by model probability
(function(){
  if (settled.length < 5) { $("calib").innerHTML = '<div class="empty">Needs a few settled trades first.</div>'; return; }
  const buckets = [[0,.5,"Long shots (model under 50%)"],[.5,.75,"Toss-ups+ (50–75%)"],[.75,1.01,"Strong (75%+)"]];
  const rows = buckets.map(([a,b,l]) => {
    const s = settled.filter(t => t.p >= a && t.p < b);
    if (!s.length) return "";
    const exp = s.reduce((x,t) => x + t.p, 0) / s.length;
    const act = s.filter(t => t.result === "win").length / s.length;
    const gap = act - exp;
    return `<tr><td>${l}</td><td>${s.length}</td><td>${pct(exp)}</td><td class="${gap>=-0.05?"pos":"neg"}">${pct(act)}</td></tr>`;
  }).join("");
  const kinds = ["high","low"].map(k => {
    const s = settled.filter(t => (k === "low") === t.isLow);
    if (!s.length) return "";
    const exp = s.reduce((x,t) => x + t.p, 0) / s.length, act = s.filter(t => t.result === "win").length / s.length;
    return `<tr><td>All ${k}s</td><td>${s.length}</td><td>${pct(exp)}</td><td class="${act-exp>=-0.05?"pos":"neg"}">${pct(act)}</td></tr>`;
  }).join("");
  $("calib").innerHTML = "<table><tr><th>Trade type</th><th>Trades</th><th>Expected win</th><th>Actual win</th></tr>" + rows + kinds + "</table>" +
    '<div class="help" style="margin-top:8px">Red means the model is winning noticeably less often than it promised.</div>';
})();

}
renderTrades();

// forecast errors
(function(){
  const e = D.errors || [];
  if (!e.length) { $("errors").innerHTML = '<div class="empty">Builds up as markets settle. After about 10 days per city, these averages become bias corrections.</div>'; return; }
  const m = {};
  e.forEach(r => { (m[r.city] = m[r.city] || []).push(r.actual - r.forecast); });
  const rows = Object.entries(m).sort();
  $("errors").innerHTML = "<table><tr><th>City</th><th>Days</th><th>Average error</th><th>Typical miss</th></tr>" +
    rows.map(([c,v]) => { const avg = v.reduce((a,b)=>a+b,0)/v.length, mad = v.reduce((a,b)=>a+Math.abs(b),0)/v.length;
      return `<tr><td>${esc(c)}</td><td>${v.length}</td><td>${avg>=0?"+":""}${avg.toFixed(1)}°</td><td>${mad.toFixed(1)}°</td></tr>`; }).join("") + "</table>";
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("Wrote", build())
