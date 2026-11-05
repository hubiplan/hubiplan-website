// Bilder groß im Fenster (Zeitleiste der Chronik, Galerie): Ein Klick auf ein Bild zeigt
// es groß in einem Fenster (<dialog>); ohne JavaScript öffnet der Link das Bild selbst.
// Mehrere Bilder einer Gruppe (Ereignis, Album) blättert man mit „Voriges/Nächstes Bild“
// oder den Pfeiltasten.
// Esc, „Schließen“ oder ein Klick daneben schließen das Fenster.
(function () {
  "use strict";
  var fenster = document.getElementById("bild-fenster");
  if (!fenster || !fenster.showModal) return;
  var bild = fenster.querySelector("img");
  var unterschrift = fenster.querySelector(".bild-unterschrift");
  var blaettern = fenster.querySelector(".bild-blaettern");
  var zaehler = fenster.querySelector(".bild-zaehler");
  var gruppe = [];
  var stelle = 0;
  var zuletzt = null;

  function zeigen(i) {
    stelle = (i + gruppe.length) % gruppe.length;
    var link = gruppe[stelle];
    var klein = link.querySelector("img");
    bild.src = link.href;
    bild.alt = klein ? klein.alt : "";
    unterschrift.textContent = link.dataset.unterschrift || "";
    unterschrift.hidden = !unterschrift.textContent;
    blaettern.hidden = gruppe.length < 2;
    zaehler.textContent = (zaehler.dataset.vorlage || "{n} / {m}")
      .replace("{n}", stelle + 1)
      .replace("{m}", gruppe.length);
    zuletzt = link;
  }

  document.addEventListener("click", function (e) {
    if (e.target === fenster) {
      fenster.close();
      return;
    }
    if (e.target.closest && e.target.closest(".bild-zurueck")) return zeigen(stelle - 1);
    if (e.target.closest && e.target.closest(".bild-weiter")) return zeigen(stelle + 1);
    var link = e.target.closest ? e.target.closest("a.zeitleiste-bild, a.galerie-bild") : null;
    if (!link || e.ctrlKey || e.metaKey || e.shiftKey) return;
    e.preventDefault();
    var behaelter = link.closest(".zeitleiste-bilder, .galerie-bilder");
    gruppe = behaelter
      ? Array.prototype.slice.call(behaelter.querySelectorAll("a.zeitleiste-bild, a.galerie-bild"))
      : [link];
    zeigen(gruppe.indexOf(link));
    fenster.showModal();
  });
  fenster.addEventListener("keydown", function (e) {
    if (gruppe.length < 2) return;
    if (e.key === "ArrowLeft") zeigen(stelle - 1);
    else if (e.key === "ArrowRight") zeigen(stelle + 1);
  });
  fenster.addEventListener("close", function () {
    bild.src = "";
    if (zuletzt) zuletzt.focus();
  });
})();
