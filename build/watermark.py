#!/usr/bin/env python3
"""
ASEM — Watermark de imagenes (proteccion contra robo).

Procesa imagenes en assets/img/ y agrega el isologo de ASEM centrado,
sutil y semi-transparente. El isologo replica exactamente al del navbar
(4 postes + viga + asiento turquesa + techo triangular).

Posicion central = dificil cropear sin destruir la foto.
Sutil + transparente = no afea la imagen.

Excluye automaticamente:
  - hero-*.webp (el hero ya tiene overlay + texto encima)
  - ASEM-mobiliario-* (es el logo de ASEM, no necesita marca)

Uso:
  python3 build/watermark.py            # marca las nuevas
  python3 build/watermark.py --force    # re-marca todas (peligro: doble)
"""
import json
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / 'assets' / 'img'
MANIFEST = ROOT / 'build' / '.watermarked.json'

# NO marcar estos archivos
SKIP_PATTERNS = [
    'ASEM-mobiliario-para-eventos-en-bogota',  # logo del footer
    'hero-1-salas-lounge',
    'hero-2-mobiliario-rustico',
    'hero-3-sillas-acapulco',
    'hero-4-parasoles',
    'evento-mockup',  # mockups reservados
]

def should_skip(filename: str) -> bool:
    return any(p in filename for p in SKIP_PATTERNS)

def draw_isologo(target_img: Image.Image, size: int, alpha_white: int = 130, alpha_turquesa: int = 115):
    """Dibuja el isologo de ASEM en una capa transparente del tamano dado.
    Replica exacto el SVG del navbar (viewBox 72x82).
    Devuelve una Image RGBA lista para pegar."""
    # Calcular dimensiones: viewBox es 72x82
    s = size / 72.0
    iso_w = size
    iso_h = int(82 * s)

    iso = Image.new('RGBA', (iso_w, iso_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(iso)

    WHITE = (255, 255, 255, alpha_white)
    TURQ = (64, 176, 203, alpha_turquesa)

    def rect(x1, y1, x2, y2, fill):
        d.rectangle([(x1 * s, y1 * s), (x2 * s, y2 * s)], fill=fill)

    # Triangulo del techo: points (36,0), (54,22), (18,22)
    d.polygon([(36 * s, 0), (54 * s, 22 * s), (18 * s, 22 * s)], fill=WHITE)
    # Postes verticales internos (cabecera): x=0, y=22, w=9, h=32  |  x=63, y=22, w=9, h=32
    rect(0, 22, 9, 54, WHITE)
    rect(63, 22, 72, 54, WHITE)
    # Asiento turquesa: x=9, y=36, w=54, h=19
    rect(9, 36, 63, 55, TURQ)
    # Viga horizontal superior del asiento: x=0, y=51, w=72, h=9
    rect(0, 51, 72, 60, WHITE)
    # Pies inferiores: x=0, y=58, w=6, h=14  |  x=66, y=58, w=6, h=14
    rect(0, 58, 6, 72, WHITE)
    rect(66, 58, 72, 72, WHITE)

    # Sombra suave detras para legibilidad sobre cualquier fondo (incluso blanco)
    shadow_pad = 28
    shadow = Image.new('RGBA', (iso_w + shadow_pad * 2, iso_h + shadow_pad * 2), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    OFS = shadow_pad
    SHADOW_ALPHA = 95  # suficiente para legibilidad sin sobrecargar al iso transparente

    def s_rect(x1, y1, x2, y2):
        sd.rectangle([(x1 * s + OFS, y1 * s + OFS), (x2 * s + OFS, y2 * s + OFS)], fill=(0, 0, 0, SHADOW_ALPHA))

    sd.polygon([(36 * s + OFS, 0 + OFS), (54 * s + OFS, 22 * s + OFS), (18 * s + OFS, 22 * s + OFS)], fill=(0, 0, 0, SHADOW_ALPHA))
    s_rect(0, 22, 9, 54)
    s_rect(63, 22, 72, 54)
    s_rect(9, 36, 63, 55)
    s_rect(0, 51, 72, 60)
    s_rect(0, 58, 6, 72)
    s_rect(66, 58, 72, 72)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=7))

    # Componer: sombra primero, iso encima
    final = Image.new('RGBA', (iso_w + 30, iso_h + 30), (0, 0, 0, 0))
    final.alpha_composite(shadow)
    final.alpha_composite(iso, dest=(OFS, OFS))
    return final, OFS  # devuelve el padding tambien

def add_watermark(image_path: Path) -> bool:
    """Pega el isologo de ASEM centrado, sutil. Devuelve True si proceso OK."""
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f'  skip ({e}): {image_path.name}')
        return False

    fmt = img.format or 'PNG'
    W, H = img.size

    if max(W, H) < 300:
        return False

    img_rgba = img.convert('RGBA') if img.mode != 'RGBA' else img

    # Tamano del isologo: 9% del lado mayor (cubre suficiente para ser visible
    # sin tapar la foto). El iso tiene aspect 72/82 = ~0.88 (un poco mas alto que ancho)
    iso_size = max(60, int(max(W, H) * 0.09))
    iso_layer, ofs = draw_isologo(img_rgba, iso_size, alpha_white=90, alpha_turquesa=78)
    iso_w, iso_h = iso_layer.size

    # Centrar
    x = (W - iso_w) // 2
    y = (H - iso_h) // 2

    img_rgba.alpha_composite(iso_layer, dest=(x, y))

    # Guardar en formato original
    ext = image_path.suffix.lower()
    if ext in ('.jpg', '.jpeg') or fmt == 'JPEG':
        img_rgba.convert('RGB').save(image_path, 'JPEG', quality=88)
    elif ext == '.webp' or fmt == 'WEBP':
        img_rgba.save(image_path, 'WEBP', quality=85)
    elif ext == '.png' or fmt == 'PNG':
        img_rgba.save(image_path, 'PNG')
    else:
        img_rgba.save(image_path)
    return True

def load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text())
        except Exception:
            return {}
    return {}

def save_manifest(data: dict):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(data, indent=2, sort_keys=True))

def main():
    force = '--force' in sys.argv
    manifest = {} if force else load_manifest()

    if not IMG_DIR.exists():
        print(f'No existe {IMG_DIR}')
        return

    targets = sorted(IMG_DIR.glob('*'))
    targets = [t for t in targets if t.is_file() and t.suffix.lower() in {'.webp', '.jpg', '.jpeg', '.png'}]
    print(f'Total imagenes encontradas: {len(targets)}')

    processed = 0
    skipped_logo = 0
    skipped_already = 0
    skipped_small = 0
    for p in targets:
        if should_skip(p.name):
            skipped_logo += 1
            continue
        size = p.stat().st_size
        record = manifest.get(p.name)
        if record and record.get('size') == size and not force:
            skipped_already += 1
            continue
        if add_watermark(p):
            # Releer tamano post-watermark
            new_size = p.stat().st_size
            manifest[p.name] = {'size': new_size}
            processed += 1
            print(f'  + {p.name}')
        else:
            skipped_small += 1

    save_manifest(manifest)
    print()
    print(f'Procesadas: {processed}')
    print(f'Saltadas (logos): {skipped_logo}')
    print(f'Saltadas (ya watermarked): {skipped_already}')
    print(f'Saltadas (muy chicas): {skipped_small}')

if __name__ == '__main__':
    main()
