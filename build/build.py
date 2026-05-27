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

# Cache-buster: cambia cada build para forzar al navegador a recargar CSS/JS
import time
ASSET_VERSION = str(int(time.time()))

SITE = 'https://alquilersalasparaeventosymobiliario.com'
WA_PHONE = '573013228490'
WA_LINK = f'https://wa.me/{WA_PHONE}?text=Hola,%20quiero%20cotizar%20mobiliario'

# ============================================================
# Reseñas reales (Google Maps) — base de datos para schema y testimonios
# ============================================================
REVIEWS = [
    {
        'author': 'Stefania García',
        'date': '2025-05-15',
        'rating': 5,
        'text': 'Totalmente recomendado por las siguientes razones: respuesta inmediata a través de WhatsApp, variedad de mobiliario y excelente comunicación para coordinar la entrega. Las personas que entregaron el mobiliario fueron muy puntuales y dejaron todo perfectamente armado.',
        'short': 'Respuesta inmediata por WhatsApp, variedad de mobiliario y excelente comunicación. El equipo de entrega fue puntual y dejó todo perfectamente armado.',
    },
    {
        'author': 'María Andrea Bohórquez',
        'date': '2025-09-20',
        'rating': 5,
        'text': 'El servicio fue excelente, me atendieron amablemente, me apoyaron en todo el proceso de alquiler del mobiliario. Las personas que vinieron a entregarme las salas y los calentadores me ayudaron no solo a organizarlos sino que también me asesoraron.',
        'short': 'El servicio fue excelente, me apoyaron en todo el proceso. Las personas que entregaron las salas y los calentadores me ayudaron a organizarlos y me asesoraron.',
    },
    {
        'author': 'Jhon Alexander Herrera',
        'date': '2025-07-22',
        'rating': 5,
        'text': 'Súper recomendados, excelente servicio. La atención de Laura la comercial estupenda. Es muy cordial y efectiva. El evento salió de maravilla. Muchas gracias.',
        'short': 'Súper recomendados, excelente servicio. La atención de Laura la comercial es muy cordial y efectiva. El evento salió de maravilla.',
    },
    {
        'author': 'Leonardo Romero',
        'date': '2025-12-15',
        'rating': 5,
        'text': 'Todo excelente. El personal de entrega del mobiliario muy amable y decente.',
        'short': 'Todo excelente. El personal de entrega del mobiliario muy amable y decente.',
    },
    {
        'author': 'AnFerTM Studios',
        'date': '2025-11-18',
        'rating': 5,
        'text': 'Buen servicio en general, entrega y recogida del mobiliario de manera oportuna e idónea atención al cliente. Recomendado.',
        'short': 'Buen servicio en general, entrega y recogida oportuna. Idónea atención al cliente. Recomendado.',
    },
]

# ============================================================
# FAQ — preguntas comunes optimizadas para AI search (ChatGPT, Perplexity, AIO)
# ============================================================
FAQS = [
    {
        'q': '¿Cuánto cuesta alquilar mobiliario para un evento en Bogotá?',
        'a': 'El precio depende del tipo y cantidad de mobiliario, la fecha y la ubicación. En ASEM cotizamos cada evento de forma personalizada y respondemos por WhatsApp en minutos con propuesta clara y precio cerrado. Escríbenos al 301 322 8490 con los detalles de tu evento para recibir una cotización sin compromiso.',
    },
    {
        'q': '¿Incluyen montaje, desmontaje y transporte?',
        'a': 'Sí. Nuestro servicio incluye entrega, montaje completo, desmontaje y recogida después del evento. Coordinamos los horarios contigo para que solo te encargues de disfrutar. El transporte está incluido dentro de Bogotá y se cotiza por separado para municipios aledaños.',
    },
    {
        'q': '¿Atienden eventos fuera de Bogotá?',
        'a': 'Sí, cubrimos Bogotá y sus alrededores (Chía, Cota, Cajicá, La Calera, Sopó, Tabio y municipios cercanos). Para eventos en otras zonas, consulta disponibilidad por WhatsApp y coordinamos transporte y montaje a la medida de tu evento.',
    },
    {
        'q': '¿Qué tipos de eventos cubren?',
        'a': 'Atendemos bodas, cocteles, lanzamientos de marca, ferias, eventos corporativos, fiestas privadas, activaciones, celebraciones al aire libre, eventos sociales y empresariales. Con más de 10 años de experiencia y más de 500 eventos al año en Bogotá.',
    },
    {
        'q': '¿Con cuánta anticipación debo reservar?',
        'a': 'Recomendamos reservar con al menos 2-3 semanas de anticipación, especialmente para fechas de alta demanda (diciembre, mayo, agosto). Para eventos urgentes consulta disponibilidad por WhatsApp; muchas veces logramos atender pedidos de última hora si tenemos el mobiliario disponible.',
    },
    {
        'q': '¿Cómo solicito una cotización?',
        'a': 'Escríbenos por WhatsApp a Laura al 301 322 8490 o Paola al 301 600 3031, indicando: fecha del evento, ubicación, número de invitados y tipo de mobiliario que necesitas. Respondemos en minutos con una propuesta clara y precio cerrado, sin compromiso.',
    },
]

