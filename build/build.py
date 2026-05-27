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

def schema_jsonld_subpage(page, custom=None):
    """Schema.org JSON-LD para cada subpagina: Service + Breadcrumbs.
    Si hay datos custom (productos, faq), enriquece con hasOfferCatalog + FAQPage
    para maximizar visibilidad en ChatGPT / Perplexity / Google AI Overviews."""
    import json as _json, html as _html
    custom = custom or {}
    slug = page.get('slug', '')
    title = page.get('Meta Title', '')
    desc = page.get('Meta Description', '')
    h1 = page.get('H1', '')
    if h1.startswith('(No'):
        h1 = title
    images = page.get('images', [])
    image_url = f'{SITE}/assets/img/{images[0]["file"]}' if images else f'{SITE}/assets/img/hero-1-salas-lounge.webp'

    # Service base
    service = {
        '@type': 'Service',
        '@id': f'{SITE}/{slug}/#service',
        'name': h1,
        'description': desc,
        'serviceType': 'Alquiler de mobiliario para eventos',
        'provider': {'@id': f'{SITE}/#business'},
        'areaServed': [
            {'@type': 'City', 'name': 'Bogotá'},
            {'@type': 'AdministrativeArea', 'name': 'Cundinamarca, Colombia'},
        ],
        'url': f'{SITE}/{slug}/',
        'image': image_url,
        # Hereda el rating del LocalBusiness — refuerza confianza en cada subpagina
        'aggregateRating': {
            '@type': 'AggregateRating',
            'ratingValue': '4.7',
            'reviewCount': '90',
            'bestRating': '5',
        },
    }
    # hasOfferCatalog si hay productos enriquecidos
    if custom.get('productos_rich'):
        # Limpiar entidades HTML del 'name' para JSON-LD
        def clean(s):
            return _html.unescape(s).replace('&nbsp;', ' ')
        service['hasOfferCatalog'] = {
            '@type': 'OfferCatalog',
            'name': f'{h1} — opciones disponibles',
            'itemListElement': [
                {
                    '@type': 'Offer',
                    'itemOffered': {
                        '@type': 'Product',
                        'name': clean(p['name']),
                        'description': clean(p['desc']),
                        'category': 'Alquiler de mobiliario para eventos',
                    },
                    'availability': 'https://schema.org/InStock',
                    'priceCurrency': 'COP',
                }
                for p in custom['productos_rich']
            ],
        }

    graph = [
        service,
        {
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Inicio', 'item': SITE + '/'},
                {'@type': 'ListItem', 'position': 2, 'name': h1, 'item': f'{SITE}/{slug}/'},
            ],
        },
    ]
    # FAQPage si hay FAQs especificas para esta subpagina
    if custom.get('faq'):
        def clean(s):
            return _html.unescape(s).replace('&nbsp;', ' ')
        graph.append({
            '@type': 'FAQPage',
            '@id': f'{SITE}/{slug}/#faq',
            'mainEntity': [
                {
                    '@type': 'Question',
                    'name': clean(f['q']),
                    'acceptedAnswer': {'@type': 'Answer', 'text': clean(f['a'])},
                }
                for f in custom['faq']
            ],
        })

    return '<script type="application/ld+json">' + _json.dumps({
        '@context': 'https://schema.org',
        '@graph': graph,
    }, ensure_ascii=False, indent=2) + '</script>'

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

<a class="wa-sticky-mobile" href="{WA_LINK}" target="_blank" rel="noopener" aria-label="Cotizar por WhatsApp">
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M.057 24l1.687-6.163a11.867 11.867 0 0 1-1.587-5.946C.16 5.335 5.495 0 12.05 0a11.817 11.817 0 0 1 8.413 3.488 11.824 11.824 0 0 1 3.48 8.414c-.003 6.557-5.338 11.892-11.893 11.892a11.9 11.9 0 0 1-5.688-1.448L.057 24zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884a9.86 9.86 0 0 0 1.692 5.543l-.999 3.648 3.796-.99zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"></path></svg>
  Cotizar por WhatsApp
</a>

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

