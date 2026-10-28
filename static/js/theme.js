/* Theme: runs in <head> before paint. Remembers the choice in localStorage;
   falls back to the operating-system preference the first time. */
(function () {
  var KEY = "ecolens-theme";
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* storage blocked */ }
  var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.setAttribute("data-theme", saved || (prefersDark ? "dark" : "light"));

  window.EcoTheme = {
    toggle: function () {
      var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem(KEY, next); } catch (e) { /* ignore */ }
      document.dispatchEvent(new CustomEvent("themechange", { detail: next }));
      return next;
    }
  };
})();
