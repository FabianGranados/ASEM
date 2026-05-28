#!/bin/bash
# Replicar cross-sell v2 (combina-hero full-bleed, 6 cards) en todas las paginas internas.
# - Quita seccion vieja (.combinacion antes de seo-imgs)
# - Inyecta seccion nueva (.combina-hero despues de showcase-section)
# - Matriz por mood (vintage / moderno / corporativo)
# - 5 reals + 1 yellow placeholder + 1 blue testimonio (placeholder text)

set -euo pipefail
cd "$(dirname "$0")/.."

# Metadata: slug | display name | hero photo filename
get_photo() {
  case "$1" in
    salas-lounge-para-eventos-en-bogota)       echo "hero-salas-lounge-banner.webp" ;;
    salas-rusticas-para-eventos-bogota)        echo "hero-2-mobiliario-rustico.webp" ;;
    comedores-rusticos-eventos-bogota)         echo "hero-comedores-rusticos-banner.webp" ;;
    mesas-para-eventos-bogota)                 echo "hero-mesas-banner.webp" ;;
    mesas-picnic-para-eventos-bogota)          echo "" ;;  # empty
    mesas-sillas-industriales-eventos-bogota)  echo "hero-industrial-banner.webp" ;;
    sillas-para-eventos-bogota)                echo "hero-sillas-lounge-banner.webp" ;;
    sillas-para-juntas-bogota)                 echo "hero-sillas-interlocutoras-banner.webp" ;;
    sillas-acapulco-para-eventos-bogota)       echo "hero-acapulco-banner.webp" ;;
    poltronas-para-eventos-en-bogota)          echo "poltronas-para-eventos-empresariales.webp" ;;
    bombillos-vintage-para-eventos)            echo "hero-bombillos-banner.webp" ;;
    pista-de-baile-para-eventos)               echo "hero-pista-baile-banner.webp" ;;
    mobiliario-led-eventos-bogota)             echo "hero-led-banner.webp" ;;
    calefactores-ambiente-para-eventos)        echo "hero-calefactores-banner.webp" ;;
    separadores-de-fila-para-eventos)          echo "hero-separadores-fila-banner.webp" ;;
    acarreos-trasteos-y-mudanzas-bogota)       echo "" ;;  # empty
  esac
}
get_name() {
  case "$1" in
    salas-lounge-para-eventos-en-bogota)       echo "Salas Lounge" ;;
    salas-rusticas-para-eventos-bogota)        echo "Salas R&uacute;sticas" ;;
    comedores-rusticos-eventos-bogota)         echo "Comedores R&uacute;sticos" ;;
    mesas-para-eventos-bogota)                 echo "Mesas Lounge" ;;
    mesas-picnic-para-eventos-bogota)          echo "Mesas Picnic" ;;
    mesas-sillas-industriales-eventos-bogota)  echo "Mobiliario Industrial" ;;
    sillas-para-eventos-bogota)                echo "Sillas Lounge" ;;
    sillas-para-juntas-bogota)                 echo "Sillas Interlocutoras" ;;
    sillas-acapulco-para-eventos-bogota)       echo "Sillas Acapulco" ;;
    poltronas-para-eventos-en-bogota)          echo "Poltronas Lounge" ;;
    bombillos-vintage-para-eventos)            echo "Bombillos Vintage" ;;
    pista-de-baile-para-eventos)               echo "Pista de Baile LED" ;;
    mobiliario-led-eventos-bogota)             echo "Mobiliario LED" ;;
    calefactores-ambiente-para-eventos)        echo "Calefactores" ;;
    separadores-de-fila-para-eventos)          echo "Separadores de Fila" ;;
    acarreos-trasteos-y-mudanzas-bogota)       echo "Acarreos y Mudanzas" ;;
  esac
}