# ============================================================
# Datos especificos por subpagina (copy enriquecido + FAQ + productos)
# ============================================================
SUBPAGE_CUSTOM = {
    '02_SALAS_LOUNGE': {
        'hero_subtitle': 'Salas lounge en cuero y velvet para bodas, c&oacute;cteles, eventos sociales y empresariales. Configuraci&oacute;n modular seg&uacute;n tu espacio, montaje incluido y entrega puntual en Bogot&aacute;.',
        'hero_specs': [
            ('M5 11h14v9H5z M7 11V7a5 5 0 0 1 10 0v4', 'Cuero y velvet premium'),
            ('M12 2v4 M4.93 4.93l2.83 2.83 M16.24 16.24l2.83 2.83 M2 12h4 M18 12h4', 'Mas de 5 colores'),
            ('M3 7h18 M5 7v13h14V7 M9 10h6 M9 14h6', 'Montaje incluido'),
            ('M21 12.79A9 9 0 1 1 11.21 3A7 7 0 0 0 21 12.79z', 'Apto interior y exterior'),
        ],
        'gallery_keywords': ['sala', 'lounge', 'loft'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Salas lounge completas', 'desc': 'Sof&aacute;s, poltronas, mesa de centro y cubos para 6-12 personas.',
             'icon': 'M3 12h18 M5 12V8a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v4 M3 12v6 M21 12v6'},
            {'name': 'Sof&aacute;s y sillones', 'desc': 'Cuero ecol&oacute;gico blanco, negro, gris y velvet para zonas VIP.',
             'icon': 'M5 11h14v9H5z M7 11V7a5 5 0 0 1 10 0v4'},
            {'name': 'Mesas de centro lounge', 'desc': 'Mesas en vidrio, madera y lacadas que complementan cada sala.',
             'icon': 'M3 8h18v3H3z M5 11v8 M19 11v8'},
            {'name': 'Cubos y puffs auxiliares', 'desc': 'Asientos flexibles que se acomodan a la cantidad de invitados.',
             'icon': 'M4 6h7v7H4z M13 6h7v7h-7z M4 15h7v7H4z M13 15h7v7h-7z'},
        ],
        'ventajas_rich': [
            {'title': 'Configuraci&oacute;n modular',
             'desc': 'Adaptamos la sala al tama&ntilde;o y forma de tu espacio. Combinamos sof&aacute;s, poltronas y mesas auxiliares seg&uacute;n el flujo de invitados.'},
            {'title': 'Cuero y velvet premium',
             'desc': 'Materiales de alta calidad, f&aacute;ciles de limpiar y resistentes. Tonos disponibles: blanco, negro, gris, beige y velvet en varios colores.'},
            {'title': 'Apto interior y exterior',
             'desc': 'Para sal&oacute;n de eventos, terraza, jard&iacute;n, hotel o coworking. Con cubierta si hay riesgo de lluvia, mantenemos la est&eacute;tica intacta.'},
            {'title': 'Servicio completo',
             'desc': 'Entrega, montaje, instalaci&oacute;n de la sala seg&uacute;n el dise&ntilde;o acordado, y recogida posterior. T&uacute; solo disfrutas.'},
        ],
        'faq': [
            {'q': '&iquest;Cu&aacute;ntos invitados caben en una sala lounge?',
             'a': 'Una sala lounge completa de ASEM acomoda c&oacute;modamente entre 6 y 12 personas. Si tu evento es m&aacute;s grande, combinamos varias salas creando islas de conversaci&oacute;n distribuidas en el espacio. Cot&iacute;zanos cantidad esperada de invitados y dise&ntilde;amos el montaje a tu medida.'},
            {'q': '&iquest;Qu&eacute; colores y materiales tienen disponibles?',
             'a': 'Tenemos salas en cuero ecol&oacute;gico blanco, negro y gris, y en velvet en varios tonos (beige, mostaza, esmeralda, marino). Combinables seg&uacute;n el estilo de tu evento: bodas, c&oacute;cteles corporativos, lanzamientos de marca, fiestas privadas.'},
            {'q': '&iquest;Sirven para eventos al aire libre?',
             'a': 'S&iacute;. Las salas lounge funcionan perfectamente en terrazas, jardines y patios. El cuero es resistente a la humedad ambiente. Solo recomendamos cubierta tipo carpa si hay riesgo de lluvia fuerte para proteger los acabados.'},
            {'q': '&iquest;Cu&aacute;nto cuesta alquilar una sala lounge en Bogot&aacute;?',
             'a': 'El precio depende del n&uacute;mero de piezas, duraci&oacute;n y ubicaci&oacute;n del evento. Cotizamos por WhatsApp en minutos con propuesta clara: incluye sof&aacute;s, mesas, transporte, montaje y recogida. Escr&iacute;benos al 301 322 8490 con detalles de tu evento.'},
            {'q': '&iquest;Puedo combinar la sala lounge con otros estilos?',
             'a': 'Por supuesto. Muchos eventos combinan sala lounge para zona VIP/c&oacute;ctel + sillas tiffany para ceremonia + mesas rusticas para comida. Mezclamos estilos y te asesoramos para que el ambiente sea coherente y memorable.'},
            {'q': '&iquest;Con cu&aacute;nta anticipaci&oacute;n debo reservar?',
             'a': 'Recomendamos al menos 2-3 semanas. Para fechas de alta demanda (diciembre, fines de semana de mayo y agosto, San Valent&iacute;n) reservar con 4-6 semanas garantiza disponibilidad. Si es urgente consulta por WhatsApp; muchas veces logramos atender de &uacute;ltima hora.'},
        ],
        'testimonios_indices': [0, 1, 2],
    },
    '03_SALAS_RUSTICAS': {
        'hero_subtitle': 'Salas r&uacute;sticas en madera natural y cojines tipo barril, perfectas para bodas al aire libre, eventos campestres y celebraciones con est&eacute;tica natural en Bogot&aacute; y alrededores.',
        'hero_specs': [
            ('M3 21l3-3 M21 21l-3-3 M9 21V11l3-4 3 4v10 M5 21V14h4 M15 21v-7h4', 'Madera natural'),
            ('M21 12.79A9 9 0 1 1 11.21 3A7 7 0 0 0 21 12.79z', 'Ideal exterior'),
            ('M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z', 'Perfecto para bodas'),
            ('M3 7h18 M5 7v13h14V7 M9 10h6 M9 14h6', 'Montaje incluido'),
        ],
        'gallery_keywords': ['rustica', 'rusticas', 'rustico', 'madera', 'sala'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Salas r&uacute;sticas completas', 'desc': 'Sof&aacute;s en madera con cojines tipo barril y mesa de centro a juego.',
             'icon': 'M3 12h18 M5 12V8a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v4'},
            {'name': 'Butacos y bancas', 'desc': 'Asientos auxiliares en madera natural para acomodar grupos grandes.',
             'icon': 'M4 8h16v4H4z M6 12v8 M18 12v8'},
            {'name': 'Mesas centrales r&uacute;sticas', 'desc': 'Mesas en madera con acabado natural o envejecido seg&uacute;n el estilo.',
             'icon': 'M3 8h18v3H3z M5 11v8 M19 11v8'},
            {'name': 'Cojines y mantas', 'desc': 'Textiles complementarios en tonos naturales para reforzar la est&eacute;tica.',
             'icon': 'M4 4h16v16H4z M4 12h16 M12 4v16'},
        ],
        'ventajas_rich': [
            {'title': 'Est&eacute;tica natural &uacute;nica',
             'desc': 'Madera real, no imitaci&oacute;n. Cada pieza tiene la textura y nudos propios que dan car&aacute;cter a tu evento, ideal para bodas y eventos campestres.'},
            {'title': 'Perfecto al aire libre',
             'desc': 'Pensado para jardines, fincas, viñedos y eventos campestres. La madera resiste el sol y la humedad sin perder su belleza natural.'},
            {'title': 'Combina con otros estilos',
             'desc': 'La madera natural acompa&ntilde;a perfecto comedores r&uacute;sticos, bombillos vintage y decoraci&oacute;n tipo wedding boho. Te asesoramos para el conjunto perfecto.'},
            {'title': 'Servicio completo',
             'desc': 'Entrega en Bogot&aacute; y alrededores (Chía, Cota, La Calera, etc.), montaje, instalaci&oacute;n cuidadosa y recogida posterior incluidos.'},
        ],
        'faq': [
            {'q': '&iquest;Sirven para bodas al aire libre?',
             'a': 'S&iacute;, las salas r&uacute;sticas son nuestra opci&oacute;n m&aacute;s pedida para bodas al aire libre, fincas y eventos campestres. La madera natural y los cojines tipo barril crean la atm&oacute;sfera c&aacute;lida y acogedora ideal para ceremonias y c&oacute;cteles de boda.'},
            {'q': '&iquest;Qu&eacute; pasa si llueve el d&iacute;a del evento?',
             'a': 'Recomendamos siempre coordinar una cubierta tipo carpa o lona para tu evento al aire libre. La madera resiste salpicaduras pero no lluvia fuerte. Si hay alerta de lluvia para tu fecha, te asesoramos para reubicar el mobiliario a un espacio cubierto sin costo extra.'},
            {'q': '&iquest;Atienden eventos fuera de Bogot&aacute;?',
             'a': 'S&iacute;, cubrimos toda la sabana de Bogot&aacute;: Ch&iacute;a, Cota, Caj&iacute;c&aacute;, La Calera, Sop&oacute;, Tabio, Tenjo, Madrid, Mosquera. Para eventos en fincas y haciendas de la zona campestre, coordinamos transporte y montaje sin problema.'},
            {'q': '&iquest;Cu&aacute;ntos invitados acomoda una sala r&uacute;stica?',
             'a': 'Una sala r&uacute;stica completa acomoda entre 6 y 10 personas. Para bodas grandes combinamos varias salas creando &aacute;reas de descanso distribuidas por el lugar. Cot&iacute;zanos n&uacute;mero esperado de invitados y dise&ntilde;amos el montaje.'},
            {'q': '&iquest;Se puede combinar con comedores r&uacute;sticos?',
             'a': 'S&iacute;, es la combinaci&oacute;n m&aacute;s pedida para bodas: sala r&uacute;stica para zona c&oacute;ctel + comedores r&uacute;sticos largos tipo banquete para la cena. Si quieres el paquete completo, escr&iacute;benos por WhatsApp y te armamos cotizaci&oacute;n unificada.'},
            {'q': '&iquest;Cu&aacute;nto cuesta una sala r&uacute;stica en Bogot&aacute;?',
             'a': 'El precio depende del n&uacute;mero de piezas, duraci&oacute;n y ubicaci&oacute;n del evento. Cotizamos personalizado por WhatsApp en minutos. Escr&iacute;benos al 301 322 8490 con la fecha, ubicaci&oacute;n y n&uacute;mero de invitados de tu evento.'},
        ],
        'testimonios_indices': [0, 1, 2],
    },
    '04_MESAS_LOUNGE': {
        'hero_subtitle': 'Mesas de coctel, mesas redondas con lycra, mesas en vidrio y mesas altas para c&oacute;cteles, bodas y eventos corporativos en Bogot&aacute;. Variedad de tama&ntilde;os y acabados para cada montaje.',
        'hero_specs': [
            ('M3 8h18v3H3z M5 11v8 M19 11v8', 'Vidrio, madera y lycra'),
            ('M12 2v4 M4.93 4.93l2.83 2.83 M16.24 16.24l2.83 2.83 M2 12h4 M18 12h4', 'Multiples colores'),
            ('M9 5h6 M10 3v2 M14 3v2 M9 7h6v12a3 3 0 0 1-3 3h0a3 3 0 0 1-3-3z', 'Altas y bajas'),
            ('M3 7h18 M5 7v13h14V7', 'Montaje incluido'),
        ],
        'gallery_keywords': ['mesa', 'mesas', 'coctel'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Mesas de c&oacute;ctel altas', 'desc': 'Mesas tipo cocktail con lycra blanca, negra o de colores para eventos de pie.',
             'icon': 'M9 5h6 M10 3v2 M14 3v2 M9 7h6v12a3 3 0 0 1-3 3h0a3 3 0 0 1-3-3z'},
            {'name': 'Mesas redondas con lycra', 'desc': 'Mesas redondas con lycra spandex en variedad de colores, ideales para banquetes.',
             'icon': 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z M12 6v6l4 2'},
            {'name': 'Mesas de vidrio', 'desc': 'Mesas modernas en vidrio templado para zonas c&oacute;ctel y &aacute;reas VIP.',
             'icon': 'M3 8h18v3H3z M5 11v8 M19 11v8'},
            {'name': 'Mesas en madera', 'desc': 'Mesas en madera natural para complementar mobiliario r&uacute;stico o industrial.',
             'icon': 'M4 8h16v4H4z M6 12v8 M18 12v8'},
        ],
        'ventajas_rich': [
            {'title': 'Variedad de estilos',
             'desc': 'Tenemos mesas para cualquier tipo de evento: c&oacute;ctel, banquete, corporativo, boda, conferencia. Combinables entre s&iacute; o con sillas y salas lounge.'},
            {'title': 'Lycra spandex en m&uacute;ltiples colores',
             'desc': 'Forros de lycra blanca, negra, dorada, plateada y colores personalizados que se ajustan perfectamente sin pliegues.'},
            {'title': 'Alturas para cada momento',
             'desc': 'Mesas altas (110cm) para c&oacute;ctel de pie, mesas est&aacute;ndar (75cm) para banquete sentado, mesas bajas para zona lounge.'},
            {'title': 'Servicio completo',
             'desc': 'Transporte, montaje, instalaci&oacute;n de forros y recogida incluidos. Llegamos puntuales y dejamos todo armado.'},
        ],
        'faq': [
            {'q': '&iquest;Cu&aacute;ntos invitados caben en cada mesa?',
             'a': 'Las mesas redondas est&aacute;ndar (1.50m de di&aacute;metro) acomodan 8-10 personas para banquete sentado. Las mesas altas de c&oacute;ctel acomodan 4-6 personas de pie. Para mesas largas tipo banquete, calculamos 60cm de espacio por persona.'},
            {'q': '&iquest;Qu&eacute; colores de lycra tienen?',
             'a': 'Manejamos blanco, negro, dorado, plateado, rojo, azul marino y verde esmeralda como colores base. Para colores personalizados o pantone espec&iacute;fico consulta disponibilidad y tiempo de preparaci&oacute;n.'},
            {'q': '&iquest;Las mesas vienen con sillas?',
             'a': 'Las mesas se cotizan por separado de las sillas para que armes el conjunto exacto que necesitas. Si quieres el paquete completo (mesas + sillas + lounge), te armamos cotizaci&oacute;n unificada por WhatsApp.'},
            {'q': '&iquest;Hacen montaje de los forros de lycra?',
             'a': 'S&iacute;, el montaje y ajuste de los forros est&aacute; incluido. Llegamos antes del evento, montamos las mesas con sus forros perfectamente estirados, y recogemos todo al final.'},
            {'q': '&iquest;Qu&eacute; pasa si se manchan los forros durante el evento?',
             'a': 'No te preocupes. Los forros est&aacute;n incluidos en el alquiler y nosotros nos encargamos de la limpieza posterior. Solo en caso de da&ntilde;o severo (corte, quemadura) se cobra reposici&oacute;n.'},
            {'q': '&iquest;Cu&aacute;nto cuesta alquilar mesas para eventos en Bogot&aacute;?',
             'a': 'El precio depende del tipo y cantidad de mesas, los forros, la duraci&oacute;n y ubicaci&oacute;n del evento. Cotizamos por WhatsApp en minutos. Escr&iacute;benos al 301 322 8490 con los detalles de tu evento.'},
        ],
        'testimonios_indices': [0, 1, 2],
    },
    '05_SILLAS_LOUNGE': {
        'hero_subtitle': 'Sillas tiffany, sillas altas de c&oacute;ctel, sillas tipo barra y sillas chiavari para bodas, c&oacute;cteles y eventos sociales en Bogot&aacute;. Variedad de estilos y colores para cada montaje.',
        'hero_specs': [
            ('M5 8h14v9H5z M7 17v3 M17 17v3 M5 8V5h14v3', 'Tiffany y chiavari'),
            ('M12 2v4 M4.93 4.93l2.83 2.83 M16.24 16.24l2.83 2.83 M2 12h4 M18 12h4', 'Variedad de colores'),
            ('M3 7h18 M5 7v13h14V7', 'Apilables y c&oacute;modas'),
            ('M3 21l3-3 M21 21l-3-3 M9 21V11l3-4 3 4v10', 'Interior y exterior'),
        ],
        'gallery_keywords': ['silla', 'sillas'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Sillas Tiffany', 'desc': 'Las cl&aacute;sicas sillas Tiffany en variedad de colores para bodas y eventos elegantes.',
             'icon': 'M5 8h14v9H5z M7 17v3 M17 17v3 M5 8V5h14v3'},
            {'name': 'Sillas altas de c&oacute;ctel', 'desc': 'Sillas tipo barra para mesas altas de c&oacute;ctel con respaldo y apoyo.',
             'icon': 'M9 5h6 M9 7h6v12a3 3 0 0 1-3 3 3 3 0 0 1-3-3z'},
            {'name': 'Sillas chiavari', 'desc': 'Sillas chiavari en madera o resina, ic&oacute;nicas para bodas y galas.',
             'icon': 'M6 8h12v10H6z M8 18v2 M16 18v2 M8 8V4h8v4'},
            {'name': 'Sillas blancas plegables', 'desc': 'Sillas blancas pr&aacute;cticas y elegantes para ceremonias y eventos al aire libre.',
             'icon': 'M5 8h14v8H5z M7 16v4 M17 16v4'},
        ],
        'ventajas_rich': [
            {'title': 'Variedad para cada evento',
             'desc': 'Desde sillas Tiffany para bodas hasta sillas altas de c&oacute;ctel para eventos de pie. Te asesoramos para el tipo de silla ideal seg&uacute;n el momento del evento.'},
            {'title': 'Colores y acabados',
             'desc': 'Blanco, negro, dorado, plateado, transparente, madera natural. Combinables seg&uacute;n el c&oacute;digo de color de tu evento.'},
            {'title': 'Cojines incluidos',
             'desc': 'Las sillas Tiffany y chiavari incluyen cojines blancos o del color que elijas. Sin costo adicional.'},
            {'title': 'Apilables y resistentes',
             'desc': 'Construcci&oacute;n robusta en madera o resina de alta calidad. Apilables para optimizar espacio durante el montaje.'},
        ],
        'faq': [
            {'q': '&iquest;Qu&eacute; tipos de sillas tienen disponibles?',
             'a': 'Manejamos sillas Tiffany (las cl&aacute;sicas para bodas), sillas altas de c&oacute;ctel para mesas tipo bar, sillas chiavari en madera natural o dorada, sillas blancas plegables para ceremonias, y sillas de comedor variadas.'},
            {'q': '&iquest;Las sillas Tiffany incluyen coj&iacute;n?',
             'a': 'S&iacute;. Todas nuestras sillas Tiffany y chiavari incluyen coj&iacute;n blanco sin costo adicional. Si quieres cojines de otro color (dorado, rosa, gris, etc.) consulta disponibilidad y posibles cargos m&iacute;nimos por personalizaci&oacute;n.'},
            {'q': '&iquest;Cu&aacute;ntos invitados acomodan?',
             'a': 'Una mesa redonda de 1.50m acomoda 8 sillas. Una mesa de banquete de 2.40m acomoda 8-10 sillas. Para ceremonias acomodamos en filas con pasillo central de 1.20m. Cu&eacute;ntanos cantidad de invitados y dise&ntilde;amos el montaje.'},
            {'q': '&iquest;Sirven para eventos al aire libre?',
             'a': 'S&iacute;. Las sillas Tiffany y chiavari resisten perfectamente al aire libre. Solo recomendamos cubierta si hay riesgo de lluvia fuerte. Para terrenos blandos (jard&iacute;n h&uacute;medo) usamos sillas con base ancha para evitar que se hundan.'},
            {'q': '&iquest;Cu&aacute;nto cuesta alquilar sillas en Bogot&aacute;?',
             'a': 'El precio depende del tipo de silla, cantidad, duraci&oacute;n y ubicaci&oacute;n del evento. Cotizamos por WhatsApp en minutos con propuesta clara. Escr&iacute;benos al 301 322 8490 con la fecha, tipo de silla y n&uacute;mero de invitados.'},
            {'q': '&iquest;Cu&aacute;nto antes debo reservar para una boda?',
             'a': 'Para bodas recomendamos reservar con 4-6 semanas de anticipaci&oacute;n, especialmente en temporada alta (diciembre, mayo, agosto). Las sillas Tiffany son nuestro inventario m&aacute;s pedido para bodas, as&iacute; que entre m&aacute;s anticipado mejor.'},
        ],
        'testimonios_indices': [0, 1, 2],
    },
    '06_SILLAS_INTERLOCUTORAS': {
        'hero_subtitle': 'Sillas para juntas, conferencias y eventos corporativos en Bogot&aacute;. Modelos c&oacute;modos para sesiones largas, apilables, en negro, gris y tonos ejecutivos.',
        'hero_specs': [
            ('M5 8h14v9H5z M7 17v3 M17 17v3', 'C&oacute;modas para sesiones largas'),
            ('M4 6h16v3H4z M4 14h16v3H4z M4 22h16', 'Apilables'),
            ('M3 12h18 M5 12V8a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v4', 'Acolchado ergon&oacute;mico'),
            ('M3 7h18 M5 7v13h14V7', 'Entrega y recogida incluida'),
        ],
        'gallery_keywords': ['silla', 'interlocutora', 'conferencia', 'junta'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Sillas interlocutoras cl&aacute;sicas', 'desc': 'Sillas tipo ejecutivo con respaldo medio, ideales para juntas directivas.',
             'icon': 'M5 8h14v9H5z M7 17v3 M17 17v3 M5 8V5h14v3'},
            {'name': 'Sillas para conferencias', 'desc': 'Asientos acolchados y apilables para auditorios, capacitaciones y seminarios.',
             'icon': 'M6 8h12v10H6z M8 18v2 M16 18v2'},
            {'name': 'Sillas plegables corporativas', 'desc': 'Sillas pr&aacute;cticas para eventos masivos: ferias, lanzamientos, ruedas de prensa.',
             'icon': 'M5 8h14v8H5z M7 16v4 M17 16v4'},
            {'name': 'Sillas tipo Eames', 'desc': 'Estilo m&aacute;s moderno y minimalista para reuniones creativas o coworking.',
             'icon': 'M6 5l-2 7h16l-2-7 M8 12v7 M16 12v7'},
        ],
        'ventajas_rich': [
            {'title': 'Pensadas para sesiones largas',
             'desc': 'Acolchado ergon&oacute;mico que mantiene la comodidad durante reuniones de 2-4 horas. Apoyo lumbar y soporte adecuado.'},
            {'title': 'Apilables y f&aacute;ciles de transportar',
             'desc': 'Optimizamos el espacio durante el montaje y desmontaje. Llegamos antes del evento para evitar interrupciones.'},
            {'title': 'Acabados corporativos',
             'desc': 'Negro, gris ejecutivo y tonos sobrios que no distraen del contenido del evento. Apariencia profesional y limpia.'},
            {'title': 'Servicio express',
             'desc': 'Para eventos corporativos coordinamos entrega y montaje fuera del horario laboral para no interrumpir tu jornada de oficina.'},
        ],
        'faq': [
            {'q': '&iquest;Qu&eacute; tipo de sillas tienen para auditorios y conferencias?',
             'a': 'Manejamos sillas apilables acolchadas (la opci&oacute;n m&aacute;s solicitada para auditorios), sillas plegables corporativas, sillas interlocutoras tipo ejecutivo y sillas tipo Eames para ambientes m&aacute;s modernos. Todas pensadas para sesiones largas.'},
            {'q': '&iquest;Hacen montaje fuera del horario laboral?',
             'a': 'S&iacute;. Para eventos corporativos coordinamos entrega y montaje en horario nocturno o muy temprano en la ma&ntilde;ana para no interrumpir tu jornada. Solo coord&iacute;nalo previamente con nuestro equipo.'},
            {'q': '&iquest;Pueden hacer entrega para varios d&iacute;as?',
             'a': 'S&iacute;, para eventos corporativos multi-d&iacute;a (congresos, ferias, capacitaciones) tenemos tarifas especiales por d&iacute;a adicional. La log&iacute;stica es la misma: entrega inicial, mantenimiento y recogida al final.'},
            {'q': '&iquest;Cu&aacute;ntos invitados acomodan en formato auditorio?',
             'a': 'En formato auditorio (filas con pasillo central de 1.20m) calculamos 0.6 m&sup2; por persona. Te asesoramos para optimizar el aforo seg&uacute;n las dimensiones del sal&oacute;n y normas de evacuaci&oacute;n.'},
            {'q': '&iquest;Cu&aacute;nto cuesta alquilar sillas para eventos empresariales?',
             'a': 'El precio depende de la cantidad, el modelo, la duraci&oacute;n y ubicaci&oacute;n. Cotizamos por WhatsApp en minutos con propuesta clara que incluye entrega, montaje y recogida. Escr&iacute;benos al 301 322 8490 con detalles del evento.'},
            {'q': '&iquest;Pueden coordinar con el departamento de eventos de mi empresa?',
             'a': 'Por supuesto. Trabajamos regularmente con &aacute;reas de eventos corporativos y agencias. Coordinamos directamente con tu equipo log&iacute;stico, manejamos facturaci&oacute;n empresarial y nos ajustamos a tus procesos internos de aprobaci&oacute;n.'},
        ],
        'testimonios_indices': [0, 1, 4],
    },
    '07_POLTRONAS': {
        'hero_subtitle': 'Poltronas individuales en cuero ecol&oacute;gico blanco, negro y vintage para zonas VIP, eventos corporativos y &aacute;reas de descanso. Acabado premium y comodidad para sesiones largas.',
        'hero_specs': [
            ('M5 11h14v9H5z M7 11V7a5 5 0 0 1 10 0v4', 'Cuero ecol&oacute;gico premium'),
            ('M12 2v4 M4.93 4.93l2.83 2.83 M16.24 16.24l2.83 2.83 M2 12h4 M18 12h4', 'Blanco, negro, vintage'),
            ('M5 11l4 4 8-8', 'Asiento amplio y c&oacute;modo'),
            ('M3 7h18 M5 7v13h14V7', 'Montaje incluido'),
        ],
        'gallery_keywords': ['poltrona', 'poltronas'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Poltronas cuero blanco', 'desc': 'Las cl&aacute;sicas poltronas blancas para zonas VIP, c&oacute;cteles y lanzamientos de marca.',
             'icon': 'M5 11h14v9H5z M7 11V7a5 5 0 0 1 10 0v4'},
            {'name': 'Poltronas cuero negro', 'desc': 'Poltronas en cuero negro para eventos corporativos y ambientes m&aacute;s formales.',
             'icon': 'M5 11h14v9H5z M7 11V7a5 5 0 0 1 10 0v4 M5 17h14'},
            {'name': 'Poltronas vintage', 'desc': 'Estilo cl&aacute;sico tipo Chesterfield o capiton&eacute; para eventos con est&eacute;tica retro.',
             'icon': 'M5 11h14v9H5z M5 13h14 M5 15h14 M5 17h14 M7 11V7a5 5 0 0 1 10 0v4'},
            {'name': 'Poltronas reclinables', 'desc': 'Modelos con respaldo reclinable para &aacute;reas de descanso o salones de espera.',
             'icon': 'M5 11l5-5h4l5 5v9H5z M9 20v-4 M15 20v-4'},
        ],
        'ventajas_rich': [
            {'title': 'Cuero ecol&oacute;gico premium',
             'desc': 'Acabado de alta calidad, resistente y f&aacute;cil de limpiar. Apariencia profesional que se mantiene impecable durante todo el evento.'},
            {'title': 'Comodidad para sesiones largas',
             'desc': 'Asiento amplio, respaldo ergon&oacute;mico y relleno de espuma de alta densidad. Ideal para entrevistas, ruedas de prensa y &aacute;reas VIP.'},
            {'title': 'Combinables con cualquier mobiliario',
             'desc': 'Funcionan perfecto solas o en conjunto con salas lounge, mesas de centro y cubos auxiliares. Te asesoramos para crear el espacio ideal.'},
            {'title': 'Servicio completo',
             'desc': 'Entrega, montaje, ubicaci&oacute;n seg&uacute;n el layout acordado, y recogida al final del evento. Sin esfuerzo de tu lado.'},
        ],
        'faq': [
            {'q': '&iquest;Qu&eacute; colores y estilos de poltronas tienen?',
             'a': 'Manejamos poltronas en cuero ecol&oacute;gico blanco (la m&aacute;s popular), negro, gris, beige y modelos vintage tipo Chesterfield capiton&eacute;. Para colores especiales o estilos personalizados consulta disponibilidad.'},
            {'q': '&iquest;Las poltronas vienen con cojines?',
             'a': 'El cuero ecol&oacute;gico ya tiene relleno de espuma de alta densidad integrado, no necesita cojines extra. Si quieres cojines decorativos adicionales (en color o estampado) cot&iacute;zalos como complemento.'},
            {'q': '&iquest;Para qu&eacute; tipo de eventos son ideales?',
             'a': 'Las poltronas son perfectas para: zonas VIP en c&oacute;cteles y lanzamientos, &aacute;reas de descanso en bodas y galas, salones de espera para ruedas de prensa, espacios de entrevista uno-a-uno, &aacute;reas de fotograf&iacute;a profesional.'},
            {'q': '&iquest;Cu&aacute;ntas poltronas recomiendan para un evento?',
             'a': 'Depende del aforo: para 50 invitados, 2-3 poltronas crean una zona VIP. Para 100+ invitados recomendamos 4-6 poltronas distribuidas. Para zonas de fotos o entrevistas, 1-2 poltronas con mesa de centro funcionan perfecto.'},
            {'q': '&iquest;Sirven para eventos al aire libre?',
             'a': 'S&iacute;, el cuero ecol&oacute;gico es resistente a humedad ambiente. Solo recomendamos cubierta tipo carpa si hay riesgo de lluvia fuerte. Si vas a usarlas en exteriores soleados, evitamos exposici&oacute;n directa prolongada al sol para preservar el acabado.'},
            {'q': '&iquest;Cu&aacute;nto cuesta alquilar poltronas en Bogot&aacute;?',
             'a': 'El precio depende del tipo, cantidad, duraci&oacute;n y ubicaci&oacute;n. Cotizamos por WhatsApp en minutos con propuesta clara. Escr&iacute;benos al 301 322 8490 con los detalles de tu evento y dise&ntilde;amos el conjunto ideal.'},
        ],
        'testimonios_indices': [0, 1, 4],
    },
    '08_COMEDORES_RUSTICOS': {
        'hero_subtitle': 'Comedores r&uacute;sticos largos tipo banquete con sillas tiffany, butacos, carretes y barras de madera. La opci&oacute;n preferida para bodas, comidas corporativas y eventos al aire libre en Bogot&aacute;.',
        'hero_specs': [
            ('M3 21l3-3 M21 21l-3-3 M9 21V11l3-4 3 4v10', 'Madera natural'),
            ('M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78z', 'Ideal bodas'),
            ('M4 8h16v4H4z M6 12v8 M18 12v8', 'Mesas largas tipo banquete'),
            ('M3 7h18 M5 7v13h14V7', 'Montaje incluido'),
        ],
        'gallery_keywords': ['comedor', 'comedores', 'rustica', 'rusticas', 'rustico', 'banquete', 'mesa', 'carrete'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Mesas largas tipo banquete', 'desc': 'Mesas r&uacute;sticas de 2-3 metros en madera natural, ideales para boda y comidas formales.',
             'icon': 'M4 8h16v4H4z M6 12v8 M18 12v8'},
            {'name': 'Sillas tiffany doradas o madera', 'desc': 'Sillas tiffany acabado dorado o madera natural que combinan con los comedores r&uacute;sticos.',
             'icon': 'M5 8h14v9H5z M7 17v3 M17 17v3 M5 8V5h14v3'},
            {'name': 'Butacos y bancas de madera', 'desc': 'Bancas largas tipo wedding para acomodar grupos grandes con est&eacute;tica r&uacute;stica.',
             'icon': 'M4 6h16v3H4z M4 16h16v3H4z'},
            {'name': 'Barras y carretes vintage', 'desc': 'Barras de madera y carretes industriales tipo wood como mesas auxiliares o de c&oacute;ctel.',
             'icon': 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z M12 7v10 M7 12h10'},
        ],
        'ventajas_rich': [
            {'title': 'Madera natural genuina',
             'desc': 'Cada mesa tiene la textura y nudos propios de la madera real. La est&eacute;tica r&uacute;stica auT&eacute;ntica que necesitan las bodas modernas y eventos campestres.'},
            {'title': 'Mesas largas y manteles opcionales',
             'desc': 'Mesas de 2 y 3 metros pueden unirse para banquetes de 30, 50 o 100+ personas. Puedes pedirlas con o sin mantel seg&uacute;n el estilo deseado.'},
            {'title': 'Combinan perfecto con todo',
             'desc': 'Funcionan con sillas Tiffany doradas o de madera, con sala lounge para zona c&oacute;ctel, con bombillos vintage colgantes, con decoraci&oacute;n floral.'},
            {'title': 'Para eventos al aire libre',
             'desc': 'Resistentes a la humedad y al sol moderado. Perfectas para bodas en fincas, viñedos, jardines y eventos campestres alrededor de Bogot&aacute;.'},
        ],
        'faq': [
            {'q': '&iquest;Qu&eacute; tama&ntilde;os de mesas tipo banquete tienen?',
             'a': 'Manejamos mesas r&uacute;sticas largas de 2.40m (8-10 personas) y 3m (10-12 personas). Pueden unirse formando mesas de banquete continuas para 20, 50 o 100+ personas. Te asesoramos seg&uacute;n el aforo de tu evento.'},
            {'q': '&iquest;Vienen con mantel o sin mantel?',
             'a': 'Las mesas se cotizan sin mantel porque muchas bodas prefieren la est&eacute;tica de la madera natural visible. Si quieres mantel (blanco, beige, lino crudo, runner), lo cotizamos como complemento.'},
            {'q': '&iquest;Las mesas vienen con sillas?',
             'a': 'Las mesas y sillas se cotizan por separado para flexibilidad. La combinaci&oacute;n m&aacute;s pedida es mesa r&uacute;stica + sillas Tiffany doradas o de madera. Si quieres el paquete completo te armamos cotizaci&oacute;n unificada.'},
            {'q': '&iquest;Cu&aacute;ntas personas caben por metro de mesa?',
             'a': 'Calculamos 60cm de espacio por persona para banquete c&oacute;modo. Una mesa de 2.40m acomoda 8 personas (4 por lado), una de 3m acomoda 10 personas. Si quieres holgura para servir m&aacute;s c&oacute;modamente, calcula 70-80cm por persona.'},
            {'q': '&iquest;Atienden bodas en fincas fuera de Bogot&aacute;?',
             'a': 'S&iacute;. Cubrimos Bogot&aacute; y toda la sabana: Ch&iacute;a, Cota, Caj&iacute;c&aacute;, La Calera, Sop&oacute;, Tabio, Tenjo, Madrid, Mosquera. Para fincas m&aacute;s alejadas (Vill&aacute;ngel, Anolaima, etc.) consulta disponibilidad y costo de transporte.'},
            {'q': '&iquest;Cu&aacute;nto cuesta un comedor r&uacute;stico para una boda?',
             'a': 'El precio depende de la cantidad de mesas, sillas, ubicaci&oacute;n y duraci&oacute;n. Cotizamos por WhatsApp en minutos. Para paquetes de boda completos (comedor + sillas + sala lounge + bombillos vintage) tenemos descuentos por volumen.'},
        ],
        'testimonios_indices': [0, 1, 2],
    },
    '10_MOB_INDUSTRIAL': {
        'hero_subtitle': 'Mobiliario industrial en hierro y madera para ferias, eventos corporativos y activaciones de marca. Mesas, sillas, barras y lamparas estilo loft urbano con car&aacute;cter.',
        'hero_specs': [
            ('M4 6h16v3H4z M4 14h16v3H4z M8 9v5 M16 9v5', 'Hierro + madera'),
            ('M3 5h6v6H3z M15 5h6v6h-6z M3 13h6v6H3z M15 13h6v6h-6z', 'Estilo loft urbano'),
            ('M9 12l2 2 4-4 M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z', 'Resistente y duradero'),
            ('M3 7h18 M5 7v13h14V7', 'Montaje incluido'),
        ],
        'gallery_keywords': ['industrial', 'industriales'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Mesas industriales', 'desc': 'Mesas con base de hierro y tablero de madera para ferias, comedores y &aacute;reas de c&oacute;ctel.',
             'icon': 'M3 8h18v3H3z M5 11v8 M19 11v8'},
            {'name': 'Sillas y butacos industriales', 'desc': 'Sillas met&aacute;licas o con asiento de madera, ideales para barras y mesas altas.',
             'icon': 'M5 8h14v9H5z M7 17v3 M17 17v3 M5 8V5h14v3'},
            {'name': 'Barras industriales', 'desc': 'Barras met&aacute;licas para servicio de c&oacute;cteles con la est&eacute;tica de bar industrial.',
             'icon': 'M3 7h18v3H3z M5 10v10h14V10 M9 14h6'},
            {'name': 'Lamparas y luz c&aacute;lida', 'desc': 'L&aacute;mparas tipo Edison y focos colgantes que complementan el estilo industrial.',
             'icon': 'M9 18h6 M10 22h4 M8 13a5 5 0 0 1 4-8 5 5 0 0 1 4 8c-1 1-2 2-2 3v1H10v-1c0-1-1-2-2-3z'},
        ],
        'ventajas_rich': [
            {'title': 'Est&eacute;tica con car&aacute;cter',
             'desc': 'La combinaci&oacute;n hierro + madera crea un look loft urbano que destaca en ferias, lanzamientos de marca y eventos corporativos modernos.'},
            {'title': 'Resistente y duradero',
             'desc': 'Estructura met&aacute;lica robusta y madera tratada que aguantan el uso intensivo de eventos masivos sin perder apariencia.'},
            {'title': 'Versatilidad de montaje',
             'desc': 'Combinable con bombillos vintage, sillas tiffany y mobiliario lounge para crear ambientes h&iacute;bridos modernos-cl&aacute;sicos.'},
            {'title': 'Para ferias y activaciones',
             'desc': 'Ideal para stands en ferias industriales, expo, lanzamientos de marca tech, eventos en oficinas y coworking.'},
        ],
        'faq': [
            {'q': '&iquest;Qu&eacute; tipo de eventos prefieren este estilo?',
             'a': 'El mobiliario industrial brilla en: ferias y expos, lanzamientos de marca (especialmente tech), eventos corporativos modernos, activaciones en cervecer&iacute;as artesanales o restaurantes con estilo, fotograf&iacute;a de moda y publicidad.'},
            {'q': '&iquest;Combina con otros estilos?',
             'a': 'S&iacute;. Lo industrial combina perfecto con bombillos vintage (super pedidos para eventos al aire libre), sillas tiffany doradas o de madera y mobiliario r&uacute;stico. Para eventos m&aacute;s formales combina bien con sala lounge en cuero negro.'},
            {'q': '&iquest;Las mesas industriales son altas o bajas?',
             'a': 'Manejamos ambas: mesas altas industriales (110cm) para c&oacute;ctel de pie y mesas est&aacute;ndar (75cm) para banquete sentado. Tambi&eacute;n barras altas en estilo industrial para servicio de bebidas y c&oacute;cteler&iacute;a.'},
            {'q': '&iquest;Es resistente para uso al aire libre?',
             'a': 'S&iacute;. La estructura de hierro resiste la intemperie sin oxidarse f&aacute;cilmente. La madera del tablero tiene acabado tratado para resistir humedad ambiente. Solo recomendamos cubierta tipo carpa si hay riesgo de lluvia fuerte.'},
            {'q': '&iquest;Hacen entrega para ferias multi-d&iacute;a?',
             'a': 'S&iacute;. Para ferias de 2-5 d&iacute;as tenemos tarifas especiales por d&iacute;a adicional. Entregamos antes del montaje del stand, hacemos mantenimiento intermedio si es necesario, y recogemos al cierre.'},
            {'q': '&iquest;Cu&aacute;nto cuesta alquilar mobiliario industrial en Bogot&aacute;?',
             'a': 'Depende del tipo de piezas, cantidad, duraci&oacute;n y ubicaci&oacute;n. Cotizamos personalizado por WhatsApp en minutos. Escr&iacute;benos al 301 322 8490 con los detalles de tu evento o feria.'},
        ],
        'testimonios_indices': [0, 1, 4],
    },
    '11_MESAS_PICNIC': {
        'hero_subtitle': 'Mesas tipo picnic, cojines y mantas para eventos al aire libre con est&eacute;tica casual y relajada. Perfectos para bodas campestres, eventos infantiles, brunch y celebraciones tipo picnic urbano.',
        'hero_specs': [
            ('M3 12h18 M5 12V8a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v4 M3 12v6 M21 12v6', 'Estilo picnic relajado'),
            ('M21 12.79A9 9 0 1 1 11.21 3A7 7 0 0 0 21 12.79z', 'Para exterior'),
            ('M4 4h16v16H4z M4 12h16 M12 4v16', 'Manteles y cojines'),
            ('M3 7h18 M5 7v13h14V7', 'Montaje incluido'),
        ],
        'gallery_keywords': ['picnic'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Mesas picnic cl&aacute;sicas', 'desc': 'Mesas tradicionales con banca incorporada en madera natural, ideales para parques.',
             'icon': 'M4 8h16v4H4z M6 12v8 M18 12v8'},
            {'name': 'Mesas bajas tipo japon&eacute;s', 'desc': 'Mesas bajas con cojines en el piso para experiencias informales tipo "low table".',
             'icon': 'M4 12h16v3H4z M6 15v5 M18 15v5'},
            {'name': 'Cojines y mantas', 'desc': 'Textiles en variedad de colores y estampados para acomodar invitados.',
             'icon': 'M3 5h18v4H3z M6 9v10 M18 9v10 M3 19h18'},
            {'name': 'Conjuntos completos picnic', 'desc': 'Paquetes que incluyen mesa + cojines + mantel + canasta decorativa.',
             'icon': 'M6 4h12v5H6z M5 9h14v11H5z M9 14h6'},
        ],
        'ventajas_rich': [
            {'title': 'Est&eacute;tica casual y c&aacute;lida',
             'desc': 'La combinaci&oacute;n de madera + textiles crea atm&oacute;sferas relajadas perfectas para brunch, picnic urbano, bodas campestres y celebraciones infantiles.'},
            {'title': 'Para exterior puro',
             'desc': 'Pensado para jardines, parques, fincas, terrazas y patios. Resistente al sol y la humedad ambiente.'},
            {'title': 'Combinable con otros estilos',
             'desc': 'Funciona perfecto con bombillos vintage colgantes, comedores r&uacute;sticos para la cena, y bouquets florales en colores tierra.'},
            {'title': 'Montaje y desmontaje &aacute;gil',
             'desc': 'Logr&iacute;stica simple porque las mesas picnic vienen ya armadas. Llegamos, las ubicamos y listo. Recogida igual de r&aacute;pida al final del evento.'},
        ],
        'faq': [
            {'q': '&iquest;Para qu&eacute; eventos sirven las mesas picnic?',
             'a': 'Son perfectas para: bodas campestres y al aire libre, eventos infantiles y fiestas de cumplea&ntilde;os familiares, brunch en jardines, eventos corporativos relajados (team building), picnic urbano y celebraciones tipo "garden party".'},
            {'q': '&iquest;Las mesas picnic vienen con banca incorporada?',
             'a': 'S&iacute;, las mesas picnic cl&aacute;sicas vienen con banca a ambos lados integrada — un solo bloque listo para usar. Tambi&eacute;n manejamos mesas bajas tipo japon&eacute;s donde los invitados se sientan en el piso con cojines.'},
            {'q': '&iquest;Incluyen mantel y cojines?',
             'a': 'El alquiler base incluye solo la mesa con banca. Manteles tipo cuadros vichy, cojines y mantas decorativas se cotizan como complemento. Te asesoramos para crear el "look picnic" completo seg&uacute;n tu paleta de colores.'},
            {'q': '&iquest;Cu&aacute;ntas personas caben por mesa picnic?',
             'a': 'Una mesa picnic cl&aacute;sica acomoda 6 personas (3 por lado). Para grupos grandes combinamos varias mesas formando filas tipo banquete. Para mesas bajas tipo japon&eacute;s calculamos 4-6 personas por mesa con cojines individuales.'},
            {'q': '&iquest;Sirven para eventos infantiles?',
             'a': 'Por supuesto. Las mesas picnic son nuestro inventario m&aacute;s pedido para fiestas infantiles porque la altura es ideal para ni&ntilde;os, la madera es segura (sin esquinas filosas) y el ambiente picnic es divertido para los peques.'},
            {'q': '&iquest;Cu&aacute;nto cuesta alquilar mesas picnic en Bogot&aacute;?',
             'a': 'El precio depende de la cantidad, los complementos (cojines, manteles) y la ubicaci&oacute;n. Cotizamos por WhatsApp en minutos. Escr&iacute;benos al 301 322 8490 con los detalles de tu evento.'},
        ],
        'testimonios_indices': [0, 1, 2],
    },
    '12_MOB_ACAPULCO': {
        'hero_subtitle': 'Sillas Acapulco multicolor y unicolor para eventos frescos, fiestas tropicales y celebraciones al aire libre en Bogot&aacute;. El cl&aacute;sico mexicano con personalidad para tu evento.',
        'hero_specs': [
            ('M5 8h14v9H5z M7 17v3 M17 17v3', 'Sillas Acapulco ic&oacute;nicas'),
            ('M12 2v4 M4.93 4.93l2.83 2.83 M16.24 16.24l2.83 2.83 M2 12h4 M18 12h4', 'Multicolor o unicolor'),
            ('M21 12.79A9 9 0 1 1 11.21 3A7 7 0 0 0 21 12.79z', 'Apto exterior'),
            ('M3 7h18 M5 7v13h14V7', 'Montaje incluido'),
        ],
        'gallery_keywords': ['acapulco'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Sillas Acapulco multicolor', 'desc': 'Las cl&aacute;sicas sillas Acapulco en mezcla de colores vibrantes (fucsia, turquesa, amarillo, lima).',
             'icon': 'M5 8h14v9H5z M7 17v3 M17 17v3'},
            {'name': 'Sillas Acapulco unicolor', 'desc': 'Para una est&eacute;tica m&aacute;s sobria: blanco, negro o un solo color a juego con tu paleta.',
             'icon': 'M5 8h14v9H5z M7 17v3 M17 17v3'},
            {'name': 'Mesas tipo Acapulco', 'desc': 'Mesas auxiliares y centrales con el mismo estilo de tejido para complementar el conjunto.',
             'icon': 'M3 8h18v3H3z M5 11v8 M19 11v8'},
            {'name': 'Sets completos Acapulco', 'desc': 'Conjuntos de 4 sillas + mesa central, perfectos para zonas chill out tropicales.',
             'icon': 'M4 6h7v7H4z M13 6h7v7h-7z M4 15h7v7H4z M13 15h7v7h-7z'},
        ],
        'ventajas_rich': [
            {'title': 'Ic&oacute;nicas y reconocibles',
             'desc': 'Las sillas Acapulco son un cl&aacute;sico del dise&ntilde;o mexicano. Tu evento se ve fotogr&aacute;fico, tropical y memorable con solo unas pocas piezas.'},
            {'title': 'Colores que alegran',
             'desc': 'Disponibles en m&uacute;ltiples colores vibrantes o tonos sobrios seg&uacute;n el c&oacute;digo de tu evento. Combinables entre s&iacute; para crear paletas alegres.'},
            {'title': 'Resistente al exterior',
             'desc': 'Estructura met&aacute;lica con tejido de PVC tratado. Aguantan sol directo, humedad y uso intensivo sin perder color ni forma.'},
            {'title': 'Para eventos casual y temas tropical',
             'desc': 'Ideales para: bodas en clima c&aacute;lido, fiestas tem&aacute;ticas, eventos de piscina, terraza chill, beach club, lanzamientos de marca con est&eacute;tica fresh.'},
        ],
        'faq': [
            {'q': '&iquest;Qu&eacute; colores de sillas Acapulco tienen?',
             'a': 'Manejamos los colores cl&aacute;sicos vibrantes: fucsia, turquesa, amarillo, naranja, lima, azul, rojo. Tambi&eacute;n versiones sobrias: blanco, negro, gris y c&aacute;mara natural. Puedes mezclarlos (multicolor) o pedir todas en un solo color (unicolor).'},
            {'q': '&iquest;Para qu&eacute; tipo de eventos son ideales?',
             'a': 'Las sillas Acapulco brillan en: bodas con est&eacute;tica tropical o boho, fiestas tem&aacute;ticas (Frida Kahlo, mexicana, tropical), eventos en piscina o beach club, terrazas y patios, lanzamientos de marca con estilo fresco, eventos infantiles coloridos.'},
            {'q': '&iquest;Son c&oacute;modas para eventos largos?',
             'a': 'S&iacute;. El tejido de PVC se adapta a la postura y la inclinaci&oacute;n del respaldo es ergon&oacute;mica. Son perfectas para eventos de 3-6 horas. Para sesiones m&aacute;s largas (boda completa) puedes combinarlas con cojines extra para mayor comodidad.'},
            {'q': '&iquest;Sirven al aire libre con lluvia o sol fuerte?',
             'a': 'Resisten perfectamente sol y humedad ambiente sin perder color. Para lluvia fuerte recomendamos protecci&oacute;n tipo carpa porque aunque el tejido es resistente, prolongados charcos pueden manchar. El estructural met&aacute;lico tiene tratamiento anti-corrosi&oacute;n.'},
            {'q': '&iquest;Las sillas Acapulco se pueden apilar?',
             'a': 'S&iacute;, son apilables verticalmente, lo que optimiza espacio durante el montaje. Esto nos permite llegar puntuales aunque tengas un montaje complicado o de gran volumen.'},
            {'q': '&iquest;Cu&aacute;nto cuesta alquilar sillas Acapulco en Bogot&aacute;?',
             'a': 'El precio depende de la cantidad, el color (multicolor vs unicolor), duraci&oacute;n y ubicaci&oacute;n del evento. Cotizamos por WhatsApp en minutos. Escr&iacute;benos al 301 322 8490 con detalles de tu evento.'},
        ],
        'testimonios_indices': [0, 1, 2],
    },
    '09_MOBILIARIO_LED': {
        'hero_subtitle': 'Mesas, barras, poltronas y mesas altas LED que transforman cualquier espacio. Colores ajustables, bater&iacute;a de 8-10 horas, ideales para fiestas nocturnas, c&oacute;cteles y eventos corporativos en Bogot&aacute;.',
        'hero_banner': 'hero-led-banner.webp',
        # Specs rapidos visibles al lado del hero (B2B-friendly)
        'hero_specs': [
            ('M8 5h8 M10 3v2 M14 3v2 M9 8h6v9a3 3 0 0 1-3 3h0a3 3 0 0 1-3-3z', '8-10h bateria'),
            ('M12 2v4 M12 18v4 M4.93 4.93l2.83 2.83 M16.24 16.24l2.83 2.83 M2 12h4 M18 12h4 M4.93 19.07l2.83-2.83 M16.24 7.76l2.83-2.83', '16 colores RGB'),
            ('M12 22s8-7 8-13a8 8 0 0 0-16 0c0 6 8 13 8 13z M12 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6z', 'Apto exterior'),
            ('M3 7h18 M5 7v13h14V7 M9 10h6 M9 14h6 M9 18h6', 'Montaje incluido'),
        ],
        # Showcase usa solo fotos LED (las "Otras Referencias" quedan en DOM ocultas para SEO)
        'gallery_keywords': ['led', 'iluminad', 'mobiliario-para-eventos-en-bogota'],
        'use_showcase': True,
        'productos_rich': [
            {
                'name': 'Mesas iluminadas LED',
                'desc': 'Mesas centrales y de cubo iluminadas que cambian entre 16 colores.',
                'icon': 'M3 8h18v9H3z M3 8l3-3h12l3 3 M9 17v3 M15 17v3',
            },
            {
                'name': 'Barras LED para c&oacute;cteles',
                'desc': 'Barras modulares con frente iluminado para open bar y servicio de bebidas.',
                'icon': 'M3 7h18v3H3z M5 10v10h14V10 M9 14h6',
            },
            {
                'name': 'Poltronas y sillas LED',
                'desc': 'Sillones, puff y sillas con luz interior para zonas lounge y descanso.',
                'icon': 'M5 11h14v9H5z M7 11V7a5 5 0 0 1 10 0v4',
            },
            {
                'name': 'Mesas altas LED',
                'desc': 'Mesas tipo cocktail iluminadas, perfectas para eventos de pie.',
                'icon': 'M6 4h12v3H6z M9 7v13 M15 7v13 M5 20h14',
            },
        ],
        'ventajas_rich': [
            {
                'title': 'Impacto visual &uacute;nico',
                'desc': '16 colores RGB ajustables v&iacute;a control remoto. Sincronizable con el ambiente o cambio autom&aacute;tico al ritmo de la m&uacute;sica.',
            },
            {
                'title': 'Bater&iacute;a de 8 a 10 horas',
                'desc': 'Sin cables visibles, sin necesidad de toma corriente. Te damos las piezas cargadas al 100% para que las ubiques donde quieras.',
            },
            {
                'title': 'Resistente para interior y exterior',
                'desc': 'Acabado tratado contra salpicaduras y polvo. Apto para terrazas y jardines (con cobertura si hay riesgo de lluvia fuerte).',
            },
            {
                'title': 'Servicio completo incluido',
                'desc': 'Entrega, montaje, controles remotos, asistencia t&eacute;cnica durante el evento y recogida posterior. Tu solo disfrutas.',
            },
        ],
        'faq': [
            {
                'q': '&iquest;El mobiliario LED funciona con bater&iacute;a o necesita corriente?',
                'a': 'Todo nuestro mobiliario LED viene con bater&iacute;a recargable interna de 8 a 10 horas de autonom&iacute;a. No requiere cables ni toma corriente durante el evento, lo que te permite ubicar las piezas en cualquier punto del espacio (centro de pista, jardines, terrazas, etc.).',
            },
            {
                'q': '&iquest;Cu&aacute;nto dura la carga de las bater&iacute;as?',
                'a': 'Cada pieza LED tiene entre 8 y 10 horas de autonom&iacute;a con una sola carga, suficiente para cualquier evento est&aacute;ndar. Las entregamos cargadas al 100%. Para eventos extendidos podemos coordinar cargas intermedias o intercambio de unidades.',
            },
            {
                'q': '&iquest;Se pueden cambiar los colores durante el evento?',
                'a': 'S&iacute;. Cada pieza incluye control remoto con 16 colores fijos, modos de fade gradual y cambio autom&aacute;tico sincronizado. Te dejamos los controles para que ajustes el ambiente seg&uacute;n el momento del evento (m&aacute;s sutil para c&oacute;ctel, m&aacute;s din&aacute;mico para fiesta).',
            },
            {
                'q': '&iquest;Es seguro y resistente para uso al aire libre?',
                'a': 'S&iacute;. El mobiliario LED tiene acabado resistente a salpicaduras y polvo (apto IP54 en su mayor&iacute;a). Funciona perfectamente en terrazas, jardines y eventos al aire libre. Para zonas con riesgo de lluvia fuerte recomendamos cubierta tipo carpa.',
            },
            {
                'q': '&iquest;Qu&eacute; tipos de mobiliario LED tienen disponibles?',
                'a': 'Contamos con mesas iluminadas (centrales, de cubo y altas), barras LED para c&oacute;cteles, sillas y poltronas LED, puff iluminados y sets completos de sala LED. Tambi&eacute;n combinamos con pista de baile LED Infinity 3D para eventos completos.',
            },
            {
                'q': '&iquest;Cu&aacute;nto cuesta alquilar mobiliario LED en Bogot&aacute;?',
                'a': 'El precio depende de la cantidad de piezas, el tipo (mesa, barra, silla, sala completa), la duraci&oacute;n y la ubicaci&oacute;n del evento. Cotizamos por WhatsApp en minutos con propuesta clara y precio cerrado. Escr&iacute;benos al 301 322 8490 con los detalles de tu evento.',
            },
        ],
        # Indices de REVIEWS a mostrar (Stefania, Jhon, AnFerTM — los mas relevantes para LED)
        'testimonios_indices': [0, 2, 4],
    },
    '13_CALEFACTORES': {
        'hero_subtitle': 'Calefactores de ambiente pir&aacute;mide y hongo para eventos al aire libre en Bogot&aacute;. Mantienen el calor en terrazas, jardines y carpas cuando baja la temperatura.',
        'hero_specs': [
            ('M12 2c1.5 2 1.5 4 0 6s-1.5 4 0 6 M8 4c1 1.5 1 3 0 4.5s-1 3 0 4.5 M16 4c1 1.5 1 3 0 4.5s-1 3 0 4.5 M5 14h14v7H5z', 'Hongo y pir&aacute;mide'),
            ('M3 7h4 M21 7h-4 M3 12h4 M21 12h-4 M3 17h4 M21 17h-4 M12 4v16', 'Calienta hasta 25 m&sup2;'),
            ('M9 5h6 M10 3v2 M14 3v2 M9 7h6v12a3 3 0 0 1-3 3h0a3 3 0 0 1-3-3z', '4-6 horas autonom&iacute;a'),
            ('M9 12l2 2 4-4', 'Seguro y certificado'),
        ],
        'gallery_keywords': ['calefactor', 'calefactores', 'hongo', 'piramide'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Calefactor pir&aacute;mide', 'desc': 'El cl&aacute;sico calefactor pir&aacute;mide con llama visible, est&eacute;tica moderna para eventos al aire libre.',
             'icon': 'M12 2L4 22h16z M12 8v12'},
            {'name': 'Calefactor hongo', 'desc': 'Calefactor tipo hongo o paraguas que calienta &aacute;reas amplias de manera uniforme.',
             'icon': 'M4 8h16 M12 8v14 M3 4h18l-3 4H6z'},
            {'name': 'Calefactores de mesa', 'desc': 'Calefactores compactos para zonas de c&oacute;ctel y mesas de banquete.',
             'icon': 'M3 7h18 M5 7v13h14V7 M9 12h6'},
            {'name': 'Soporte t&eacute;cnico durante el evento', 'desc': 'Cambio de cilindros y monitoreo si tu evento dura m&aacute;s de 4-6 horas.',
             'icon': 'M9 12l2 2 4-4 M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z'},
        ],
        'ventajas_rich': [
            {'title': 'Indispensable en Bogot&aacute;',
             'desc': 'Por las temperaturas nocturnas y de altura, casi todos los eventos al aire libre en Bogot&aacute; necesitan calefacci&oacute;n para que los invitados est&eacute;n c&oacute;modos toda la noche.'},
            {'title': 'Calienta &aacute;reas amplias',
             'desc': 'Un calefactor pir&aacute;mide o hongo calienta efectivamente un radio de 3-4 metros (~25 m&sup2;). Para eventos m&aacute;s grandes distribuimos varias unidades estrat&eacute;gicamente.'},
            {'title': 'Seguro y certificado',
             'desc': 'Cilindros con v&aacute;lvula de seguridad, estructura estable anti-vuelco, llama visible controlada. Aptos para uso pr&oacute;ximo a invitados.'},
            {'title': 'Servicio incluido',
             'desc': 'Transporte, instalaci&oacute;n, cilindros con gas, encendido al inicio del evento y recogida posterior. Incluido en el precio del alquiler.'},
        ],
        'faq': [
            {'q': '&iquest;Cu&aacute;ntos calefactores necesito para mi evento?',
             'a': 'Como regla general: 1 calefactor por cada 20-25m&sup2; (radio de 3-4m alrededor). Para una boda de 100 personas en jard&iacute;n cubierto recomendamos 4-6 calefactores distribuidos en zonas estrat&eacute;gicas (c&oacute;ctel, pista, comedor). Te asesoramos por WhatsApp.'},
            {'q': '&iquest;Cu&aacute;nto tiempo dura el cilindro?',
             'a': 'Un cilindro est&aacute;ndar dura 4-6 horas dependiendo de la intensidad. Para eventos m&aacute;s largos (boda completa de 6-8 horas) coordinamos cambios de cilindro durante el evento sin costo adicional, o entregamos cilindros de respaldo.'},
            {'q': '&iquest;Son seguros con ni&ntilde;os e invitados cerca?',
             'a': 'S&iacute;. La llama est&aacute; aislada en estructura de vidrio templado o malla met&aacute;lica. La base es estable y pesada para evitar vuelcos accidentales. Aun as&iacute;, recomendamos mantener al menos 1 metro de distancia entre el calefactor y los invitados.'},
            {'q': '&iquest;Funcionan con lluvia o vientos fuertes?',
             'a': 'Resisten llovizna y vientos moderados (la llama est&aacute; protegida). Para lluvia fuerte o vientos huracanados recomendamos apagarlos por seguridad. Si tu evento es al aire libre con riesgo de mal clima, coordinamos cubierta tipo carpa.'},
            {'q': '&iquest;Hay opciones el&eacute;ctricas en lugar de gas?',
             'a': 'Manejamos principalmente calefactores a gas porque calientan m&aacute;s &aacute;rea y no dependen de tomas de corriente al aire libre. Para eventos interiores podemos coordinar opciones el&eacute;ctricas a pedido. Consulta por WhatsApp.'},
            {'q': '&iquest;Cu&aacute;nto cuesta alquilar calefactores en Bogot&aacute;?',
             'a': 'El precio depende del tipo (pir&aacute;mide vs hongo), cantidad, duraci&oacute;n y ubicaci&oacute;n del evento. Incluye cilindros, instalaci&oacute;n y soporte t&eacute;cnico. Cotizamos por WhatsApp en minutos. Escr&iacute;benos al 301 322 8490.'},
        ],
        'testimonios_indices': [0, 1, 2],
    },
    '14_SEPARADORES_FILA': {
        'hero_subtitle': 'Postes separadores con cinta retr&aacute;ctil o cord&oacute;n para organizar entradas, accesos VIP, &aacute;reas restringidas y flujos de invitados en eventos sociales y empresariales.',
        'hero_specs': [
            ('M4 4v16 M10 4v16 M16 4v16 M22 4v16', 'Cinta retr&aacute;ctil 2m'),
            ('M12 2v4 M4.93 4.93l2.83 2.83 M16.24 16.24l2.83 2.83 M2 12h4 M18 12h4', 'Dorado, negro, rojo'),
            ('M9 12l2 2 4-4 M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z', 'Base pesada estable'),
            ('M3 7h18 M5 7v13h14V7', 'Montaje incluido'),
        ],
        'gallery_keywords': ['separador', 'separadores', 'organizador', 'fila'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Postes con cinta retr&aacute;ctil', 'desc': 'El modelo m&aacute;s vers&aacute;til: cinta de 2 metros que se ajusta a cualquier espacio entre postes.',
             'icon': 'M4 4v16 M10 4v16 M16 4v16'},
            {'name': 'Postes con cord&oacute;n', 'desc': 'Modelo cl&aacute;sico tipo cordon de hotel/teatro con cuerda forrada en terciopelo rojo o negro.',
             'icon': 'M5 4v16 M19 4v16 M5 10c5 0 9 0 14 0'},
            {'name': 'Postes dorados premium', 'desc': 'Postes con acabado dorado mate o brillante, perfectos para eventos elegantes y red carpet.',
             'icon': 'M12 2v20 M9 6h6 M9 18h6'},
            {'name': 'Base ancha estable', 'desc': 'Base pesada anti-vuelco que evita ca&iacute;das incluso en eventos masivos con paso de muchas personas.',
             'icon': 'M4 18h16 M8 18v-8 M16 18v-8 M10 10h4l-2-6z'},
        ],
        'ventajas_rich': [
            {'title': 'Organizaci&oacute;n profesional',
             'desc': 'Marca claramente los accesos: entrada VIP, zona prensa, taquilla, fila de espera, &aacute;reas restringidas. Da imagen de evento bien organizado.'},
            {'title': 'F&aacute;cil instalaci&oacute;n',
             'desc': 'Los postes se montan en segundos y la cinta retr&aacute;ctil se ajusta autom&aacute;ticamente. F&aacute;cil mover si necesitas ajustar el layout durante el evento.'},
            {'title': 'Variedad de acabados',
             'desc': 'Negro mate (corporativo), dorado (red carpet), rojo cl&aacute;sico (premiere), plateado (moderno). Combinables seg&uacute;n el c&oacute;digo del evento.'},
            {'title': 'Base pesada y estable',
             'desc': 'Base anti-vuelco que aguanta paso intensivo de personas. No se mueve con golpes accidentales y mantiene la l&iacute;nea recta durante todo el evento.'},
        ],
        'faq': [
            {'q': '&iquest;Para qu&eacute; eventos sirven los separadores?',
             'a': 'Los separadores son indispensables para: filas de entrada en eventos masivos, accesos VIP en c&oacute;cteles y galas, control de aforo en exposiciones, &aacute;reas restringidas tipo backstage, red carpets, taquillas, separaci&oacute;n entre p&uacute;blico y artistas en conciertos.'},
            {'q': '&iquest;Cu&aacute;l es la distancia ideal entre postes?',
             'a': 'La cinta retr&aacute;ctil mide 2 metros m&aacute;ximo. Para filas rectas recomendamos espaciar postes cada 1.5-2m. Para esquinas o l&iacute;neas curvas, postes cada 1m. Te asesoramos seg&uacute;n el dise&ntilde;o de tu evento.'},
            {'q': '&iquest;Qu&eacute; colores de cinta y cord&oacute;n tienen?',
             'a': 'Cinta: negra, roja, dorada y plateada. Cord&oacute;n estilo terciopelo: rojo, negro, dorado. Postes: negros, dorados (mate y brillante), plateados. Combinaciones populares: postes dorados + cinta roja (red carpet), postes negros + cinta negra (corporativo).'},
            {'q': '&iquest;Cu&aacute;ntos separadores necesito para mi evento?',
             'a': 'Depende del aforo y el dise&ntilde;o del flujo. Para 100 invitados t&iacute;picamente 4-8 separadores en accesos clave. Para eventos masivos (300+ personas) recomendamos 12-20 distribuidos. Cu&eacute;ntanos el evento y te asesoramos.'},
            {'q': '&iquest;Hacen montaje del dise&ntilde;o de filas?',
             'a': 'S&iacute;. Llegamos antes del evento, instalamos los postes seg&uacute;n el layout acordado y conectamos las cintas/cordones. Si necesitas ajustes durante el evento, nuestro equipo puede asistir.'},
            {'q': '&iquest;Cu&aacute;nto cuesta alquilar separadores de fila en Bogot&aacute;?',
             'a': 'Depende del modelo (cinta o cord&oacute;n), cantidad y duraci&oacute;n del alquiler. Cotizamos por WhatsApp en minutos con propuesta clara que incluye montaje. Escr&iacute;benos al 301 322 8490 con detalles de tu evento.'},
        ],
        'testimonios_indices': [0, 1, 4],
    },
    '15_BOMBILLOS_VINTAGE': {
        'hero_subtitle': 'Cadenas de bombillos vintage para techos, terrazas, jardines y carpas. La iluminaci&oacute;n c&aacute;lida ideal para bodas, eventos al aire libre y celebraciones nocturnas en Bogot&aacute;.',
        'hero_specs': [
            ('M9 18h6 M10 22h4 M8 13a5 5 0 0 1 4-8 5 5 0 0 1 4 8c-1 1-2 2-2 3v1H10v-1c0-1-1-2-2-3z', 'Luz c&aacute;lida vintage'),
            ('M21 12.79A9 9 0 1 1 11.21 3A7 7 0 0 0 21 12.79z', 'Apto exterior'),
            ('M5 12h14 M12 5v14', 'Variedad de longitudes'),
            ('M3 7h18 M5 7v13h14V7', 'Instalaci&oacute;n incluida'),
        ],
        'gallery_keywords': ['bombillo', 'bombillos', 'vintage'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Cadenas bombillos vintage', 'desc': 'Extensiones de cadena con bombillos tipo Edison c&aacute;lidos para techos y patios.',
             'icon': 'M3 4h18 M6 4v3 M10 4v3 M14 4v3 M18 4v3 M9 18h6 M10 22h4 M8 13a5 5 0 0 1 4-8 5 5 0 0 1 4 8'},
            {'name': 'Bombillos individuales', 'desc': 'Bombillos Edison sueltos para complementar montajes existentes o decoraciones especiales.',
             'icon': 'M9 18h6 M10 22h4 M8 13a5 5 0 0 1 4-8 5 5 0 0 1 4 8c-1 1-2 2-2 3v1H10v-1c0-1-1-2-2-3z'},
            {'name': 'Instalaciones tipo Pinterest', 'desc': 'Dise&ntilde;os colgantes en zigzag, cascada o cielo estrellado para terrazas y jardines.',
             'icon': 'M3 12s4-8 9-8 9 8 9 8-4 8-9 8-9-8-9-8z'},
            {'name': 'Cadenas para fincas', 'desc': 'Extensiones largas para iluminar &aacute;reas amplias en bodas y eventos campestres.',
             'icon': 'M3 8c4 4 8-4 12 0s8-4 12 0 M3 16c4 4 8-4 12 0s8-4 12 0'},
        ],
        'ventajas_rich': [
            {'title': 'Atm&oacute;sfera m&aacute;gica instant&aacute;nea',
             'desc': 'La luz c&aacute;lida ambar de los bombillos vintage transforma cualquier espacio en algo m&aacute;gico. El detalle que hace que las fotos de tu evento se vean profesionales.'},
            {'title': 'Para techos, jardines y carpas',
             'desc': 'Funcionan perfecto colgados de techos, &aacute;rboles, vigas, carpas o tendidos entre postes. Versatilidad para cualquier espacio interior o exterior.'},
            {'title': 'Resistente a la intemperie',
             'desc': 'Bombillos y cableado tratados para uso exterior (IP44). Resisten salpicaduras y humedad ambiente sin problemas.'},
            {'title': 'Instalaci&oacute;n profesional',
             'desc': 'Nosotros instalamos las cadenas en el lugar y dise&ntilde;o que acuerdes. Llegamos antes del evento, montamos, conectamos a corriente y dejamos todo listo.'},
        ],
        'faq': [
            {'q': '&iquest;Cu&aacute;ntos metros de cadena necesito?',
             'a': 'Para una boda al aire libre en jard&iacute;n de 200m&sup2; recomendamos 30-50 metros de cadena distribuidos. Para una terraza de 50m&sup2;, 15-20 metros suficientes. Cu&eacute;ntanos las dimensiones de tu espacio y dise&ntilde;amos el montaje ideal.'},
            {'q': '&iquest;Los bombillos vienen prendidos toda la noche?',
             'a': 'S&iacute;. Una vez instalados y conectados a corriente, los bombillos quedan encendidos durante todo el evento. Los Edison tienen vida &uacute;til de 1000+ horas y no se calientan al tacto despu&eacute;s de algunos segundos.'},
            {'q': '&iquest;Necesito tomas de corriente especiales?',
             'a': 'No, funcionan con tomas est&aacute;ndar de 110V. En la instalaci&oacute;n verificamos que haya toma cerca o coordinamos con tu coordinador de evento. Para eventos en fincas sin energ&iacute;a estable manejamos opciones con planta el&eacute;ctrica.'},
            {'q': '&iquest;Resisten lluvia?',
             'a': 'Los bombillos y cableado tienen tratamiento IP44 contra salpicaduras y lluvia moderada. Para lluvia fuerte recomendamos protecci&oacute;n tipo carpa o cubierta. Si hay riesgo de tormenta severa, podemos desconectar temporalmente por seguridad.'},
            {'q': '&iquest;Combinan con otros estilos de mobiliario?',
             'a': 'Los bombillos vintage son el comod&iacute;n perfecto: combinan con mobiliario r&uacute;stico (la combinaci&oacute;n cl&aacute;sica de bodas), con mesas industriales (estilo loft), con sillas tiffany doradas (galas), con mobiliario picnic (eventos al aire libre).'},
            {'q': '&iquest;Cu&aacute;nto cuesta alquilar bombillos vintage en Bogot&aacute;?',
             'a': 'El precio depende de los metros de cadena, la instalaci&oacute;n (altura, dise&ntilde;o) y ubicaci&oacute;n del evento. Incluye instalaci&oacute;n, conexi&oacute;n y desmontaje. Cotizamos por WhatsApp en minutos al 301 322 8490.'},
        ],
        'testimonios_indices': [0, 1, 2],
    },
    '16_PISTA_BAILE': {
        'hero_subtitle': 'Pista de baile LED Infinity 3D con efecto t&uacute;nel infinito multicolor. La estrella visual de cualquier fiesta nocturna, boda con baile o evento corporativo en Bogot&aacute;.',
        'hero_specs': [
            ('M3 12c0-5 4-9 9-9s9 4 9 9-4 9-9 9-9-4-9-9z M12 3v9l6 3', 'Efecto t&uacute;nel 3D infinito'),
            ('M12 2v4 M4.93 4.93l2.83 2.83 M16.24 16.24l2.83 2.83 M2 12h4 M18 12h4', '16 colores RGB'),
            ('M9 18V5l12-2v13', 'Sincroniza con la m&uacute;sica'),
            ('M3 7h18 M5 7v13h14V7', 'Montaje incluido'),
        ],
        'gallery_keywords': ['pista', 'baile'],
        'use_showcase': True,
        'productos_rich': [
            {'name': 'Pista LED Infinity 3D', 'desc': 'El modelo estrella con efecto t&uacute;nel infinito multicolor que cambia al ritmo de la m&uacute;sica.',
             'icon': 'M3 12c0-5 4-9 9-9s9 4 9 9-4 9-9 9-9-4-9-9z M9 12c0-2 1-3 3-3s3 1 3 3-1 3-3 3-3-1-3-3z'},
            {'name': 'Pistas modulares 2x2', 'desc': 'Pistas en m&oacute;dulos cuadrados de 60cm que se ensamblan para crear el tama&ntilde;o deseado.',
             'icon': 'M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M13 13h7v7h-7z'},
            {'name': 'Pistas grandes para eventos masivos', 'desc': 'Configuraciones de 4x4 metros (16m&sup2;) hasta 6x6 metros (36m&sup2;) para fiestas grandes.',
             'icon': 'M3 3h18v18H3z M3 9h18 M3 15h18 M9 3v18 M15 3v18'},
            {'name': 'Sistema sincronizado con DJ', 'desc': 'Conexi&oacute;n via mando o sync con consola del DJ. Cambios de color autom&aacute;ticos al beat.',
             'icon': 'M9 18V5l12-2v13 M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M18 19a3 3 0 1 0 0-6 3 3 0 0 0 0 6z'},
        ],
        'ventajas_rich': [
            {'title': 'Efecto visual de impacto',
             'desc': 'El efecto t&uacute;nel infinito multicolor crea fotos y videos espectaculares. La pista se vuelve el protagonista visual del evento, tus invitados no podr&aacute;n parar de bailar.'},
            {'title': '16 colores y modos',
             'desc': 'M&uacute;ltiples colores RGB con cambios autom&aacute;ticos, modos fade, modos strobe sincronizados con la m&uacute;sica. Control remoto incluido.'},
            {'title': 'Sincronizable con DJ',
             'desc': 'Conectable a la consola del DJ para que los cambios de color coincidan con los beats. Tambi&eacute;n funciona en modo aut&oacute;nomo con cambios al sonido ambiente.'},
            {'title': 'Servicio t&eacute;cnico completo',
             'desc': 'Montaje, instalaci&oacute;n el&eacute;ctrica, pruebas pre-evento, asistencia t&eacute;cnica durante el evento si lo necesitas, y desmontaje. Tu solo disfrutas.'},
        ],
        'faq': [
            {'q': '&iquest;Qu&eacute; es la pista LED Infinity 3D?',
             'a': 'Es una pista de baile cuadrada con un efecto &oacute;ptico de t&uacute;nel infinito multicolor que cambia al ritmo de la m&uacute;sica. Cada m&oacute;dulo tiene cientos de luces LED que se reflejan creando la ilusi&oacute;n de profundidad infinita. Es el modelo m&aacute;s espectacular del mercado.'},
            {'q': '&iquest;Qu&eacute; tama&ntilde;os de pista manejan?',
             'a': 'Manejamos m&oacute;dulos de 60x60cm que se ensamblan para cualquier dimensi&oacute;n. Los tama&ntilde;os m&aacute;s pedidos: 2x2 metros (4m&sup2;) para fiestas peque&ntilde;as, 3x3 metros (9m&sup2;) para 50-100 invitados, 4x4 metros (16m&sup2;) para 100-200 invitados, 6x6 metros (36m&sup2;) para eventos masivos.'},
            {'q': '&iquest;Cu&aacute;l es el espacio recomendado seg&uacute;n los invitados?',
             'a': 'Calculamos 0.4 m&sup2; por persona bailando simult&aacute;neamente, asumiendo que el 30-50% de los invitados estar&aacute; en la pista en el momento pico. Para 100 invitados: 12-20 m&sup2; (3x4 a 4x5m). Te asesoramos en la cotizaci&oacute;n.'},
            {'q': '&iquest;Necesita instalaci&oacute;n el&eacute;ctrica especial?',
             'a': 'Funciona con tomas est&aacute;ndar de 110V. Para pistas grandes (16m&sup2;+) necesitamos 2-3 tomas separadas para distribuir la carga. En la inspecci&oacute;n previa verificamos el suministro el&eacute;ctrico del lugar y coordinamos si necesitas planta auxiliar.'},
            {'q': '&iquest;Se puede usar al aire libre?',
             'a': 'S&iacute;, pero recomendamos cubierta tipo carpa porque aunque los m&oacute;dulos son resistentes a la humedad ambiente, lluvia directa puede da&ntilde;ar el sistema el&eacute;ctrico. Para eventos al aire libre confirmamos que haya cubierta y suelo nivelado.'},
            {'q': '&iquest;Cu&aacute;nto cuesta alquilar la pista LED en Bogot&aacute;?',
             'a': 'El precio depende del tama&ntilde;o de pista (m&sup2;), duraci&oacute;n del evento y ubicaci&oacute;n. Incluye transporte, montaje, instalaci&oacute;n el&eacute;ctrica, control remoto, asistencia t&eacute;cnica durante el evento y desmontaje. Cotizamos por WhatsApp al 301 322 8490.'},
        ],
        'testimonios_indices': [0, 2, 4],
    },
}

