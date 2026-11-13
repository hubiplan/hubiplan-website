// Vereinslogo im Kopf: lädt es nicht, bleibt nur der Name, ohne leeren Bildrahmen
// (UX-Audit 31.10. R02).
(function () {
  "use strict";
  var bild = document.querySelector(".marke img");
  if (!bild) return;
  function weg() { bild.remove(); }
  if (bild.complete && bild.naturalWidth === 0) weg();
  else bild.addEventListener("error", weg, { once: true });
})();

// Untermenüs (<details class="untermenue">): Esc, Tippen daneben und Öffnen eines anderen
// schließen sie; Fokus zurück auf den Menüpunkt.
(function () {
  "use strict";
  var alle = Array.prototype.slice.call(document.querySelectorAll("details.untermenue"));
  if (!alle.length) return;
  alle.forEach(function (d) {
    d.addEventListener("toggle", function () {
      if (d.open) alle.forEach(function (x) { if (x !== d) x.open = false; });
    });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    alle.forEach(function (d) {
      if (d.open) { d.open = false; d.querySelector("summary").focus(); }
    });
  });
  document.addEventListener("click", function (e) {
    alle.forEach(function (d) { if (d.open && !d.contains(e.target)) d.open = false; });
  });
})();

// Handymenü (<details class="menue">): Esc und Tippen daneben schließen es;
// nach Esc liegt der Fokus wieder auf „Menü“ (Barrierefreiheit W-08).
(function () {
  "use strict";
  var menue = document.querySelector("details.menue");
  if (!menue) return;
  var knopf = menue.querySelector("summary");
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && menue.open) {
      menue.open = false;
      knopf.focus();
    }
  });
  document.addEventListener("click", function (e) {
    if (menue.open && !menue.contains(e.target)) menue.open = false;
  });
})();

// Knopf „Nach oben“ (Stilregler to_top): erst nach gut einer Bildschirmhöhe Blättern sichtbar
(function () {
  "use strict";
  var knopf = document.querySelector(".nach-oben");
  if (!knopf) return;
  var zeigen = function () { knopf.hidden = window.scrollY < window.innerHeight * 1.2; };
  window.addEventListener("scroll", zeigen, { passive: true });
  zeigen();
  knopf.addEventListener("click", function (e) {
    e.preventDefault();
    var ruhig = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: ruhig ? "auto" : "smooth" });
    var sprung = document.querySelector(".sprung");
    if (sprung) sprung.focus({ preventScroll: true });
  });
})();
