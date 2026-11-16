// „Zeigen“ in der Vorschau von HUBIplan (Webseite › Gestaltung › Feinabstimmung, Ralf 16.11.2026):
// HUBIplan schaltet den Modus per postMessage ein; dann rahmt die Webseite beim Überfahren
// Kopf, Titelbild, Bereiche und Fuß ein und meldet einen Klick als Bereich an HUBIplan zurück.
// Nur in der Vorschau geladen und nur, wenn die Seite in einem Rahmen steht.
(function () {
  'use strict'
  if (window.parent === window) return
  // Reihenfolge zählt: das Genaueste zuerst
  var TEILE = [
    ['#kopf', 'kopf'],
    ['#fuss', 'fuss'],
    ['.buehne, .karussell, .titelbild, .seiten-titelbild', 'startseite'],
    [
      '.termine, .monat, .kacheln, .einheiten-liste, .galerie-bilder, .galerie-alben, .ehrungen-karten, .personenkarte, .wuerde, .chronik, .chronik-auszug-liste, .zeitleiste-abschnitt, .rangliste, .ergebnisliste',
      'bereiche',
    ],
    ['main h1', 'unterseiten'],
    ['body[data-seite="start"] main > section', 'startseite'],
    ['#inhalt', 'grundstil'],
  ]
  var an = false
  var namen = {}
  var rahmen = null
  var schild = null

  function finde(el) {
    if (!el || !el.closest) return null
    for (var i = 0; i < TEILE.length; i++) {
      var treffer = el.closest(TEILE[i][0])
      if (treffer) return { el: treffer, bereich: TEILE[i][1] }
    }
    return null
  }
  function weg() {
    if (rahmen) rahmen.classList.remove('zeigen-rahmen')
    rahmen = null
    if (schild) schild.hidden = true
  }
  function zeige(teil) {
    if (rahmen === teil.el) return
    weg()
    rahmen = teil.el
    rahmen.classList.add('zeigen-rahmen')
    if (!schild) {
      schild = document.createElement('div')
      schild.className = 'zeigen-schild'
      schild.setAttribute('aria-hidden', 'true')
      document.body.appendChild(schild)
    }
    var r = rahmen.getBoundingClientRect()
    schild.textContent = namen[teil.bereich] || teil.bereich
    schild.style.top = Math.max(r.top + window.scrollY + 6, window.scrollY + 6) + 'px'
    schild.style.left = r.left + window.scrollX + 6 + 'px'
    schild.hidden = false
  }

  window.addEventListener('message', function (e) {
    if (e.source !== window.parent) return
    var d = e.data
    if (!d || d.hubiplan !== 'zeigen') return
    an = !!d.an
    if (d.namen && typeof d.namen === 'object') namen = d.namen
    document.documentElement.toggleAttribute('data-zeigen', an)
    if (!an) weg()
  })
  document.addEventListener('mouseover', function (e) {
    if (!an) return
    var teil = finde(e.target)
    if (teil) zeige(teil)
    else weg()
  })
  document.addEventListener(
    'click',
    function (e) {
      if (!an) return
      var teil = finde(e.target)
      if (!teil) return
      // Im Zeigemodus führt kein Link weg; der Klick wählt nur den Bereich
      e.preventDefault()
      e.stopPropagation()
      window.parent.postMessage({ hubiplan: 'bereich', bereich: teil.bereich }, '*')
    },
    true,
  )
  // HUBIplan weiß so, dass die Seite zeigen kann (ältere Stände melden sich nicht)
  window.parent.postMessage({ hubiplan: 'zeigen-bereit' }, '*')
})()
