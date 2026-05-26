/* Marca html.js para que el CSS aplique animaciones */
document.documentElement.classList.add('js');

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
