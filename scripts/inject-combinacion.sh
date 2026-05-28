#!/bin/bash
# Inserta seccion "Combina con" en cada pagina interna
# - 3 cards con cross-link curado
# - Tarjeta amarilla para categorias sin foto real

set -euo pipefail
cd "$(dirname "$0")/.."

# Metadata: slug | display name | hero/photo filename | "real" o "empty"
get_meta() {
  case "$1" in
    salas-lounge-para-eventos-en-bogota)       echo "Salas Lounge|hero-salas-lounge-banner.webp|real" ;;
    salas-rusticas-para-eventos-bogota)        echo "Salas Rusticas|hero-2-mobiliario-rustico.webp|real" ;;
    comedores-rusticos-eventos-bogota)         echo "Comedores Rusticos||empty" ;;
    mesas-para-eventos-bogota)                 echo "Mesas Lounge|hero-mesas-banner.webp|real" ;;
    mesas-picnic-para-eventos-bogota)          echo "Mesas Picnic||empty" ;;
    mesas-sillas-industriales-eventos-bogota)  echo "Mobiliario Industrial|hero-industrial-banner.webp|real" ;;
    sillas-para-eventos-bogota)                echo "Sillas Lounge|sillas-para-fiestas-en-bogota.webp|real" ;;
    sillas-para-juntas-bogota)                 echo "Sillas Interlocutoras|hero-sillas-interlocutoras-banner.webp|real" ;;
    sillas-acapulco-para-eventos-bogota)       echo "Sillas Acapulco|hero-acapulco-banner.webp|real" ;;
    poltronas-para-eventos-en-bogota)          echo "Poltronas Lounge||empty" ;;
    bombillos-vintage-para-eventos)            echo "Bombillos Vintage|hero-bombillos-banner.webp|real" ;;
    pista-de-baile-para-eventos)               echo "Pista de Baile LED|hero-pista-baile-banner.webp|real" ;;
    mobiliario-led-eventos-bogota)             echo "Mobiliario LED|hero-led-banner.webp|real" ;;
    calefactores-ambiente-para-eventos)        echo "Calefactores|hero-calefactores-banner.webp|real" ;;
    separadores-de-fila-para-eventos)          echo "Separadores de Fila|hero-separadores-fila-banner.webp|real" ;;
    acarreos-trasteos-y-mudanzas-bogota)       echo "Acarreos y Mudanzas||empty" ;;
  esac
}

# Cross-link matrix: page slug → 3 related slugs
get_related() {
  case "$1" in
    salas-lounge-para-eventos-en-bogota)       echo "sillas-acapulco-para-eventos-bogota mesas-para-eventos-bogota pista-de-baile-para-eventos" ;;
    salas-rusticas-para-eventos-bogota)        echo "comedores-rusticos-eventos-bogota bombillos-vintage-para-eventos mesas-picnic-para-eventos-bogota" ;;
    comedores-rusticos-eventos-bogota)         echo "salas-rusticas-para-eventos-bogota bombillos-vintage-para-eventos mesas-sillas-industriales-eventos-bogota" ;;
    mesas-para-eventos-bogota)                 echo "salas-lounge-para-eventos-en-bogota sillas-acapulco-para-eventos-bogota poltronas-para-eventos-en-bogota" ;;
    mesas-picnic-para-eventos-bogota)          echo "mesas-sillas-industriales-eventos-bogota bombillos-vintage-para-eventos salas-rusticas-para-eventos-bogota" ;;
    mesas-sillas-industriales-eventos-bogota)  echo "mesas-picnic-para-eventos-bogota comedores-rusticos-eventos-bogota salas-rusticas-para-eventos-bogota" ;;
    sillas-para-eventos-bogota)                echo "salas-lounge-para-eventos-en-bogota mesas-para-eventos-bogota poltronas-para-eventos-en-bogota" ;;
    sillas-para-juntas-bogota)                 echo "salas-lounge-para-eventos-en-bogota mesas-para-eventos-bogota separadores-de-fila-para-eventos" ;;
    sillas-acapulco-para-eventos-bogota)       echo "salas-lounge-para-eventos-en-bogota mesas-para-eventos-bogota poltronas-para-eventos-en-bogota" ;;
    poltronas-para-eventos-en-bogota)          echo "salas-lounge-para-eventos-en-bogota sillas-acapulco-para-eventos-bogota mesas-para-eventos-bogota" ;;
    bombillos-vintage-para-eventos)            echo "salas-rusticas-para-eventos-bogota pista-de-baile-para-eventos comedores-rusticos-eventos-bogota" ;;
    pista-de-baile-para-eventos)               echo "mobiliario-led-eventos-bogota salas-lounge-para-eventos-en-bogota bombillos-vintage-para-eventos" ;;
    mobiliario-led-eventos-bogota)             echo "pista-de-baile-para-eventos salas-lounge-para-eventos-en-bogota sillas-acapulco-para-eventos-bogota" ;;
    calefactores-ambiente-para-eventos)        echo "salas-rusticas-para-eventos-bogota bombillos-vintage-para-eventos comedores-rusticos-eventos-bogota" ;;
    separadores-de-fila-para-eventos)          echo "salas-lounge-para-eventos-en-bogota sillas-para-juntas-bogota pista-de-baile-para-eventos" ;;
    acarreos-trasteos-y-mudanzas-bogota)       echo "salas-lounge-para-eventos-en-bogota mesas-para-eventos-bogota calefactores-ambiente-para-eventos" ;;
  esac
}

