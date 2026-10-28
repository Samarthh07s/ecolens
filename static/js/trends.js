/* Trends page: location + range filters, Chart.js line charts with a
   moving-average overlay, summary stats, trend direction and 6-hour estimate. */
(function () {
  "use strict";
  var E = window.Eco, el = E.el, $ = function (id) { return document.getElementById(id); };
  var state = { location: E.store("ecolens-trend-loc") || "", range: "24h", data: null, charts: {} };

  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

  function loadLocations() {
    return E.fetchJSON("/api/history?range=30d").then(function (d) {
      var sel = $("locSelect");
      while (sel.options.length > 1) sel.remove(1);
      (d.locations || []).forEach(function (l) {
        sel.appendChild(el("option", { value: l.location_key, text: l.location_name + " (" + l.n + " readings)" }));
      });
      // default to the most recently used location
      var keys = (d.locations || []).map(function (l) { return l.location_key; });
      if (keys.indexOf(state.location) < 0) state.location = keys[0] || "";
      sel.value = state.location;
    });
  }

  function load() {
    var q = new URLSearchParams({ range: state.range });
    if (state.location) q.set("location", state.location);
    $("btnCsv").href = "/api/export.csv?" + q.toString();
    E.fetchJSON("/api/trends?" + q.toString())
      .then(function (d) { $("errorBox").hidden = true; state.data = d; render(d); })
      .catch(function (e) { var b = $("errorBox"); b.textContent = e.message; b.hidden = false; });
  }

  function render(d) {
    var empty = d.empty;
    $("emptyState").hidden = !empty;
    $("trendContent").hidden = empty;
    if (empty) { $("pointsInfo").textContent = ""; return; }

    var src = d.sources || {};
    $("pointsInfo").textContent = d.points + " hourly points (" + (src.live || 0) + " live refreshes, " +
      (src.hourly || 0) + " API hourly) · moving average: " + d.moving_average_window + " h";

    renderStats(d);
    ["aqi", "temperature", "score"].forEach(function (m) {
      var pill = $("trend-" + m), t = d.trends[m];
      if (!t) { pill.textContent = ""; return; }
      pill.className = "trend-pill " + t.direction.replace(/\s+/g, "-");
      var arrow = { improving: "▲ ", worsening: "▼ ", rising: "↗ ", falling: "↘ ", stable: "→ " }[t.direction] || "";
      pill.textContent = arrow + cap(t.direction) + (t.change_24h !== null ? " (" + sign(t.change_24h) + " / 24 h)" : "");
      pill.title = "Linear-fit slope: " + t.slope_per_hour + " per hour";
    });

    drawChart("chartAqi", "aqi", "AQI", css("--lv-usg"), d.forecast.aqi);
    drawChart("chartTemp", "temperature", "°C", css("--lv-cold"), d.forecast.temperature);
    drawChart("chartScore", "score", "Score", css("--accent"), null);
    renderForecast(d.forecast);
  }

  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
  function sign(v) { return (v > 0 ? "+" : "") + v.toFixed(1); }

  function renderStats(d) {
    var box = $("statCards");
    box.textContent = "";
    [["aqi", "Air Quality (AQI)", 0], ["temperature", "Temperature (°C)", 1], ["score", "Health Score", 0]].forEach(function (m) {
      var s = d.stats[m[0]];
      if (!s) return;
      box.appendChild(el("article", { "class": "card stat-card" }, [
        el("h2", { text: m[1] }),
        el("div", { "class": "stat-row" }, [
          el("div", {}, [el("span", { text: "Avg" }), el("strong", { text: E.fmt(s.avg, m[2]) })]),
          el("div", {}, [el("span", { text: "Min" }), el("strong", { text: E.fmt(s.min, m[2]) })]),
          el("div", {}, [el("span", { text: "Max" }), el("strong", { text: E.fmt(s.max, m[2]) })])
        ])
      ]));
    });
  }

  function labelFor(iso) {
    var d = new Date(iso);
    if (state.range === "24h") return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    return d.toLocaleString([], { day: "numeric", month: "short", hour: "2-digit" });
  }

  function drawChart(canvasId, key, unit, color, forecast) {
    var d = state.data, s = d.series[key];
    if (state.charts[canvasId]) state.charts[canvasId].destroy();
    if (!s) return;
    var labels = d.labels.map(labelFor);
    var values = s.values.slice(), ma = s.moving_avg.slice();
    var est = null;
    if (forecast && forecast.length) {
      // dashed estimate continues from the last real point
      est = values.map(function () { return null; });
      est[est.length - 1] = values[values.length - 1];
      forecast.forEach(function (f) {
        labels.push(labelFor(f.ts) + " (est.)");
        values.push(null); ma.push(null); est.push(f.value);
      });
    }
    var ink = css("--ink"), muted = css("--muted"), line = css("--line");
    var datasets = [
      { label: unit, data: values, borderColor: color, backgroundColor: color + "22", fill: true,
        tension: .3, pointRadius: values.length > 60 ? 0 : 2, borderWidth: 2, spanGaps: true },
      { label: d.moving_average_window + "-h moving average", data: ma, borderColor: ink, borderDash: [],
        borderWidth: 1.5, pointRadius: 0, tension: .3, fill: false, spanGaps: true }
    ];
    if (est) datasets.push({ label: "Estimate (linear)", data: est, borderColor: color, borderDash: [6, 5],
      borderWidth: 2, pointRadius: 2, fill: false, spanGaps: true });

    state.charts[canvasId] = new Chart(document.getElementById(canvasId), {
      type: "line",
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true, maintainAspectRatio: false, animation: { duration: 500 },
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { color: muted, boxWidth: 14, usePointStyle: true } },
          tooltip: { callbacks: { label: function (c) {
            return c.parsed.y === null ? null : c.dataset.label + ": " + c.parsed.y.toFixed(1);
          } } }
        },
        scales: {
          x: { ticks: { color: muted, maxTicksLimit: 8, maxRotation: 0 }, grid: { color: line } },
          y: { ticks: { color: muted }, grid: { color: line }, beginAtZero: key !== "temperature" }
        }
      }
    });
  }

  function renderForecast(f) {
    var tb = $("forecastTable").querySelector("tbody");
    tb.textContent = "";
    var n = Math.max(f.aqi.length, f.temperature.length);
    if (!n) {
      tb.appendChild(el("tr", {}, [el("td", { colspan: "3", "class": "muted", text: "Need at least 4 hourly points for an estimate." })]));
      return;
    }
    for (var i = 0; i < n; i++) {
      var a = f.aqi[i], t = f.temperature[i];
      tb.appendChild(el("tr", {}, [
        el("td", { text: E.localTime((a || t).ts, true) }),
        el("td", { "class": "num", text: a ? "~" + E.fmt(a.value, 0) : "—" }),
        el("td", { "class": "num", text: t ? "~" + E.fmt(t.value, 1) + " °C" : "—" })
      ]));
    }
  }

  // Filters
  $("locSelect").addEventListener("change", function () {
    state.location = this.value;
    E.store("ecolens-trend-loc", state.location);
    load();
  });
  document.querySelectorAll(".segmented button").forEach(function (b) {
    b.addEventListener("click", function () {
      document.querySelectorAll(".segmented button").forEach(function (x) { x.classList.remove("active"); });
      b.classList.add("active");
      state.range = b.dataset.range;
      load();
    });
  });
  document.addEventListener("themechange", function () { if (state.data && !state.data.empty) render(state.data); });

  if (typeof Chart === "undefined") {
    var b = $("errorBox");
    b.textContent = "Chart library failed to load (static/vendor/chart.min.js is missing).";
    b.hidden = false;
  }
  loadLocations().catch(function () { /* still try to load all-locations data */ }).then(load);
})();
