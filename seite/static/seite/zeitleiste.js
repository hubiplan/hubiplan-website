// Zeitleiste der Chronik: Ein Klick auf ein Bild zeigt es groß in einem Fenster
// (<dialog>); ohne JavaScript öffnet der Link das Bild selbst. Esc, „Schließen“ oder
// ein Klick daneben schließen das Fenster.
(function () {
  "use strict";
  var fenster = document.getElementById("bild-fenster");
  if (!fenster || !fenster.showModal) return;
  var bild = fenster.querySelector("img");
  var unterschrift = fenster.querySelector(".bild-unterschrift");
  var zuletzt = null;
  document.addEventListener("click", function (e) {
    if (e.target === fenster) {
      fenster.close();
      return;
    }
    var link = e.target.closest ? e.target.closest("a.zeitleiste-bild") : null;
    if (!link || e.ctrlKey || e.metaKey || e.shiftKey) return;
    e.preventDefault();
    var klein = link.querySelector("img");
    bild.src = link.href;
    bild.alt = klein ? klein.alt : "";
    unterschrift.textContent = link.dataset.unterschrift || "";
    unterschrift.hidden = !unterschrift.textContent;
    zuletzt = link;
    fenster.showModal();
  });
  fenster.addEventListener("close", function () {
    bild.src = "";
    if (zuletzt) zuletzt.focus();
  });
})();
