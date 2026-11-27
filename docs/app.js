/* An Island That Makes Room — Roatán crowding interactive.
   Data: data/crowd_data.js (built by scripts/build_hexes.py). No network requests. */
(function () {
  "use strict";

  const D = window.CROWD_DATA;
  if (!D) { document.getElementById("subtitle").textContent = "Data file missing — run scripts/build_hexes.py."; return; }

  const MAX_TOWER_M = 3500;     // tallest possible tower (3 ships, max capacity)
  const ANIM_MS = 600;
  const fmt = new Intl.NumberFormat("en-US");
  const feats = D.hexes.features;
  const nT = D.terminals.length;
  const S = D.ships;

  // --- text from the data file (textContent only, never innerHTML) ---
  document.getElementById("title").textContent = D.title;
  document.getElementById("subtitle").textContent = D.subtitle;
  document.documentElement.style.setProperty("--res", D.colours.residents);
  document.documentElement.style.setProperty("--vis", D.colours.visitors);
  const notes = document.getElementById("notes");
  const v = D.visitors;
  const assumption = (D.terminal_params || []).map(t =>
    `Assumption — ${t.name}: ${Math.round(t.share_near * 100)}% of passengers stay around the terminal, fading over ~${t.decay_km} km, none beyond ${t.max_km} km.`
  ).join(" ") + " Ship buttons: ship 1 docks at the first terminal, ship 2 at the second, ship 3 at the first again.";
  const big = D.biggest_call ? `Largest single call in the data: ${D.biggest_call.ship}, ${fmt.format(D.biggest_call.passengers)} passengers.` : "";
  [...D.notes, assumption, big, "Month menu: that month's passengers at each terminal divided by the days in the month (no daily dates in the data).", `"Near the ports" = hexagons within ${v.near_port_km} km of a terminal with a ship in port.`,
   `Hexagons are ${D.cell_size_m} m across. Island outline: SINIT 2016 via OCHA HDX.`]
    .filter(Boolean).forEach(t => { const li = document.createElement("li"); li.textContent = t; notes.appendChild(li); });
  // Economy: estimated spending, always shown with its caveat and reference.
  const E = D.economy;
  function safeLink(url, text) {
    const a = document.createElement("a");
    a.textContent = text;
    if (/^https:\/\//.test(url || "")) { a.href = url; a.target = "_blank"; a.rel = "noopener noreferrer"; }
    return a;
  }
  if (E && E.spend_per_passenger_usd) {
    document.getElementById("econ-label").textContent = `${E.label} (≈ US$${E.spend_per_passenger_usd.toFixed(2)} per passenger)`;
    const n = document.getElementById("econ-note");
    n.append(document.createTextNode(E.caveat + " Source: "), safeLink(E.reference_url, E.reference));
    document.getElementById("econ-box").hidden = false;
    [E.jobs_note].filter(Boolean).forEach(t => {
      const li = document.createElement("li");
      li.append(document.createTextNode(t + " Source: "), safeLink(E.reference_url, "BREA/FCCA 2024"));
      notes.appendChild(li);
    });
  }
  if (D.scope_note) {
    const sc = document.getElementById("scope"); sc.textContent = D.scope_note; sc.hidden = false;
  }
  const w = document.getElementById("placeholder");
  if (D.residents_mode !== "population_raster") {
    w.textContent = "Residents are spread by land area for now (placeholder) — a population grid will place them where people actually live.";
  } else {
    const tot = D.residents_raster_total ? ` The grid itself puts about ${fmt.format(D.residents_raster_total)} people on the island; the map uses ${fmt.format(Math.round(D.residents_total))}.` : "";
    w.textContent = (D.residents_note || "Residents placed with a population grid.") + tot;
    w.className = "scope";
  }
  w.hidden = false;

  // --- state ---
  const slider = document.getElementById("capacity");
  slider.min = S.capacity_min; slider.max = S.capacity_max; slider.step = S.capacity_step; slider.value = S.default_capacity;
  const state = { ships: 0, capacity: S.default_capacity, month: null };
  const months = D.months || [];
  const monthSel = document.getElementById("month");
  months.slice().reverse().forEach(m => {
    const o = document.createElement("option"); o.value = String(months.indexOf(m)); o.textContent = m.label;
    monthSel.appendChild(o);
  });
  let shown = feats.map(() => 0);          // visitors currently drawn per hexagon

  function visitorsFor(ships, capacity) {
    return feats.map(f => {
      let total = 0;
      for (let s = 0; s < ships; s++) total += capacity * f.properties.share[s % nT];
      return total;
    });
  }

  function visitorsForMonth(m) {
    return feats.map(f => f.properties.share.reduce((acc, s, t) => acc + s * m.passengers[t] / m.days, 0));
  }
  function currentVisitors() {
    return state.month === null ? visitorsFor(state.ships, state.capacity) : visitorsForMonth(months[state.month]);
  }

  // Fixed height scale so towers are comparable across all states (scenarios and real months).
  const worst = visitorsFor(S.max_ships, S.capacity_max);
  let maxPeople = Math.max(...feats.map((f, i) => f.properties.res + worst[i]));
  months.forEach(m => { const vm = visitorsForMonth(m); feats.forEach((f, i) => { maxPeople = Math.max(maxPeople, f.properties.res + vm[i]); }); });
  const M_PER_PERSON = MAX_TOWER_M / maxPeople;
  const peoplePerKm = Math.round(1000 / M_PER_PERSON / 10) * 10;
  const towerNote = `Tower height: 1 km ≈ ${fmt.format(peoplePerKm)} people (same scale in every view)`;
  document.getElementById("scale-note").textContent = towerNote;

  function geojsonWith(vis) {
    return {
      type: "FeatureCollection",
      features: feats.map((f, i) => ({
        type: "Feature", geometry: f.geometry,
        properties: {
          id: f.properties.id,
          res: f.properties.res, vis: vis[i],
          h_res: f.properties.res * M_PER_PERSON,
          h_top: (f.properties.res + vis[i]) * M_PER_PERSON,
        },
      })),
    };
  }

  // --- statistics ---
  function updateStats(vis) {
    const resTot = D.residents_total;
    const visTot = vis.reduce((a, b) => a + b, 0);
    document.getElementById("s-total").textContent = fmt.format(Math.round(resTot + visTot));
    document.getElementById("s-per100").textContent = (visTot / resTot * 100).toFixed(1);

    const active = state.month === null
      ? [...Array(nT).keys()].filter(t => state.ships > t)
      : [...Array(nT).keys()].filter(t => months[state.month].passengers[t] > 0);
    const terms = active.length ? active : [...Array(nT).keys()];
    let rNear = 0, vNear = 0;
    feats.forEach((f, i) => { if (terms.some(t => f.properties.near[t])) { rNear += f.properties.res; vNear += vis[i]; } });
    document.getElementById("s-near").textContent = vNear < 1
      ? "Everyone you meet lives here"
      : `1 in ${Math.max(1, Math.round((rNear + vNear) / vNear))} people you meet is a visitor`;

    if (E && E.spend_per_passenger_usd) {
      const usd = Math.round(visTot * E.spend_per_passenger_usd / 1000) * 1000;
      document.getElementById("s-spend").textContent = visTot < 1 ? "No cruise visitors — US$0" : `≈ US$${fmt.format(usd)} that day`;
    }
    let best = 0, bi = 0;
    feats.forEach((f, i) => { const p = f.properties.res + vis[i]; if (p > best) { best = p; bi = i; } });
    const share = best ? vis[bi] / best * 100 : 0;
    document.getElementById("s-busiest").textContent =
      `${fmt.format(Math.round(best))} people · ${share.toFixed(0)}% visitors`;
  }

  // --- Tanaka view: people-density surface with illuminated contours ---
  const TK = D.tanaka, GR = D.grid;
  const GW = GR.width, GH = GR.height;
  const GRID_CORNERS = [[GR.west, GR.north], [GR.west + GW * GR.dlon, GR.north],
                        [GR.west + GW * GR.dlon, GR.north - GH * GR.dlat], [GR.west, GR.north - GH * GR.dlat]];
  const gidx = Int32Array.from(GR.idx);
  const resArr = feats.map(f => f.properties.res), landArr = feats.map(f => f.properties.land_km2);
  const THR = TK.thresholds_per_km2;
  const hexRGB = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const C_RES = hexRGB(D.colours.residents), C_VIS = hexRGB(D.colours.visitors), C_LOW = hexRGB(D.colours.tanaka_low);
  const az = TK.light_azimuth_deg * Math.PI / 180, LX = Math.sin(az), LY = Math.cos(az);
  const UP = 3;                                     // fill image is 3x the grid resolution

  function blankPng() { const c = document.createElement("canvas"); c.width = c.height = 1; return c.toDataURL("image/png"); }

  function gaussKernel(sigma) {
    const r = Math.ceil(3 * sigma), k = [];
    let s = 0;
    for (let i = -r; i <= r; i++) { const v = Math.exp(-0.5 * (i / sigma) ** 2); k.push(v); s += v; }
    return k.map(v => v / s);
  }
  const KER = gaussKernel(TK.blur_sigma_cells), KR = (KER.length - 1) / 2;
  function blur(a) {
    const tmp = new Float64Array(a.length), out = new Float64Array(a.length);
    for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
      let s = 0; for (let k = -KR; k <= KR; k++) { const xx = x + k; if (xx >= 0 && xx < GW) s += a[y * GW + xx] * KER[k + KR]; }
      tmp[y * GW + x] = s;
    }
    for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
      let s = 0; for (let k = -KR; k <= KR; k++) { const yy = y + k; if (yy >= 0 && yy < GH) s += tmp[yy * GW + x] * KER[k + KR]; }
      out[y * GW + x] = s;
    }
    return out;
  }
  function densityOf(perHex) {
    const d = new Float64Array(GW * GH);
    for (let i = 0; i < d.length; i++) { const h = gidx[i]; if (h >= 0) d[i] = perHex[h] / landArr[h]; }
    return d;
  }
  function sample(a, gx, gy) {            // bilinear, gx/gy in cell units (cell centres at +0.5)
    const x = Math.min(Math.max(gx - 0.5, 0), GW - 1), y = Math.min(Math.max(gy - 0.5, 0), GH - 1);
    const x0 = Math.floor(x), y0 = Math.floor(y), x1 = Math.min(x0 + 1, GW - 1), y1 = Math.min(y0 + 1, GH - 1);
    const fx = x - x0, fy = y - y0;
    return (a[y0 * GW + x0] * (1 - fx) + a[y0 * GW + x1] * fx) * (1 - fy) + (a[y1 * GW + x0] * (1 - fx) + a[y1 * GW + x1] * fx) * fy;
  }
  const lonOf = x => GR.west + x * GR.dlon, latOf = y => GR.north - y * GR.dlat;

  function drawTanaka(vis) {
    const tot = blur(densityOf(resArr.map((r, i) => r + vis[i])));
    const vd = blur(densityOf(vis));
    // fill: banded by density, hue by visitor share
    const cw = GW * UP, ch = GH * UP, cv = document.createElement("canvas");
    cv.width = cw; cv.height = ch;
    const ctx = cv.getContext("2d"), img = ctx.createImageData(cw, ch), px = img.data;
    for (let y = 0; y < ch; y++) for (let x = 0; x < cw; x++) {
      const gx = (x + 0.5) / UP, gy = (y + 0.5) / UP;
      const t = sample(tot, gx, gy);
      let lvl = 0; while (lvl < THR.length && t >= THR[lvl]) lvl++;
      const o = (y * cw + x) * 4;
      if (!lvl) { px[o + 3] = 0; continue; }
      const sh = Math.min(1, (t > 1e-9 ? sample(vd, gx, gy) / t : 0) / TK.share_full_coral);
      const k = 0.25 + 0.75 * lvl / THR.length;
      for (let c = 0; c < 3; c++) {
        const hue = C_RES[c] * (1 - sh) + C_VIS[c] * sh;
        px[o + c] = Math.round(C_LOW[c] * (1 - k) + hue * k);
      }
      px[o + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    // keep the surface off the sea: cut the image along the real coastline (smooth edge)
    if (TK.clip_to_land) {
    ctx.globalCompositeOperation = "destination-in";
    ctx.beginPath();
    const lg = D.land.geometry, polys = lg.type === "MultiPolygon" ? lg.coordinates : [lg.coordinates];
    polys.forEach(poly => poly.forEach(ring => ring.forEach(([lon, lat], k) => {
      const X = (lon - GR.west) / GR.dlon * UP, Y = (GR.north - lat) / GR.dlat * UP;
      k ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y);
    })));
    ctx.fill("evenodd");
    ctx.globalCompositeOperation = "source-over";
    }
    map.getSource("tk-fill").updateImage({ url: cv.toDataURL("image/png"), coordinates: GRID_CORNERS });

    // illuminated contour lines, split into runs of similar shade
    const contours = d3.contours().size([GW, GH]).thresholds(THR)(Array.from(tot));
    const out = [];
    contours.forEach(cn => cn.coordinates.forEach(poly => poly.forEach(ring => {
      let run = null, runBin = -1;
      for (let i = 1; i < ring.length; i++) {
        const [x0, y0] = ring[i - 1], [x1, y1] = ring[i];
        const dx = x1 - x0, dyN = -(y1 - y0), len = Math.hypot(dx, dyN);
        if (!len) continue;
        let nx = dyN / len, ny = -dx / len;                       // a normal (east, north)
        const mx = (x0 + x1) / 2, my = (y0 + y1) / 2;
        const sea = TK.clip_to_land && gidx[Math.min(GH - 1, Math.max(0, Math.floor(my))) * GW + Math.min(GW - 1, Math.max(0, Math.floor(mx)))] < 0;
        if (sea) { if (run && run.length > 1) out.push({ type: "Feature", properties: { s: runBin / 7 }, geometry: { type: "LineString", coordinates: run } }); run = null; runBin = -1; continue; }
        if (sample(tot, mx + nx * 0.5, my - ny * 0.5) > sample(tot, mx - nx * 0.5, my + ny * 0.5)) { nx = -nx; ny = -ny; }
        const bin = Math.round(((nx * LX + ny * LY) + 1) / 2 * 7);
        const p0 = [lonOf(x0), latOf(y0)], p1 = [lonOf(x1), latOf(y1)];
        if (bin === runBin && run) run.push(p1);
        else {
          if (run && run.length > 1) out.push({ type: "Feature", properties: { s: runBin / 7 }, geometry: { type: "LineString", coordinates: run } });
          run = [p0, p1]; runBin = bin;
        }
      }
      if (run && run.length > 1) out.push({ type: "Feature", properties: { s: runBin / 7 }, geometry: { type: "LineString", coordinates: run } });
    })));
    map.getSource("tk-lines").setData({ type: "FeatureCollection", features: out });
  }

  let view = "towers";
  const ramp = document.getElementById("ramp");
  ramp.style.background = `linear-gradient(to right, ${D.colours.residents}, ${D.colours.visitors})`;
  function setView(v) {
    view = v;
    document.querySelectorAll(".view button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.view === v)));
    const tk = v === "tanaka";
    ["res", "vis"].forEach(l => map.setLayoutProperty(l, "visibility", tk ? "none" : "visible"));
    ["tk-fill", "tk-lines"].forEach(l => map.setLayoutProperty(l, "visibility", tk ? "visible" : "none"));
    ramp.hidden = !tk;
    document.getElementById("scale-note").textContent = tk
      ? `Contours: ${fmt.format(THR[0])}–${fmt.format(THR[THR.length - 1])} people/km² (same levels in every view) · colour: residents → cruise visitors`
      : towerNote;
    map.easeTo({ pitch: tk ? 0 : 58, duration: 700 });
    render(true);
  }

  // --- map ---
  const map = new maplibregl.Map({
    container: "map",
    attributionControl: false,
    maxPitch: 70,
    style: {
      version: 8,
      sources: {
        land: { type: "geojson", data: D.land },
        hexes: { type: "geojson", data: geojsonWith(shown) },
        "tk-fill": { type: "image", url: blankPng(), coordinates: GRID_CORNERS },
        "tk-lines": { type: "geojson", data: { type: "FeatureCollection", features: [] } },
      },
      layers: [
        { id: "sea", type: "background", paint: { "background-color": D.colours.sea } },
        { id: "land", type: "fill", source: "land", paint: { "fill-color": D.colours.land, "fill-outline-color": D.colours.land_outline } },
        { id: "tk-fill", type: "raster", source: "tk-fill", layout: { visibility: "none" },
          paint: { "raster-opacity": 1, "raster-resampling": "linear", "raster-fade-duration": 0 } },
        { id: "tk-lines", type: "line", source: "tk-lines", layout: { visibility: "none", "line-cap": "round", "line-join": "round" },
          paint: { "line-width": TK.line_width, "line-color": ["interpolate", ["linear"], ["get", "s"], 0, D.colours.tanaka_shadow, 1, D.colours.tanaka_light] } },
        { id: "res", type: "fill-extrusion", source: "hexes",
          paint: { "fill-extrusion-color": D.colours.residents, "fill-extrusion-base": 0,
                   "fill-extrusion-height": ["get", "h_res"], "fill-extrusion-opacity": 0.95 } },
        { id: "vis", type: "fill-extrusion", source: "hexes",
          filter: [">", ["get", "vis"], 0.5],   // no visitors -> no coral cap
          paint: { "fill-extrusion-color": D.colours.visitors, "fill-extrusion-base": ["get", "h_res"],
                   "fill-extrusion-height": ["get", "h_top"], "fill-extrusion-opacity": 0.95 } },
      ],
    },
  });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
  map.addControl(new maplibregl.AttributionControl({ compact: true,
    customAttribution: "Outline: SINIT/OCHA HDX · Residents: INE · MapLibre" }),
    window.innerWidth <= 640 ? "top-left" : "bottom-right");

  // Keep the island clear of the panel: left of it on wide screens, above it on phones.
  function panelPadding() {
    const p = document.getElementById("panel").getBoundingClientRect();
    const narrow = window.innerWidth <= 640;
    return narrow
      ? { top: 20, right: 20, left: 20, bottom: Math.round(p.height) + 10 }
      : { top: 30, right: 60, bottom: 30, left: Math.round(p.right) + 20 };
  }

  function homeView(animate) {
    const cam = map.cameraForBounds(D.bounds, { padding: panelPadding(), bearing: -25 });
    if (!cam) return;
    // tilted 3D view needs extra room for the far end of the island
    const tilt = view === "tanaka" ? 0 : 58;
    const opts = { center: cam.center, zoom: cam.zoom - (tilt ? 0.45 : 0), bearing: -25, pitch: tilt };
    animate ? map.easeTo({ ...opts, duration: 800 }) : map.jumpTo(opts);
  }

  let ready = false;
  map.on("load", () => {
    ready = true;
    homeView(false);
    // Terminal names sit out in the sea (south of the shore) with a thin leader line, so they
    // never cover the towers. The westernmost name extends left, the others right, so the
    // names and lines never cross each other.
    const LEADER = 40;
    const westLon = Math.min(...D.terminals.map(t => t.lon));
    D.terminals.forEach(t => {
      const el = document.createElement("div");
      el.className = "terminal-marker" + (t.lon === westLon ? " west" : " east");
      el.setAttribute("aria-label", t.name);
      const line = document.createElement("span");
      line.className = "leader"; line.style.height = `${LEADER}px`;
      const lab = document.createElement("div");
      lab.className = "terminal-label"; lab.textContent = t.name;
      lab.style.top = `${12 + LEADER}px`;
      el.append(line, lab);
      new maplibregl.Marker({ element: el }).setLngLat([t.lon, t.lat]).addTo(map);
    });
    render(true);
  });

  // tap / click a hexagon
  map.on("click", e => {
    const f = map.queryRenderedFeatures(e.point, { layers: ["vis", "res"] })[0];
    if (!f) return;
    const p = f.properties;
    const box = document.createElement("div");
    const line = (label, val) => { const d = document.createElement("div"); d.textContent = `${label}: ${fmt.format(Math.round(val))}`; box.appendChild(d); };
    line("Residents", p.res); line("Visitors", p.vis);
    new maplibregl.Popup({ closeButton: true }).setLngLat(e.lngLat).setDOMContent(box).addTo(map);
  });
  ["res", "vis"].forEach(l => {
    map.on("mouseenter", l, () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", l, () => { map.getCanvas().style.cursor = ""; });
  });

  // --- transitions ---
  let raf = null;
  function render(instant) {
    const target = currentVisitors();
    const note = document.getElementById("day-note");
    if (state.month === null) { note.hidden = true; }
    else {
      const m = months[state.month];
      const calls = m.calls.reduce((a, b) => a + b, 0), pax = m.passengers.reduce((a, b) => a + b, 0);
      note.textContent = `${m.label}: ${fmt.format(calls)} ship calls and ${fmt.format(pax)} passengers in the month — on an average day about ${(calls / m.days).toFixed(1)} ships and ${fmt.format(Math.round(pax / m.days))} visitors.`;
      note.hidden = false;
    }
    updateStats(target);
    const src = map.getSource("hexes");
    if (!src) return;
    if (view === "tanaka") { shown = target; src.setData(geojsonWith(shown)); drawTanaka(target); return; }
    const from = shown.slice();
    if (raf) cancelAnimationFrame(raf);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (instant || reduce) { shown = target; src.setData(geojsonWith(shown)); return; }
    const t0 = performance.now();
    const step = now => {
      const k = Math.min(1, (now - t0) / ANIM_MS);
      const e = 1 - Math.pow(1 - k, 3);
      shown = from.map((a, i) => a + (target[i] - a) * e);
      src.setData(geojsonWith(shown));
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
  }

  document.querySelectorAll(".ships button").forEach(b => {
    b.addEventListener("click", () => {
      state.ships = Number(b.dataset.ships);
      state.month = null; monthSel.value = "";
      document.querySelectorAll(".ships button").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
      render(false);
    });
  });
  const capOut = document.getElementById("capacity-value");
  const showCap = () => { capOut.textContent = fmt.format(state.capacity); };
  slider.addEventListener("input", () => { state.capacity = Number(slider.value); showCap(); if (state.month === null) render(true); });
  monthSel.addEventListener("change", () => {
    state.month = monthSel.value === "" ? null : Number(monthSel.value);
    if (state.month !== null) document.querySelectorAll(".ships button").forEach(x => x.setAttribute("aria-pressed", "false"));
    else { state.ships = 0; document.querySelector('.ships button[data-ships="0"]').setAttribute("aria-pressed", "true"); }
    render(false);
  });
  showCap();
  document.getElementById("reset").addEventListener("click", () => homeView(true));
  document.querySelectorAll(".view button").forEach(b => b.addEventListener("click", () => { if (ready) setView(b.dataset.view); }));
  updateStats(shown);
})();
