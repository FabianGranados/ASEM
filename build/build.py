#!/usr/bin/env python3
"""
ASEM — Generador del sitio estatico.

Lee build/pages.json (extraido del Excel SEO) y emite:
  - index.html (home)
  - <slug>/index.html para cada subpagina (17 en total)
  - assets/img/<filename>.<ext> placeholders con el alt text dibujado
  - sitemap.xml
  - robots.txt

Para regenerar:  python3 build/build.py
"""
import json
import os
import re
import sys
from html import escape
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / 'build' / 'pages.json').read_text(encoding='utf-8'))

SITE = 'https://alquilersalasparaeventosymobiliario.com'
WA_PHONE = '573013228490'
WA_LINK = f'https://wa.me/{WA_PHONE}?text=Hola,%20quiero%20cotizar%20mobiliario'

# Map "MOBILIARIO X" labels (uppercase, may include tilde) to slug + display name + intro text
ESTILOS = {
    'MOBILIARIO LOUNGE':     ('salas-lounge-para-eventos-en-bogota',     'Lounge',     'Salas comodas en cuero y velvet para conversacion intima.'),
    'MOBILIARIO INDUSTRIAL': ('mesas-sillas-industriales-eventos-bogota','Industrial', 'Madera, hierro y luz calida con energia urbana.'),
    'MOBILIARIO RUSTICO':    ('salas-rusticas-para-eventos-bogota',      'Rustico',    'Texturas naturales para bodas y celebraciones al aire libre.'),
    'MOBILIARIO RÚSTICO':    ('salas-rusticas-para-eventos-bogota',      'Rustico',    'Texturas naturales para bodas y celebraciones al aire libre.'),
    'MOBILIARIO PICNIC':     ('mesas-picnic-para-eventos-bogota',        'Picnic',     'Mesas bajas, cojines y mantas para encuentros relajados.'),
    'MOBILIARIO LED':        ('mobiliario-led-eventos-bogota',           'LED',        'Mobiliario iluminado para fiestas con alma de club.'),
    'MOBILIARIO ACAPULCO':   ('sillas-acapulco-para-eventos-bogota',     'Acapulco',   'Sillas iconicas para eventos frescos con aire tropical.'),
}

# Categoria adicional — Comedores rusticos (link)
CATEGORIAS = [
    ('Salas Lounge',           'salas-lounge-para-eventos-en-bogota'),
    ('Salas Rusticas',         'salas-rusticas-para-eventos-bogota'),
    ('Mesas Lounge',           'mesas-para-eventos-bogota'),
    ('Sillas Lounge',          'sillas-para-eventos-bogota'),
    ('Sillas Interlocutoras',  'sillas-para-juntas-bogota'),
    ('Poltronas Lounge',       'poltronas-para-eventos-en-bogota'),
    ('Comedores Rusticos',     'comedores-rusticos-eventos-bogota'),
]
ESTILO_MENU = [
    ('Mobiliario LED',        'mobiliario-led-eventos-bogota'),
    ('Mobiliario Industrial', 'mesas-sillas-industriales-eventos-bogota'),
    ('Mobiliario Picnic',     'mesas-picnic-para-eventos-bogota'),
    ('Mobiliario Acapulco',   'sillas-acapulco-para-eventos-bogota'),
]
ACCESORIOS_MENU = [
    ('Calefactores de Ambiente', 'calefactores-ambiente-para-eventos'),
    ('Separadores de Fila',      'separadores-de-fila-para-eventos'),
    ('Bombillos Vintage',        'bombillos-vintage-para-eventos'),
    ('Pista de Baile',           'pista-de-baile-para-eventos'),
]

# Paleta usada para placeholders de imagenes (por tipo de pagina)
PLACEHOLDER_PALETTE = {
    'lounge':   ((64, 176, 203), (168, 221, 233)),
    'rustico':  ((151, 122, 88),  (212, 187, 155)),
    'mesas':    ((26, 122, 146),  (168, 221, 233)),
    'sillas':   ((64, 176, 203),  (240, 192, 96)),
    'led':      ((46, 14, 88),    (240, 192, 96)),
    'industrial': ((13, 42, 50),  (102, 102, 102)),
    'picnic':   ((131, 168, 84),  (240, 192, 96)),
    'acapulco': ((64, 176, 203),  (240, 192, 96)),
    'comedores':((151, 122, 88),  (212, 187, 155)),
    'calefactores': ((212, 100, 50), (240, 192, 96)),
    'separadores':  ((130, 130, 130), (240, 192, 96)),
    'bombillos':    ((26, 32, 50),   (240, 192, 96)),
    'pista':        ((46, 14, 88),   (64, 176, 203)),
    'acarreos':     ((13, 42, 50),   (240, 192, 96)),
    'default':      ((64, 176, 203), (168, 221, 233)),
}

def palette_for(page_key, filename):
    k = (page_key + ' ' + filename).lower()
    if 'lounge' in k:        return PLACEHOLDER_PALETTE['lounge']
    if 'rustico' in k or 'rusticas' in k or 'rustica' in k: return PLACEHOLDER_PALETTE['rustico']
    if 'industrial' in k:    return PLACEHOLDER_PALETTE['industrial']
    if 'comedor' in k:       return PLACEHOLDER_PALETTE['comedores']
    if 'led' in k:           return PLACEHOLDER_PALETTE['led']
    if 'picnic' in k:        return PLACEHOLDER_PALETTE['picnic']
    if 'acapulco' in k:      return PLACEHOLDER_PALETTE['acapulco']
    if 'calefact' in k:      return PLACEHOLDER_PALETTE['calefactores']
    if 'separador' in k:     return PLACEHOLDER_PALETTE['separadores']
    if 'bombillo' in k or 'vintage' in k: return PLACEHOLDER_PALETTE['bombillos']
    if 'pista' in k or 'baile' in k:      return PLACEHOLDER_PALETTE['pista']
    if 'acarreo' in k or 'trasteo' in k or 'mudanza' in k: return PLACEHOLDER_PALETTE['acarreos']
    if 'mesa' in k:          return PLACEHOLDER_PALETTE['mesas']
    if 'silla' in k:         return PLACEHOLDER_PALETTE['sillas']
    return PLACEHOLDER_PALETTE['default']

