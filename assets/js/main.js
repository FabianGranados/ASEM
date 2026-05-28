/* Marca html.js para que el CSS aplique animaciones */
document.documentElement.classList.add('js');

/* Auto-detect site updates (workaround del CDN cache de GitHub Pages).
   Hace polling de /version.txt cada 90s. Si la version cambia, muestra
   un banner discreto con boton para recargar. */
(function () {
  var CURRENT_VERSION = null;
  var POLL_INTERVAL = 90000;  // 90 segundos
  function fetchVersion() {
    fetch('/version.txt?t=' + Date.now(), { cache: 'no-store' })
      .then(function (r) { return r.text(); })
      .then(function (v) {
        v = v.trim();
        if (!CURRENT_VERSION) {
          CURRENT_VERSION = v;
          return;
        }
        if (v !== CURRENT_VERSION) {
          showUpdateBanner();
        }
      })
      .catch(function () { /* offline ok */ });
  }
  function showUpdateBanner() {
    if (document.getElementById('site-update-banner')) return;
    var bar = document.createElement('div');
    bar.id = 'site-update-banner';
    bar.innerHTML = '<span>Hay una versión nueva del sitio.</span> <button type="button">Actualizar</button>';
    bar.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;background:#0D2A32;color:#fff;padding:10px 16px;display:flex;justify-content:center;align-items:center;gap:14px;font:14px/1.4 -apple-system,BlinkMacSystemFont,sans-serif;box-shadow:0 2px 12px rgba(0,0,0,0.3);';
    var btn = bar.querySelector('button');
    btn.style.cssText = 'background:#40B0CB;color:#0D2A32;border:0;padding:6px 14px;border-radius:3px;font-weight:600;cursor:pointer;font-family:inherit;';
    btn.addEventListener('click', function () {
      // Hard reload con timestamp para bypassear CDN
      var url = window.location.pathname + '?v=' + Date.now() + window.location.hash;
      window.location.replace(url);
    });
    document.body.appendChild(bar);
  }
  // Primera lectura inmediata, luego polling
  fetchVersion();
  setInterval(fetchVersion, POLL_INTERVAL);
})();

/* Anti-robo de imagenes — bloquea click derecho y drag-and-drop sobre <img>.
   Detiene el ~95% del robo casual. No detiene DevTools ni screenshots
   (eso es imposible en navegador), pero detiene "click derecho > guardar". */
(function () {
  document.addEventListener('contextmenu', function (e) {
    if (e.target && e.target.tagName === 'IMG') {
      e.preventDefault();
      return false;
    }
  }, false);
  document.addEventListener('dragstart', function (e) {
    if (e.target && e.target.tagName === 'IMG') {
      e.preventDefault();
      return false;
    }
  }, false);
  // Tambien bloquea click derecho sobre el marco del showcase y cat-cards
  // (que usan background-image y otros divs como capa de proteccion)
  document.querySelectorAll('.showcase-frame, .cat-card, .galeria-grid figure').forEach(function (el) {
    el.addEventListener('contextmenu', function (e) { e.preventDefault(); });
  });
})();

/* Navbar scroll border */
(function () {
  var nav = document.getElementById('navbar');
  if (!nav) return;
  function onScroll() {
    if (window.scrollY > 60) nav.classList.add('scrolled');
    else nav.classList.remove('scrolled');
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();

/* Mobile menu */
(function () {
  var burger = document.getElementById('navBurger');
  var overlay = document.getElementById('navOverlay');
  if (!burger || !overlay) return;
  burger.addEventListener('click', function () {
    burger.classList.toggle('open');
    overlay.classList.toggle('open');
    document.body.style.overflow = overlay.classList.contains('open') ? 'hidden' : '';
  });
  overlay.querySelectorAll('a').forEach(function (a) {
    a.addEventListener('click', function () {
      burger.classList.remove('open');
      overlay.classList.remove('open');
      document.body.style.overflow = '';
    });
  });
})();

/* Hero slideshow — cycle every 2.5s with crossfade, pause when tab hidden */
(function () {
  var slides = document.querySelectorAll('.hero-slide');
  var dots = document.querySelectorAll('.hero-dots button');
  if (slides.length < 2) return;
  var idx = 0;
  var timer = null;
  function show(n) {
    idx = (n + slides.length) % slides.length;
    slides.forEach(function (s, i) { s.classList.toggle('is-active', i === idx); });
    dots.forEach(function (d, i) { d.classList.toggle('is-active', i === idx); });
  }
  function next() { show(idx + 1); }
  function start() { stop(); timer = setInterval(next, 2500); }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }
  dots.forEach(function (d, i) {
    d.addEventListener('click', function () { show(i); start(); });
  });
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) stop(); else start();
  });
  start();
})();

