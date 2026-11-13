// Bilderkarussell: wechselt ruhig von selbst (Zeit je Karussell aus HUBIplan,
// data-takt in Sekunden, sonst 7), danach wieder von vorn. Hält beim
// Darüberfahren, beim Fokus und auf Knopfdruck an. Bei „Bewegung reduzieren“
// startet es angehalten. Die Knöpfe liegen im Bild und erscheinen bei Maus,
// Tastaturfokus oder nach Antippen. Ohne Skript lässt sich das Band seitlich
// wischen bzw. scrollen. Auf Wunsch beginnt es mit einem zufälligen Bild (data-zufall).
// Texte in der Sprache der Seite (basis.html, Element seite-texte)
const t = (s) => {
  const e = document.getElementById('seite-texte')
  if (!e) return s
  try {
    return JSON.parse(e.textContent)[s] || s
  } catch {
    return s
  }
}
const STANDARD = 7
const ANTIPPEN = 4000 // so lange bleiben die Knöpfe nach dem Antippen sichtbar

document.querySelectorAll('[data-karussell]').forEach((box) => {
  const band = box.querySelector('.karussell-band')
  const bilder = Array.from(band.children)
  const zaehler = box.querySelector('.karussell-zaehler')
  const zurueck = box.querySelector('[data-zurueck]')
  const weiter = box.querySelector('[data-weiter]')
  const pause = box.querySelector('[data-pause]')
  const sekunden = Number(box.dataset.takt)
  // Stilregler „Bilderkarussell blättert“: nur von Hand, langsam (doppelte Zeit) oder normal
  const art = document.documentElement.dataset.stCarousel
  const grund = sekunden >= 3 && sekunden <= 30 ? sekunden : STANDARD
  const takt = grund * 1000 * (art === 'slow' ? 2 : 1)
  const ruhig = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  box.querySelector('.karussell-steuerung').hidden = false

  let angehalten = ruhig || art === 'off' // vom Besucher angehalten
  let verweilt = false // Maus oder Fokus im Karussell
  let uhr

  const aktuell = () => Math.round(band.scrollLeft / band.clientWidth)
  const zeige = (i) => {
    const ziel = (i + bilder.length) % bilder.length
    band.scrollTo({ left: ziel * band.clientWidth, behavior: ruhig ? 'auto' : 'smooth' })
  }
  const auffrischen = () => {
    zaehler.textContent = `${aktuell() + 1} / ${bilder.length}`
  }
  const planen = () => {
    clearTimeout(uhr)
    if (!angehalten && !verweilt && !document.hidden) {
      uhr = setTimeout(() => {
        zeige(aktuell() + 1)
        planen()
      }, takt)
    }
  }
  const setzePause = (an) => {
    angehalten = an
    pause.setAttribute('aria-pressed', String(an))
    pause.setAttribute('aria-label', an ? t('Weiter abspielen') : t('Anhalten'))
    pause.textContent = an ? '▶' : '❚❚'
    // Während es läuft, Wechsel nicht ansagen (sonst redet der Screenreader ständig)
    zaehler.setAttribute('aria-live', an ? 'polite' : 'off')
    planen()
  }

  zurueck.addEventListener('click', () => {
    zeige(aktuell() - 1)
    planen()
  })
  weiter.addEventListener('click', () => {
    zeige(aktuell() + 1)
    planen()
  })
  pause.addEventListener('click', () => setzePause(!angehalten))
  band.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault()
      zeige(aktuell() + (e.key === 'ArrowLeft' ? -1 : 1))
    }
  })
  const halten = (an) => () => {
    verweilt = an
    planen()
  }
  box.addEventListener('mouseenter', halten(true))
  box.addEventListener('mouseleave', halten(false))
  box.addEventListener('focusin', halten(true))
  box.addEventListener('focusout', (e) => {
    if (!box.contains(e.relatedTarget)) halten(false)()
  })
  // Touch: Antippen zeigt die Knöpfe eine Weile und hält so lange an
  let ausblenden
  box.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'mouse') return
    box.classList.add('zeigen')
    halten(true)()
    clearTimeout(ausblenden)
    ausblenden = setTimeout(() => {
      box.classList.remove('zeigen')
      if (!box.contains(document.activeElement)) halten(false)()
    }, ANTIPPEN)
  })
  document.addEventListener('visibilitychange', planen)
  let warte
  band.addEventListener('scroll', () => {
    clearTimeout(warte)
    warte = setTimeout(auffrischen, 80)
  })
  // Auf Wunsch (HUBIplan: „Beginnt mit einem zufälligen Bild“) zufällig beginnen
  const start = 'zufall' in box.dataset ? Math.floor(Math.random() * bilder.length) : 0
  if (start > 0) {
    bilder[start].querySelector('img')?.removeAttribute('loading')
    band.scrollTo({ left: start * band.clientWidth, behavior: 'auto' })
  }
  setzePause(angehalten)
  auffrischen()
})
