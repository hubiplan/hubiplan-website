// Kontaktformular: Rechenaufgabe gegen Spam lösen und die Nachricht direkt an
// HUBIplan schicken (dort gelten Drosselung und Prüfung).
(function () {
  "use strict";
  var form = document.getElementById("kontakt");
  // Webseite #137: Du-Anrede (Stilregler address=informal) auf deutschen Seiten
  var DU = {
    "Bitte Ihren Namen eingeben.": "Bitte deinen Namen eingeben.",
    "Danke! Ihre Nachricht ist angekommen.": "Danke! Deine Nachricht ist angekommen.",
    "Danke! Ihre Nachricht ist bei {name} angekommen.": "Danke! Deine Nachricht ist bei {name} angekommen.",
    "Eine Bestätigung geht an {email}.": "Eine Bestätigung geht an {email}.",
    "Sicherheitsprüfung erneuert. Ihre Nachricht bleibt erhalten. Bitte senden Sie erneut.":
      "Sicherheitsprüfung erneuert. Deine Nachricht bleibt erhalten. Bitte sende sie erneut.",
    "Das Formular ist abgelaufen. Bitte kopieren Sie Ihre Nachricht und laden Sie die Seite neu.":
      "Das Formular ist abgelaufen. Bitte kopiere deine Nachricht und lade die Seite neu.",
    "Diese Nachricht ist bereits bei uns angekommen. Sie müssen sie nicht erneut senden.":
      "Diese Nachricht ist bereits bei uns angekommen. Du musst sie nicht erneut senden.",
    "An diese Stelle kann gerade keine Nachricht gehen. Bitte schreiben Sie über den Menüpunkt „Kontakt“ an den Verein.":
      "An diese Stelle kann gerade keine Nachricht gehen. Bitte schreib über den Menüpunkt „Kontakt“ an den Verein."
  };
  // Texte in der Sprache der Seite (basis.html, Element seite-texte)
  function t(s) {
    var e = document.getElementById("seite-texte");
    if (!e) return (form && form.dataset.anrede === "du" && DU[s]) || s;
    try { return JSON.parse(e.textContent)[s] || s; } catch (x) { return s; }
  }
  if (!form || !window.crypto || !window.crypto.subtle || !window.fetch) return;
  var meldung = form.querySelector(".meldung");
  var knopf = form.querySelector("button[type=submit]");
  var geladen = Date.now();
  // Bereit: Senden freigeben, Hinweis für Browser ohne JavaScript weg (UX-Audit 31.10. S09)
  var ohneJs = document.getElementById("k-ohne-js");
  if (ohneJs) ohneJs.hidden = true;
  knopf.disabled = false;

  // Neue Rechenaufgabe holen, ohne die Seite neu zu laden; Eingaben bleiben (S03)
  async function neueAufgabe() {
    var res = await fetch(form.dataset.neu, { credentials: "same-origin", cache: "no-store" });
    if (!res.ok) throw new Error("keine neue Aufgabe");
    var a = await res.json();
    if (!a || !a.token || !a.salt) throw new Error("keine neue Aufgabe");
    form.dataset.token = a.token;
    form.dataset.salz = a.salt;
    form.dataset.schwierigkeit = String(a.difficulty || 16);
    geladen = Date.now();
  }

  function zeige(text, fehler) {
    meldung.textContent = text;
    meldung.classList.toggle("fehler", !!fehler);
  }

  // Feldfehler direkt am Feld (aria-invalid + aria-describedby), Barrierefreiheit W-05
  var FELDER = {
    name: ["k-name", t("Bitte Ihren Namen eingeben.")],
    email: ["k-mail", t("Bitte eine gültige E-Mail-Adresse eingeben, z. B. name@beispiel.de.")],
    subject: ["k-betreff", t("Bitte einen Betreff eingeben.")],
    message: ["k-text", t("Bitte eine Nachricht mit mindestens 10 Zeichen eingeben.")]
  };

  function feldFehler(name, text) {
    var feld = document.getElementById(FELDER[name][0]);
    var hinweis = document.getElementById(FELDER[name][0] + "-fehler");
    if (text) {
      feld.setAttribute("aria-invalid", "true");
      hinweis.textContent = text;
      hinweis.hidden = false;
    } else {
      feld.removeAttribute("aria-invalid");
      hinweis.textContent = "";
      hinweis.hidden = true;
    }
  }

  function pruefen() {
    var erstes = null;
    Object.keys(FELDER).forEach(function (name) {
      var feld = document.getElementById(FELDER[name][0]);
      var ok = feld.checkValidity() && feld.value.trim() !== "";
      feldFehler(name, ok ? "" : FELDER[name][1]);
      if (!ok && !erstes) erstes = feld;
    });
    return erstes;
  }

  // Fehler verschwindet, sobald das Feld stimmt
  Object.keys(FELDER).forEach(function (name) {
    var feld = document.getElementById(FELDER[name][0]);
    feld.addEventListener("input", function () {
      if (feld.getAttribute("aria-invalid") === "true" && feld.checkValidity() && feld.value.trim() !== "")
        feldFehler(name, "");
    });
  });

  function nullBits(bytes) {
    var bits = 0;
    for (var i = 0; i < bytes.length; i++) {
      if (bytes[i] === 0) { bits += 8; continue; }
      var b = bytes[i];
      while ((b & 0x80) === 0) { bits++; b <<= 1; }
      return bits;
    }
    return bits;
  }

  async function loese(salz, schwierigkeit) {
    var enc = new TextEncoder();
    for (var nonce = 0; nonce < 50000000; nonce++) {
      var digest = await crypto.subtle.digest("SHA-256", enc.encode(salz + nonce));
      if (nullBits(new Uint8Array(digest)) >= schwierigkeit) return nonce;
    }
    throw new Error("keine Lösung");
  }

  // Nach dem Senden ersetzt eine deutliche Bestätigung das (leere) Formular, mit Empfänger und
  // Kopie; „Weitere Nachricht“ holt das Formular zurück (UX-Audit 16.11. WS-13)
  var aufgabeFehlt = false;
  function erfolg(name, kopie) {
    var kasten = document.createElement("div");
    kasten.className = "kontakt-erfolg";
    kasten.setAttribute("role", "status");
    kasten.tabIndex = -1;
    var titel = document.createElement("p");
    titel.className = "kontakt-erfolg-titel";
    titel.textContent = name
      ? t("Danke! Ihre Nachricht ist bei {name} angekommen.").replace("{name}", name)
      : t("Danke! Ihre Nachricht ist angekommen.");
    kasten.appendChild(titel);
    if (kopie) {
      var p = document.createElement("p");
      p.textContent = t("Eine Bestätigung geht an {email}.").replace("{email}", kopie);
      kasten.appendChild(p);
    }
    var weiter = document.createElement("button");
    weiter.type = "button";
    weiter.className = "knopf hell";
    weiter.textContent = t("Weitere Nachricht");
    weiter.addEventListener("click", function () {
      if (aufgabeFehlt) { location.reload(); return; }
      kasten.remove();
      form.hidden = false;
      document.getElementById("k-name").focus();
    });
    kasten.appendChild(weiter);
    form.hidden = true;
    form.parentNode.insertBefore(kasten, form);
    kasten.focus();
  }

  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    var erstes = pruefen();
    if (erstes) {
      zeige(t("Bitte die markierten Felder prüfen."), true);
      erstes.focus();
      return;
    }
    knopf.disabled = true;
    zeige(t("Nachricht wird vorbereitet …"));
    try {
      var nonce = await loese(form.dataset.salz, parseInt(form.dataset.schwierigkeit, 10) || 16);
      var warten = 3500 - (Date.now() - geladen);
      if (warten > 0) await new Promise(function (r) { setTimeout(r, warten); });
      var daten = {
        recipient: form.recipient.value,
        name: form.name.value.trim(),
        email: form.email.value.trim(),
        subject: form.subject.value.trim(),
        message: form.message.value.trim(),
        copy: form.copy.checked,
        homepage: form.homepage.value,
        challenge: form.dataset.token,
        nonce: nonce
      };
      var kopf = { "Content-Type": "application/json" };
      if (form.dataset.vorschau) kopf["X-Preview-Session"] = form.dataset.vorschau;
      zeige(t("Nachricht wird gesendet …"));
      var res = await fetch(form.dataset.ziel, {
        method: "POST",
        headers: kopf,
        body: JSON.stringify(daten),
        credentials: "omit",
        mode: "cors"
      });
      if (res.ok) {
        var an = document.getElementById("k-an");
        var kopie = daten.copy ? daten.email : "";
        form.reset();
        zeige("");
        knopf.disabled = false;
        erfolg(an ? an.textContent.trim() : "", kopie);
        // Für eine weitere Nachricht schon jetzt eine neue Aufgabe holen; geht das nicht, lädt
        // „Weitere Nachricht“ die Seite neu
        try { await neueAufgabe(); } catch (e) { aufgabeFehlt = true; }
        return;
      }
      var text = t("Die Nachricht konnte nicht gesendet werden.");
      var erstesFeld = null;
      try {
        var body = await res.json();
        if (body && body.code === "expired") {
          // Aufgabe abgelaufen: neue holen, Eingaben bleiben stehen
          try {
            await neueAufgabe();
            zeige(t("Sicherheitsprüfung erneuert. Ihre Nachricht bleibt erhalten. Bitte senden Sie erneut."), true);
          } catch (e) {
            zeige(t("Das Formular ist abgelaufen. Bitte kopieren Sie Ihre Nachricht und laden Sie die Seite neu."), true);
          }
          knopf.disabled = false;
          knopf.focus();
          return;
        }
        if (body && body.code === "used") {
          // Diese Aufgabe wurde schon benutzt: die Nachricht ist bereits angekommen
          zeige(t("Diese Nachricht ist bereits bei uns angekommen. Sie müssen sie nicht erneut senden."));
          try { await neueAufgabe(); } catch (e) { /* nächster Versuch lädt neu */ }
          knopf.disabled = false;
          return;
        }
        if (body && body.code === "too_fast") {
          await new Promise(function (r) { setTimeout(r, 1500); });
          text = body.detail;
        }
        else if (body && body.detail) text = body.detail;
        else if (body && body.recipient) {
          // Fester Empfänger nicht mehr erreichbar (z. B. Rolle inzwischen ohne Adresse)
          text = t("An diese Stelle kann gerade keine Nachricht gehen. Bitte schreiben Sie über den Menüpunkt „Kontakt“ an den Verein.");
        }
        else if (body && typeof body === "object") {
          // Feldfehler von HUBIplan dem jeweiligen Feld zuordnen
          Object.keys(body).forEach(function (name) {
            if (!FELDER[name]) return;
            var meldung = Array.isArray(body[name]) ? body[name].join(" ") : String(body[name]);
            feldFehler(name, meldung);
            if (!erstesFeld) erstesFeld = document.getElementById(FELDER[name][0]);
          });
          text = erstesFeld ? t("Bitte die markierten Felder prüfen.") : t("Bitte die Angaben prüfen.");
        }
      } catch (e) { /* keine JSON-Antwort */ }
      if (res.status === 429) text = t("Zu viele Nachrichten. Bitte später erneut versuchen.");
      zeige(text, true);
      knopf.disabled = false;
      if (erstesFeld) erstesFeld.focus();
    } catch (e) {
      zeige(t("Die Nachricht konnte nicht gesendet werden. Bitte später erneut versuchen."), true);
      knopf.disabled = false;
    }
  });
})();