# Matriz: para cada pagina, los 6 slots en orden visual del grid
# Posicion 1 (esquina sup-izq): yellow
# Posiciones 2-5: real cross-links (mood-fit)
# Posicion 6 (esquina inf-der): blue testimonio
# Formato: yellow_slug|real1|real2|real3|real4|testimonio_text|testimonio_name|testimonio_event
get_layout() {
  case "$1" in
    bombillos-vintage-para-eventos)
      echo "mesas-picnic-para-eventos-bogota|salas-rusticas-para-eventos-bogota|comedores-rusticos-eventos-bogota|calefactores-ambiente-para-eventos|sillas-acapulco-para-eventos-bogota|Los bombillos cambiaron la noche &mdash; el jard&iacute;n qued&oacute; tipo Pinterest, exactamente como lo so&ntilde;&aacute;bamos.|Andrea M.|Boda &middot; La Calera"
      ;;
    salas-rusticas-para-eventos-bogota)
      echo "mesas-picnic-para-eventos-bogota|comedores-rusticos-eventos-bogota|bombillos-vintage-para-eventos|calefactores-ambiente-para-eventos|sillas-acapulco-para-eventos-bogota|Las salas r&uacute;sticas fueron el coraz&oacute;n del montaje. Madera real, todos preguntaron d&oacute;nde las alquilamos.|Camila R.|Boda &middot; Chía"
      ;;
    comedores-rusticos-eventos-bogota)
      echo "mesas-picnic-para-eventos-bogota|salas-rusticas-para-eventos-bogota|bombillos-vintage-para-eventos|calefactores-ambiente-para-eventos|mesas-sillas-industriales-eventos-bogota|Las mesas de banquete fueron perfectas &mdash; fotos incre&iacute;bles, todos los invitados c&oacute;modos.|Daniela P.|Boda &middot; Sopó"
      ;;
    calefactores-ambiente-para-eventos)
      echo "mesas-picnic-para-eventos-bogota|salas-rusticas-para-eventos-bogota|comedores-rusticos-eventos-bogota|bombillos-vintage-para-eventos|sillas-acapulco-para-eventos-bogota|La fiesta no acab&oacute; a las 10pm como ten&iacute;amos miedo. Con los calefactores todos quedaron afuera hasta la 1am.|Sebasti&aacute;n V.|Boda &middot; Chía"
      ;;
    mesas-picnic-para-eventos-bogota)
      echo "acarreos-trasteos-y-mudanzas-bogota|salas-rusticas-para-eventos-bogota|comedores-rusticos-eventos-bogota|bombillos-vintage-para-eventos|sillas-acapulco-para-eventos-bogota|Las mesas picnic fueron justo el toque casual que necesit&aacute;bamos para el matrimonio campestre.|Mar&iacute;a F.|Boda &middot; La Calera"
      ;;
    mesas-sillas-industriales-eventos-bogota)
      echo "mesas-picnic-para-eventos-bogota|salas-rusticas-para-eventos-bogota|comedores-rusticos-eventos-bogota|bombillos-vintage-para-eventos|mesas-para-eventos-bogota|El mobiliario industrial le dio un aire distinto al lanzamiento. Muy bien recibido en redes.|Carolina T.|Marketing &middot; Bogot&aacute;"
      ;;
    sillas-acapulco-para-eventos-bogota)
      echo "mesas-picnic-para-eventos-bogota|salas-lounge-para-eventos-en-bogota|mesas-para-eventos-bogota|poltronas-para-eventos-en-bogota|bombillos-vintage-para-eventos|Las sillas acapulco arcoíris fueron LA foto de la fiesta. Todo el mundo se sentaba ah&iacute; para los retratos.|Sara M.|Cumpleaños &middot; Bogot&aacute;"
      ;;
    salas-lounge-para-eventos-en-bogota)
      echo "mesas-picnic-para-eventos-bogota|mesas-para-eventos-bogota|sillas-acapulco-para-eventos-bogota|poltronas-para-eventos-en-bogota|pista-de-baile-para-eventos|El c&oacute;ctel de bienvenida qued&oacute; impecable &mdash; la sala lounge se sinti&oacute; de revista.|Andr&eacute;s S.|Cocktail empresarial &middot; Bogot&aacute;"
      ;;
    mesas-para-eventos-bogota)
      echo "mesas-picnic-para-eventos-bogota|salas-lounge-para-eventos-en-bogota|sillas-para-eventos-bogota|poltronas-para-eventos-en-bogota|sillas-acapulco-para-eventos-bogota|Las mesas con lycra dorada cerraron el look elegante que buscaba para la gala anual.|Mar&iacute;a J.|Gala empresarial &middot; Bogot&aacute;"
      ;;
    sillas-para-eventos-bogota)
      echo "mesas-picnic-para-eventos-bogota|salas-lounge-para-eventos-en-bogota|mesas-para-eventos-bogota|poltronas-para-eventos-en-bogota|sillas-acapulco-para-eventos-bogota|Sillas perfectas para el c&oacute;ctel. C&oacute;modas y elegantes &mdash; la gente las pidi&oacute; hasta el final.|Juliana C.|Empresarial &middot; Usaquén"
      ;;
    sillas-para-juntas-bogota)
      echo "acarreos-trasteos-y-mudanzas-bogota|salas-lounge-para-eventos-en-bogota|mesas-para-eventos-bogota|separadores-de-fila-para-eventos|mobiliario-led-eventos-bogota|Sillas c&oacute;modas y montaje a tiempo. La rueda de prensa sali&oacute; impecable.|Mar&iacute;a J.|Comunicaciones &middot; Centro de Convenciones"
      ;;
    poltronas-para-eventos-en-bogota)
      echo "mesas-picnic-para-eventos-bogota|salas-lounge-para-eventos-en-bogota|sillas-acapulco-para-eventos-bogota|mesas-para-eventos-bogota|sillas-para-eventos-bogota|Las poltronas blancas le dieron a la zona VIP el toque premium que ped&iacute;a el cliente.|Diego R.|Producci&oacute;n &middot; Bogot&aacute;"
      ;;
    pista-de-baile-para-eventos)
      echo "mesas-picnic-para-eventos-bogota|mobiliario-led-eventos-bogota|salas-lounge-para-eventos-en-bogota|bombillos-vintage-para-eventos|separadores-de-fila-para-eventos|La pista LED fue protagonista &mdash; todos los invitados terminaron en el centro tom&aacute;ndose fotos.|Camila B.|Boda &middot; Hacienda"
      ;;
    mobiliario-led-eventos-bogota)
      echo "mesas-picnic-para-eventos-bogota|pista-de-baile-para-eventos|salas-lounge-para-eventos-en-bogota|sillas-acapulco-para-eventos-bogota|mesas-para-eventos-bogota|El mobiliario LED transform&oacute; la pista de noche. S&uacute;per recomendado.|Andr&eacute;s M.|Cumpleaños 30 &middot; Bogot&aacute;"
      ;;
    separadores-de-fila-para-eventos)
      echo "acarreos-trasteos-y-mudanzas-bogota|salas-lounge-para-eventos-en-bogota|sillas-para-juntas-bogota|pista-de-baile-para-eventos|mobiliario-led-eventos-bogota|Los separadores dorados ordenaron la fila VIP de manera elegante &mdash; muy profesional.|Marcela V.|Producci&oacute;n &middot; Hotel JW"
      ;;
    acarreos-trasteos-y-mudanzas-bogota)
      echo "mesas-picnic-para-eventos-bogota|salas-lounge-para-eventos-en-bogota|mesas-para-eventos-bogota|comedores-rusticos-eventos-bogota|calefactores-ambiente-para-eventos|Manejaron la mudanza de oficina con cuidado total. Lleg&oacute; todo perfecto y a tiempo.|Andr&eacute;s O.|Empresarial &middot; Bogot&aacute;"
      ;;
  esac
}

