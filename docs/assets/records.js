// Record pages: study, BioSample, run, place and country, as frozen in the release.
(function(){
  const U = window.UMA; const { esc, fmt } = U;
  const kind = document.body.dataset.page;
  U.frame("search");
  const main = document.getElementById("main");
  const kv = (pairs) => `<dl class="kv">${pairs.filter(([, v]) => v !== null && v !== undefined && v !== "").map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("")}</dl>`;
  const placeLink = (s) => s.place_id ? `<a href="${U.href.place(s.place_id)}">${esc(s.place)}</a>` : "";
  const where = (s) => [placeLink(s), esc(s.region || ""), s.country ? `<a href="${U.href.country(s.country)}">${esc(s.country)}</a>` : ""].filter(Boolean).join(", ");
  const studyLink = (a) => `<a class="mono" href="${U.href.study(a)}">${esc(a)}</a>`;
  const ncbi = (a) => `<a href="https://www.ncbi.nlm.nih.gov/${/^PRJ/.test(a) ? "bioproject" : /^SAM/.test(a) ? "biosample" : "sra"}/${encodeURIComponent(a)}">NCBI</a>`;
  const counter = (arr) => { const m = new Map(); arr.forEach((v) => { if (v) m.set(v, (m.get(v) || 0) + 1); }); return [...m.entries()].sort((a, b) => b[1] - a[1]); };

  async function studyPage(){
    const acc = U.param("acc").toUpperCase();
    let d;
    try { d = await U.study(acc); } catch { return U.fail(main, `${acc || "This study"} is not in this release.`); }
    U.setTitle(`${acc}: ${d.title || "Study"}`);
    const S = d.sampleRows, R = d.runRows;
    const urban = S.filter((s) => s.tier === "confirmed_urban" || s.tier === "probable_urban").length;
    const years = R.map((r) => (r.release_date || "").slice(0, 4)).filter(Boolean).sort();
    main.innerHTML = `<p class="small"><a href="./search.html">← Search</a></p>
      <div class="hero"><p class="mono faint" style="margin:0">BioProject ${esc(acc)} · ${ncbi(acc)}</p><h1>${esc(d.title || acc)}</h1>
        ${d.description ? `<p class="lead" style="font-size:15px">${esc(d.description.length > 900 ? d.description.slice(0, 900) + "…" : d.description)}</p>` : ""}</div>
      <div class="grid g4">${[[S.length, "BioSamples"], [urban, "urban BioSamples"], [R.length, "runs"], [R.reduce((a, r) => a + (r.bases || 0), 0), "sequenced"]]
        .map(([n, l], i) => `<div class="card stat"><div class="n">${i === 3 ? esc(U.humanBases(n)) : fmt(n)}</div><div class="l">${l}</div></div>`).join("")}</div>
      <section class="grid g3">
        <div class="card"><h3>Study</h3>${kv([["Centre", esc(d.center)], ["Data type", esc(d.data_type)], ["Submitted", esc(d.submission_date)],
          ["Runs released", years.length ? esc(years[0] === years[years.length - 1] ? years[0] : `${years[0]}–${years[years.length - 1]}`) : ""]])}</div>
        <div class="card"><h3>Eligibility</h3>${U.bars(counter(S.map((s) => s.tier)).map(([k, v]) => ({ label: U.TIER[k] || k, value: v })))}</div>
        <div class="card"><h3>Places</h3>${U.bars(counter(S.map((s) => s.place_id ? `${s.place_id}|${s.place}` : s.country ? `c|${s.country}` : "")).map(([k, v]) => {
          const [id, name] = k.split("|"); return { label: id === "c" ? `${name} (country only)` : name, value: v, href: id === "c" ? U.href.country(name) : U.href.place(id) }; }), { limit: 8 }) || '<p class="muted small">No validated location.</p>'}</div>
      </section>
      <section><div class="section-head"><h2>BioSamples</h2><button class="btn" id="dls">CSV</button></div><div id="samples"></div></section>
      <section><div class="section-head"><h2>Runs</h2><button class="btn" id="dlr">CSV</button></div><div id="runs"></div></section>`;
    U.table(document.getElementById("samples"), [
      { label: "BioSample", render: (s) => `<a class="mono" href="${U.href.sample(s.accession)}">${esc(s.accession)}</a><div class="small muted">${esc(s.title || "")}</div>` },
      { label: "Tier", render: (s) => U.tierPill(s.tier) }, { label: "Habitat", render: (s) => esc(U.HABITAT[s.context] || s.context || "") },
      { label: "Place", render: where }, { key: "collection_date", label: "Collected", render: (s) => esc(s.collection_date || s.collection_year || "") },
    ], S, { pageSize: 25 });
    U.table(document.getElementById("runs"), [
      { label: "Run", render: (r) => `<a class="mono" href="${U.href.run(r.accession)}">${esc(r.accession)}</a>` },
      { label: "BioSample", render: (r) => r.sample ? `<a class="mono" href="${U.href.sample(r.sample)}">${esc(r.sample)}</a>` : "" },
      { key: "assay", label: "Assay" }, { key: "instrument", label: "Instrument" }, { key: "layout", label: "Layout" },
      { label: "Bases", num: true, render: (r) => esc(U.humanBases(r.bases)) }, { key: "release_date", label: "Released" },
    ], R, { pageSize: 25 });
    document.getElementById("dls").onclick = () => U.download(`${acc}_biosamples.csv`, U.toCSV(S, d.sample_cols), "text/csv");
    document.getElementById("dlr").onclick = () => U.download(`${acc}_runs.csv`, U.toCSV(R, d.run_cols), "text/csv");
  }

  async function samplePage(){
    const acc = U.param("acc").toUpperCase();
    const projs = await U.lookup(acc);
    if (!projs) return U.fail(main, `${acc || "This BioSample"} is not in this release.`);
    const list = Array.isArray(projs) ? projs : [projs];
    const d = await U.study(list[0]);
    const s = d.sampleRows.find((x) => x.accession === acc);
    if (!s) return U.fail(main, `${acc} could not be read from ${list[0]}.`);
    const runs = (await Promise.all(list.map((p) => (p === list[0] ? Promise.resolve(d) : U.study(p)))))
      .flatMap((x) => x.runRows.filter((r) => r.sample === acc));
    U.setTitle(`${acc}: ${s.title || "BioSample"}`);
    main.innerHTML = `<p class="small"><a href="${U.href.study(list[0])}">← ${esc(list[0])}</a></p>
      <div class="hero"><p class="mono faint" style="margin:0">BioSample ${esc(acc)} · ${ncbi(acc)}</p><h1>${esc(s.title || acc)}</h1><p>${U.tierPill(s.tier)} ${s.context ? `<span class="tier">${esc(U.HABITAT[s.context] || s.context)}</span>` : ""}</p></div>
      <div class="grid g2">
        <div class="card"><h3>Location</h3>${kv([["Accepted", where(s) || '<span class="muted">not resolved</span>'], ["Validation", esc(s.location_status)],
          ["Submitted text", esc(s.submitted_location)], ["Coordinates", s.lat != null ? esc(`${s.lat}, ${s.lon}`) : ""]])}
          <p class="small muted">Accepted places come from GeoNames, matched to the submitted text and coordinates; only verified or probable matches are shown as a place.</p></div>
        <div class="card"><h3>Sample</h3>${kv([["Collected", esc(s.collection_date || s.collection_year)], ["Isolation source", esc(s.isolation_source)],
          ["Broad scale", esc(s.env_broad_scale)], ["Local scale", esc(s.env_local_scale)], ["Medium", esc(s.env_medium)],
          ["Studies", list.map(studyLink).join(", ")]])}</div>
      </div>
      ${s.eligibility_reason ? `<section class="card"><h3>Why this tier</h3><p class="small">${esc(s.eligibility_reason)}</p></section>` : ""}
      <section><h2>Runs</h2><div id="runs"></div></section>`;
    U.table(document.getElementById("runs"), [
      { label: "Run", render: (r) => `<a class="mono" href="${U.href.run(r.accession)}">${esc(r.accession)}</a>` },
      { key: "assay", label: "Assay" }, { key: "strategy", label: "Strategy" }, { key: "instrument", label: "Instrument" },
      { label: "Bases", num: true, render: (r) => esc(U.humanBases(r.bases)) }, { key: "release_date", label: "Released" },
    ], runs);
  }

  async function runPage(){
    const acc = U.param("acc").toUpperCase();
    const proj = await U.lookup(acc);
    if (!proj) return U.fail(main, `${acc || "This run"} is not in this release.`);
    const d = await U.study(proj);
    const r = d.runRows.find((x) => x.accession === acc);
    if (!r) return U.fail(main, `${acc} could not be read from ${proj}.`);
    const s = d.sampleRows.find((x) => x.accession === r.sample) || {};
    U.setTitle(`${acc}: run`);
    main.innerHTML = `<p class="small"><a href="${U.href.study(proj)}">← ${esc(proj)}</a></p>
      <div class="hero"><p class="mono faint" style="margin:0">Run ${esc(acc)} · ${ncbi(acc)}</p><h1>${esc(r.assay || "Sequencing run")} · ${esc(r.instrument || r.platform || "")}</h1></div>
      <div class="grid g2">
        <div class="card"><h3>Run</h3>${kv([["Experiment", esc(r.experiment)], ["Assay class", esc(r.assay)], ["Library", esc([r.strategy, r.source, r.layout].filter(Boolean).join(" · "))],
          ["Platform", esc([r.platform, r.instrument].filter(Boolean).join(" · "))], ["Size", esc(`${U.humanBases(r.bases)}, ${fmt(r.spots)} spots`)],
          ["Released", esc(r.release_date)], ["Download", r.download_url ? `<a href="${esc(r.download_url)}">SRA file</a> · <span class="mono small">fasterq-dump ${esc(acc)}</span>` : `<span class="mono small">fasterq-dump ${esc(acc)}</span>`]])}</div>
        <div class="card"><h3>From</h3>${kv([["BioSample", r.sample ? `<a class="mono" href="${U.href.sample(r.sample)}">${esc(r.sample)}</a> ${U.tierPill(s.tier)}` : ""],
          ["Habitat", esc(U.HABITAT[s.context] || s.context)], ["Place", where(s)], ["Study", `${studyLink(proj)} ${esc(d.title || "")}`]])}</div>
      </div>`;
  }

  async function placePage(){
    const id = U.param("id"), iso = U.param("country").toUpperCase();
    const [P, S] = await Promise.all([U.getJSON("places.json"), U.getJSON("studies.json")]);
    const places = U.rows(P.place_cols, P.places), countries = U.rows(P.country_cols, P.countries);
    const studies = U.rows(S.cols, S.rows);
    const byAcc = Object.fromEntries(studies.map((s) => [s.accession, s]));
    const cname = Object.fromEntries(countries.map((c) => [c.iso2, c.name]));
    const studyCols = [
      { label: "Study", render: (s) => `<a class="mono" href="${U.href.study(s.accession)}">${esc(s.accession)}</a><div>${esc(s.title || "")}</div>` },
      { label: "Habitats", render: (s) => esc(s.habitats.map((h) => U.HABITAT[h] || h).join(", ")) },
      { label: "Assays", render: (s) => esc(s.assays.join(", ")) },
      { key: "samples", label: "BioSamples (study)", num: true }, { key: "runs", label: "Runs", num: true }];
    if (id){
      const p = places.find((x) => String(x.id) === id);
      if (!p) return U.fail(main, "No samples from this place in this release.");
      U.setTitle(`${p.name}, ${cname[p.country] || p.country}`);
      const st = p.studies.map((a) => byAcc[a]).filter(Boolean);
      main.innerHTML = `<p class="small"><a href="${U.href.country(p.country)}">← ${esc(cname[p.country] || p.country)}</a></p>
        <div class="hero"><p class="faint mono" style="margin:0">GeoNames <a href="https://www.geonames.org/${encodeURIComponent(p.id)}">${esc(p.id)}</a></p>
          <h1>${esc(p.name)}</h1><p class="lead">${esc([p.region, cname[p.country]].filter(Boolean).join(", "))}${p.population ? ` · population ${fmt(p.population)}` : ""}</p></div>
        <div class="grid g3">${[[p.samples, "BioSamples"], [p.urban_samples, "urban BioSamples"], [st.length, "studies"]].map(([n, l]) => `<div class="card stat"><div class="n">${fmt(n)}</div><div class="l">${l}</div></div>`).join("")}</div>
        <section><h2>Studies with samples here</h2><div id="st"></div></section>`;
      U.table(document.getElementById("st"), studyCols, st);
    } else {
      const c = countries.find((x) => x.iso2 === iso);
      if (!c) return U.fail(main, "No samples from this country in this release.");
      U.setTitle(c.name);
      const pl = places.filter((p) => p.country === iso);
      const st = studies.filter((s) => s.countries.includes(iso));
      main.innerHTML = `<p class="small"><a href="./search.html">← Search</a></p>
        <div class="hero"><h1>${esc(c.name)}</h1><p class="lead">${esc(U.CONTINENT[c.continent] || c.continent || "")}</p></div>
        <div class="grid g3">${[[c.samples, "BioSamples with a validated location here"], [c.urban_samples, "urban BioSamples"], [c.studies, "studies"]].map(([n, l]) => `<div class="card stat"><div class="n">${fmt(n)}</div><div class="l">${l}</div></div>`).join("")}</div>
        <section class="card"><h2>Places</h2>${U.bars(pl.map((p) => ({ label: p.name, value: p.samples, href: U.href.place(p.id) })), { limit: 15 }) || '<p class="muted">No sample is located more precisely than the country.</p>'}
          ${pl.length > 15 ? `<p class="small muted">${fmt(pl.length)} places in all.</p>` : ""}</section>
        <section><h2>Studies</h2><p class="small muted">Studies whose BioSamples are mostly located here (up to three countries are indexed per study).</p><div id="st"></div></section>`;
      U.table(document.getElementById("st"), studyCols, st);
    }
  }

  const pages = { study: studyPage, sample: samplePage, run: runPage, place: placePage };
  (pages[kind] || (() => U.fail(main, "Unknown page.")))().catch((e) => U.fail(main, `Could not load this record (${e.message}).`));
})();