def get_font(size):
    for path in [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def wrap_text(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ''
    for w in words:
        test = (cur + ' ' + w).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def make_placeholder(out_path, alt_text, palette):
    """Genera una imagen 800x600 con gradiente y el alt text superpuesto."""
    W, H = 800, 600
    c1, c2 = palette
    img = Image.new('RGB', (W, H), c1)
    # gradiente vertical simple
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        for x in range(W):
            px[x, y] = (r, g, b)
    draw = ImageDraw.Draw(img)
    # marco interno
    draw.rectangle([(24, 24), (W - 24, H - 24)], outline=(255, 255, 255, 90), width=2)
    # ASEM monogram en esquina
    asem_font = get_font(28)
    draw.text((40, 36), 'ASEM', font=asem_font, fill=(255, 255, 255))
    draw.text((40, 70), 'PLACEHOLDER', font=get_font(14), fill=(255, 255, 255, 200))
    # alt text centrado
    text = alt_text.strip() if alt_text else os.path.splitext(os.path.basename(out_path))[0].replace('-', ' ')
    text = text.upper()
    font = get_font(34)
    lines = wrap_text(draw, text, font, W - 120)
    line_h = font.getbbox('Ag')[3] + 8
    total_h = line_h * len(lines)
    y = (H - total_h) / 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((W - w) / 2, y), line, font=font, fill=(255, 255, 255))
        y += line_h
    ext = os.path.splitext(out_path)[1].lower()
    fmt = {'.webp': 'WEBP', '.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG'}.get(ext, 'PNG')
    img.save(out_path, fmt, quality=82)

# ============================================================
# Plantillas HTML
# ============================================================

LOGO_SVG = '''<svg class="brand-logo" width="36" height="42" viewBox="0 0 72 82" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <rect x="0" y="58" width="6" height="14" fill="#FFFFFF" rx="1"></rect>
  <rect x="66" y="58" width="6" height="14" fill="#FFFFFF" rx="1"></rect>
  <rect x="0" y="51" width="72" height="9" fill="#FFFFFF" rx="1"></rect>
  <rect x="0" y="22" width="9" height="32" fill="#FFFFFF" rx="1"></rect>
  <rect x="63" y="22" width="9" height="32" fill="#FFFFFF" rx="1"></rect>
  <rect x="9" y="36" width="54" height="19" fill="#40B0CB" rx="2"></rect>
  <polygon points="36,0 54,22 18,22" fill="#FFFFFF"></polygon>
</svg>'''

WORDMARK = '<span class="brand-wordmark" aria-label="ASEM"><span class="a">A</span><span class="s">S</span><span class="e">E</span><span class="m">M</span></span>'

def asset(path, depth):
    """Devuelve URL relativa al CSS/JS desde una pagina con `depth` niveles bajo root."""
    return '../' * depth + path

def link_to(slug, depth):
    """Link absoluto-relativo a un slug interno."""
    if not slug:
        return '../' * depth or './'
    return '../' * depth + slug + '/'

def navbar_html(depth):
    home = '../' * depth if depth else './'
    estilos = '\n'.join(f'      <a href="{link_to(s, depth)}">{escape(n)}</a>' for n, s in ESTILO_MENU)
    categorias = '\n'.join(f'      <a href="{link_to(s, depth)}">{escape(n)}</a>' for n, s in CATEGORIAS)
    accesorios = '\n'.join(f'      <a href="{link_to(s, depth)}">{escape(n)}</a>' for n, s in ACCESORIOS_MENU)
    overlay_estilos = '\n'.join(f'      <li><a href="{link_to(s, depth)}">{escape(n)}</a></li>' for n, s in ESTILO_MENU)
    overlay_categorias = '\n'.join(f'      <li><a href="{link_to(s, depth)}">{escape(n)}</a></li>' for n, s in CATEGORIAS)
    overlay_accesorios = '\n'.join(f'      <li><a href="{link_to(s, depth)}">{escape(n)}</a></li>' for n, s in ACCESORIOS_MENU)
    return f'''<nav class="navbar" id="navbar">
  <a href="{home}" class="brand" aria-label="ASEM home">
    {LOGO_SVG}
    <span class="brand-sep" aria-hidden="true"></span>
    {WORDMARK}
  </a>

  <div class="nav-links">
    <div class="nav-item"><a href="{home}">Inicio</a></div>
    <div class="nav-item">
      <button class="nav-trigger" type="button">Mobiliario por estilo</button>
      <div class="nav-dropdown">
{estilos}
      </div>
    </div>
    <div class="nav-item">
      <button class="nav-trigger" type="button">Mobiliario por categoria</button>
      <div class="nav-dropdown">
{categorias}
      </div>
    </div>
    <div class="nav-item">
      <button class="nav-trigger" type="button">Accesorios</button>
      <div class="nav-dropdown">
{accesorios}
      </div>
    </div>
    <div class="nav-item"><a href="{link_to('acarreos-trasteos-y-mudanzas-bogota', depth)}">Acarreos y Mudanzas</a></div>
  </div>

  <a class="btn-cotizar desktop-only" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar ahora</a>
  <button class="nav-burger" id="navBurger" aria-label="Menu"><span></span><span></span><span></span></button>
</nav>

<div class="nav-overlay" id="navOverlay">
  <a href="{home}">Inicio</a>
  <details>
    <summary>Mobiliario por estilo</summary>
    <ul>
{overlay_estilos}
    </ul>
  </details>
  <details>
    <summary>Mobiliario por categoria</summary>
    <ul>
{overlay_categorias}
    </ul>
  </details>
  <details>
    <summary>Accesorios</summary>
    <ul>
{overlay_accesorios}
    </ul>
  </details>
  <a href="{link_to('acarreos-trasteos-y-mudanzas-bogota', depth)}">Acarreos, Trasteos y Mudanzas</a>
  <a class="btn-cotizar" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar ahora</a>
</div>'''

def footer_html(depth):
    nav = '\n'.join(f'        <li><a href="{link_to(s, depth)}">{escape(n)}</a></li>' for n, s in CATEGORIAS[:4] + [('Acarreos y Mudanzas', 'acarreos-trasteos-y-mudanzas-bogota')])
    estilos = '\n'.join(f'        <li><a href="{link_to(s, depth)}">{escape(n)}</a></li>' for n, s in ESTILO_MENU)
    img_prefix = '../' * depth if depth else './'
    return f'''<footer class="footer">
  <div class="footer-inner">
    <div class="footer-col footer-brand">
      <a href="{'../' * depth if depth else './'}" class="brand" aria-label="ASEM home">
        {LOGO_SVG}
        <span class="brand-sep"></span>
        {WORDMARK}
      </a>
      <p class="footer-tag">Alquiler de mobiliario<br>para eventos en Bogota, Colombia</p>
      <img class="footer-logo-img" src="{img_prefix}assets/img/ASEM-mobiliario-para-eventos-en-bogota.png" alt="ASEM mobiliario para eventos en bogota" loading="lazy" width="160" height="80">
    </div>
    <div class="footer-col">
      <span class="footer-col-title">Navegacion</span>
      <ul>
{nav}
      </ul>
    </div>
    <div class="footer-col">
      <span class="footer-col-title">Estilos</span>
      <ul>
{estilos}
      </ul>
    </div>
    <div class="footer-col">
      <span class="footer-col-title">Contacto</span>
      <ul>
        <li><a href="https://wa.me/573013228490" target="_blank" rel="noopener">
          <svg class="social-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M.057 24l1.687-6.163a11.867 11.867 0 0 1-1.587-5.946C.16 5.335 5.495 0 12.05 0a11.817 11.817 0 0 1 8.413 3.488 11.824 11.824 0 0 1 3.48 8.414c-.003 6.557-5.338 11.892-11.893 11.892a11.9 11.9 0 0 1-5.688-1.448L.057 24zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884a9.86 9.86 0 0 0 1.692 5.543l-.999 3.648 3.796-.99zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"></path></svg>
          WhatsApp 301 322 8490</a></li>
        <li><a href="https://wa.me/573016003031" target="_blank" rel="noopener">
          <svg class="social-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M.057 24l1.687-6.163a11.867 11.867 0 0 1-1.587-5.946C.16 5.335 5.495 0 12.05 0a11.817 11.817 0 0 1 8.413 3.488 11.824 11.824 0 0 1 3.48 8.414c-.003 6.557-5.338 11.892-11.893 11.892a11.9 11.9 0 0 1-5.688-1.448L.057 24zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884a9.86 9.86 0 0 0 1.692 5.543l-.999 3.648 3.796-.99zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"></path></svg>
          WhatsApp 301 600 3031</a></li>
        <li><a href="https://instagram.com/alquilersalasparaeventos" target="_blank" rel="noopener">
          <svg class="social-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"></rect><circle cx="12" cy="12" r="4"></circle><circle cx="17.5" cy="6.5" r="0.6" fill="currentColor"></circle></svg>
          @alquilersalasparaeventos</a></li>
      </ul>
    </div>
  </div>
  <div class="footer-bottom">
    <div class="footer-copy">ASEM &copy; 2026 &middot; Bogota, Colombia</div>
    <div class="footer-copy">Laura 301 322 8490 &middot; Paola 301 600 3031</div>
  </div>
</footer>

<a class="wa-float" href="{WA_LINK}" target="_blank" rel="noopener" aria-label="WhatsApp">
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M.057 24l1.687-6.163a11.867 11.867 0 0 1-1.587-5.946C.16 5.335 5.495 0 12.05 0a11.817 11.817 0 0 1 8.413 3.488 11.824 11.824 0 0 1 3.48 8.414c-.003 6.557-5.338 11.892-11.893 11.892a11.9 11.9 0 0 1-5.688-1.448L.057 24zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884a9.86 9.86 0 0 0 1.692 5.543l-.999 3.648 3.796-.99zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"></path></svg>
</a>'''

def head_html(title, description, canonical, depth, og_image_filename=None):
    css_path = asset('assets/css/styles.css', depth)
    og_url = f'{SITE}/{canonical}/' if canonical else f'{SITE}/'
    og_img = ''
    if og_image_filename:
        og_img = f'<meta property="og:image" content="{SITE}/assets/img/{escape(og_image_filename)}">'
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description)}">
<link rel="canonical" href="{og_url}">
<meta property="og:type" content="website">
<meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(description)}">
<meta property="og:url" content="{og_url}">
{og_img}
<meta name="robots" content="index,follow">
<link rel="stylesheet" href="{css_path}">
</head>
<body>'''

def cta_block(h2, h3, dorado=False):
    btn_class = 'btn-large' if not dorado else 'btn btn-turquesa'
    return f'''<section class="cta-block">
  <h2>{escape(h2)}</h2>
  <h3>{escape(h3)}</h3>
  <a class="btn-large" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar por WhatsApp
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"></path><path d="m13 5 7 7-7 7"></path></svg>
  </a>
