/* Shared helpers used by every page.
   Security note: all dynamic text is inserted with textContent (never
   innerHTML), so data from the API or user input can't inject markup. */
(function () {
  "use strict";

  /** Create an element: el("div", {class: "x", text: "hi"}, [children]) */
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === "text") node.textContent = v;
      else if (k === "class") node.className = v;
      else if (k === "dataset") Object.keys(v).forEach(function (d) { node.dataset[d] = v[d]; });
      else if (k.indexOf("on") === 0 && typeof v === "function") node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    });
    (children || []).forEach(function (c) {
      if (c === null || c === undefined) return;
      node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return node;
  }

  /** Inline SVG icon built from path data (no external assets). */
  var ICONS = {
    mask: "M4 9c3-2 13-2 16 0v4c0 3-4 6-8 6s-8-3-8-6zM4 10H2M20 10h2M8 13h8",
    run: "M13 5a2 2 0 1 0 0-.01M7 21l3-6 3 2v4M10 15l1-5 4 3h3M8 11l3-2",
    sun: "M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5",
    drop: "M12 3c4 5 6 8 6 11a6 6 0 0 1-12 0c0-3 2-6 6-11z",
    window: "M4 4h16v16H4zM12 4v16M4 12h16",
    inhaler: "M8 3h5v6H8zM6 9h9l-1 12H7zM15 12h4v4h-4",
    alert: "M12 3l10 18H2zM12 10v5M12 18v.01"
  };
  function icon(name) {
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    var p = document.createElementNS(ns, "path");
    p.setAttribute("d", ICONS[name] || ICONS.alert);
    svg.appendChild(p);
    return svg;
  }

  /** fetch JSON with a timeout and friendly errors. */
  function fetchJSON(url, opts) {
    opts = opts || {};
    var ctrl = new AbortController();
    var timer = setTimeout(function () { ctrl.abort(); }, opts.timeout || 30000);
    var init = { method: opts.method || "GET", signal: ctrl.signal, headers: {} };
    if (opts.body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
    }
    return fetch(url, init).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) {
          var err = new Error(data.error || ("Request failed (" + res.status + ")"));
          err.status = res.status;
          err.data = data;
          throw err;
        }
        return data;
      });
    }, function (e) {
      if (e.name === "AbortError") throw new Error("The request took too long. Please try again.");
      throw new Error("Cannot reach the EcoLens server. Is the black run.bat window still open?");
    }).finally(function () { clearTimeout(timer); });
  }

  var toastTimer;
  function toast(msg, ms) {
    var t = document.getElementById("toast");
    if (!t) return;
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.hidden = true; }, ms || 3000);
  }

  function fmt(v, digits) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return Number(v).toFixed(digits === undefined ? 0 : digits);
  }

  function timeAgo(iso) {
    var d = new Date(iso);
    var s = Math.round((Date.now() - d.getTime()) / 1000);
    if (s < 45) return "just now";
    if (s < 3600) return Math.round(s / 60) + " min ago";
    if (s < 86400) return Math.round(s / 3600) + " h ago";
    return Math.round(s / 86400) + " d ago";
  }

  function localTime(iso, withDate) {
    var d = new Date(iso);
    var o = { hour: "2-digit", minute: "2-digit" };
    if (withDate) { o.day = "numeric"; o.month = "short"; }
    return d.toLocaleString([], o);
  }

  function store(key, value) {
    try {
      if (value === undefined) return localStorage.getItem(key);
      localStorage.setItem(key, value);
    } catch (e) { return null; }
  }

  // Desktop browser notifications (only if the user enabled them on the Alerts page)
  function notify(title, body) {
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    if (store("ecolens-notify") !== "on") return;
    try { new Notification(title, { body: body, icon: "/static/favicon.svg", tag: title }); } catch (e) { /* ignore */ }
  }

  function updateAlertCount() {
    var badge = document.getElementById("navAlertCount");
    if (!badge) return;
    fetchJSON("/api/alerts").then(function (d) {
      var n = (d.alerts || []).length;
      badge.textContent = n > 99 ? "99+" : String(n);
      badge.hidden = n === 0;
    }).catch(function () { /* offline: ignore */ });
  }

  // Wire up the nav + theme toggle on every page
  document.addEventListener("DOMContentLoaded", function () {
    var toggle = document.getElementById("themeToggle");
    if (toggle) toggle.addEventListener("click", function () {
      var t = window.EcoTheme.toggle();
      toast(t === "dark" ? "Dark theme" : "Light theme", 1200);
    });
    var navBtn = document.getElementById("navToggle");
    var nav = document.getElementById("mainNav");
    if (navBtn && nav) navBtn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      navBtn.setAttribute("aria-expanded", open ? "true" : "false");
    });
    updateAlertCount();
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/static/sw.js").catch(function () { /* optional enhancement */ });
    }
  });

  window.Eco = {
    el: el, icon: icon, fetchJSON: fetchJSON, toast: toast, fmt: fmt,
    timeAgo: timeAgo, localTime: localTime, store: store, notify: notify,
    updateAlertCount: updateAlertCount
  };
})();
