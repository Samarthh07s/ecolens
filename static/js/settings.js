(function () {
  "use strict";
  var E = window.Eco, $ = function (id) { return document.getElementById(id); };
  function load() {
    E.fetchJSON("/api/profile").then(function (p) {
      $("displayName").value = p.display_name || "";
      $("healthProfile").value = p.health_profile || "general";
      $("units").value = p.units || "metric";
    }).catch(function (e) { $("settingsStatus").textContent = e.message; });
  }
  $("settingsForm").addEventListener("submit", function (e) {
    e.preventDefault();
    E.fetchJSON("/api/profile", { method: "PUT", body: {
      display_name: $("displayName").value,
      health_profile: $("healthProfile").value,
      units: $("units").value
    }}).then(function (p) {
      E.store("ecolens-profile", p.health_profile);
      $("settingsStatus").textContent = "Saved just now. The dashboard will use this profile on its next refresh.";
      E.toast("Preferences saved");
    }).catch(function (err) { $("settingsStatus").textContent = err.message; });
  });
  load();
})();
