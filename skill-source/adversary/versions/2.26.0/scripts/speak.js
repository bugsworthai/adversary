/* Reads a PR's summary aloud, one sentence at a time, with the browser's own speech (no network,
   nothing leaves the page). Play, Pause, Stop and a speed setting. The text stays on the page. */
(function () {
  var synth = window.speechSynthesis, active = null, chosen = "", KEY = "adversarypr-voice";
  var NOVELTY = /^(Albert|Bad News|Bahh|Bells|Boing|Bubbles|Cellos|Good News|Jester|Organ|Superstar|Trinoids|Whisper|Wobble|Zarvox|Fred|Junior|Ralph|Kathy|Eddy|Flo|Grandma|Grandpa|Reed|Rocko|Sandy|Shelley)\b/;
  try { chosen = localStorage.getItem(KEY) || ""; } catch (e) {}
  function lang() { return (document.documentElement.lang || "en").slice(0, 2).toLowerCase(); }
  // Natural-sounding voices usually say so in their name; the plainer built-in ones come last.
  function score(v) {
    var n = v.name || "", sc = 0;
    if (/premium|enhanced|neural|natural/i.test(n)) sc += 4;
    if (/^(Samantha|Ava|Allison|Zoe|Serena|Daniel|Karen|Moira|Tessa|Aria|Jenny|Guy|Libby|Ryan|Sonia)\b/i.test(n)) sc += 2;
    if (v.localService) sc += 1;
    return sc;
  }
  function voices() {
    var all = synth ? synth.getVoices() : [];
    return all.filter(function (v) { return (v.lang || "").slice(0, 2).toLowerCase() === lang() && !NOVELTY.test(v.name); })
      .map(function (v, i) { return { v: v, i: i, s: score(v) }; })
      .sort(function (a, b) { return b.s - a.s || a.i - b.i; }).map(function (x) { return x.v; });
  }
  // Only a voice that runs on this device is picked for you. An online voice sends the text to its
  // provider, so it is used only if you choose it.
  function pick() {
    var list = voices(), mine = list.filter(function (v) { return v.name === chosen; })[0];
    return mine || list.filter(function (v) { return v.localService; })[0] || null;
  }
  window.__adversaryVoice = pick;
  function init(box) {
    var spans = [].slice.call(box.querySelectorAll(".ls")), bar = box.querySelector(".lbar"), note = box.querySelector(".lnote");
    if (!synth || !window.SpeechSynthesisUtterance) { bar.hidden = true; note.hidden = false; return; }
    var sel = box.querySelector(".l-voice"), vnote = box.querySelector(".lvnote");
    function fill() {
      var list = voices(); if (!list.length) { sel.parentNode.hidden = true; return; }
      var cur = pick(), loc = list.filter(function (v) { return v.localService; }), net = list.filter(function (v) { return !v.localService; });
      function opts(arr, label) { return arr.length ? '<optgroup label="' + label + '">' + arr.map(function (v) { return '<option value="' + v.name.replace(/"/g, "&quot;") + '">' + v.name.replace(/</g, "&lt;") + "</option>"; }).join("") + "</optgroup>" : ""; }
      sel.innerHTML = opts(loc, "On this device") + opts(net, "Online (sends the text to the voice provider)");
      if (cur) sel.value = cur.name; note2();
    }
    function note2() { var v = pick(); vnote.textContent = v && !v.localService ? "This voice is online: the text is sent to its provider." : ""; }
    sel.onchange = function () { chosen = sel.value; try { localStorage.setItem(KEY, chosen); } catch (e) {} [].forEach.call(document.querySelectorAll(".l-voice"), function (o) { o.value = chosen; }); note2(); if (playing) { halt(false); playing = true; label(); say(i); } };
    fill(); if (synth.addEventListener) synth.addEventListener("voiceschanged", fill); else synth.onvoiceschanged = fill;
    var play = box.querySelector(".l-play"), stop = box.querySelector(".l-stop"), rate = box.querySelector(".l-rate"), msg = box.querySelector(".lmsg");
    var i = 0, playing = false, gen = 0, me = { stop: function () { halt(true); } };
    function mark(k) { spans.forEach(function (s, j) { s.classList.toggle("now", j === k); }); if (k >= 0 && spans[k].scrollIntoView && !box.contains(document.activeElement)) { /* keep the page where it is */ } }
    function label() { play.textContent = playing ? "Pause" : (i > 0 ? "Resume" : "Play"); play.setAttribute("aria-pressed", playing); }
    function halt(reset) { gen++; playing = false; synth.cancel(); if (reset) { i = 0; mark(-1); msg.textContent = ""; } label(); }
    function say(k) {
      if (k >= spans.length) { halt(true); msg.textContent = "Finished"; return; }
      i = k; mark(k); msg.textContent = "Sentence " + (k + 1) + " of " + spans.length;
      var my = gen, u = new SpeechSynthesisUtterance(spans[k].textContent); u.rate = +rate.value || 1; u.lang = document.documentElement.lang || "en"; var vo = pick(); if (vo) { u.voice = vo; u.lang = vo.lang; }
      u.onend = function () { if (playing && my === gen) say(k + 1); };
      u.onerror = function () { if (my === gen && playing) { halt(false); msg.textContent = "Speech stopped"; } };
      synth.speak(u);
    }
    play.onclick = function () {
      if (playing) { halt(false); msg.textContent = "Paused"; return; }
      if (active && active !== me) active.stop();
      active = me; synth.cancel(); gen++; playing = true; label(); say(i);
    };
    stop.onclick = function () { halt(true); };
    spans.forEach(function (s, k) { s.addEventListener("click", function () { if (active && active !== me) active.stop(); active = me; synth.cancel(); gen++; playing = true; label(); say(k); }); });
    label();
  }
  function start() {
    [].forEach.call(document.querySelectorAll(".listen"), init);
    window.addEventListener("pagehide", function () { if (synth) synth.cancel(); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
