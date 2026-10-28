/* Alerts page: list stored alerts, clear all, opt-in browser notifications. */
(function () {
  "use strict";
  var E = window.Eco, el = E.el, $ = function (id) { return document.getElementById(id); };

  function load() {
    E.fetchJSON("/api/alerts").then(function (d) {
      $("errorBox").hidden = true;
      render(d.alerts || []);
    }).catch(function (e) {
      var b = $("errorBox"); b.textContent = e.message; b.hidden = false;
    });
  }

  function render(alerts) {
    var list = $("alertList");
    list.textContent = "";
    $("emptyState").hidden = alerts.length > 0;
    $("btnClear").disabled = alerts.length === 0;
    alerts.forEach(function (a) {
      list.appendChild(el("article", { "class": "alert-banner", dataset: { level: a.severity } }, [
        el("div", {}, [
          el("div", { "class": "sev", text: a.severity === "critical" ? "Critical" : "Warning" }),
          el("div", { "class": "title", text: a.title }),
          el("div", { "class": "action", text: a.action }),
          el("div", { "class": "meta", text: a.location_name + " · " + E.localTime(a.created_at, true) + " (" + E.timeAgo(a.created_at) + ")" })
        ])
      ]));
    });
    E.updateAlertCount();
  }

  $("btnClear").addEventListener("click", function () {
    if (!window.confirm("Delete all stored alerts? This cannot be undone.")) return;
    E.fetchJSON("/api/alerts", { method: "DELETE" }).then(function (d) {
      E.toast("Cleared " + d.cleared + " alert" + (d.cleared === 1 ? "" : "s"));
      load();
    }).catch(function (e) { E.toast(e.message, 4000); });
  });

  // ---------------------------------------------------------- notifications
  function notifyUI() {
    var btn = $("btnNotify"), label = btn.querySelector("span"), status = $("notifyStatus");
    if (!("Notification" in window)) {
      btn.disabled = true;
      status.textContent = "This browser does not support desktop notifications.";
      return;
    }
    var on = Notification.permission === "granted" && E.store("ecolens-notify") === "on";
    label.textContent = on ? "Disable notifications" : "Enable notifications";
    if (Notification.permission === "denied") {
      status.textContent = "Notifications are blocked for this site. Allow them from the lock icon in the address bar.";
    } else {
      status.textContent = on
        ? "Notifications are on: you'll get a desktop pop-up when the dashboard raises a new alert."
        : "Notifications are off. Alerts still appear as banners on the dashboard.";
    }
  }

  $("btnNotify").addEventListener("click", function () {
    if (!("Notification" in window)) return;
    if (Notification.permission === "granted" && E.store("ecolens-notify") === "on") {
      E.store("ecolens-notify", "off");
      notifyUI();
      return;
    }
    // Permission is requested ONLY here, after the user clicks.
    Notification.requestPermission().then(function (p) {
      if (p === "granted") {
        E.store("ecolens-notify", "on");
        try { new Notification("EcoLens notifications enabled", { body: "You'll be notified when a new alert is raised.", icon: "/static/favicon.svg" }); } catch (e) { /* ignore */ }
      }
      notifyUI();
    });
  });

  notifyUI();
  load();
})();