render_real_card() {
  local slug="$1"
  local photo=$(get_photo "$slug")
  local name=$(get_name "$slug")
  cat <<HTML
    <a href="../${slug}/" class="combina-hero-card">
      <div class="combina-hero-card-bg" style="background-image:url('../assets/img/${photo}')"></div>
      <div class="combina-hero-card-overlay"></div>
      <div class="combina-hero-card-body">
        <span class="combina-hero-card-name">${name}</span>
        <span class="combina-hero-card-arrow" aria-hidden="true">&rarr;</span>
      </div>
    </a>
HTML
}

render_yellow_card() {
  local slug="$1"
  local name=$(get_name "$slug")
  cat <<HTML
    <a href="../${slug}/" class="combina-hero-card combina-hero-card-empty">
      <div class="combina-hero-card-bg"></div>
      <div class="combina-hero-card-empty-content">
        <span class="combina-hero-card-empty-eyebrow">Pr&oacute;ximamente</span>
        <h4 class="combina-hero-card-empty-title">${name}</h4>
        <span class="combina-hero-card-empty-cta">Ver categor&iacute;a &rarr;</span>
      </div>
    </a>
HTML
}

render_blue_card() {
  local text="$1"
  local name="$2"
  local event="$3"
  cat <<HTML
    <div class="combina-hero-card combina-hero-card-blue">
      <div class="combina-hero-card-blue-inner">
        <span class="quote-mark" aria-hidden="true">&ldquo;</span>
        <p class="testimonial-text">${text}</p>
        <div class="testimonial-attribution">
          <span class="testimonial-name">${name}</span>
          <span class="testimonial-event">${event}</span>
        </div>
      </div>
    </div>
HTML
}

