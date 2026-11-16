// Terminkarten: ein Klick irgendwo auf die Karte öffnet das Fenster mit allen
// Angaben (<dialog>); Esc, „Schließen“ oder ein Klick daneben schließen es.
(function () {
  "use strict";
  document.addEventListener("click", function (e) {
    var fenster = e.target.closest ? e.target.closest("dialog.termin-fenster") : null;
    if (fenster) {
      // Klick auf den abgedunkelten Rand (das <dialog> selbst) schließt
      if (e.target === fenster) fenster.close();
      return;
    }
    var karte = e.target.closest ? e.target.closest("li.termin") : null;
    if (!karte || e.target.closest("a")) return;
    var knopf = karte.querySelector(".termin-knopf");
    var ziel = knopf && document.getElementById(knopf.dataset.termin);
    if (ziel && ziel.showModal && !ziel.open) ziel.showModal();
  });
})();

// Webseite #156: Knopf „Adresse kopieren“ beim Kalender-Abo. Er erscheint nur, wenn der
// Browser die Zwischenablage anbietet; sonst bleibt die Adresse zum Markieren stehen.
(function () {
  "use strict";
  if (!navigator.clipboard || !window.isSecureContext) return;
  document.querySelectorAll("[data-kopieren]").forEach(function (knopf) {
    var quelle = document.getElementById(knopf.dataset.kopieren);
    if (!quelle) return;
    var absatz = knopf.closest("[hidden]");
    if (absatz) absatz.hidden = false;
    var text = knopf.textContent;
    knopf.addEventListener("click", function () {
      navigator.clipboard.writeText(quelle.textContent.trim()).then(function () {
        knopf.textContent = knopf.dataset.kopiert;
        setTimeout(function () { knopf.textContent = text; }, 2500);
      });
    });
  });
})();