def schema_jsonld_home():
    """Schema.org JSON-LD para LocalBusiness + AggregateRating + Reviews + FAQPage.
    Critico para LLMs (ChatGPT, Perplexity, Google AI Overviews, Bing Copilot)."""
    import json as _json
    business = {
        '@context': 'https://schema.org',
        '@graph': [
            {
                '@type': 'LocalBusiness',
                '@id': f'{SITE}/#business',
                'name': 'ASEM Alquiler de Salas y Mobiliario',
                'alternateName': 'ASEM',
                'description': 'Alquiler de mobiliario premium para eventos en Bogotá: salas lounge, mesas, sillas, mobiliario industrial, rústico, LED, Acapulco, picnic, calefactores, pista de baile LED y accesorios.',
                'url': SITE + '/',
                'logo': f'{SITE}/assets/img/ASEM-mobiliario-para-eventos-en-bogota.png',
                'image': f'{SITE}/assets/img/hero-1-salas-lounge.webp',
                'foundingDate': '2014',
                'priceRange': '$$',
                'areaServed': [
                    {'@type': 'City', 'name': 'Bogotá'},
                    {'@type': 'AdministrativeArea', 'name': 'Cundinamarca, Colombia'},
                ],
                'address': {
                    '@type': 'PostalAddress',
                    'addressLocality': 'Bogotá',
                    'addressRegion': 'Cundinamarca',
                    'addressCountry': 'CO',
                },
                'telephone': '+57-301-322-8490',
                'contactPoint': [
                    {'@type': 'ContactPoint', 'telephone': '+57-301-322-8490', 'contactType': 'sales', 'name': 'Laura Martínez', 'areaServed': 'CO', 'availableLanguage': 'Spanish'},
                    {'@type': 'ContactPoint', 'telephone': '+57-301-600-3031', 'contactType': 'sales', 'name': 'Paola Castro', 'areaServed': 'CO', 'availableLanguage': 'Spanish'},
                ],
                'sameAs': [
                    'https://instagram.com/alquilersalasparaeventos',
                ],
                'aggregateRating': {
                    '@type': 'AggregateRating',
                    'ratingValue': '4.7',
                    'reviewCount': '90',
                    'bestRating': '5',
                    'worstRating': '1',
                },
                'review': [
                    {
                        '@type': 'Review',
                        'author': {'@type': 'Person', 'name': r['author']},
                        'datePublished': r['date'],
                        'reviewRating': {'@type': 'Rating', 'ratingValue': str(r['rating']), 'bestRating': '5'},
                        'reviewBody': r['text'],
                    }
                    for r in REVIEWS
                ],
                'makesOffer': [
                    {'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'name': 'Alquiler de salas lounge para eventos', 'url': f'{SITE}/salas-lounge-para-eventos-en-bogota/'}},
                    {'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'name': 'Alquiler de mobiliario LED para eventos', 'url': f'{SITE}/mobiliario-led-eventos-bogota/'}},
                    {'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'name': 'Alquiler de sillas Acapulco para eventos', 'url': f'{SITE}/sillas-acapulco-para-eventos-bogota/'}},
                    {'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'name': 'Alquiler de mesas picnic para eventos', 'url': f'{SITE}/mesas-picnic-para-eventos-bogota/'}},
                    {'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'name': 'Alquiler de mobiliario industrial para eventos', 'url': f'{SITE}/mesas-sillas-industriales-eventos-bogota/'}},
                    {'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'name': 'Alquiler de salas rústicas para eventos', 'url': f'{SITE}/salas-rusticas-para-eventos-bogota/'}},
                    {'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'name': 'Alquiler de calefactores para eventos', 'url': f'{SITE}/calefactores-ambiente-para-eventos/'}},
                    {'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'name': 'Alquiler de pista de baile LED', 'url': f'{SITE}/pista-de-baile-para-eventos/'}},
                ],
                'slogan': 'Ambienta, impacta y celebra',
            },
            {
                '@type': 'FAQPage',
                '@id': f'{SITE}/#faq',
                'mainEntity': [
                    {
                        '@type': 'Question',
                        'name': f['q'],
                        'acceptedAnswer': {'@type': 'Answer', 'text': f['a']},
                    }
                    for f in FAQS
                ],
            },
            {
                '@type': 'WebSite',
                '@id': f'{SITE}/#website',
                'url': SITE + '/',
                'name': 'ASEM Alquiler de Salas y Mobiliario',
                'description': 'Alquiler de mobiliario premium para eventos en Bogotá. Más de 10 años, 500+ eventos al año, 4.7★ en Google con 90 reseñas.',
                'publisher': {'@id': f'{SITE}/#business'},
                'inLanguage': 'es-CO',
            },
        ],
    }
    return '<script type="application/ld+json">' + _json.dumps(business, ensure_ascii=False, indent=2) + '</script>'

def schema_jsonld_subpage(page):
    """Schema.org JSON-LD para cada subpagina: Service + breadcrumbs."""
    import json as _json
    slug = page.get('slug', '')
    title = page.get('Meta Title', '')
    desc = page.get('Meta Description', '')
    h1 = page.get('H1', '')
    if h1.startswith('(No'):
        h1 = title
    images = page.get('images', [])
    image_url = f'{SITE}/assets/img/{images[0]["file"]}' if images else f'{SITE}/assets/img/hero-1-salas-lounge.webp'
    graph = {
        '@context': 'https://schema.org',
        '@graph': [
            {
                '@type': 'Service',
                '@id': f'{SITE}/{slug}/#service',
                'name': h1,
                'description': desc,
                'serviceType': 'Alquiler de mobiliario para eventos',
                'provider': {'@id': f'{SITE}/#business'},
                'areaServed': {'@type': 'City', 'name': 'Bogotá'},
                'url': f'{SITE}/{slug}/',
                'image': image_url,
            },
            {
                '@type': 'BreadcrumbList',
                'itemListElement': [
                    {'@type': 'ListItem', 'position': 1, 'name': 'Inicio', 'item': SITE + '/'},
                    {'@type': 'ListItem', 'position': 2, 'name': h1, 'item': f'{SITE}/{slug}/'},
                ],
            },
        ],
    }
    return '<script type="application/ld+json">' + _json.dumps(graph, ensure_ascii=False, indent=2) + '</script>'

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
  </div>

  <a class="btn-cotizar btn-wa desktop-only" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar ahora</a>
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
  <a class="btn-cotizar btn-wa" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar ahora</a>
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
      <p class="footer-tag">Alquiler de mobiliario premium<br>para eventos en Bogot&aacute; y alrededores</p>
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

<a class="wa-float" href="{WA_LINK}" target="_blank" rel="noopener" aria-label="Escribenos por WhatsApp">
  <div class="wa-bubble" aria-hidden="true">
    <div class="wa-msgs">
      <span class="wa-msg is-active">&iquest;Est&aacute;s organizando un evento? Escr&iacute;beme</span>
      <span class="wa-msg">Ven, hablamos por WhatsApp</span>
      <span class="wa-msg">Te asesoramos sin compromiso</span>
      <span class="wa-msg">Cotizaci&oacute;n r&aacute;pida en minutos</span>
    </div>
    <div class="wa-typing" aria-hidden="true"><span></span><span></span><span></span></div>
  </div>
  <div class="wa-icon">
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M.057 24l1.687-6.163a11.867 11.867 0 0 1-1.587-5.946C.16 5.335 5.495 0 12.05 0a11.817 11.817 0 0 1 8.413 3.488 11.824 11.824 0 0 1 3.48 8.414c-.003 6.557-5.338 11.892-11.893 11.892a11.9 11.9 0 0 1-5.688-1.448L.057 24zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884a9.86 9.86 0 0 0 1.692 5.543l-.999 3.648 3.796-.99zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"></path></svg>
  </div>
</a>'''

def head_html(title, description, canonical, depth, og_image_filename=None, jsonld=''):
    css_path = asset('assets/css/styles.css', depth) + f'?v={ASSET_VERSION}'
    og_url = f'{SITE}/{canonical}/' if canonical else f'{SITE}/'
    og_img = ''
    if og_image_filename:
        og_img = f'<meta property="og:image" content="{SITE}/assets/img/{escape(og_image_filename)}">'
    return f'''<!DOCTYPE html>
<html lang="es-CO">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description)}">
<link rel="canonical" href="{og_url}">
<meta property="og:type" content="website">
<meta property="og:locale" content="es_CO">
<meta property="og:site_name" content="ASEM">
<meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(description)}">
<meta property="og:url" content="{og_url}">
{og_img}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{escape(title)}">
<meta name="twitter:description" content="{escape(description)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="author" content="ASEM Alquiler de Salas y Mobiliario">
<meta name="geo.region" content="CO-CUN">
<meta name="geo.placename" content="Bogotá">
<link rel="stylesheet" href="{css_path}">
{jsonld}
</head>
<body>'''

def cta_block(h2, h3, dorado=False):
    btn_class = 'btn-large' if not dorado else 'btn btn-turquesa'
    return f'''<section class="cta-block">
  <h2>{escape(h2)}</h2>
  <h3>{escape(h3)}</h3>
  <a class="btn-large btn-wa" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar por WhatsApp
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"></path><path d="m13 5 7 7-7 7"></path></svg>
  </a>
</section>'''

def testimonios_block():
    """Seccion de testimonios con resenas reales de Google (refuerza schema AggregateRating).
    Visible para usuarios (prueba social) + signal LLM/AI Overviews."""
    # Toma las primeras 4 (Stefania, Maria Andrea, Jhon Alexander, Leonardo)
    items = []
    for r in REVIEWS[:4]:
        # initial letter for avatar
        initial = r['author'][0].upper()
        stars = '★' * int(r['rating'])
        date_label = {
            '2025-05-15': 'Hace un año',
            '2025-09-20': 'Hace 8 meses',
            '2025-07-22': 'Hace 10 meses',
            '2025-12-15': 'Hace 5 meses',
            '2025-11-18': 'Hace 6 meses',
        }.get(r['date'], '')
        items.append(f'''      <article class="testimonio reveal">
        <div class="testimonio-head">
          <div class="testimonio-avatar" aria-hidden="true">{escape(initial)}</div>
          <div class="testimonio-meta">
            <div class="testimonio-name">{escape(r['author'])}</div>
            <div class="testimonio-date">
              <span class="testimonio-stars" aria-label="{r['rating']} de 5 estrellas">{stars}</span>
              <span>&middot; {escape(date_label)}</span>
            </div>
          </div>
        </div>
        <blockquote class="testimonio-text">{escape(r['short'])}</blockquote>
      </article>''')
    cards_html = '\n'.join(items)
    return f'''<section class="testimonios-section" id="testimonios" aria-labelledby="testimonios-title">
  <div class="testimonios-inner">
    <div class="testimonios-head reveal">
      <span class="label">Rese&ntilde;as</span>
      <h2 id="testimonios-title">Lo que dicen quienes nos eligen</h2>
      <a class="testimonios-rating" href="https://www.google.com/search?q=ASEM+alquiler+salas+y+mobiliario+bogota" target="_blank" rel="noopener">
        <span class="testimonios-rating-num">4.7</span>
        <span class="testimonios-rating-stars" aria-hidden="true">★★★★★</span>
        <span class="testimonios-rating-meta">en Google &middot; 90 rese&ntilde;as verificadas</span>
      </a>
    </div>
    <div class="testimonios-grid">
{cards_html}
    </div>
  </div>
</section>'''

def faq_block():
    """Seccion FAQ con FAQPage schema. Cada Q usa <details> nativo (accordion).
    Optimizado para Google AI Overviews y consultas conversacionales."""
    items = []
    for f in FAQS:
        items.append(f'''      <details class="faq-item reveal">
        <summary>
          <span class="faq-q">{escape(f['q'])}</span>
          <svg class="faq-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
        </summary>
        <div class="faq-a">{escape(f['a'])}</div>
      </details>''')
    items_html = '\n'.join(items)
    return f'''<section class="faq-section" id="faq" aria-labelledby="faq-title">
  <div class="faq-inner">
    <div class="faq-head reveal">
      <span class="label">Preguntas frecuentes</span>
      <h2 id="faq-title">Lo que m&aacute;s nos preguntan</h2>
      <p class="faq-sub">Todo lo que necesitas saber antes de cotizar tu evento. &iquest;Algo m&aacute;s? Escr&iacute;benos por WhatsApp.</p>
    </div>
    <div class="faq-list">
{items_html}
    </div>
  </div>
</section>'''

def cta_final_block():
    """Bloque final dorado con boton WhatsApp verde — climax visual antes del footer.
    Headline no usa h1/h2/h3 para no inflar las cuentas SEO del Excel."""
    return f'''<section class="cta-final cta-final-gold" id="contacto">
  <span class="label reveal">Cu&eacute;ntanos</span>
  <div class="cta-final-headline reveal" role="heading" aria-level="2">&iquest;Tienes un evento<br>en mente?</div>
  <p class="cta-final-sub reveal">Cu&eacute;ntanos qu&eacute; imaginas. Cotizaci&oacute;n r&aacute;pida, montaje incluido, sin compromiso.</p>
  <a class="btn-large btn-wa reveal" href="{WA_LINK}" target="_blank" rel="noopener">Hablar por WhatsApp
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"></path><path d="m13 5 7 7-7 7"></path></svg>
  </a>
  <div class="cta-phones reveal">Laura 301 322 8490 &middot; Paola 301 600 3031</div>
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
                     og_image_filename=images[0]['file'] if images else None,
                     jsonld=schema_jsonld_subpage(page))
    nav = navbar_html(depth)

    # Hero interior
    hero = f'''<section class="hero-inner">
  <div class="breadcrumbs"><a href="../">Inicio</a> &nbsp;&middot;&nbsp; {escape(h1.replace("Alquiler de ", "").replace(" en Bogotá para Eventos", ""))}</div>
  <h1>{escape(h1)}</h1>
  <p class="hero-sub">{escape(desc)}</p>
  <div class="hero-ctas">
    <a class="btn btn-wa" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar por WhatsApp</a>
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
<script src="{asset('assets/js/main.js', depth)}?v={ASSET_VERSION}"></script>
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
                     og_image_filename=images[0]['file'] if images else None,
                     jsonld=schema_jsonld_subpage(page))
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
    <a class="btn btn-wa" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar por WhatsApp</a>
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
  <a class="btn-large btn-wa" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar por WhatsApp
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"></path><path d="m13 5 7 7-7 7"></path></svg>
  </a>
</section>

{cta_final_block()}
{footer_html(depth)}
<script src="{asset('assets/js/main.js', depth)}?v={ASSET_VERSION}"></script>
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
                     og_image_filename='alquiler-de-mobiliario-para-eventos-en-bogota.webp',
                     jsonld=schema_jsonld_home())
    nav = navbar_html(depth)

    # Cat cards for the 6 estilos
    cards = []
    cat_meta = [
        ('MOBILIARIO LOUNGE',     'salas-lounge-para-eventos-en-bogota',     'Sillones, poltronas y mesas de centro para crear espacios &iacute;ntimos y c&oacute;modos.'),
        ('MOBILIARIO INDUSTRIAL', 'mesas-sillas-industriales-eventos-bogota','Mesas y sillas con car&aacute;cter &mdash; madera, hierro y luz c&aacute;lida con alma urbana.'),
        ('MOBILIARIO RÚSTICO',    'salas-rusticas-para-eventos-bogota',      'Madera natural y detalles vintage perfectos para bodas al aire libre.'),
        ('MOBILIARIO PICNIC',     'mesas-picnic-para-eventos-bogota',        'Mesas, cojines y mantas tipo picnic para encuentros relajados al aire libre.'),
        ('MOBILIARIO LED',        'mobiliario-led-eventos-bogota',           'Mesas, sillas y barras iluminadas que suben la energ&iacute;a de cualquier fiesta.'),
        ('MOBILIARIO ACAPULCO',   'sillas-acapulco-para-eventos-bogota',     'Sillas ic&oacute;nicas multicolor para eventos frescos con aire tropical.'),
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

    # 2 tarjetas adicionales pendientes de URL final (Silleteria, Ferias) — ya con foto real
    pending_meta = [
        ('SILLETERÍA', 'Sillas Tiffany, banquete y ceremonia. Volumen alto para bodas y eventos masivos.', 'silleteria-para-eventos-bogota.webp',  'Silleteria para eventos en Bogota'),
        ('FERIAS',     'Mobiliario para stands, activaciones de marca y montajes feriales.',                'mobiliario-para-ferias-bogota.webp',     'Mobiliario para ferias en Bogota'),
    ]
    for h3_name, desc_, img_file, alt_ in pending_meta:
        cards.append(f'''    <div class="cat-card cat-card-pending reveal" role="img" aria-label="{escape(h3_name)}">
      <img src="assets/img/{escape(img_file)}" alt="{escape(alt_)}" loading="lazy">
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
        ('CALEFACTORES',        'calefactores-ambiente-para-eventos',  'Calefactores pir&aacute;mide y hongo para que la noche fr&iacute;a no acabe la fiesta.',          'calefactor-piramide-en-alquiler.webp',          'calefactor piramide en alquiler'),
        ('PISTA DE BAILE LED',  'pista-de-baile-para-eventos',         'Pista LED Infinity 3D &mdash; el efecto t&uacute;nel sube la energ&iacute;a a media noche.',     'pista-de-baile-led-para-eventos.webp',          'pista de baile led para eventos'),
        ('BOMBILLOS VINTAGE',   'bombillos-vintage-para-eventos',      'Cadenas de bombillos vintage para techos, terrazas y jardines.',                                'bombillos-vintage-para-eventos.webp',           'bombillos vintage para eventos'),
        ('SEPARADORES DE FILA', 'separadores-de-fila-para-eventos',    'Separadores con cinta retr&aacute;ctil para accesos VIP y flujo organizado.',                   'separadores-de-fila-dorados-para-eventos.webp', 'separadores de fila dorados para eventos'),
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

    # gallery — showcase interactivo (1 foto al frente + misma foto blureada al fondo)
    # Todos los <img> renderizados (SEO intacto), solo 1 visible. Navegacion arrows + auto.
    showcase_imgs = []
    for i, img in enumerate(gallery_images):
        cls = 'showcase-img is-active' if i == 0 else 'showcase-img'
        showcase_imgs.append(f'      <img class="{cls}" src="assets/img/{escape(img["file"])}" alt="{escape(img["alt"])}" data-idx="{i}" loading="lazy">')
    showcase_html = '\n'.join(showcase_imgs)
    first_img_src = f'assets/img/{escape(gallery_images[0]["file"])}' if gallery_images else ''
    gallery_total = len(gallery_images)

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
    <span class="label anim anim-1">Bogot&aacute; &middot; Colombia &middot; Desde 2014</span>
    <h1 class="anim anim-2">{escape(h1)}</h1>
    <p class="hero-subtitle anim anim-3">M&aacute;s de 10 a&ntilde;os creando ambientes inolvidables. Mobiliario premium para bodas, c&oacute;cteles, ferias y celebraciones que se recuerdan.</p>
    <div class="hero-ctas anim anim-4">
      <a href="#catalogo" class="btn btn-outline-light">Ver cat&aacute;logo</a>
      <a class="btn btn-wa" href="{WA_LINK}" target="_blank" rel="noopener">Cotizar por WhatsApp</a>
    </div>
    <a href="#testimonios" class="hero-rating anim anim-4" aria-label="Ver reseñas">
      <span class="hero-rating-stars" aria-hidden="true">★★★★★</span>
      <span class="hero-rating-text"><strong>4.7</strong> en Google <span class="dot">&middot;</span> 90 rese&ntilde;as</span>
    </a>
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
    <div class="stat reveal"><div class="stat-num">10+</div><div class="stat-label">A&ntilde;os en eventos</div></div>
    <div class="stat reveal"><div class="stat-num">+500</div><div class="stat-label">Eventos al a&ntilde;o</div></div>
    <div class="stat reveal"><div class="stat-num">12</div><div class="stat-label">Estilos disponibles</div></div>
    <div class="stat reveal"><div class="stat-num">Bogot&aacute;</div><div class="stat-label">Y alrededores</div></div>
  </div>
</section>

<section class="catalogo" id="catalogo">
  <div class="section-head">
    <div class="section-head-text reveal">
      <span class="label">Mobiliario</span>
      <p class="title-section">Estilos que ambientan<br>tu evento.</p>
    </div>
    <p class="section-head-aside reveal">
      Cada colecci&oacute;n est&aacute; pensada para un tipo de evento.
      Mezclamos piezas para que el ambiente cuente tu historia y tus
      invitados se sientan parte de algo especial.
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
      M&aacute;s all&aacute; del mobiliario: iluminaci&oacute;n, calefacci&oacute;n y elementos
      que terminan de ambientar y de cuidar a tus invitados.
    </p>
  </div>
  <div class="catalogo-grid">
{chr(10).join(acc_cards)}
  </div>
</section>

<section class="cta-block">
  <h2>{escape(h2_habla)}</h2>
  <p class="cta-block-sub">&iquest;Tienes dudas o necesitas cotizaci&oacute;n r&aacute;pida? Te respondemos por WhatsApp en minutos &mdash; propuesta clara, precio cerrado, sin compromiso.</p>
  <a class="btn-large btn-wa" href="{WA_LINK}" target="_blank" rel="noopener">Hablar por WhatsApp
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"></path><path d="m13 5 7 7-7 7"></path></svg>
  </a>
</section>

<section class="instagram-strip">
  <span class="label">@alquilersalasparaeventos</span>
  <h2>{escape(h2_ig)}</h2>
  <h3>{escape(h3_siguenos)}</h3>
  <a class="ig-link" href="https://instagram.com/alquilersalasparaeventos" target="_blank" rel="noopener">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"></rect><circle cx="12" cy="12" r="4"></circle><circle cx="17.5" cy="6.5" r="0.6" fill="currentColor"></circle></svg>
    Ver montajes recientes
  </a>
</section>

<section class="showcase-section" id="eventos">
  <div class="showcase-bg" id="showcaseBg" style="background-image:url('{first_img_src}')" aria-hidden="true"></div>
  <div class="showcase-bg-overlay" aria-hidden="true"></div>

  <div class="showcase-head">
    <span class="label on-dark">Galer&iacute;a</span>
    <h2 class="on-dark">{escape(h2_eventos)}</h2>
    <p class="showcase-sub">Bodas, c&oacute;cteles, ferias, lanzamientos y eventos corporativos que hemos ambientado en Bogot&aacute;.</p>
  </div>

  <div class="showcase" id="showcase">
    <button class="showcase-arrow showcase-prev" id="showcasePrev" type="button" aria-label="Foto anterior">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"></path></svg>
    </button>

    <div class="showcase-frame">
      <div class="showcase-imgs" id="showcaseImgs">
{showcase_html}
      </div>
    </div>

    <button class="showcase-arrow showcase-next" id="showcaseNext" type="button" aria-label="Foto siguiente">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"></path></svg>
    </button>
  </div>

  <div class="showcase-footer">
    <div class="showcase-caption" id="showcaseCaption">{escape(gallery_images[0]["alt"]) if gallery_images else ""}</div>
    <div class="showcase-counter">
      <span class="showcase-current" id="showcaseCurrent">01</span>
      <span class="showcase-divider">/</span>
      <span class="showcase-total">{gallery_total:02d}</span>
    </div>
  </div>
</section>

{testimonios_block()}

{faq_block()}

{cta_final_block()}
{footer_html(depth)}
<script src="{asset('assets/js/main.js', depth)}?v={ASSET_VERSION}"></script>
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