</section>'''

def cta_final_block():
    """Bloque final con headline visual sin usar h1/h2/h3 para no inflar las cuentas SEO del Excel."""
    return f'''<section class="cta-final" id="contacto">
  <span class="label reveal">Cuentanos</span>
  <div class="cta-final-headline reveal" role="heading" aria-level="2">Tienes un evento<br>en mente?</div>
  <p class="cta-final-sub reveal">Cuentanos y creamos el ambiente perfecto.</p>
  <a class="btn-large reveal" href="{WA_LINK}" target="_blank" rel="noopener">Hablar por WhatsApp
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"></path><path d="m13 5 7 7-7 7"></path></svg>
  </a>
  <div class="cta-phones reveal">301 322 8490 &middot; 301 600 3031</div>
</section>'''

# ============================================================
# Parseo del CONTENIDO COMPLETO
# ============================================================

def parse_contenido(raw):
    """Devuelve dict con intro (str), productos (list), ventajas (list), complemento (str)."""
    if not raw:
        return {}
    parts = {'intro': '', 'productos': [], 'ventajas': [], 'complemento': '', 'keywords': ''}
    lines = [l.rstrip() for l in raw.split('\n')]
    section = 'intro'
    intro_buf = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        ls = s.lower()
        if ls.startswith('productos:'):
            section = 'productos'
            rest = s.split(':', 1)[1].strip()
            if rest:
                parts['productos'] = [p.strip() for p in re.split(r'\s*/\s*', rest) if p.strip()]
            continue
        if ls.startswith('ventajas:'):
            section = 'ventajas'
            continue
        if ls.startswith('complementa') or ls.startswith('complementa tu'):
            section = 'complemento'
            parts['complemento'] = s
            continue
        if ls.startswith('keywords:'):
            section = 'keywords'
            parts['keywords'] = s.split(':', 1)[1].strip()
            continue
        if section == 'intro':
            intro_buf.append(s)
        elif section == 'ventajas':
            v = re.sub(r'^[-•\*]\s*', '', s).strip()
            if v:
                parts['ventajas'].append(v)
        elif section == 'productos':
            parts['productos'].extend([p.strip() for p in re.split(r'\s*/\s*', s) if p.strip()])
    parts['intro'] = '\n\n'.join(intro_buf)
    return parts

# ============================================================
# Generadores de paginas
# ============================================================

def render_subpage(key, page):
    slug = page['slug']
    depth = 1
    title = page.get('Meta Title') or page.get('H1', '')
    desc = page.get('Meta Description') or ''
    h1 = page.get('H1') or ''
    h2s = page.get('H2 (todos)', []) or []
    h3s = page.get('H3 (todos)', []) or []
    h4s = page.get('H4 (todos)', []) or []
    images = page.get('images', []) or []
    content = parse_contenido(page.get('CONTENIDO COMPLETO', ''))

    # Identify H2s by role (Ventajas, ¿Quieres/¿Listo, Otras Referencias)
    h2_ventajas = next((h for h in h2s if h.lower().startswith('ventajas')), None)
    h2_cta = next((h for h in h2s if h.startswith('¿') or h.lower().startswith('listo')), None)
    h2_refs = next((h for h in h2s if 'referencias' in h.lower() or 'otras' in h.lower()), None)
    h3_explora = next((h for h in h3s if 'explora' in h.lower() or 'descubre' in h.lower() or 'conoce' in h.lower() or 'mira' in h.lower()), None)
    h3_escribe = next((h for h in h3s if 'escr' in h.lower()), None)
    # Quirk del sitio original: a veces "Ventajas..." aparece como H3 (caso 03_SALAS_RUSTICAS).
    h3_ventajas = next((h for h in h3s if h.lower().startswith('ventajas')), None)
    # Quirk: a veces un MOBILIARIO X esta en H3 ademas de en H4 (08, 11, 16).
    h3_mobiliario_extra = next((h for h in h3s if h.upper().startswith('MOBILIARIO')), None)

    head = head_html(title, desc, slug, depth,
                     og_image_filename=images[0]['file'] if images else None)
    nav = navbar_html(depth)

    # Hero interior
    hero = f'''<section class="hero-inner">
  <div class="breadcrumbs"><a href="../">Inicio</a> &nbsp;&middot;&nbsp; {escape(h1.replace("Alquiler de ", "").replace(" en Bogotá para Eventos", ""))}</div>
  <h1>{escape(h1)}</h1>
  <p class="hero-sub">{escape(desc)}</p>
  <div class="hero-ctas">
    <a class="btn btn-turquesa" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar por WhatsApp</a>
    <a class="btn btn-outline-light" href="#galeria">Ver galeria</a>
  </div>
