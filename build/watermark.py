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
    """Watermark 'ASEM' centrado con colores de marca (A blanco, S turquesa,
    E suave, M dorado) semi-transparente. Posicion centrada = mas dificil de
    cropear sin destruir la imagen."""
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f'  skip ({e}): {image_path.name}')
        return False

    fmt = img.format or 'PNG'
    W, H = img.size

    if max(W, H) < 300:
        return False

    # Tamano grande para que sea dificil cropear: 22% del lado mayor
    font_size = max(48, int(max(W, H) * 0.22))
    font = get_font(font_size)

    # Colores de marca de ASEM (mismos que el wordmark del navbar/footer)
    # Alpha 110/255 (~43%) — suficiente para identificar, no para tapar la foto
    ALPHA = 110
    letters = [
        ('A', (255, 255, 255, ALPHA)),   # blanco
        ('S', (64, 176, 203, ALPHA)),    # turquesa
        ('E', (168, 221, 233, ALPHA)),   # suave
        ('M', (240, 192, 96, ALPHA)),    # dorado
    ]

    # Trabajar en RGBA para soporte de transparencia
    img_rgba = img.convert('RGBA') if img.mode != 'RGBA' else img
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Medir cada letra y calcular spacing tipo navbar (letter-spacing generoso)
    letter_metrics = []
    for ch, _ in letters:
        bbox = draw.textbbox((0, 0), ch, font=font)
        letter_metrics.append({'w': bbox[2] - bbox[0], 'h': bbox[3] - bbox[1], 'top': bbox[1]})

    letter_spacing = int(font_size * 0.18)  # gap entre letras
    total_w = sum(m['w'] for m in letter_metrics) + letter_spacing * (len(letters) - 1)
    max_h = max(m['h'] for m in letter_metrics)

    # Centrar horizontal y vertical
    start_x = (W - total_w) / 2
    y = (H - max_h) / 2 - letter_metrics[0]['top']

    # Stroke (outline) negro semi-transparente para que las letras sean
    # legibles sobre cualquier fondo (claro u oscuro)
    stroke_w = max(2, font_size // 60)

    current_x = start_x
    for i, (ch, color) in enumerate(letters):
        try:
            draw.text((current_x, y), ch, font=font, fill=color,
                      stroke_width=stroke_w, stroke_fill=(0, 0, 0, 90))
        except TypeError:
            # Pillow viejos sin stroke_width
            draw.text((current_x, y), ch, font=font, fill=color)
        current_x += letter_metrics[i]['w'] + letter_spacing

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
