// Schwebende Hinweisleiste (hubiplan, Ralf 16.11.2026): Besucher schließen den Kasten mit ×.
// Er bleibt nur in diesem Browserfenster zu (sessionStorage, kein Cookie); bei neuem Text
// erscheint er wieder.
(function () {
  "use strict";
  var leiste = document.querySelector("[data-hinweis-schwebend]");
  if (!leiste) return;
  var knopf = leiste.querySelector(".hinweis-zu");
  var text = leiste.querySelector(".hinweis-text");
  var schluessel = "hinweis-zu:" + (text ? text.textContent.trim() : "");
  try {
    if (window.sessionStorage.getItem(schluessel)) { leiste.hidden = true; return; }
  } catch (e) { /* ohne Speicher bleibt der Kasten sichtbar */ }
  if (!knopf) return;
  knopf.hidden = false;
  knopf.addEventListener("click", function () {
    leiste.hidden = true;
    try { window.sessionStorage.setItem(schluessel, "1"); } catch (e) { /* egal */ }
  });
})();