</section>'''

    # Intro
    intro_paragraphs = ''
    if content.get('intro'):
        paras = [p for p in content['intro'].split('\n\n') if p.strip()]
        intro_paragraphs = '\n'.join(f'    <p class="lead">{escape(p)}</p>' if i == 0 else f'    <p>{escape(p)}</p>'
                                     for i, p in enumerate(paras))
    productos_block = ''
    if content.get('productos'):
        productos_block = f'    <p><strong>Productos:</strong> {" &middot; ".join(escape(p) for p in content["productos"])}</p>'
    intro_html = ''
    if intro_paragraphs or productos_block:
        intro_html = f'''<section class="intro reveal">
  <div class="intro-inner">
{intro_paragraphs}
{productos_block}
  </div>
</section>'''

    # Galeria con H3 explora
    gallery_h3 = h3_explora or 'Explora algunos de nuestros montajes:'
    gallery_imgs = []
    for img in images:
        # Skip ASEM logo at the bottom
        if 'ASEM-mobiliario-para-eventos-en-bogota' in img['file']:
            continue
        gallery_imgs.append(img)
    figs = '\n'.join(
        f'      <figure class="reveal"><img src="../assets/img/{escape(img["file"])}" alt="{escape(img["alt"])}" loading="lazy"></figure>'
        for img in gallery_imgs)
    gallery_html = f'''<section class="galeria-interior" id="galeria">
  <div class="galeria-interior-inner">
    <div class="galeria-eyebrow" role="heading" aria-level="2">Galeria de montajes</div>
    <h3>{escape(gallery_h3)}</h3>
    <div class="galeria-grid">
{figs}
    </div>
  </div>
