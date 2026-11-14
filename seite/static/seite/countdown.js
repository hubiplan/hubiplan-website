// Countdown-Abschnitte: zählt jede Sekunde bis zum Ziel (data-ziel, ISO mit Zeitzone)
// herunter. Danach zeigt der Abschnitt seinen Text für „nach Ablauf“ oder verschwindet.
(function () {
  "use strict";
  var zaehler = Array.prototype.slice.call(document.querySelectorAll(".countdown-zaehler[data-ziel]"));
  if (!zaehler.length) return;
  var eintraege = zaehler.map(function (el) {
    return { el: el, ziel: Date.parse(el.dataset.ziel), teile: el.querySelectorAll("[data-teil]") };
  }).filter(function (e) { return !isNaN(e.ziel); });

  function ablaufen(e) {
    var abschnitt = e.el.closest("[data-countdown]");
    if (!abschnitt) return;
    var danach = abschnitt.querySelector(".countdown-danach");
    if (danach) {
      e.el.hidden = true;
      abschnitt.querySelectorAll(".countdown-ziel, .countdown-text").forEach(function (x) { x.hidden = true; });
      danach.hidden = false;
    } else {
      abschnitt.hidden = true;
    }
  }

  function schritt() {
    var jetzt = Date.now();
    eintraege = eintraege.filter(function (e) {
      var rest = Math.floor((e.ziel - jetzt) / 1000);
      if (rest <= 0) {
        ablaufen(e);
        return false;
      }
      var werte = {
        tage: Math.floor(rest / 86400),
        stunden: Math.floor((rest % 86400) / 3600),
        minuten: Math.floor((rest % 3600) / 60),
        sekunden: rest % 60
      };
      e.teile.forEach(function (zahl) {
        var wert = werte[zahl.dataset.teil];
        if (zahl.textContent !== String(wert)) {
          zahl.textContent = String(wert);
          var einheit = zahl.nextElementSibling;
          if (einheit && einheit.dataset) {
            einheit.textContent = wert === 1 ? einheit.dataset.ein : einheit.dataset.mehr;
          }
        }
      });
      return true;
    });
    if (eintraege.length) window.setTimeout(schritt, 1000 - (Date.now() % 1000) + 5);
  }
  schritt();
})();
