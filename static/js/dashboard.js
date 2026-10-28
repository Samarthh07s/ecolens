/* Dashboard: search, geolocation, live data, score ring, cards,
   recommendations, best time window, alert banners and noise. */
(function () {
  "use strict";
  var E = window.Eco, el = E.el, $ = function (id) { return document.getElementById(id); };

  var boot = JSON.parse($("bootData").textContent);
  var RING_C = 2 * Math.PI * 84;
  var LOC_KEY = "ecolens-location", PROFILE_KEY = "ecolens-profile";

  var state = {
    location: readSavedLocation() || boot["default"],
    profile: E.store(PROFILE_KEY) || "general",
    payload: null,
    loading: false,
    dismissed: {}
  };

  function readSavedLocation() {
    try {
      var l = JSON.parse(E.store(LOC_KEY) || "null");
      if (l && typeof l.lat === "number" && typeof l.lon === "number" && typeof l.name === "string") return l;
    } catch (e) { /* ignore */ }
    return null;
  }

  // ------------------------------------------------------------------ load
  function load() {
    if (state.loading) return;
    state.loading = true;
    var refresh = $("btnRefresh");
    refresh.disabled = true; refresh.classList.add("loading");
    document.body.classList.add("loading");
    $("locName").textContent = state.location.name;

    var q = new URLSearchParams({
      lat: state.location.lat, lon: state.location.lon,
      name: state.location.name, profile: state.profile
    });
    E.fetchJSON("/api/current?" + q.toString(), { timeout: 40000 })
      .then(function (data) {
        hideError();
        render(data);
      })
      .catch(function (err) { showError(err.message); })
      .finally(function () {
        state.loading = false;
        refresh.disabled = false; refresh.classList.remove("loading");
        document.body.classList.remove("loading");
      });
  }

  function showError(msg) {
    var box = $("errorBox");
    box.textContent = "";
    box.appendChild(el("strong", { text: "Couldn't load data. " }));
    box.appendChild(document.createTextNode(msg + " "));
    box.appendChild(el("button", { "class": "link-btn", type: "button", text: "Try again", onclick: load }));
    box.hidden = false;
  }
  function hideError() { $("errorBox").hidden = true; }

  // ---------------------------------------------------------------- render
  function render(d) {
    state.payload = d;
    var c = d.current;
    var reportLink = $("reportLink");
    if (reportLink) {
      reportLink.href = "/report?" + new URLSearchParams({
        lat: d.location.lat, lon: d.location.lon, name: d.location.name, profile: state.profile
      }).toString();
    }

    // Header
    $("locName").textContent = d.location.name;
    $("locCoords").textContent = d.location.lat.toFixed(3) + "°, " + d.location.lon.toFixed(3) + "°";
    var t = $("lastUpdated");
    t.textContent = E.localTime(d.updated_at, true) + " (" + E.timeAgo(d.updated_at) + ")";
    t.setAttribute("datetime", d.updated_at);
    var sb = $("statusBadge");
    sb.hidden = false;
    if (d.offline) {
      sb.className = "status status-offline";
      sb.textContent = "Offline – showing cached data from " + E.localTime(d.updated_at, true);
      sb.title = d.offline_reason || "";
    } else {
      sb.className = "status status-live";
      sb.textContent = "Live";
      sb.title = "";
    }

    renderAlerts(d.alerts || []);
    renderScore(d.analysis.score);
    renderPatterns(d.analysis.patterns || []);

    // Cards
    setField("aqi", c.aqi, 0); setField("pm25", c.pm25, 1); setField("pm10", c.pm10, 1);
    setField("temperature", c.temperature, 1); setField("feels_like", c.feels_like, 1);
    setField("heat_index", c.heat_index, 1);
    setField("humidity", c.humidity, 0); setField("wind", c.wind, 0);
    setField("uv", c.uv, 1); setField("uv_max", c.uv_max_today, 1);
    setCard("cardAqi", d.bands.aqi, "aqi");
    setCard("cardTemp", d.bands.temperature, "temperature");
    setCard("cardHum", d.bands.humidity, "humidity");
    setCard("cardUv", d.bands.uv, "uv");
    setPin("aqi", c.aqi, 500);
    setPin("uv", c.uv, 14);
    var hb = document.querySelector('[data-bar="humidity"]');
    hb.style.width = Math.max(0, Math.min(100, c.humidity || 0)) + "%";
    hb.parentElement.parentElement.dataset.level = d.bands.humidity.level;

    renderNoise(c.noise, d.noise_meta);
    renderRecommendations(d.recommendations);
    renderOutlook(d.upcoming || [], d.recommendations.best_window);
    E.updateAlertCount();
  }

  function setField(name, value, digits) {
    document.querySelectorAll('[data-f="' + name + '"]').forEach(function (n) {
      n.textContent = E.fmt(value, digits);
    });
  }

  function setCard(id, band, key) {
    var card = $(id);
    card.dataset.level = band.level;
    var b = card.querySelector(".badge");
    b.dataset.level = band.level;
    b.textContent = band.label;
    var adv = card.querySelector('[data-advice="' + key + '"]');
    if (adv) adv.textContent = band.advice || "";
  }

  function setPin(name, value, max) {
    var pin = document.querySelector('[data-pin="' + name + '"]');
    if (!pin) return;
    var pct = value === null || value === undefined ? 0 : Math.max(0, Math.min(1, value / max)) * 100;
    pin.style.left = "calc(" + pct.toFixed(1) + "% - 2px)";
  }

  function renderScore(s) {
    var panel = document.querySelector(".score-panel");
    panel.dataset.level = s.level;
    var ring = $("ringValue");
    ring.style.strokeDasharray = RING_C.toFixed(2);
    var pct = s.score === null ? 0 : s.score / 100;
    // next frame so the CSS transition animates from the previous value
    requestAnimationFrame(function () { ring.style.strokeDashoffset = (RING_C * (1 - pct)).toFixed(2); });
    animateNumber($("scoreValue"), s.score);
    $("scoreLabel").textContent = s.label;

    var note = s.noise_included
      ? "Includes all 5 factors (noise measured)."
      : "Noise not measured — weights renormalised over 4 factors.";
    if (s.capped) {
      note += " Capped by " + niceName(s.limiting_factor) + " (weakest-link rule).";
    }
    $("scoreNote").textContent = note;
  }

  function niceName(m) {
    return { aqi: "air quality", heat_index: "heat", uv: "UV", humidity: "humidity", noise: "noise" }[m] || m;
  }

  function animateNumber(node, target) {
    if (target === null || target === undefined) { node.textContent = "—"; return; }
    var from = parseInt(node.textContent, 10);
    if (isNaN(from)) from = 0;
    var start = performance.now(), dur = 800;
    function step(now) {
      var p = Math.min(1, (now - start) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      node.textContent = String(Math.round(from + (target - from) * eased));
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function renderPatterns(list) {
    var ul = $("patternList");
    ul.textContent = "";
    if (!list.length) {
      ul.appendChild(el("li", { "class": "pattern ok", dataset: { level: "good" } }, [
        el("div", { "class": "p-title", text: "No risky patterns detected" }),
        el("div", { "class": "p-detail", text: "Heat, pollution build-up, UV and noise are all below their warning rules." })
      ]));
      return;
    }
    list.forEach(function (p) {
      ul.appendChild(el("li", { "class": "pattern", dataset: { level: p.severity } }, [
        el("div", { "class": "p-title" }, [
          p.title,
          el("span", { "class": "badge", dataset: { level: p.severity }, text: p.severity === "high" ? "High" : "Moderate" })
        ]),
        el("div", { "class": "p-detail", text: p.detail })
      ]));
    });
  }

  // ---------------------------------------------------------------- alerts
  function renderAlerts(alerts) {
    var stack = $("alertStack");
    stack.textContent = "";
    var key = state.location.lat + "," + state.location.lon;
    alerts.forEach(function (a) {
      if (a.is_new) E.notify("EcoLens: " + a.title, a.action);
      var id = key + ":" + a.kind;
      if (state.dismissed[id]) return;
      stack.appendChild(el("div", { "class": "alert-banner", role: "alert", dataset: { level: a.severity } }, [
        el("div", {}, [
          el("div", { "class": "sev", text: a.severity === "critical" ? "Critical" : "Warning" }),
          el("div", { "class": "title", text: a.title }),
          el("div", { "class": "action", text: a.action })
        ]),
        el("button", {
          "class": "dismiss", type: "button", "aria-label": "Dismiss alert", text: "×",
          onclick: function (ev) { state.dismissed[id] = true; ev.currentTarget.parentElement.remove(); }
        })
      ]));
    });
  }

  // ------------------------------------------------------- recommendations
  function renderRecommendations(r) {
    var v = $("verdict");
    v.textContent = r.verdict;
    v.dataset.level = r.level;
    $("verdictSummary").textContent = r.summary;
    $("profileNote").textContent = r.profile_label + " · " + r.profile_note;

    var reasons = $("reasonList");
    reasons.textContent = "";
    (r.reasons || []).forEach(function (txt) { reasons.appendChild(el("li", { text: txt })); });

    var ul = $("actionList");
    ul.textContent = "";
    r.actions.forEach(function (a) {
      ul.appendChild(el("li", {}, [
        el("span", { "class": "a-icon" }, [E.icon(a.icon)]),
        el("div", {}, [
          el("div", { "class": "a-title", text: a.title }),
          el("div", { "class": "a-text", text: a.text })
        ])
      ]));
    });

    var box = $("bestWindow");
    box.textContent = "";
    var b = r.best_window;
    if (!b) {
      box.appendChild(el("p", { "class": "muted", text: "Not enough forecast data to pick a window." }));
      return;
    }
    box.appendChild(el("div", { "class": "best-day", text: b.day }));
    box.appendChild(el("div", { "class": "best-time", text: b.start + " – " + b.end }));
    box.appendChild(el("div", { "class": "best-stats" }, [
      el("span", { "class": "chip", dataset: { level: aqiLevel(b.avg_aqi) }, text: "AQI ~" + b.avg_aqi }),
      el("span", { "class": "chip", dataset: { level: uvLevel(b.avg_uv) }, text: "UV ~" + E.fmt(b.avg_uv, 1) }),
      el("span", { "class": "chip", dataset: { level: b.avg_heat_index > 32 ? "usg" : "good" }, text: "Feels ~" + E.fmt(b.avg_heat_index, 0) + "°C" })
    ]));
  }

  function aqiLevel(a) {
    if (a === null || a === undefined) return "none";
    if (a <= 50) return "good"; if (a <= 100) return "moderate"; if (a <= 150) return "usg";
    if (a <= 200) return "unhealthy"; if (a <= 300) return "very-unhealthy"; return "hazardous";
  }
  function uvLevel(u) {
    if (u === null || u === undefined) return "none";
    if (u < 3) return "good"; if (u < 6) return "moderate"; if (u < 8) return "usg";
    if (u < 11) return "unhealthy"; return "very-unhealthy";
  }

  function renderOutlook(hours, best) {
    var box = $("outlook");
    box.textContent = "";
    var axis = box.nextElementSibling;
    if (axis && axis.classList.contains("outlook-axis")) axis.remove();
    if (!hours.length) return;
    var max = Math.max.apply(null, hours.map(function (h) { return h.aqi || 0; }).concat([100]));
    var bestStart = best ? best.start_local : null;
    var bestIdx = -1;
    hours.forEach(function (h, i) { if (h.time_local === bestStart) bestIdx = i; });
    hours.forEach(function (h, i) {
      var bar = el("div", {
        "class": "ob" + (bestIdx >= 0 && i >= bestIdx && i < bestIdx + 2 ? " best" : ""),
        dataset: { level: aqiLevel(h.aqi) },
        title: h.time_local.slice(11, 16) + " · AQI " + E.fmt(h.aqi) + " · UV " + E.fmt(h.uv, 1) + " · " + E.fmt(h.temperature, 0) + "°C"
      });
      bar.style.height = Math.max(4, ((h.aqi || 0) / max) * 100) + "%";
      box.appendChild(bar);
    });
    var mid = hours[Math.floor(hours.length / 2)];
    box.insertAdjacentElement("afterend", el("div", { "class": "outlook-axis" }, [
      el("span", { text: hours[0].time_local.slice(11, 16) }),
      el("span", { text: "AQI, next 24 h (outlined = best window)" }),
      el("span", { text: (mid ? "" : "") + hours[hours.length - 1].time_local.slice(11, 16) })
    ]));
  }

  // ----------------------------------------------------------------- noise
  function renderNoise(db, meta) {
    var band = window.EcoNoise.band(db);
    var card = $("cardNoise");
    card.dataset.level = band.level;
    var badge = card.querySelector(".badge");
    badge.dataset.level = band.level;
    badge.textContent = band.label;
    $("noiseValue").textContent = db === null || db === undefined ? "—" : E.fmt(db, 0);
    setMeter(db);
    if (meta && meta.ts) {
      $("noiseHint").textContent = (meta.method === "mic" ? "Measured with microphone " : "Entered manually ") +
        E.timeAgo(meta.ts) + ". Approximate, uncalibrated.";
    }
  }

  function setMeter(db) {
    var m = $("noiseMeter");
    var pct = db === null || db === undefined ? 0 : Math.max(0, Math.min(1, db / 120)) * 100;
    m.style.width = pct + "%";
    m.parentElement.dataset.level = window.EcoNoise.band(db).level;
  }

  function submitNoise(db, method) {
    return E.fetchJSON("/api/noise", {
      method: "POST",
      body: { lat: state.location.lat, lon: state.location.lon, name: state.location.name,
              db: db, method: method, profile: state.profile }
    }).then(function (res) {
      if (res.payload) render(res.payload);
      else renderNoise(res.db, { method: method, ts: new Date().toISOString() });
      E.toast("Noise saved: ~" + E.fmt(res.db, 0) + " dB");
    }).catch(function (e) { E.toast(e.message, 5000); });
  }

  function startNoise() {
    var btn = $("btnNoise"), label = btn.querySelector("span"), card = $("cardNoise");
    btn.disabled = true;
    card.classList.add("measuring");
    label.textContent = "Allow microphone…";
    window.EcoNoise.measure({
      seconds: 5,
      onLevel: function (db, progress) {
        label.textContent = "Listening… " + Math.max(0, Math.ceil(5 - progress * 5)) + " s";
        $("noiseValue").textContent = E.fmt(db, 0);
        setMeter(db);
      }
    }).then(function (avg) {
      return submitNoise(avg, "mic");
    }).catch(function (e) {
      E.toast(e.message, 6000);
      $("noiseHint").textContent = e.message;
      renderNoise(state.payload ? state.payload.current.noise : null, state.payload ? state.payload.noise_meta : null);
    }).finally(function () {
      btn.disabled = false;
      card.classList.remove("measuring");
      label.textContent = "Measure noise";
    });
  }

  // ---------------------------------------------------------------- search
  var searchSeq = 0, searchTimer = null, results = [], activeIdx = -1;
  var input = $("cityInput"), list = $("cityList");

  function closeList() { list.hidden = true; input.setAttribute("aria-expanded", "false"); activeIdx = -1; }

  function showResults(items, message) {
    results = items;
    list.textContent = "";
    activeIdx = -1;
    if (message) {
      list.appendChild(el("li", { "class": "empty-row", text: message }));
    }
    items.forEach(function (r, i) {
      list.appendChild(el("li", {
        role: "option", id: "opt-" + i, "aria-selected": "false",
        onmousedown: function (ev) { ev.preventDefault(); choose(i); }
      }, [
        el("span", { text: r.name }),
        el("span", { "class": "muted", text: r.lat.toFixed(2) + ", " + r.lon.toFixed(2) })
      ]));
    });
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
  }

  function highlight(i) {
    var opts = list.querySelectorAll('[role="option"]');
    opts.forEach(function (o, j) { o.setAttribute("aria-selected", j === i ? "true" : "false"); });
    activeIdx = i;
    if (opts[i]) { opts[i].scrollIntoView({ block: "nearest" }); input.setAttribute("aria-activedescendant", opts[i].id); }
  }

  function choose(i) {
    var r = results[i];
    if (!r) return;
    setLocation({ name: r.name, lat: r.lat, lon: r.lon });
    input.value = "";
    closeList();
    input.blur();
  }

  input.addEventListener("input", function () {
    var q = input.value.trim();
    clearTimeout(searchTimer);
    if (q.length < 2) { closeList(); return; }
    searchTimer = setTimeout(function () {
      var seq = ++searchSeq;
      showResults([], "Searching…");
      E.fetchJSON("/api/search?q=" + encodeURIComponent(q))
        .then(function (d) {
          if (seq !== searchSeq) return;
          showResults(d.results || [], (d.results || []).length ? null : "No matching places found");
        })
        .catch(function (e) { if (seq === searchSeq) showResults([], e.message); });
    }, 300);
  });
  input.addEventListener("keydown", function (e) {
    if (list.hidden) return;
    if (e.key === "ArrowDown") { e.preventDefault(); highlight(Math.min(results.length - 1, activeIdx + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); highlight(Math.max(0, activeIdx - 1)); }
    else if (e.key === "Enter") { e.preventDefault(); choose(activeIdx >= 0 ? activeIdx : 0); }
    else if (e.key === "Escape") { closeList(); }
  });
  input.addEventListener("blur", function () { setTimeout(closeList, 150); });

  function setLocation(loc) {
    state.location = loc;
    state.dismissed = {};
    E.store(LOC_KEY, JSON.stringify(loc));
    $("noiseHint").textContent = "Uses your microphone for ~5 s. Uncalibrated estimate; phones and laptops differ.";
    load();
  }

  // ------------------------------------------------------------- geolocate
  $("btnLocate").addEventListener("click", function () {
    var btn = this;
    if (!navigator.geolocation) { E.toast("Location is not supported by this browser.", 4000); return; }
    btn.disabled = true;
    E.toast("Finding your location…", 2000);
    navigator.geolocation.getCurrentPosition(function (pos) {
      btn.disabled = false;
      setLocation({
        name: "My location",
        lat: Math.round(pos.coords.latitude * 10000) / 10000,
        lon: Math.round(pos.coords.longitude * 10000) / 10000
      });
    }, function (err) {
      btn.disabled = false;
      var msg = {
        1: "Location permission denied. Allow it from the address bar, or search for your city.",
        2: "Your location is unavailable right now. Search for your city instead.",
        3: "Finding your location timed out. Try again or search for your city."
      }[err.code] || "Could not get your location.";
      E.toast(msg, 6000);
    }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 });
  });

  // --------------------------------------------------------------- profile
  var sel = $("profileSelect");
  if (!sel.querySelector('option[value="' + state.profile + '"]')) state.profile = "general";
  sel.value = state.profile;
  sel.addEventListener("change", function () {
    state.profile = sel.value;
    E.store(PROFILE_KEY, state.profile);
    E.fetchJSON("/api/profile", {
      method: "PUT",
      body: { health_profile: state.profile }
    }).catch(function () { /* localStorage remains the fallback */ });
    E.toast("Profile: " + sel.options[sel.selectedIndex].text);
    load();
  });

  // ----------------------------------------------------------------- modal
  var modal = $("howModal");
  $("btnHow").addEventListener("click", function () {
    var box = $("howBreakdown");
    box.textContent = "";
    if (state.payload) {
      var s = state.payload.analysis.score;
      var rows = s.components.map(function (c) {
        return el("tr", {}, [
          el("td", { text: niceName(c.metric) }),
          el("td", { "class": "num", text: c.value === null ? "not measured" : E.fmt(c.value, 1) }),
          el("td", { "class": "num", text: c.subscore === null ? "—" : E.fmt(c.subscore, 0) }),
          el("td", { "class": "num", text: (c.effective_weight * 100).toFixed(1) + "%" }),
          el("td", { "class": "num", text: c.contribution === null ? "—" : E.fmt(c.contribution, 1) })
        ]);
      });
      box.appendChild(el("h3", { text: "Right now for " + state.payload.location.name }));
      box.appendChild(el("div", { "class": "table-scroll" }, [el("table", { "class": "tbl" }, [
        el("thead", {}, [el("tr", {}, [
          el("th", { text: "Factor" }), el("th", { text: "Value" }), el("th", { text: "Sub-score" }),
          el("th", { text: "Weight used" }), el("th", { text: "Points" })
        ])]),
        el("tbody", {}, rows)
      ])]));
      box.appendChild(el("p", { "class": "small", text:
        "Weighted total = " + E.fmt(s.weighted_score, 1) +
        (s.capped ? " → capped to " + s.score + " by the weakest-link rule (" + niceName(s.limiting_factor) + ")." : " → score " + s.score + ".") }));
    }
    modal.showModal();
  });
  $("howClose").addEventListener("click", function () { modal.close(); });
  modal.addEventListener("click", function (e) { if (e.target === modal) modal.close(); });

  // --------------------------------------------------------------- buttons
  $("btnRefresh").addEventListener("click", load);
  $("btnNoise").addEventListener("click", startNoise);
  $("manualNoise").addEventListener("submit", function (e) {
    e.preventDefault();
    var v = parseFloat($("manualDb").value);
    if (isNaN(v) || v < 0 || v > 140) { E.toast("Enter a number between 0 and 140 dB.", 3500); return; }
    $("manualDb").value = "";
    submitNoise(Math.round(v * 10) / 10, "manual");
  });

  // Keep the "x min ago" text fresh
  setInterval(function () {
    if (state.payload) {
      $("lastUpdated").textContent = E.localTime(state.payload.updated_at, true) + " (" + E.timeAgo(state.payload.updated_at) + ")";
    }
  }, 30000);

  load();
})();