</section>'''

    # Ventajas — usa h2 si Excel lo lista en H2, h3 si lo lista en H3, span si no esta
    ventajas_title = h2_ventajas or h3_ventajas
    ventajas_tag = 'h2' if h2_ventajas else ('h3' if h3_ventajas else None)
    ventajas_html = ''
    if ventajas_title and content.get('ventajas'):
        lis = '\n'.join(f'      <li>{escape(v)}</li>' for v in content['ventajas'])
        ventajas_html = f'''<section class="ventajas reveal">
  <div class="ventajas-inner">
    <{ventajas_tag}>{escape(ventajas_title)}</{ventajas_tag}>
    <ul>
{lis}
    </ul>
  </div>
</section>'''
    elif ventajas_title:
        ventajas_html = f'''<section class="ventajas reveal">
  <div class="ventajas-inner">
    <{ventajas_tag}>{escape(ventajas_title)}</{ventajas_tag}>
  </div>
</section>'''

    # CTA block
    cta_html = ''
    if h2_cta:
        cta_html = cta_block(h2_cta, h3_escribe or 'Escribenos y recibe tu cotizacion personalizada en minutos.')

    # Referencias — combina extras de H3 (si los hay) con los H4 estandar.
    # Quirk del sitio original: a veces un "MOBILIARIO X" se renderizo como h3.
    def lookup_estilo(label):
        key_norm = label.replace('Ú', 'U').upper()
        entry = ESTILOS.get(label) or ESTILOS.get(label.replace('Ú', 'U')) or ESTILOS.get(label.replace('U', 'Ú'))
        if not entry:
            for k_, v_ in ESTILOS.items():
                if k_.upper().replace('Ú', 'U') == key_norm:
                    entry = v_
                    break
        return entry

    refs_items = []
    if h3_mobiliario_extra:
        refs_items.append(('h3', h3_mobiliario_extra))
    for h4 in h4s:
        refs_items.append(('h4', h4))

    refs_cards = []
    for tag, label in refs_items:
        entry = lookup_estilo(label)
        if entry:
            ref_slug, ref_name, ref_desc = entry
            refs_cards.append(f'''      <a class="ref-card" href="{link_to(ref_slug, depth)}">
        <{tag}>{escape(label)}</{tag}>
        <span>{escape(ref_desc)}</span>
        <div class="arrow">Ver mas &rarr;</div>
      </a>''')
        else:
            refs_cards.append(f'''      <div class="ref-card">
        <{tag}>{escape(label)}</{tag}>
      </div>''')
    referencias_html = ''
    if h2_refs:
        referencias_html = f'''<section class="referencias reveal">
  <div class="referencias-inner">
    <h2>{escape(h2_refs)}</h2>
    <div class="referencias-grid">
{chr(10).join(refs_cards)}
    </div>
  </div>
</section>'''

    body = f'''{head}
{nav}
{hero}
{intro_html}
{gallery_html}
{ventajas_html}
{cta_html}
{referencias_html}
{cta_final_block()}
{footer_html(depth)}
<script src="{asset('assets/js/main.js', depth)}"></script>
</body>
</html>'''
    return body

def render_acarreos(key, page):
    """Pagina especial 17 — sin H1, layout distinto."""
    slug = page['slug']
    depth = 1
    title = page.get('Meta Title')
    desc = page.get('Meta Description')
    images = page.get('images', [])
    head = head_html(title, desc, slug, depth,
                     og_image_filename=images[0]['file'] if images else None)
    nav = navbar_html(depth)

    figs = '\n'.join(
        f'      <figure class="reveal"><img src="../assets/img/{escape(img["file"])}" alt="{escape(img["alt"])}" loading="lazy"></figure>'
        for img in images if 'ASEM-mobiliario' not in img['file'])

    body = f'''{head}
{nav}

<section class="hero-inner">
  <div class="breadcrumbs"><a href="../">Inicio</a> &nbsp;&middot;&nbsp; Acarreos, Trasteos y Mudanzas</div>
  <h2 class="acarreos-titulo">SERVICIO DE CAMIONES</h2>
  <h3 class="acarreos-sub">PARA MERCANC&Iacute;AS, EVENTOS Y MUDANZAS.</h3>
  <p class="hero-sub">{escape(desc)}</p>
  <div class="hero-ctas">
    <a class="btn btn-turquesa" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar por WhatsApp</a>
  </div>
</section>