def render_productos_rich(productos):
    """Renderiza productos como cards con iconos SVG (cuando hay datos enriquecidos)."""
    cards = []
    for p in productos:
        icon_paths = ''.join(f'<path d="{seg.strip()}"/>' for seg in p['icon'].split('M') if seg.strip()).replace('<path d="', '<path d="M')
        cards.append(f'''      <div class="producto-card reveal">
        <svg class="producto-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{icon_paths}</svg>
        <div class="producto-name">{p['name']}</div>
        <div class="producto-desc">{p['desc']}</div>
      </div>''')
    return f'''<section class="productos-section reveal">
  <div class="productos-inner">
    <span class="label">Productos disponibles</span>
    <div class="productos-grid">
{chr(10).join(cards)}
    </div>
  </div>
</section>'''

def render_ventajas_rich(title, items, tag='h2'):
    """Renderiza ventajas con icono check + titulo + descripcion rica (en lugar de bullets simples)."""
    lis = []
    for item in items:
        lis.append(f'''      <div class="ventaja-rich reveal">
        <div class="ventaja-rich-check" aria-hidden="true">&#10003;</div>
        <div class="ventaja-rich-body">
          <div class="ventaja-rich-title">{item['title']}</div>
          <div class="ventaja-rich-desc">{item['desc']}</div>
        </div>
      </div>''')
    return f'''<section class="ventajas ventajas-rich reveal">
  <div class="ventajas-inner">
    <{tag}>{escape(title)}</{tag}>
    <div class="ventajas-rich-grid">
{chr(10).join(lis)}
    </div>
  </div>
</section>'''

