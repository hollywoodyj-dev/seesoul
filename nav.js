(function () {
  var toggle = document.getElementById("navToggle");
  var nav = document.getElementById("siteNav");
  if (!toggle || !nav) return;

  function isOpen() {
    return toggle.getAttribute("aria-expanded") === "true";
  }
  function set(open, returnFocus) {
    nav.classList.toggle("site-nav--open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.setAttribute("aria-label", open ? "关闭导航菜单" : "打开导航菜单");
    if (returnFocus) toggle.focus();
  }

  set(false);
  toggle.addEventListener("click", function () {
    set(!isOpen());
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && isOpen()) set(false, true);
  });
  nav.addEventListener("click", function (e) {
    if (e.target.closest("a")) set(false);
  });
  document.addEventListener("click", function (e) {
    if (isOpen() && !nav.contains(e.target) && !toggle.contains(e.target)) set(false);
  });
  var mobile = window.matchMedia("(max-width: 960px)");
  function closeOnDesktop() {
    if (!mobile.matches && isOpen()) set(false);
  }
  mobile.addEventListener("change", closeOnDesktop);
  window.addEventListener("resize", closeOnDesktop);
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) set(false);
  });
})();