<section class="intro reveal">
  <div class="intro-inner">
    <p class="lead">Servicio de camiones para mercancias, eventos y mudanzas en Bogota. Acarreos dentro y fuera de Bogota con modelos recientes, gran capacidad de carga y disponibilidad 24 horas.</p>
    <h3 class="acarreos-h3">Acarreos dentro y fuera de Bogot&aacute;</h3>
    <ul class="acarreos-list">
      <li><span class="check">&#10003;</span> Modelos recientes</li>
      <li><span class="check">&#10003;</span> Capacidad de carga</li>
      <li><span class="check">&#10003;</span> 24 Horas disponibles</li>
      <li><span class="check">&#10003;</span> Acarreos dentro y fuera de Bogot&aacute;</li>
    </ul>
  </div>
</section>

<section class="galeria-interior" id="galeria">
  <div class="galeria-interior-inner">
    <div class="galeria-eyebrow" role="heading" aria-level="3">Nuestra flota y servicios</div>
    <p class="galeria-sub">Acarreos, trasteos y mudanzas en Bogota.</p>
    <div class="galeria-grid">
{figs}
    </div>
  </div>
</section>

<section class="cta-block">
  <div class="cta-block-overhead" role="heading" aria-level="3">&iexcl;Cotizar Ahora!</div>
  <h2>o ll&aacute;manos al siguiente n&uacute;mero 301 6003031</h2>
  <a class="btn-large" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar por WhatsApp
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"></path><path d="m13 5 7 7-7 7"></path></svg>
  </a>
</section>

{cta_final_block()}
{footer_html(depth)}
<script src="{asset('assets/js/main.js', depth)}"></script>
</body>
</html>'''
    return body

def render_home(key, page):
    depth = 0
    title = page.get('Meta Title')
    desc = page.get('Meta Description')
    h1 = page.get('H1') or ''   # AMBIENTA, IMPACTA Y CELEBRA
    h2s = page.get('H2 (todos)', [])  # ¡Habla con nuestro equipo comercial! / Instagram / NUESTROS EVENTOS
    h3s = page.get('H3 (todos)', [])  # MOBILIARIO X x6 + SÍGUENOS EN
    images = page.get('images', [])

    # Pick gallery images for "NUESTROS EVENTOS" — all except the 6 cat-card-likes and logo
    cat_card_images = {
        'MOBILIARIO LOUNGE':     'sala-lounge-para-eventos-en-bogota.webp',
        'MOBILIARIO INDUSTRIAL': 'alquiler-de-muebles-industriales-para-eventos.jpg',
        'MOBILIARIO RÚSTICO':    'salas-rusticas-en-alquiler.webp',
        'MOBILIARIO PICNIC':     'mesas-picnic-para-eventos-bogota.webp',
        'MOBILIARIO LED':        'alquiler-de-salas-led-para-eventos-en-bogota.webp',
        'MOBILIARIO ACAPULCO':   'sillas-acapulco-para-eventos-sociales-en-bogota.webp',
    }
    used_files = set(cat_card_images.values())
    gallery_images = [img for img in images if img['file'] not in used_files and 'ASEM-mobiliario' not in img['file']]

    h2_habla = next((h for h in h2s if 'habla' in h.lower()), '¡Habla con nuestro equipo comercial!')
    h2_ig    = next((h for h in h2s if h.lower() == 'instagram'), 'Instagram')
    h2_eventos = next((h for h in h2s if 'eventos' in h.lower()), 'NUESTROS EVENTOS')
    h3_siguenos = next((h for h in h3s if 'siguenos' in h.lower() or 'síguenos' in h.lower()), 'SÍGUENOS EN')

    head = head_html(title, desc, '', depth,
                     og_image_filename='alquiler-de-mobiliario-para-eventos-en-bogota.webp')
    nav = navbar_html(depth)

    # Cat cards for the 6 estilos
    cards = []
    cat_meta = [
        ('MOBILIARIO LOUNGE',     'salas-lounge-para-eventos-en-bogota',     'Salas comodas en cuero y velvet para conversacion intima.'),
        ('MOBILIARIO INDUSTRIAL', 'mesas-sillas-industriales-eventos-bogota','Madera, hierro y luz calida con energia urbana.'),
        ('MOBILIARIO RÚSTICO',    'salas-rusticas-para-eventos-bogota',      'Texturas naturales para bodas y eventos al aire libre.'),
        ('MOBILIARIO PICNIC',     'mesas-picnic-para-eventos-bogota',        'Mesas bajas y picnic para encuentros relajados.'),
        ('MOBILIARIO LED',        'mobiliario-led-eventos-bogota',           'Mobiliario iluminado para fiestas con alma de club.'),
        ('MOBILIARIO ACAPULCO',   'sillas-acapulco-para-eventos-bogota',     'Sillas iconicas para eventos frescos con aire tropical.'),
    ]
    for h3_name, slug_, desc_ in cat_meta:
        img_file = cat_card_images[h3_name]
        # alt text from images list
        alt = next((i['alt'] for i in images if i['file'] == img_file), h3_name)
        cards.append(f'''    <a href="{slug_}/" class="cat-card reveal">
      <img src="assets/img/{escape(img_file)}" alt="{escape(alt)}" loading="lazy">
      <div class="cat-card-overlay-rest">
        <h3 class="cat-card-name">{escape(h3_name)}</h3>
      </div>
      <div class="cat-card-overlay-hover">
        <span class="cat-card-name">{escape(h3_name)}</span>
        <p class="cat-card-desc">{escape(desc_)}</p>
        <span class="cat-card-arrow">&rarr;</span>
      </div>
    </a>''')

    # 2 tarjetas adicionales pendientes de URL final (Silleteria, Ferias)
    pending_meta = [
        ('SILLETERÍA', 'Sillas para bodas, banquetes y ceremonias de volumen.'),
        ('FERIAS',     'Stands, montajes feriales y activaciones de marca.'),
    ]
    for h3_name, desc_ in pending_meta:
        cards.append(f'''    <div class="cat-card cat-card-pending reveal" role="img" aria-label="{escape(h3_name)}">
      <div class="cat-card-overlay-rest">
        <h3 class="cat-card-name">{escape(h3_name)}</h3>
      </div>
      <div class="cat-card-overlay-hover">
        <span class="cat-card-name">{escape(h3_name)}</span>
        <p class="cat-card-desc">{escape(desc_)}</p>
        <span class="cat-card-soon">Pronto</span>
      </div>
    </div>''')

    # Tarjetas de accesorios (mismo estilo cat-card que las anteriores) — linkean a paginas reales
    acc_cat_meta = [
        ('CALEFACTORES',        'calefactores-ambiente-para-eventos',  'Para que la noche fria no acabe la fiesta antes de tiempo.',          'calefactor-piramide-en-alquiler.webp',          'calefactor piramide en alquiler'),
        ('PISTA DE BAILE LED',  'pista-de-baile-para-eventos',         'Superficie iluminada que sube la energia a media noche.',           'pista-de-baile-led-para-eventos.webp',          'pista de baile led para eventos'),
        ('BOMBILLOS VINTAGE',   'bombillos-vintage-para-eventos',      'Cadenas de luces calidas para techos, terrazas y patios.',          'bombillos-vintage-para-eventos.webp',           'bombillos vintage para eventos'),
        ('SEPARADORES DE FILA', 'separadores-de-fila-para-eventos',    'Para organizar entradas, accesos VIP y areas con flujo elegante.',  'separadores-de-fila-dorados-para-eventos.webp', 'separadores de fila dorados para eventos'),
    ]
    acc_cards = []
    for h3_name, slug_, desc_, img_file, alt_ in acc_cat_meta:
        acc_cards.append(f'''    <a href="{slug_}/" class="cat-card reveal">
      <img src="assets/img/{escape(img_file)}" alt="{escape(alt_)}" loading="lazy">
      <div class="cat-card-overlay-rest">
        <h3 class="cat-card-name">{escape(h3_name)}</h3>
      </div>
      <div class="cat-card-overlay-hover">
        <span class="cat-card-name">{escape(h3_name)}</span>
        <p class="cat-card-desc">{escape(desc_)}</p>
        <span class="cat-card-arrow">&rarr;</span>
      </div>
    </a>''')

    # gallery — incluye TODAS las imagenes de eventos del Excel (no las 6 cat-cards ni el logo footer)
    # Las primeras 8 visibles; resto colapsado tras boton "Ver mas eventos" (los <img> siguen en el HTML para SEO)
    GALLERY_INITIAL = 8
    figs_lines = []
    for i, img in enumerate(gallery_images):
        cls = 'reveal' if i < GALLERY_INITIAL else 'reveal gallery-extra'
        figs_lines.append(f'      <figure class="{cls}"><img src="assets/img/{escape(img["file"])}" alt="{escape(img["alt"])}" loading="lazy"></figure>')
    gallery_figs = '\n'.join(figs_lines)
    extras_count = max(0, len(gallery_images) - GALLERY_INITIAL)
    gallery_more_btn = ''
    if extras_count > 0:
        gallery_more_btn = f'''    <div class="galeria-more-wrap">
      <button type="button" class="galeria-more-btn" id="galeriaMoreBtn" aria-expanded="false" aria-controls="galeriaGrid">
        Ver mas eventos
        <span class="galeria-more-count">({extras_count})</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"></path></svg>
      </button>
    </div>'''

    body = f'''{head}
{nav}