def render_faq_subpage(faqs, eyebrow='Preguntas frecuentes', title='Lo que m&aacute;s nos preguntan'):
    """FAQ section reusable para subpaginas con preguntas especificas de la categoria."""
    items = []
    for f in faqs:
        items.append(f'''      <details class="faq-item reveal">
        <summary>
          <span class="faq-q">{f['q']}</span>
          <svg class="faq-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
        </summary>
        <div class="faq-a">{f['a']}</div>
      </details>''')
    return f'''<section class="faq-section" id="faq" aria-labelledby="faq-sub-title">
  <div class="faq-inner">
    <div class="faq-head reveal">
      <span class="label">{eyebrow}</span>
      <h2 id="faq-sub-title">{title}</h2>
      <p class="faq-sub">&iquest;Algo m&aacute;s? Escr&iacute;benos por WhatsApp y te respondemos en minutos.</p>
    </div>
    <div class="faq-list">
{chr(10).join(items)}
    </div>
  </div>
</section>'''

def render_showcase_subpage(gallery_images_filtered, h3_caption='Explora algunos de nuestros montajes:'):
    """Showcase interactivo (mismo formato del home): 1 foto al frente +
    fondo blureado de la misma + flechas + counter + caption."""
    if not gallery_images_filtered:
        return ''
    imgs_html = []
    for i, img in enumerate(gallery_images_filtered):
        cls = 'showcase-img is-active' if i == 0 else 'showcase-img'
        imgs_html.append(f'      <img class="{cls}" src="../assets/img/{escape(img["file"])}" alt="{escape(img["alt"])}" data-idx="{i}" loading="lazy">')
    first_src = f'../assets/img/{escape(gallery_images_filtered[0]["file"])}'
    total = len(gallery_images_filtered)
    first_alt = escape(gallery_images_filtered[0]['alt']) if gallery_images_filtered else ''
    return f'''<section class="showcase-section" id="galeria">
  <div class="showcase-bg" id="showcaseBg" style="background-image:url('{first_src}')" aria-hidden="true"></div>
  <div class="showcase-bg-overlay" aria-hidden="true"></div>

  <div class="showcase-head">
    <span class="label on-dark">Galer&iacute;a de montajes</span>
    <h3 class="showcase-h3">{escape(h3_caption)}</h3>
  </div>

  <div class="showcase" id="showcase">
    <button class="showcase-arrow showcase-prev" id="showcasePrev" type="button" aria-label="Foto anterior">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"></path></svg>
    </button>
    <div class="showcase-frame">
      <div class="showcase-imgs" id="showcaseImgs">
{chr(10).join(imgs_html)}
      </div>
    </div>
    <button class="showcase-arrow showcase-next" id="showcaseNext" type="button" aria-label="Foto siguiente">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"></path></svg>
    </button>
  </div>
  <div class="showcase-footer">
    <div class="showcase-caption" id="showcaseCaption">{first_alt}</div>
    <div class="showcase-counter">
      <span class="showcase-current" id="showcaseCurrent">01</span>
      <span class="showcase-divider">/</span>
      <span class="showcase-total">{total:02d}</span>
    </div>
  </div>
</section>'''