# Genera HTML para una tarjeta dado un slug, prefijo de ruta
render_card() {
  local slug="$1"
  local prefix="$2"  # "../" para paginas internas, "" para home
  local meta=$(get_meta "$slug")
  local name=$(echo "$meta" | cut -d'|' -f1)
  local photo=$(echo "$meta" | cut -d'|' -f2)
  local kind=$(echo "$meta" | cut -d'|' -f3)
  if [ "$kind" = "real" ]; then
    cat <<HTML
      <a href="${prefix}${slug}/" class="combinacion-card">
        <div class="combinacion-card-photo">
          <img src="${prefix}assets/img/${photo}" alt="${name} ASEM" loading="lazy">
        </div>
        <div class="combinacion-card-body">
          <h4 class="combinacion-card-name">${name}</h4>
          <span class="combinacion-card-arrow" aria-hidden="true">&rarr;</span>
        </div>
      </a>
HTML
  else
    cat <<HTML
      <a href="${prefix}${slug}/" class="combinacion-card combinacion-card-empty">
        <div class="combinacion-card-photo">
          <span class="combinacion-card-photo-mark">ASEM</span>
          <span class="combinacion-card-photo-label">Foto pr&oacute;ximamente</span>
        </div>
        <div class="combinacion-card-body">
          <h4 class="combinacion-card-name">${name}</h4>
          <span class="combinacion-card-arrow" aria-hidden="true">&rarr;</span>
        </div>
      </a>
HTML
  fi
}

# Genera la seccion completa para una pagina interna
render_section_inner() {
  local slug="$1"
  local related=($(get_related "$slug"))
  cat <<HTML
<section class="combinacion reveal">
  <div class="combinacion-inner">
    <div class="combinacion-head">
      <span class="label">Combina con</span>
      <p class="combinacion-title">Otros mobiliarios que complementan perfecto tu evento.</p>
    </div>
    <div class="combinacion-grid">
$(render_card "${related[0]}" "../")
$(render_card "${related[1]}" "../")
$(render_card "${related[2]}" "../")
    </div>
  </div>
</section>
HTML
}

# Inyecta antes de la seccion <div class="seo-imgs"
inject_into_page() {
  local slug="$1"
  local file="${slug}/index.html"
  if [ ! -f "$file" ]; then echo "SKIP: $file no existe"; return; fi
  # Evitar duplicar
  if grep -q "class=\"combinacion " "$file"; then
    echo "SKIP: $slug (ya tiene seccion combinacion)"
    return
  fi
  local section=$(render_section_inner "$slug")
  # Insertar antes de <div class="seo-imgs"
  local tmp=$(mktemp)
  awk -v sec="$section" '
    /<div class="seo-imgs"/ && !done { print sec; done=1 }
    { print }
  ' "$file" > "$tmp" && mv "$tmp" "$file"
  echo "OK: $slug"
}

# Procesa todas las paginas internas
for slug in salas-lounge-para-eventos-en-bogota salas-rusticas-para-eventos-bogota comedores-rusticos-eventos-bogota mesas-para-eventos-bogota mesas-picnic-para-eventos-bogota mesas-sillas-industriales-eventos-bogota sillas-para-eventos-bogota sillas-para-juntas-bogota sillas-acapulco-para-eventos-bogota poltronas-para-eventos-en-bogota bombillos-vintage-para-eventos pista-de-baile-para-eventos mobiliario-led-eventos-bogota calefactores-ambiente-para-eventos separadores-de-fila-para-eventos acarreos-trasteos-y-mudanzas-bogota; do
  inject_into_page "$slug"
done

echo ""
echo "Listo: secciones inyectadas en paginas internas"
