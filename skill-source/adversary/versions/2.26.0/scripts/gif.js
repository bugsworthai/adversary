/* Tiny GIF89a encoder (no dependencies). frames: array of Uint8Array palette indices. */
(function (root) {
  function medianCut(samples, n) {
    var boxes = [samples];
    while (boxes.length < n) {
      var bi = -1, best = 0;
      for (var i = 0; i < boxes.length; i++) if (boxes[i].length > best && boxes[i].length > 1) { best = boxes[i].length; bi = i; }
      if (bi < 0) break;
      var b = boxes[bi], mn = [255, 255, 255], mx = [0, 0, 0];
      b.forEach(function (p) { for (var c = 0; c < 3; c++) { if (p[c] < mn[c]) mn[c] = p[c]; if (p[c] > mx[c]) mx[c] = p[c]; } });
      var ch = 0, rg = -1;
      for (var c = 0; c < 3; c++) if (mx[c] - mn[c] > rg) { rg = mx[c] - mn[c]; ch = c; }
      b.sort(function (x, y) { return x[ch] - y[ch]; });
      var h = b.length >> 1;
      boxes.splice(bi, 1, b.slice(0, h), b.slice(h));
    }
    return boxes.map(function (b) {
      var s = [0, 0, 0]; b.forEach(function (p) { s[0] += p[0]; s[1] += p[1]; s[2] += p[2]; });
      return [Math.round(s[0] / b.length), Math.round(s[1] / b.length), Math.round(s[2] / b.length)];
    });
  }
  function makePalette(imageDatas) {
    var samples = [], seen = {};
    imageDatas.forEach(function (d) {
      var px = d.data;
      for (var i = 0; i < px.length; i += 4 * 7) {
        var k = (px[i] >> 3) << 10 | (px[i + 1] >> 3) << 5 | (px[i + 2] >> 3);
        seen[k] = (seen[k] || 0) + 1;
        if (seen[k] <= 40) samples.push([px[i], px[i + 1], px[i + 2]]);
      }
    });
    var pal = medianCut(samples, 256);
    while (pal.length < 256) pal.push([0, 0, 0]);
    return pal;
  }
  function indexFrame(data, pal, cache) {
    var px = data.data, out = new Uint8Array(px.length >> 2);
    for (var i = 0, j = 0; i < px.length; i += 4, j++) {
      var r = px[i], g = px[i + 1], b = px[i + 2], key = r << 16 | g << 8 | b, v = cache[key];
      if (v === undefined) {
        var bd = 1e9, bk = 0;
        for (var k = 0; k < 256; k++) { var dr = pal[k][0] - r, dg = pal[k][1] - g, db = pal[k][2] - b, d = dr * dr + dg * dg + db * db; if (d < bd) { bd = d; bk = k; } }
        cache[key] = v = bk;
      }
      out[j] = v;
    }
    return out;
  }
  function lzw(idx, out) {
    var minCode = 8, clear = 256, eoi = 257, size = 9, next = 258, dict = new Map(), cur = 0, curBits = 0, block = [];
    function flush() { if (block.length) { out.push(block.length); for (var i = 0; i < block.length; i++) out.push(block[i]); block = []; } }
    function emit(code, sz) { cur |= code << curBits; curBits += sz; while (curBits >= 8) { block.push(cur & 255); cur >>= 8; curBits -= 8; if (block.length === 255) flush(); } }
    out.push(minCode);
    emit(clear, size);
    var prefix = idx[0];
    for (var i = 1; i < idx.length; i++) {
      var k = idx[i], key = prefix << 8 | k, hit = dict.get(key);
      if (hit !== undefined) { prefix = hit; continue; }
      emit(prefix, size);
      if (next < 4096) { dict.set(key, next++); if (next > (1 << size) && size < 12) size++; }
      else { emit(clear, size); dict.clear(); next = 258; size = 9; }
      prefix = k;
    }
    emit(prefix, size);
    if (next >= (1 << size) && size < 12) size++;
    emit(eoi, size);
    if (curBits > 0) block.push(cur & 255);
    flush();
    out.push(0);
  }
  function encode(imageDatas, w, h, delayCs) {
    var pal = makePalette(imageDatas), cache = {}, out = [];
    function w16(v) { out.push(v & 255, v >> 8 & 255); }
    "GIF89a".split("").forEach(function (c) { out.push(c.charCodeAt(0)); });
    w16(w); w16(h); out.push(0xF7, 0, 0);
    pal.forEach(function (c) { out.push(c[0], c[1], c[2]); });
    out.push(0x21, 0xFF, 11); "NETSCAPE2.0".split("").forEach(function (c) { out.push(c.charCodeAt(0)); }); out.push(3, 1, 0, 0, 0);
    var prev = null;
    imageDatas.forEach(function (d) {
      var idx = indexFrame(d, pal, cache), x0 = 0, y0 = 0, bw = w, bh = h, sub = idx;
      if (prev) {
        var minx = w, miny = h, maxx = -1, maxy = -1;
        for (var y = 0; y < h; y++) for (var x = 0; x < w; x++) if (idx[y * w + x] !== prev[y * w + x]) { if (x < minx) minx = x; if (x > maxx) maxx = x; if (y < miny) miny = y; if (y > maxy) maxy = y; }
        if (maxx < 0) { minx = miny = maxx = maxy = 0; }
        x0 = minx; y0 = miny; bw = maxx - minx + 1; bh = maxy - miny + 1;
        sub = new Uint8Array(bw * bh);
        for (var yy = 0; yy < bh; yy++) for (var xx = 0; xx < bw; xx++) sub[yy * bw + xx] = idx[(y0 + yy) * w + x0 + xx];
      }
      prev = idx;
      out.push(0x21, 0xF9, 4, 0x04); w16(delayCs); out.push(0, 0);
      out.push(0x2C); w16(x0); w16(y0); w16(bw); w16(bh); out.push(0);
      lzw(sub, out);
    });
    out.push(0x3B);
    return new Uint8Array(out);
  }
  root.GifEncoder = { encode: encode };
  if (typeof module !== "undefined") module.exports = root.GifEncoder;
})(typeof window !== "undefined" ? window : globalThis);
