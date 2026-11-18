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
    var inhalt = knopf && document.getElementById(knopf.dataset.termin);
    if (!inhalt || !inhalt.content) return;
    // Ein gemeinsames Fenster für alle Termine (UX-Audit WS-14 f)
    var dialog = document.getElementById("termin-fenster");
    if (!dialog) {
      dialog = document.createElement("dialog");
      dialog.id = "termin-fenster";
      dialog.className = "termin-fenster";
      dialog.setAttribute("aria-labelledby", "termin-fenster-titel");
      document.body.appendChild(dialog);
    }
    if (!dialog.showModal || dialog.open) return;
    dialog.replaceChildren(inhalt.content.cloneNode(true));
    dialog.showModal();
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