def render_specs_pills(specs):
    """Pills de specs rapidos en el hero (icono + texto). B2B-friendly."""
    if not specs:
        return ''
    items = []
    for icon_path, text in specs:
        # icon_path puede tener multiples segmentos separados por espacios + M
        paths = ''.join(f'<path d="{seg.strip()}"/>' for seg in icon_path.split('M') if seg.strip()).replace('<path d="', '<path d="M')
        items.append(f'''    <span class="hero-spec">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths}</svg>
      {text}
    </span>''')
    return f'''<div class="hero-specs anim anim-3" aria-label="Caracteristicas">
{chr(10).join(items)}
  </div>'''

def render_hidden_seo_imgs(images_filtered_out):
    """Mantiene en el DOM las <img> que no van al showcase (preservacion SEO).
    Google las indexa, usuarios no las ven."""
    if not images_filtered_out:
        return ''
    imgs = []
    for img in images_filtered_out:
        if 'ASEM-mobiliario' in img['file']:
            continue  # logo no necesita estar duplicado aqui (ya esta en footer)
        imgs.append(f'  <img src="../assets/img/{escape(img["file"])}" alt="{escape(img["alt"])}" loading="lazy">')
    if not imgs:
        return ''
    return f'<div class="seo-imgs" aria-hidden="true">\n{chr(10).join(imgs)}\n</div>'

