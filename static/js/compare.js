(function () {
  "use strict";
  var E = window.Eco, $ = function (id) { return document.getElementById(id); };
  var selected = { a: null, b: null };

  function wireInput(inputId, listId, key) {
    var input = $(inputId), list = $(listId), timer;
    input.addEventListener("input", function () {
      var q = input.value.trim();
      clearTimeout(timer);
      selected[key] = null;
      if (q.length < 2) { list.hidden = true; return; }
      timer = setTimeout(function () {
        E.fetchJSON("/api/search?q=" + encodeURIComponent(q)).then(function (d) {
          list.textContent = "";
          (d.results || []).slice(0, 5).forEach(function (item) {
            var row = document.createElement("button");
            row.type = "button"; row.className = "suggestion-row";
            row.textContent = item.name + " · " + item.lat.toFixed(2) + ", " + item.lon.toFixed(2);
            row.addEventListener("click", function () {
              selected[key] = item; input.value = item.name; list.hidden = true;
            });
            list.appendChild(row);
          });
          list.hidden = !list.children.length;
        }).catch(function () { list.hidden = true; });
      }, 250);
    });
  }

  function metric(label, value, suffix) {
    var box = document.createElement("div"); box.className = "compare-metric";
    var title = document.createElement("span");
    title.textContent = label;
    var valueNode = document.createElement("strong");
    valueNode.textContent = E.fmt(value, label === "Temperature" ? 1 : 0) +
      (value === null || value === undefined ? "" : (suffix || ""));
    box.appendChild(title); box.appendChild(valueNode);
    return box;
  }

  function render(d) {
    var root = $("compareResult"); root.textContent = ""; root.hidden = false;
    var a = d.locations[0], b = d.locations[1], winner = a.analysis.score.score >= b.analysis.score.score ? a : b;
    var header = document.createElement("div"); header.className = "compare-summary card";
    var eyebrow = document.createElement("span"); eyebrow.className = "eyebrow"; eyebrow.textContent = "At a glance";
    var title = document.createElement("h2"); title.textContent = winner.location.name + " has the stronger overall environment right now";
    var desc = document.createElement("p"); desc.className = "muted"; desc.textContent = "Scores are profile-aware and explainable; a higher score means healthier conditions.";
    header.appendChild(eyebrow); header.appendChild(title); header.appendChild(desc);
    root.appendChild(header);
    var grid = document.createElement("div"); grid.className = "compare-grid";
    [a, b].forEach(function (item) {
      var card = document.createElement("article"); card.className = "card compare-card";
      card.setAttribute("data-level", item.analysis.score.level);
      var head = document.createElement("div"); head.className = "card-head";
      var name = document.createElement("h2"); name.textContent = item.location.name;
      var badge = document.createElement("span"); badge.className = "badge"; badge.dataset.level = item.analysis.score.level; badge.textContent = item.analysis.score.label;
      head.appendChild(name); head.appendChild(badge);
      var score = document.createElement("div"); score.className = "compare-score"; score.textContent = item.analysis.score.score;
      var scoreUnit = document.createElement("small"); scoreUnit.textContent = "/100"; score.appendChild(scoreUnit);
      card.appendChild(head); card.appendChild(score);
      var metrics = document.createElement("div"); metrics.className = "compare-metrics";
      metrics.appendChild(metric("AQI", item.current.aqi, ""));
      metrics.appendChild(metric("Temperature", item.current.temperature, "°C"));
      metrics.appendChild(metric("Humidity", item.current.humidity, "%"));
      metrics.appendChild(metric("UV index", item.current.uv, ""));
      card.appendChild(metrics);
      var verdict = document.createElement("p"); verdict.className = "compare-verdict"; verdict.textContent = item.recommendations.verdict + " · " + item.recommendations.summary; card.appendChild(verdict);
      grid.appendChild(card);
    });
    root.appendChild(grid);
  }

  $("compareRun").addEventListener("click", function () {
    var error = $("errorBox"), a = selected.a, b = selected.b;
    if (!a || !b) { error.textContent = "Choose one result for each location before comparing."; error.hidden = false; return; }
    error.hidden = true; this.disabled = true; this.classList.add("loading");
    E.fetchJSON("/api/compare?" + new URLSearchParams({ lat1: a.lat, lon1: a.lon, name1: a.name, lat2: b.lat, lon2: b.lon, name2: b.name, profile: E.store("ecolens-profile") || "general" }))
      .then(render).catch(function (e) { error.textContent = e.message; error.hidden = false; })
      .finally(function () { $("compareRun").disabled = false; $("compareRun").classList.remove("loading"); });
  });
  wireInput("compareA", "suggestionsA", "a"); wireInput("compareB", "suggestionsB", "b");
})();