<section class="hero">
  <div class="hero-slides" aria-hidden="true">
    <div class="hero-slide is-active" style="background-image:url('assets/img/hero-1-salas-lounge.webp')"></div>
    <div class="hero-slide" style="background-image:url('assets/img/hero-2-mobiliario-rustico.webp')"></div>
    <div class="hero-slide" style="background-image:url('assets/img/hero-3-sillas-acapulco.webp')"></div>
    <div class="hero-slide" style="background-image:url('assets/img/hero-4-parasoles.webp')"></div>
  </div>
  <div class="hero-content">
    <span class="label anim anim-1">Bogota &middot; Colombia</span>
    <h1 class="anim anim-2">{escape(h1)}</h1>
    <p class="hero-subtitle anim anim-3">Con el mobiliario perfecto para cada tipo de evento en Bogota.</p>
    <div class="hero-ctas anim anim-4">
      <a href="#catalogo" class="btn btn-outline-light">Ver catalogo</a>
      <a class="btn btn-turquesa" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar por WhatsApp</a>
    </div>
  </div>
  <div class="hero-dots" role="tablist" aria-label="Cambiar imagen del hero">
    <button type="button" class="is-active" aria-label="Salas Lounge"></button>
    <button type="button" aria-label="Mobiliario rustico"></button>
    <button type="button" aria-label="Sillas Acapulco"></button>
    <button type="button" aria-label="Parasoles"></button>
  </div>
  <div class="scroll-indicator" aria-hidden="true">
    <span class="scroll-label">Scroll</span>
    <span class="scroll-line"></span>
  </div>
</section>

<section class="stats">
  <div class="stats-grid">
    <div class="stat reveal"><div class="stat-num">10+</div><div class="stat-label">Anos de experiencia</div></div>
    <div class="stat reveal"><div class="stat-num">+500</div><div class="stat-label">Eventos al ano</div></div>
    <div class="stat reveal"><div class="stat-num">6</div><div class="stat-label">Estilos de mobiliario</div></div>
    <div class="stat reveal"><div class="stat-num">Bogota</div><div class="stat-label">Y alrededores</div></div>
  </div>