def render_testimonios_subpage(review_indices):
    """Testimonios reducidos (3 cards) para subpaginas. Usa indices de REVIEWS."""
    items = []
    for idx in review_indices:
        if idx >= len(REVIEWS): continue
        r = REVIEWS[idx]
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
    return f'''<section class="testimonios-section testimonios-section-sub" aria-labelledby="testi-sub">
  <div class="testimonios-inner">
    <div class="testimonios-head reveal">
      <span class="label">Rese&ntilde;as</span>
      <h2 id="testi-sub">Quienes ya nos eligieron</h2>
      <a class="testimonios-rating" href="https://www.google.com/search?q=ASEM+alquiler+salas+y+mobiliario+bogota" target="_blank" rel="noopener">
        <span class="testimonios-rating-num">4.7</span>
        <span class="testimonios-rating-stars" aria-hidden="true">★★★★★</span>
        <span class="testimonios-rating-meta">en Google &middot; 90 rese&ntilde;as</span>
      </a>
    </div>
    <div class="testimonios-grid testimonios-grid-3">
{chr(10).join(items)}
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
    custom = SUBPAGE_CUSTOM.get(key, {})  # datos enriquecidos opcionales

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
                     jsonld=schema_jsonld_subpage(page, custom))
    nav = navbar_html(depth)

    # Hero interior — usa hero_subtitle custom si existe, sino la meta description
    hero_sub = custom.get('hero_subtitle') or escape(desc)
    specs_html = render_specs_pills(custom.get('hero_specs'))
    # Banner background opcional (foto detras del texto)
    banner = custom.get('hero_banner')
    hero_class = 'hero-inner has-banner' if banner else 'hero-inner'
    banner_html = ''
    if banner:
        banner_html = f'''  <div class="hero-banner-bg" style="background-image:url('../assets/img/{escape(banner)}')" aria-hidden="true"></div>
  <div class="hero-banner-overlay" aria-hidden="true"></div>'''
    hero = f'''<section class="{hero_class}">
{banner_html}
  <div class="breadcrumbs"><a href="../">Inicio</a> &nbsp;&middot;&nbsp; {escape(h1.replace("Alquiler de ", "").replace(" en Bogotá para Eventos", ""))}</div>
  <h1>{escape(h1)}</h1>
  <p class="hero-sub">{hero_sub}</p>
  {specs_html}
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
    # Productos: usa el bloque rich con icons si hay datos enriquecidos,
    # sino la linea simple del Excel
    productos_rich_html = ''
    productos_block = ''
    if custom.get('productos_rich'):
        productos_rich_html = render_productos_rich(custom['productos_rich'])
    elif content.get('productos'):
        productos_block = f'    <p><strong>Productos:</strong> {" &middot; ".join(escape(p) for p in content["productos"])}</p>'
    intro_html = ''
    if intro_paragraphs or productos_block:
        intro_html = f'''<section class="intro reveal">
  <div class="intro-inner">
{intro_paragraphs}
{productos_block}
  </div>
</section>'''

    # Galeria
    gallery_h3 = h3_explora or 'Explora algunos de nuestros montajes:'
    # Imagenes sin el logo de footer
    all_imgs = [img for img in images if 'ASEM-mobiliario-para-eventos-en-bogota' not in img['file']]

    # Si la subpagina define keywords de galeria, filtrar solo las relacionadas (resto va hidden SEO)
    gallery_kws = custom.get('gallery_keywords')
    if gallery_kws:
        def is_relevant(img):
            fn = img['file'].lower()
            alt = (img.get('alt') or '').lower()
            return any(kw in fn or kw in alt for kw in gallery_kws)
        gallery_imgs = [img for img in all_imgs if is_relevant(img)]
        hidden_imgs = [img for img in all_imgs if not is_relevant(img)]
    else:
        gallery_imgs = all_imgs
        hidden_imgs = []

    # Showcase (cinematografico) o masonry tradicional segun config
    if custom.get('use_showcase'):
        gallery_html = render_showcase_subpage(gallery_imgs, h3_caption=gallery_h3)
    else:
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

    # SEO hidden imgs: filtradas fuera del showcase pero presentes en DOM
    seo_hidden_html = render_hidden_seo_imgs(hidden_imgs)

    # Ventajas — usa h2 si Excel lo lista en H2, h3 si lo lista en H3, span si no esta
    ventajas_title = h2_ventajas or h3_ventajas
    ventajas_tag = 'h2' if h2_ventajas else ('h3' if h3_ventajas else None)
    ventajas_html = ''
    # Si hay datos enriquecidos en custom, usa el grid rich (titulo + descripcion por item)
    if ventajas_title and custom.get('ventajas_rich'):
        ventajas_html = render_ventajas_rich(ventajas_title, custom['ventajas_rich'], tag=ventajas_tag)
    elif ventajas_title and content.get('ventajas'):
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

    # FAQ y Testimonios opcionales (cuando hay datos custom para esta subpagina)
    faq_html_sub = render_faq_subpage(custom['faq']) if custom.get('faq') else ''
    testimonios_html_sub = render_testimonios_subpage(custom['testimonios_indices']) if custom.get('testimonios_indices') else ''

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
{productos_rich_html}
{gallery_html}
{ventajas_html}
{testimonios_html_sub}
{cta_html}
{faq_html_sub}
{referencias_html}
{cta_final_block()}
{seo_hidden_html}
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

<section class="instagram-strip">
  <span class="label">@alquilersalasparaeventos</span>
  <h2>{escape(h2_ig)}</h2>
  <h3>{escape(h3_siguenos)}</h3>
  <a class="ig-link" href="https://instagram.com/alquilersalasparaeventos" target="_blank" rel="noopener">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"></rect><circle cx="12" cy="12" r="4"></circle><circle cx="17.5" cy="6.5" r="0.6" fill="currentColor"></circle></svg>
    Ver montajes recientes
  </a>
</section>

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
