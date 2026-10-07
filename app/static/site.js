/* rogerwilco: the one script every page shares. On a narrow screen the nav is behind a menu button; this opens and
   closes it. Without JavaScript the <noscript> rule in the head shows the links instead. */
(function () {
  var head = document.querySelector(".site-head");
  var button = head && head.querySelector(".nav-toggle");
  if (!button) return;
  function set(open) {
    head.classList.toggle("open", open);
    button.setAttribute("aria-expanded", open ? "true" : "false");
    button.setAttribute("aria-label", open ? "Close menu" : "Menu");
  }
  button.addEventListener("click", function () { set(!head.classList.contains("open")); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && head.classList.contains("open")) { set(false); button.focus(); } });
  document.addEventListener("click", function (e) { if (head.classList.contains("open") && !head.contains(e.target)) set(false); });
  window.matchMedia("(min-width: 721px)").addEventListener("change", function (m) { if (m.matches) set(false); });
})();
