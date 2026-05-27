#!/usr/bin/env python3
"""
ASEM — Watermark de imagenes (proteccion contra robo).

Procesa todas las imagenes en assets/img/ y agrega un watermark sutil
"ASEM" en la esquina inferior derecha. Mantiene formato y filename
originales (sobreescribe).

Uso:
  python3 build/watermark.py            # marca solo las nuevas (no marcadas)
  python3 build/watermark.py --force    # re-marca todas (peligro: doble watermark)

Idempotencia: lleva un manifest en build/.watermarked.json con
(filename, size_bytes). Si una foto cambia de tamano (nueva subida),
se re-marca automaticamente.
"""
import json
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / 'assets' / 'img'
MANIFEST = ROOT / 'build' / '.watermarked.json'

# Estos archivos NO se marcan (logos / brand assets)
SKIP_PATTERNS = [
    'ASEM-mobiliario-para-eventos-en-bogota',  # logo del footer
]

def should_skip(filename: str) -> bool:
    return any(p in filename for p in SKIP_PATTERNS)

def get_font(size: int):
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def add_watermark(image_path: Path) -> bool:
    """Agrega 'ASEM' sutil en esquina inferior derecha. Devuelve True si proceso OK."""
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f'  skip ({e}): {image_path.name}')
        return False

    fmt = img.format or 'PNG'
    W, H = img.size

    # Skip si la imagen es muy pequena (probablemente icono)
    if max(W, H) < 300:
        return False

    # Tamano de fuente: 5% del lado mayor (mas grande para ser visible incluso
    # cuando la imagen se reduce/crop en cards). Minimo absoluto 24px.
    font_size = max(24, int(max(W, H) * 0.05))
    font = get_font(font_size)
    text = 'ASEM'

    # Trabajar en RGBA para soporte de transparencia del overlay
    img_rgba = img.convert('RGBA') if img.mode != 'RGBA' else img
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Calcular bounding box del texto
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Posicion: esquina inferior derecha con margen 3% del lado mayor
    margin = int(max(W, H) * 0.03)
    x = W - text_w - margin
    y = H - text_h - margin - bbox[1]

    # Pad y radio para la "pill" de fondo (mejora legibilidad sobre cualquier color)
    pad_x = max(8, font_size // 4)
    pad_y = max(4, font_size // 8)
    pill_box = [x - pad_x, y - pad_y, x + text_w + pad_x, y + text_h + pad_y]
    # Dibujar pill semi-transparente oscuro
    draw.rounded_rectangle(pill_box, radius=pad_y + 4, fill=(0, 0, 0, 110))

    # Sombra del texto (refuerzo)
    shadow_offset = max(1, font_size // 18)
    draw.text((x + shadow_offset, y + shadow_offset), text,
              font=font, fill=(0, 0, 0, 160))
    # Texto principal blanco mucho mas opaco
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 235))

    watermarked = Image.alpha_composite(img_rgba, overlay)

    # Guardar en formato original
    ext = image_path.suffix.lower()
    if ext in ('.jpg', '.jpeg') or fmt == 'JPEG':
        watermarked.convert('RGB').save(image_path, 'JPEG', quality=88)
    elif ext == '.webp' or fmt == 'WEBP':
        watermarked.save(image_path, 'WEBP', quality=85)
    elif ext == '.png' or fmt == 'PNG':
        watermarked.save(image_path, 'PNG')
    else:
        watermarked.save(image_path)
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