/* Sticky WhatsApp mobile — aparece despues de scroll inicial (>200px) */
(function () {
  var sticky = document.querySelector('.wa-sticky-mobile');
  if (!sticky) return;
  function onScroll() {
    if (window.scrollY > 200) sticky.classList.add('is-visible');
    else sticky.classList.remove('is-visible');
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();

/* WhatsApp floating bubble — rota frases con typing indicator (simula chat) */
(function () {
  var bubble = document.querySelector('.wa-bubble');
  var msgs = document.querySelectorAll('.wa-msg');
  if (!bubble || msgs.length < 2) return;
  var idx = 0;
  function rotate() {
    bubble.classList.add('is-typing');
    setTimeout(function () {
      msgs[idx].classList.remove('is-active');
      idx = (idx + 1) % msgs.length;
      msgs[idx].classList.add('is-active');
      bubble.classList.remove('is-typing');
    }, 900);
  }
  setInterval(rotate, 3800);
})();

/* Showcase gallery — bg blureado sigue a la foto frontal, navegacion arrows + auto */
(function () {
  var imgs = document.querySelectorAll('.showcase-img');
  var bg = document.getElementById('showcaseBg');
  var prev = document.getElementById('showcasePrev');
  var next = document.getElementById('showcaseNext');
  var current = document.getElementById('showcaseCurrent');
  var caption = document.getElementById('showcaseCaption');
  if (!imgs.length || !bg) return;
  var idx = 0;
  var timer = null;
  var INTERVAL = 5000;

  function pad(n) { return n < 10 ? '0' + n : '' + n; }

  function show(n) {
    idx = (n + imgs.length) % imgs.length;
    imgs.forEach(function (img, i) { img.classList.toggle('is-active', i === idx); });
    bg.style.backgroundImage = "url('" + imgs[idx].getAttribute('src') + "')";
    if (current) current.textContent = pad(idx + 1);
    if (caption) caption.textContent = imgs[idx].getAttribute('alt') || '';
  }
  function nextImg() { show(idx + 1); }
  function prevImg() { show(idx - 1); }
  function start() { stop(); timer = setInterval(nextImg, INTERVAL); }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }
  function reset() { stop(); start(); }

  if (next) next.addEventListener('click', function () { nextImg(); reset(); });
  if (prev) prev.addEventListener('click', function () { prevImg(); reset(); });

  // Keyboard arrows when showcase visible
  document.addEventListener('keydown', function (e) {
    var section = document.getElementById('eventos');
    if (!section) return;
    var rect = section.getBoundingClientRect();
    if (rect.top > window.innerHeight || rect.bottom < 0) return;
    if (e.key === 'ArrowRight') { nextImg(); reset(); }
    if (e.key === 'ArrowLeft')  { prevImg(); reset(); }
  });

  // Touch swipe on mobile
  var frame = document.querySelector('.showcase-frame');
  if (frame) {
    var startX = 0, startY = 0;
    frame.addEventListener('touchstart', function (e) {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    }, { passive: true });
    frame.addEventListener('touchend', function (e) {
      var dx = e.changedTouches[0].clientX - startX;
      var dy = e.changedTouches[0].clientY - startY;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) {
        if (dx < 0) nextImg(); else prevImg();
        reset();
      }
    }, { passive: true });
  }

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) stop(); else start();
  });

  start();
})();

/* Scroll reveal */
(function () {
  var els = document.querySelectorAll('.reveal');
  els.forEach(function (el) {
    var parent = el.parentElement;
    var siblings = parent ? Array.from(parent.children).filter(function (c) { return c.classList.contains('reveal'); }) : [];
    var idx = siblings.indexOf(el);
    if (idx > 0) el.style.transitionDelay = (idx * 80) + 'ms';
  });
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  els.forEach(function (el) { io.observe(el); });
})();

/* WhatsApp lead split: 65% Laura / 35% Paola, sticky por visitante via localStorage.
   Reemplaza el href de todos los botones .btn-wa, .wa-float, .wa-sticky-mobile
   con el numero asignado. Si window.gtag existe, dispara evento al click para
   trackear distribucion en Google Analytics. */
(function () {
  var STORAGE_KEY = 'asem_wa_assigned';
  var LAURA = '573013228490';
  var PAOLA = '573016003031';

  function getAssignment() {
    var saved = null;
    try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) {}
    if (saved === 'L' || saved === 'P') return saved;
    var assigned = Math.random() < 0.65 ? 'L' : 'P';
    try { localStorage.setItem(STORAGE_KEY, assigned); } catch (e) {}
    return assigned;
  }

  var assigned = getAssignment();
  var phone = assigned === 'L' ? LAURA : PAOLA;
  var comercial = assigned === 'L' ? 'laura' : 'paola';

  // Reemplaza todos los wa.me/<LAURA> con el asignado, solo en botones accionables
  var selectors = ['a.btn-wa', 'a.wa-float', 'a.wa-sticky-mobile'];
  document.querySelectorAll(selectors.join(',')).forEach(function (el) {
    var href = el.getAttribute('href') || '';
    // Solo reemplaza si tiene el numero por default (Laura). Footer info links no usan estas clases.
    href = href.replace(/wa\.me\/57\d{10}/, 'wa.me/' + phone);
    el.setAttribute('href', href);
    el.addEventListener('click', function () {
      if (typeof window.gtag === 'function') {
        window.gtag('event', 'whatsapp_click', {
          event_category: 'lead',
          event_label: comercial,
          value: 1
        });
      }
    });
  });
})();