</section>

<section class="catalogo" id="catalogo">
  <div class="section-head">
    <div class="section-head-text reveal">
      <span class="label">Mobiliario</span>
      <p class="title-section">Estilos que ambientan<br>tu evento.</p>
    </div>
    <p class="section-head-aside reveal">
      Cada coleccion esta pensada para un tipo de evento.
      Mezclamos piezas para que el ambiente cuente tu historia.
    </p>
  </div>
  <div class="catalogo-grid">
{chr(10).join(cards)}
  </div>
</section>

<section class="catalogo catalogo-accesorios" id="accesorios">
  <div class="section-head">
    <div class="section-head-text reveal">
      <span class="label">Accesorios</span>
      <p class="title-section">Detalles que cierran<br>la experiencia.</p>
    </div>
    <p class="section-head-aside reveal">
      Mas alla del mobiliario: iluminacion, calefaccion y elementos
      que terminan de ambientar y de cuidar a tus invitados.
    </p>
  </div>
  <div class="catalogo-grid">
{chr(10).join(acc_cards)}
  </div>
</section>

<section class="cta-block">
  <h2>{escape(h2_habla)}</h2>
  <p class="cta-block-sub">Tienes dudas o necesitas una cotizacion rapida? Comunicate con nuestra area comercial y recibe asesoria personalizada para tu evento.</p>
  <a class="btn-large" href="{WA_LINK}" target="_blank" rel="noopener">Hablar por WhatsApp
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"></path><path d="m13 5 7 7-7 7"></path></svg>
  </a>
</section>

<section class="instagram-strip">
  <span class="label">@alquilersalasparaeventos</span>
  <h2>{escape(h2_ig)}</h2>
  <h3>{escape(h3_siguenos)}</h3>
  <a class="ig-link" href="https://instagram.com/alquilersalasparaeventos" target="_blank" rel="noopener">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"></rect><circle cx="12" cy="12" r="4"></circle><circle cx="17.5" cy="6.5" r="0.6" fill="currentColor"></circle></svg>
    Siguenos en Instagram
  </a>
</section>

<section class="galeria-interior" id="eventos">
  <div class="galeria-interior-inner">
    <h2>{escape(h2_eventos)}</h2>
    <p class="galeria-sub">Algunos de los eventos que hemos ambientado en Bogota.</p>
    <div class="galeria-grid" id="galeriaGrid">
{gallery_figs}
    </div>
{gallery_more_btn}
  </div>
</section>

{cta_final_block()}
{footer_html(depth)}
<script src="{asset('assets/js/main.js', depth)}"></script>
</body>
</html>'''
    return body

# ============================================================
# Generador principal
# ============================================================

def collect_all_images():
    """Devuelve dict {filename: (alt, page_key)} para todas las imagenes referenciadas."""
    all_imgs = {}
    for key, page in DATA.items():
        for img in page.get('images', []):
            fn = img['file']
            if fn not in all_imgs:
                all_imgs[fn] = (img['alt'], key)
    return all_imgs

def write_placeholders():
    print('Generando placeholders de imagenes...')
    out_dir = ROOT / 'assets' / 'img'
    out_dir.mkdir(parents=True, exist_ok=True)
    all_imgs = collect_all_images()
    for fn, (alt, page_key) in all_imgs.items():
        out_path = out_dir / fn
        out_path.parent.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(fn)[1].lower()
        if ext not in ('.webp', '.jpg', '.jpeg', '.png'):
            ext = '.png'
            out_path = out_path.with_suffix('.png')
        try:
            make_placeholder(str(out_path), alt or fn, palette_for(page_key, fn))
        except Exception as e:
            print(f'  WARN placeholder {fn}: {e}')
    print(f'  {len(all_imgs)} placeholders generados.')

def write_page(out_path, html):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

def write_sitemap():
    urls = []
    for key, p in DATA.items():
        if key.startswith('00_'):
            continue
        slug = p['slug']
        urls.append((f'{SITE}/{slug}/' if slug else f'{SITE}/', '2026-05-26'))
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, lastmod in urls:
        xml.append(f'  <url><loc>{url}</loc><lastmod>{lastmod}</lastmod><changefreq>monthly</changefreq><priority>{"1.0" if url.endswith("/") and url == SITE + "/" else "0.8"}</priority></url>')
    xml.append('</urlset>')
    (ROOT / 'sitemap.xml').write_text('\n'.join(xml), encoding='utf-8')

def write_robots():
    (ROOT / 'robots.txt').write_text(
        f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n',
        encoding='utf-8'
    )

def main():
    skip_imgs = '--no-img' in sys.argv
    if not skip_imgs:
        write_placeholders()
    for key, page in DATA.items():
        if key.startswith('00_'):
            continue
        if key == '01_INICIO':
            html = render_home(key, page)
            write_page(ROOT / 'index.html', html)
            print(f'  index.html  <- {key}')
        elif key == '17_ACARREOS_MUDANZAS':
            html = render_acarreos(key, page)
            write_page(ROOT / page['slug'] / 'index.html', html)
            print(f'  {page["slug"]}/index.html  <- {key}')
        else:
            html = render_subpage(key, page)
            write_page(ROOT / page['slug'] / 'index.html', html)
            print(f'  {page["slug"]}/index.html  <- {key}')
    write_sitemap()
    write_robots()
    print('Sitemap + robots.txt OK')

if __name__ == '__main__':
    main()
