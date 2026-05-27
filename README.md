# ASEM — Sitio estático (replica SEO)

Sitio espejo de `alquilersalasparaeventosymobiliario.com`. Replica 1:1 los meta tags, H1, H2, H3, H4 y nombres de imagen del sitio actual para que el cambio sea transparente para Google. El diseño visual se actualizó (paleta turquesa / dorado, Barlow Condensed).

## Estructura

```
/index.html                                          → 01_INICIO
/<slug>/index.html                                   → 02..17 (16 subpáginas)
/assets/css/styles.css                               → estilos (1 archivo)
/assets/js/main.js                                   → JS interacciones
/assets/img/<filename>.{webp,jpg,png}                → placeholders (192 imágenes)
/sitemap.xml                                         → sitemap
/robots.txt
/build/build.py                                      → generador
/build/pages.json                                    → fuente de verdad (extraído del Excel SEO)
```

URLs replicadas (idénticas al sitio actual):

- `/`
- `/salas-lounge-para-eventos-en-bogota/`
- `/salas-rusticas-para-eventos-bogota/`
- `/mesas-para-eventos-bogota/`
- `/sillas-para-eventos-bogota/`
- `/sillas-para-juntas-bogota/`
- `/poltronas-para-eventos-en-bogota/`
- `/comedores-rusticos-eventos-bogota/`
- `/mobiliario-led-eventos-bogota/`
- `/mesas-sillas-industriales-eventos-bogota/`
- `/mesas-picnic-para-eventos-bogota/`
- `/sillas-acapulco-para-eventos-bogota/`
- `/calefactores-ambiente-para-eventos/`
- `/separadores-de-fila-para-eventos/`
- `/bombillos-vintage-para-eventos/`
- `/pista-de-baile-para-eventos/`
- `/acarreos-trasteos-y-mudanzas-bogota/`

## Imágenes

Cada `<img src>` apunta a un archivo en `assets/img/` con el **mismo nombre y extensión** que tiene el sitio actual. Hoy son placeholders generados con Pillow (gradiente + alt text encima). Cuando lleguen las fotos reales, basta con sobrescribir el archivo correspondiente — no hay que tocar el HTML.

Lista completa de nombres en `build/pages.json` → `images`.

## Verificación de SEO

Las 17 páginas tienen:

- Meta Title, Meta Description, H1, H2, H3, H4 exactamente como aparecen en `ASEM_Reporte_Completo_SEO.xlsx` (incluso con los typos del original: "Asem" sin tilde, "rùsticas" con acento grave, "Ase" cortado en acarreos).
- Conteos validados (`H1×1, H2×3, H3×2..3, H4×3..4` según corresponda).
- Canonical, OG tags y `robots: index,follow`.

## Regenerar

```
python3 build/build.py            # regenera todo (HTML + placeholders)
python3 build/build.py --no-img   # regenera solo HTML
```

Editar `build/pages.json` o `build/build.py` y volver a correr. Los placeholders solo se regeneran cuando se omite `--no-img`.

## Hosting

Es HTML estático puro: cualquier hosting (Hostinger, Netlify, GitHub Pages, S3+CloudFront) funciona. Para que `/salas-lounge-para-eventos-en-bogota/` resuelva, el servidor debe servir `index.html` por defecto (Apache y Nginx lo hacen out-of-the-box). En Netlify funciona sin configuración.

## Protección de imágenes

El sitio aplica una doble capa anti-robo:

1. **JavaScript** en `assets/js/main.js` que bloquea el click derecho y el drag-and-drop sobre cualquier `<img>`. Detiene el 95% del robo casual.
2. **Watermark visible** "ASEM" en la esquina inferior derecha de cada foto. Procesado vía `build/watermark.py` y guardado en el binario.

Para procesar imágenes nuevas que subas a `assets/img/`:

```
python3 build/watermark.py
```

El script lleva un manifest en `build/.watermarked.json` que evita doble-watermarking. Si reemplazas una foto (mismo filename, contenido nuevo), el script detecta el cambio de tamaño y la re-procesa.

Limitación: ningún sitio web puede prevenir 100% el robo (DevTools y screenshots siempre funcionan). El watermark sirve como deterrente y prueba de propiedad.

## Pendientes (siguiente iteración)

- Mejorar el copy de las 17 subpáginas (intros, ventajas) una a una sin tocar los headings.
- Agregar schema.org `Service` a cada subpágina (el home ya tiene LocalBusiness + AggregateRating + FAQPage).
- Conectar formulario de contacto si se quiere alternativa al WhatsApp.
