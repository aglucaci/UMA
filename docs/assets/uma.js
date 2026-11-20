// UMA shared code: page frame, data loading, labels and small renderers.
// Data files are built by `uma build` from one UMDB release (see uma/build.py).
(function(){
  const DATA = "./data/";
  const esc = (v) => (v ?? "").toString().replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (n) => (n == null || n === "" ? "–" : new Intl.NumberFormat("en-US").format(n));
  const param = (k) => new URLSearchParams(location.search).get(k) || "";

  const STATUS = { supported: "Supported", not_supported: "Not supported", inconclusive: "Inconclusive",
                   descriptive: "Descriptive", skipped: "Skipped", not_run: "Not run", planned: "Planned" };
  const STATUS_ORDER = ["supported", "not_supported", "inconclusive", "descriptive", "skipped", "not_run", "planned"];
  const STATUS_COLOR = { supported: "var(--ok)", not_supported: "var(--no)", inconclusive: "var(--mid)",
                         descriptive: "var(--info)", skipped: "var(--off)", not_run: "var(--off)", planned: "var(--line)" };
  const TRACK = { catalog: "Catalog", ecology: "Ecology", roadmap: "Roadmap" };
  const TIER = { confirmed_urban: "Confirmed urban", probable_urban: "Probable urban", uncertain: "Uncertain",
                 non_urban: "Not urban", non_environmental: "Not environmental" };
  const HABITAT = { municipal_wastewater: "Municipal wastewater", air_dust: "Air and dust", built_environment: "Built environment",
                    water_drainage: "Urban water and drainage", soil_greenspace: "Soil and green space", transit: "Transit",
                    surfaces_infrastructure: "Surfaces and infrastructure" };
  const CONTINENT = { AF: "Africa", AS: "Asia", EU: "Europe", NA: "North America", OC: "Oceania", SA: "South America", AN: "Antarctica" };
  const statusPill = (s) => `<span class="status s-${esc(s)}">${esc(STATUS[s] || s)}</span>`;
  const tierPill = (t) => t ? `<span class="tier ${esc(t)}">${esc(TIER[t] || t)}</span>` : "";

  // ------------------------------------------------------------ data
  // Every file is fetched with the release's build time, so a rebuilt site never mixes cached files.
  const cache = new Map();
  let stamp = null;
  function releaseInfo(){
    if (!stamp) stamp = fetch(DATA + "release.json", { cache: "no-cache" }).then((r) => r.ok ? r.json() : {}).catch(() => ({}));
    return stamp;
  }
  function getJSON(name){
    if (!cache.has(name)){
      cache.set(name, releaseInfo().then((rel) => fetch(`${DATA}${name}?v=${encodeURIComponent(rel.built_utc || "")}`))
        .then((r) => { if (!r.ok) throw new Error(`${name}: ${r.status}`); return r.json(); })
        .catch((e) => { cache.delete(name); throw e; }));
    }
    return cache.get(name);
  }
  const rows = (cols, data) => (data || []).map((r) => Object.fromEntries(cols.map((c, i) => [c, r[i]])));
  const safeName = (acc) => (acc || "_none").replace(/[^A-Za-z0-9_.-]/g, "_");
  const ixBucket = (acc) => { const d = (acc || "").replace(/\D/g, ""); return d ? d.slice(-2).padStart(2, "0") : "xx"; };
  async function study(acc){
    const d = await getJSON(`p/${safeName(acc)}.json`);
    return { ...d, sampleRows: rows(d.sample_cols, d.samples), runRows: rows(d.run_cols, d.runs) };
  }
  async function lookup(acc){            // BioSample -> [studies]; run -> study
    const ix = await getJSON(`ix/${ixBucket(acc)}.json`).catch(() => ({}));
    return ix[acc] ?? null;
  }
  function accessionKind(t){
    if (/^PRJ(NA|EB|DB)\d+$/i.test(t)) return "study";
    if (/^SAM(N|EA|D)\d+$/i.test(t)) return "sample";
    if (/^[SED]RR\d+$/i.test(t)) return "run";
    return null;
  }
  const href = {
    study: (a) => `./study.html?acc=${encodeURIComponent(a)}`,
    sample: (a) => `./sample.html?acc=${encodeURIComponent(a)}`,
    run: (a) => `./run.html?acc=${encodeURIComponent(a)}`,
    place: (id) => `./place.html?id=${encodeURIComponent(id)}`,
    country: (iso) => `./place.html?country=${encodeURIComponent(iso)}`,
    finding: (id) => `./findings.html?id=${encodeURIComponent(id)}`,
    search: (q) => `./search.html?q=${encodeURIComponent(q)}`,
  };
  async function go(text){
    const t = (text || "").trim();
    const kind = accessionKind(t);
    if (kind === "study") return location.assign(href.study(t.toUpperCase()));
    if (kind && await lookup(t.toUpperCase())) return location.assign(href[kind](t.toUpperCase()));
    if (/^[CH]\d{1,2}$/i.test(t)) return location.assign(href.finding(t.toUpperCase()));
    location.assign(href.search(t));
  }

  // ------------------------------------------------------------ frame
  const NAV = [["index", "Overview", "./index.html"], ["findings", "Findings", "./findings.html"],
               ["search", "Search", "./search.html"], ["about", "About", "./about.html"]];
  function frame(active){
    const top = document.createElement("header");
    top.className = "top";
    top.innerHTML = `<div class="wrap">
        <a class="brand" href="./index.html">UMA <small>Urban Microbiome Database releases</small></a>
        <nav class="nav" aria-label="Main">${NAV.map(([k, l, h]) => `<a href="${h}" class="${k === active ? "on" : ""}">${l}</a>`).join("")}</nav>
        <form class="topsearch" role="search"><input type="search" name="q" placeholder="Accession, study, place…" aria-label="Search"></form>
        <span class="rel" data-rel></span></div>`;
    document.body.prepend(top);
    top.querySelector("form").addEventListener("submit", (e) => { e.preventDefault(); go(e.target.q.value); });
    const foot = document.createElement("footer");
    foot.innerHTML = `<div class="wrap"><p data-relfoot></p>
      <p>UMA shows one versioned UMDB release. Catalog: <a href="https://github.com/aglucaci/UMDB">UMDB</a> (live, unreleased catalog at <a href="https://aglucaci.github.io/UMDB/">aglucaci.github.io/UMDB</a>) · analyses: <a href="https://github.com/aglucaci/STRIGA">STRIGA</a> · site: <a href="https://github.com/aglucaci/UMA">UMA</a>.</p>
      <p>UMDB curation CC BY-NC-SA 4.0; sequence data and submitter metadata remain under the INSDC policies of their archives; places from GeoNames (CC BY 4.0).</p></div>`;
    document.body.append(foot);
    releaseInfo().then((r) => {
      if (!r.version) return;
      const doi = r.doi ? ` · DOI <a href="https://doi.org/${esc(r.doi)}">${esc(r.doi)}</a>` : "";
      top.querySelector("[data-rel]").innerHTML = `Release <a href="${esc(r.url)}">${esc(r.version)}</a>`;
      foot.querySelector("[data-relfoot]").innerHTML = `Showing <a href="${esc(r.url)}">UMDB release ${esc(r.version)}</a>, catalog built ${esc((r.database_built_utc || "").slice(0, 10))}${doi}${r.analysis && r.analysis.pipeline ? `; findings by STRIGA ${esc(r.analysis.pipeline.version)}` : ""}.`;
    });
  }

  // ------------------------------------------------------------ renderers
  function bars(items, opts){
    opts = opts || {};
    const max = Math.max(1, ...items.map((d) => d.value));
    return items.slice(0, opts.limit || 10).map((d) => `<div class="bar"><span class="lab" title="${esc(d.label)}">${d.href ? `<a href="${esc(d.href)}">${esc(d.label)}</a>` : esc(d.label)}</span>
      <span class="track"><span class="fill" style="width:${(100 * d.value / max).toFixed(1)}%"></span></span><span class="num small">${fmt(d.value)}</span></div>`).join("");
  }
  // A paged table: columns [{key, label, num?, render?}], rows of objects.
  function table(el, cols, data, opts){
    opts = opts || {};
    const size = opts.pageSize || 50;
    let page = 0;
    function draw(){
      const pages = Math.max(1, Math.ceil(data.length / size));
      page = Math.min(page, pages - 1);
      const slice = data.slice(page * size, page * size + size);
      el.innerHTML = data.length ? `<div class="tablewrap"><table><thead><tr>${cols.map((c) => `<th class="${c.num ? "num" : ""}">${esc(c.label)}</th>`).join("")}</tr></thead>
        <tbody>${slice.map((r) => `<tr>${cols.map((c) => `<td class="${c.num ? "num" : ""}">${c.render ? c.render(r) : c.num ? fmt(r[c.key]) : esc(r[c.key])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
        ${pages > 1 ? `<div class="pager"><button class="btn" data-p="-1" ${page ? "" : "disabled"}>Previous</button><span>${fmt(page * size + 1)}–${fmt(Math.min(data.length, page * size + size))} of ${fmt(data.length)}</span><button class="btn" data-p="1" ${page < pages - 1 ? "" : "disabled"}>Next</button></div>` : ""}`
        : `<p class="muted">${esc(opts.empty || "Nothing to show.")}</p>`;
      el.querySelectorAll("[data-p]").forEach((b) => b.onclick = () => { page += Number(b.dataset.p); draw(); });
    }
    draw();
  }
  function parseTSV(text){
    const lines = text.replace(/\r/g, "").split("\n").filter((l) => l.length);
    const head = (lines.shift() || "").split("\t");
    return { head, rows: lines.map((l) => l.split("\t")) };
  }
  function download(name, text, type){
    const url = URL.createObjectURL(new Blob([text], { type: type || "text/plain" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: name });
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000);
  }
  function toCSV(data, cols){
    const q = (v) => { const s = Array.isArray(v) ? v.join(";") : (v ?? "").toString(); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
    return [cols.join(","), ...data.map((r) => cols.map((c) => q(r[c])).join(","))].join("\n") + "\n";
  }
  const humanBases = (b) => !b ? "–" : b >= 1e12 ? `${(b / 1e12).toFixed(2)} Tbp` : b >= 1e9 ? `${(b / 1e9).toFixed(2)} Gbp` : b >= 1e6 ? `${(b / 1e6).toFixed(1)} Mbp` : `${fmt(b)} bp`;
  const setTitle = (t) => { document.title = `${t} — UMA`; };
  const fail = (el, msg) => { el.innerHTML = `<div class="notice">${esc(msg)}</div>`; };

  window.UMA = { esc, fmt, param, STATUS, STATUS_ORDER, STATUS_COLOR, TRACK, TIER, HABITAT, CONTINENT, statusPill, tierPill,
                 releaseInfo, getJSON, rows, study, lookup, accessionKind, href, go, frame, bars, table, parseTSV,
                 download, toCSV, humanBases, setTitle, fail, ixBucket, safeName };
})();
