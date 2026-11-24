/* Animated code maps for the review page: architecture, data flow, data model.
   Draws the maps that render_preview.py lays out, one step at a time, and saves them as a GIF.
   Needs gif.js (GifEncoder) loaded before it. No network, no dependencies. */
(function () {
  // Colors come from the page's own CSS variables, the same ones the flowchart uses, so the browser's
  // light or dark mode applies to the maps too.
  var T = {};
  function readTheme() {
    var cs = getComputedStyle(document.documentElement);
    function v(n, d) { return (cs.getPropertyValue(n) || "").trim() || d; }
    T = { bg: v("--bg", "#f6f7f9"), card: v("--card", "#fff"), fg: v("--fg", "#1d2330"), muted: v("--muted", "#5b6474"), line: v("--line", "#dde1e8"),
      code: v("--code", "#f0f2f5"), accent: v("--accent", "#2f5fb3"), del: v("--del", "#fdecec"), delmk: v("--del-mk", "#b42318"), addmk: v("--add-mk", "#1f7a3a"),
      p: { P1: v("--p1", "#b42318"), P2: v("--p2", "#c4560c"), P3: v("--p3", "#2f5fb3"), P4: v("--p4", "#6b47b8"), P5: v("--p5", "#5b6474") } };
  }
  function rgb(c) {
    c = String(c).trim(); var m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(c);
    if (m) { var h = m[1]; if (h.length === 3) h = h.replace(/./g, "$&$&"); return [parseInt(h.substr(0, 2), 16), parseInt(h.substr(2, 2), 16), parseInt(h.substr(4, 2), 16)]; }
    m = /rgba?\(([^)]+)\)/.exec(c); if (m) { var q = m[1].split(","); return [+q[0], +q[1], +q[2]]; }
    return [128, 128, 128];
  }
  function al(c, a) { var q = rgb(c); return "rgba(" + q[0] + "," + q[1] + "," + q[2] + "," + a + ")"; }
  readTheme();
  var LOGO = null; try { LOGO = window.__ADV_LOGO ? new Path2D(window.__ADV_LOGO) : null; } catch (e) {}
  // The AdversaryPR helmet, drawn from its own path (viewBox 14 10 172 128), h pixels tall.
  function logo(c, x, y, h, color) { if (!LOGO) return; var k = h / 128; c.save(); c.translate(x, y); c.scale(k, k); c.translate(-14, -10); c.fillStyle = color; c.fill(LOGO); c.restore(); }
  var MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace";
  var SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif";
  var STEP = 1.3, HOLD = 1.2;

  function rr(c, x, y, w, h, r) { c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); }
  function plen(p) { var L = 0, s = []; for (var i = 1; i < p.length; i++) { var d = Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]); s.push(d); L += d; } return { L: L, s: s }; }
  function at(p, f) { var m = plen(p), d = f * m.L; for (var i = 0; i < m.s.length; i++) { if (d <= m.s[i] || i === m.s.length - 1) { var u = m.s[i] ? Math.min(1, d / m.s[i]) : 0; return [p[i][0] + (p[i + 1][0] - p[i][0]) * u, p[i][1] + (p[i + 1][1] - p[i][1]) * u]; } d -= m.s[i]; } return p[0]; }
  function trail(c, p, f1, color, w) {
    var m = plen(p), b = f1 * m.L, d = 0; c.strokeStyle = color; c.lineWidth = w; c.beginPath(); c.moveTo(p[0][0], p[0][1]);
    for (var i = 0; i < m.s.length; i++) { var s0 = d; d += m.s[i]; if (s0 >= b) break; var u = Math.min(1, (b - s0) / m.s[i]); c.lineTo(p[i][0] + (p[i + 1][0] - p[i][0]) * u, p[i][1] + (p[i + 1][1] - p[i][1]) * u); }
    c.stroke();
  }
  function arrow(c, p, color) { var n = p.length, a = p[n - 3] || p[n - 2], b = p[n - 1], ang = Math.atan2(b[1] - a[1], b[0] - a[0]); c.fillStyle = color; c.beginPath(); c.moveTo(b[0], b[1]); c.lineTo(b[0] - 9 * Math.cos(ang - .45), b[1] - 9 * Math.sin(ang - .45)); c.lineTo(b[0] - 9 * Math.cos(ang + .45), b[1] - 9 * Math.sin(ang + .45)); c.closePath(); c.fill(); }
  function text(c, s, x, y, font, color, align) { c.font = font; c.fillStyle = color; c.textAlign = align || "left"; c.textBaseline = "alphabetic"; c.fillText(s, x, y); }
  function fit(c, s, px, weight, family, maxW) { while (px > 9) { c.font = weight + " " + px + "px " + family; if (c.measureText(s).width <= maxW) break; px -= .5; } return weight + " " + px + "px " + family; }

  function drawNode(c, n, lit, rev, t, hits, pid) {
    var on = lit > .02, edge = n.hot ? T.delmk : (n.changed ? T.accent : T.line);
    c.save();
    if (on) { c.shadowColor = al(T.accent, .5 * lit); c.shadowBlur = 20 * lit; }
    rr(c, n.x, n.y, n.w, n.h, 12); c.fillStyle = n.hot ? T.del : T.code; c.fill(); c.restore();
    rr(c, n.x, n.y, n.w, n.h, 12); c.lineWidth = n.changed || n.hot ? 1.6 + lit : 1.2 + lit;
    c.strokeStyle = on ? T.accent : edge; c.stroke();
    if (n.rows && n.rows.length) {
      text(c, n.t, n.x + 14, n.y + 26, fit(c, n.t, 14, "700", MONO, n.w - 28), T.fg);
      if (n.s) text(c, n.s, n.x + 14, n.y + 42, fit(c, n.s, 11.5, "400", MONO, n.w - 28), T.muted);
      var top = n.s ? 50 : 36;
      c.fillStyle = al(T.muted, .25); c.fillRect(n.x + 1, n.y + top, n.w - 2, 1);
      for (var i = 0; i < n.rows.length; i++) {
        var a = Math.min(1, Math.max(0, rev * n.rows.length - i)); if (a <= 0) continue;
        var r = n.rows[i], ch = r.charAt(0), y = n.y + top + 22 + i * 20, col = ch === "?" ? T.delmk : (ch === "+" ? T.addmk : T.fg);
        text(c, r, n.x + 14, y, fit(c, r, 12.5, "400", MONO, n.w - 28), al(col, ch === "?" || ch === "+" ? a : a * .85));
      }
    } else {
      var cy = n.y + n.h / 2;
      text(c, n.t, n.x + n.w / 2, n.s ? cy - 2 : cy + 5, fit(c, n.t, 14, "600", SANS, n.w - 24), T.fg, "center");
      if (n.s) text(c, n.s, n.x + n.w / 2, cy + 18, fit(c, n.s, 11.5, "400", MONO, n.w - 24), T.muted, "center");
    }
    if (n.changed) { c.font = "700 9px " + MONO; var cw = c.measureText("CHANGED").width + 12; c.fillStyle = T.card; rr(c, n.x + n.w - cw - 10, n.y - 8, cw, 16, 8); c.fill(); c.lineWidth = 1; c.strokeStyle = T.accent; c.stroke(); text(c, "CHANGED", n.x + n.w - cw / 2 - 10, n.y + 3.5, "700 9px " + MONO, T.accent, "center"); }
    if (n.badges) {
      var bx = n.x + n.w - 10;
      for (var q = n.badges.length - 1; q >= 0; q--) {
        var sv = n.badges[q][0], num = n.badges[q][1], lab = sv + " #" + num; c.font = "700 10.5px " + MONO;
        var bw = c.measureText(lab).width + 14, cx, cyb = n.y + n.h;
        bx -= bw; cx = bx + bw / 2;
        c.save(); c.translate(cx, cyb); c.fillStyle = T.p[sv] || T.p.P5; rr(c, -bw / 2, -10, bw, 20, 10); c.fill(); c.lineWidth = 2; c.strokeStyle = T.card; c.stroke();
        text(c, lab, 0, 4, "700 10.5px " + MONO, "#fff", "center"); c.restore();
        if (hits) hits.push({ x: bx, y: cyb - 10, w: bw, h: 20, href: "#f-" + pid + "-" + num });
        bx -= 6;
      }
    }
  }

  function total(m) { return m.edges.length * STEP + HOLD; }

  function render(c, m, t, scale, hits, pid) {
    var W = m.w, H = m.h, steps = m.edges.length, tt = t % total(m);
    var s = Math.min(steps, Math.floor(tt / STEP)), fr = s < steps ? (tt - s * STEP) / STEP : 1, hold = tt >= steps * STEP;
    c.setTransform(scale, 0, 0, scale, 0, 0); c.clearRect(0, 0, W, H); c.fillStyle = T.card; c.fillRect(0, 0, W, H);
    c.fillStyle = al(T.muted, .16); for (var gx = 20; gx < W; gx += 40) for (var gy = 20; gy < H - 70; gy += 40) c.fillRect(gx, gy, 1.5, 1.5);
    if (LOGO) { var wh = Math.min(H * .62, 280); logo(c, (W - wh * 172 / 128) / 2, (H - 70 - wh) / 2 + 6, wh, al(T.fg, .055)); }
    if (hits) hits.length = 0;
    var lit = {}, rev = {}, first = {};
    m.nodes.forEach(function (n) { lit[n.id] = 0; rev[n.id] = 1; });
    m.edges.forEach(function (e, i) { [e.a, e.b].forEach(function (k, j) { if (!(k in first)) first[k] = [i, j]; }); });
    m.nodes.forEach(function (n) {
      if (!n.rows || !n.rows.length || !(n.id in first)) return;
      var f0 = first[n.id], i0 = f0[0];
      rev[n.id] = hold || s > i0 ? 1 : (s < i0 ? 0 : (f0[1] === 0 ? 1 : Math.max(0, (fr - .5) * 2)));
    });
    if (!hold) { var e0 = m.edges[s]; [e0.a, e0.b].forEach(function (k, j) { lit[k] = j === 0 ? Math.min(1, fr * 3) : Math.max(0, Math.min(1, (fr - .7) * 3.3)); }); }
    m.edges.forEach(function (e, i) {
      var done = i < s || hold, now = i === s && !hold, hue = e.dash ? T.delmk : T.accent;
      c.save(); c.lineCap = "round"; c.lineJoin = "round"; if (e.dash) c.setLineDash([6, 6]);
      c.strokeStyle = al(T.muted, done || now ? .55 : .35); c.lineWidth = 1.5;
      c.beginPath(); e.p.forEach(function (q, j) { j ? c.lineTo(q[0], q[1]) : c.moveTo(q[0], q[1]); }); c.stroke();
      if (done) trail(c, e.p, 1, al(hue, .7), 2);
      if (now) trail(c, e.p, fr, hue, 2.6);
      c.setLineDash([]); arrow(c, e.p, now ? hue : done ? al(hue, .75) : al(T.muted, .55)); c.restore();
      if (e.lab && plen(e.p).L >= 70 && (done || now)) {
        var mid = at(e.p, .5); c.font = "11px " + MONO; var w = c.measureText(e.lab).width + 14;
        c.fillStyle = T.card; rr(c, mid[0] - w / 2, mid[1] - 9, w, 18, 9); c.fill(); c.strokeStyle = T.line; c.lineWidth = 1; c.stroke();
        text(c, e.lab, mid[0], mid[1] + 4, "11px " + MONO, now ? T.fg : T.muted, "center");
      }
    });
    m.nodes.forEach(function (n) { drawNode(c, n, lit[n.id], rev[n.id], t, hits, pid); });
    if (!hold) { var e = m.edges[s], p = at(e.p, Math.min(1, fr * 1.05)), hue = e.dash ? T.delmk : T.accent; c.save(); c.shadowColor = al(hue, .8); c.shadowBlur = 12; c.fillStyle = hue; c.beginPath(); c.arc(p[0], p[1], 6.5, 0, 6.283); c.fill(); c.restore(); c.fillStyle = "#fff"; c.beginPath(); c.arc(p[0], p[1], 2.4, 0, 6.283); c.fill(); }
    var cap = hold ? "Every step shown. Starting again." : m.edges[s].cap, dotsW = steps * 14 + 10;
    c.fillStyle = T.code; rr(c, 20, H - 52, W - 40, 38, 10); c.fill(); c.strokeStyle = T.line; c.lineWidth = 1; c.stroke();
    for (var i = 0; i < steps; i++) { c.fillStyle = (i < s || hold) ? al(T.accent, .7) : (i === s ? T.accent : al(T.muted, .35)); c.beginPath(); c.arc(W - 40 - (steps - 1 - i) * 14, H - 33, i === s && !hold ? 4.5 : 3.2, 0, 6.283); c.fill(); }
    text(c, cap, 38, H - 28, fit(c, cap, 14, "400", SANS, W - 76 - dotsW), T.fg);
    c.font = "800 15px " + SANS; var nw = c.measureText("AdversaryPR").width;
    text(c, "AdversaryPR", W - 22, 31, "800 15px " + SANS, T.fg, "right");
    logo(c, W - 22 - nw - 10 - 22 * 172 / 128, 12, 22, T.fg);
    if (m.foot) text(c, m.foot, W / 2, H - 62, fit(c, m.foot, 11, "400", MONO, W - 60), T.muted, "center");
  }

  function makeGif(m, say) {
    return new Promise(function (res) {
      var FPS = 15, n = Math.round(total(m) * FPS), sc = Math.min(1, 960 / m.w), gw = Math.round(m.w * sc), gh = Math.round(m.h * sc);
      var off = document.createElement("canvas"); off.width = gw; off.height = gh; var oc = off.getContext("2d"), datas = [], i = 0;
      (function next() {
        var k = 0; while (k < 6 && i < n) { render(oc, m, i / FPS, sc, null, ""); datas.push(oc.getImageData(0, 0, gw, gh)); i++; k++; }
        say("Drawing frames " + i + "/" + n);
        if (i < n) setTimeout(next, 0);
        else setTimeout(function () { say("Encoding"); setTimeout(function () { res(new Blob([GifEncoder.encode(datas, gw, gh, Math.round(100 / FPS))], { type: "image/gif" })); }, 20); }, 0);
      })();
    });
  }

  var players = [], reduce = !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches), exporting = location.hash === "#export", still = exporting || location.hash === "#still";

  function init(box) {
    var data = JSON.parse(box.querySelector(".mapdata").textContent), maps = data.maps, pid = data.pid;
    var cv = box.querySelector("canvas"), ctx = cv.getContext("2d"), tabs = box.querySelector(".mtabs"), msg = box.querySelector(".mmsg"), pp = box.querySelector(".m-pp");
    var P = { box: box, cur: 0, t0: performance.now(), paused: reduce || still, pausedAt: 1e6, visible: true, hits: [], pid: pid, maps: maps, cv: cv, ctx: ctx };
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    function say(s) { msg.textContent = s; }
    function size() { var m = maps[P.cur]; cv.width = Math.round(m.w * dpr); cv.height = Math.round(m.h * dpr); cv.setAttribute("aria-label", m.name + " map, " + m.edges.length + " steps. A text version is below."); }
    function now() { return P.paused ? (P.pausedAt >= 1e5 ? total(maps[P.cur]) - .05 : P.pausedAt) : (performance.now() - P.t0) / 1000; }
    P.draw = function () { render(ctx, maps[P.cur], now(), dpr, P.hits, pid); };
    var sayBox = box.querySelector(".m-say"), lastStep = -1, synth = window.speechSynthesis;
    if (!synth || !window.SpeechSynthesisUtterance) { sayBox.parentNode.hidden = true; sayBox = null; }
    function narrate() {
      if (!sayBox || !sayBox.checked || P.paused) return;
      var m = maps[P.cur], step = Math.floor((now() % total(m)) / STEP);
      if (step === lastStep) return; lastStep = step;
      if (step >= m.edges.length) return;
      synth.cancel(); var u = new SpeechSynthesisUtterance(m.edges[step].cap); u.lang = document.documentElement.lang || "en"; var vo = window.__adversaryVoice && window.__adversaryVoice(); if (vo) { u.voice = vo; u.lang = vo.lang; } synth.speak(u);
    }
    if (sayBox) sayBox.onchange = function () { lastStep = -1; if (!sayBox.checked) synth.cancel(); };
    P.tick = function () { P.draw(); narrate(); };
    function sel(i) { lastStep = -1; if (synth) synth.cancel(); P.cur = i; P.t0 = performance.now(); if (!P.paused) P.pausedAt = 0; else P.pausedAt = 1e6; size(); [].forEach.call(tabs.children, function (b, j) { b.setAttribute("aria-selected", j === i); }); P.draw(); }
    maps.forEach(function (m, i) { var b = document.createElement("button"); b.type = "button"; b.className = "mtab"; b.setAttribute("role", "tab"); b.textContent = m.name; b.onclick = function () { sel(i); }; tabs.appendChild(b); });
    function label() { pp.textContent = P.paused ? "Play" : "Pause"; }
    pp.onclick = function () { if (P.paused) { P.t0 = performance.now() - (P.pausedAt >= 1e5 ? 0 : P.pausedAt) * 1000; P.paused = false; } else { P.pausedAt = now(); P.paused = true; } label(); };
    box.querySelector(".m-rs").onclick = function () { lastStep = -1; P.t0 = performance.now(); P.paused = false; label(); };
    function busy(on) { [].forEach.call(box.querySelectorAll(".m-gif,.m-cpy"), function (b) { b.disabled = on; }); }
    function dl(blob) { var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "adversarypr-pr" + pid + "-" + maps[P.cur].key + ".gif"; document.body.appendChild(a); a.click(); a.remove(); }
    box.querySelector(".m-gif").onclick = function () { busy(true); makeGif(maps[P.cur], say).then(function (b) { dl(b); say("Saved " + Math.round(b.size / 1024) + " KB"); busy(false); }); };
    box.querySelector(".m-cpy").onclick = function () {
      busy(true); makeGif(maps[P.cur], say).then(function (b) {
        function ok() { say("Copied the GIF"); busy(false); } function no() { dl(b); say("This browser can't copy a GIF, so it was saved instead."); busy(false); }
        try { navigator.clipboard.write([new ClipboardItem({ "image/gif": b })]).then(ok, no); } catch (e) { no(); }
      });
    };
    box.querySelector(".m-png").onclick = function () {
      P.draw(); cv.toBlob(function (b) { try { navigator.clipboard.write([new ClipboardItem({ "image/png": b })]).then(function () { say("Copied this frame"); }, function () { say("Copy was blocked"); }); } catch (e) { say("Copying isn't supported here"); } });
    };
    function pos(e) { var r = cv.getBoundingClientRect(), m = maps[P.cur]; return [(e.clientX - r.left) * m.w / r.width, (e.clientY - r.top) * m.h / r.height]; }
    function hit(e) { var q = pos(e); for (var i = 0; i < P.hits.length; i++) { var h = P.hits[i]; if (q[0] >= h.x && q[0] <= h.x + h.w && q[1] >= h.y && q[1] <= h.y + h.h) return h; } return null; }
    cv.addEventListener("mousemove", function (e) { cv.style.cursor = hit(e) ? "pointer" : "default"; });
    cv.addEventListener("click", function (e) { var h = hit(e); if (h && document.querySelector(h.href)) location.hash = h.href; });
    if ("IntersectionObserver" in window) new IntersectionObserver(function (es) { P.visible = es[0].isIntersecting; }).observe(cv);
    label(); sel(0); players.push(P);
  }

  function buildPrint() {
    players.forEach(function (P) {
      if (P.box.querySelector(".mprint")) return;
      var d = document.createElement("div"); d.className = "mprint";
      P.maps.forEach(function (m) {
        var off = document.createElement("canvas"), sc = 1.5; off.width = Math.round(m.w * sc); off.height = Math.round(m.h * sc);
        render(off.getContext("2d"), m, total(m) - .05, sc, null, ""); var img = document.createElement("img"); img.src = off.toDataURL("image/png"); img.alt = m.name + " map"; d.appendChild(img);
      });
      P.box.appendChild(d);
    });
  }
  function dropPrint() { [].forEach.call(document.querySelectorAll(".mprint"), function (d) { d.remove(); }); }

  function start() {
    [].forEach.call(document.querySelectorAll(".maps"), init);
    if (!players.length) return;
    (function loop() { if (!document.hidden) players.forEach(function (P) { if (P.visible && !P.paused) P.tick(); }); requestAnimationFrame(loop); })();
    if (window.matchMedia) { var mq = matchMedia("(prefers-color-scheme: dark)"); (mq.addEventListener ? mq.addEventListener("change", readTheme) : mq.addListener(readTheme)); }
    window.addEventListener("beforeprint", function () { readTheme(); buildPrint(); }); window.addEventListener("afterprint", dropPrint);
    if (exporting) buildPrint();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