render_section() {
  local slug="$1"
  local layout=$(get_layout "$slug")
  IFS='|' read -r yellow real1 real2 real3 real4 testi_text testi_name testi_event <<< "$layout"

  cat <<HTML
<section class="combina-hero reveal">
  <div class="combina-hero-title">
    <span class="label on-dark">Combina con</span>
    <span class="combina-hero-title-text">Tenemos m&aacute;s para tu evento.</span>
  </div>
  <div class="combina-hero-grid">
$(render_yellow_card "$yellow")
$(render_real_card "$real1")
$(render_real_card "$real2")
$(render_real_card "$real3")
$(render_real_card "$real4")
$(render_blue_card "$testi_text" "$testi_name" "$testi_event")
  </div>
</section>
HTML
}

# Procesa una pagina:
# 1. Quita seccion vieja .combinacion (si existe) - usa awk para borrar bloque <section class="combinacion ... </section>
# 2. Quita seccion .combina-hero existente (si existe, para regenerar)
# 3. Inyecta nueva seccion despues del </section> que cierra showcase-section
process_page() {
  local slug="$1"
  local file="${slug}/index.html"
  if [ ! -f "$file" ]; then echo "SKIP: $file no existe"; return; fi

  local tmp=$(mktemp)
  # Paso 1+2: quitar seccion combinacion vieja Y combina-hero existente
  python3 - "$file" "$tmp" <<'PY'
import sys, re
src, dst = sys.argv[1], sys.argv[2]
with open(src) as fh:
    content = fh.read()
# Remove old .combinacion section
content = re.sub(r'<section class="combinacion[^"]*"[^>]*>.*?</section>\s*', '', content, flags=re.DOTALL)
# Remove existing .combina-hero section (will be regenerated)
content = re.sub(r'<section class="combina-hero[^"]*"[^>]*>.*?</section>\s*', '', content, flags=re.DOTALL)
with open(dst, 'w') as fh:
    fh.write(content)
PY
  mv "$tmp" "$file"

  # Paso 3: inyectar nueva seccion despues del showcase-section closing tag
  # Localizar el </section> que cierra showcase-section
  local section_html=$(render_section "$slug")
  tmp=$(mktemp)
  awk -v sec="$section_html" '
    /<section class="showcase-section"/ { in_showcase = 1 }
    { print }
    in_showcase && /^<\/section>$/ {
      print sec
      in_showcase = 0
    }
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
  echo "OK: $slug"
}

# Lista de slugs a procesar (todos excepto bombillos que ya esta hecho)
SLUGS="salas-lounge-para-eventos-en-bogota salas-rusticas-para-eventos-bogota comedores-rusticos-eventos-bogota mesas-para-eventos-bogota mesas-picnic-para-eventos-bogota mesas-sillas-industriales-eventos-bogota sillas-para-eventos-bogota sillas-para-juntas-bogota sillas-acapulco-para-eventos-bogota poltronas-para-eventos-en-bogota pista-de-baile-para-eventos mobiliario-led-eventos-bogota calefactores-ambiente-para-eventos separadores-de-fila-para-eventos acarreos-trasteos-y-mudanzas-bogota bombillos-vintage-para-eventos"

for slug in $SLUGS; do
  process_page "$slug"
done

echo ""
echo "Listo: cross-sell v2 inyectado/actualizado en todas las paginas"
