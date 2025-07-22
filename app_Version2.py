import requests
from bs4 import BeautifulSoup
import time
import re
import json
import os
import hashlib
from urllib.parse import quote_plus
from datetime import datetime
from flask import Flask, render_template_string, request

# === CONFIGURACIÓN INICIAL ===
PUSHOVER_USER_KEY = "up7jq3birzwro1evz2m6m8sgnip1mu"
PUSHOVER_API_TOKEN = "av23np6phgzh7bzgbrkcgxf9qv2ctu"
ANUNCIOS_ENVIADOS_DB = "anuncios_enviados.txt"
TOP_Oportunidades = 5

URL_TEMPLATES = {
    "OLX.pt": "https://www.olx.pt/d/ads/q-{modelo}/",
    "Standvirtual": "https://www.standvirtual.com/motos/pesquisa?q={modelo}",
    "CustoJusto.pt": "https://www.custojusto.pt/portugal/motos/q/{modelo}"
}

app = Flask(__name__)

# HTML para la interfaz web con Bootstrap y funcionalidad moderna
HTML = """
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Vigilante de Oportunidades</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- Bootstrap 5 CDN -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #f8fafc; }
        .spinner-border { margin: 20px auto; display: block; }
        .table thead th { background: #0d6efd; color: #fff; }
        .toast-container { position:fixed; top:1rem; right:1rem; z-index:9999;}
        .brand { font-weight: bold; font-size: 1.6rem; color: #0d6efd;}
        .card { margin-top: 1.5rem;}
    </style>
</head>
<body>
<div class="container">
    <div class="d-flex justify-content-between align-items-center my-3">
        <span class="brand">🔎 Vigilante de Oportunidades</span>
        <span class="text-muted">Motos Portugal</span>
    </div>
    <div class="card shadow-sm">
        <div class="card-body">
            <form method="post" class="row g-3">
                <div class="col-md-6">
                    <label class="form-label">Modelos (coma):</label>
                    <input name="modelos" class="form-control" value="{{ filtros.modelos }}">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Precio Mínimo:</label>
                    <input name="precio_minimo" type="number" class="form-control" value="{{ filtros.precio_minimo }}">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Precio Máximo:</label>
                    <input name="precio_maximo" type="number" class="form-control" value="{{ filtros.precio_maximo }}">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Año mínimo:</label>
                    <input name="ano_minimo" type="number" class="form-control" value="{{ filtros.ano_minimo }}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Palabras clave (coma):</label>
                    <input name="palabras_clave" class="form-control" value="{{ filtros.palabras_clave }}">
                </div>
                <div class="col-md-4 d-flex align-items-end">
                    <button type="submit" name="buscar" value="buscar" class="btn btn-primary w-100">
                        <span class="bi bi-search"></span> Buscar oportunidades
                    </button>
                </div>
            </form>
        </div>
    </div>
    {% if buscando %}
        <div class="text-center my-4">
            <div class="spinner-border text-primary" role="status"></div>
            <div>Buscando oportunidades...</div>
        </div>
    {% endif %}

    {% if error %}
        <div class="alert alert-danger my-4">{{ error }}</div>
    {% endif %}

    {% if oportunidades is not none %}
        {% if oportunidades|length == 0 %}
            <div class="alert alert-warning my-4">No se encontraron resultados con los filtros seleccionados.</div>
        {% else %}
            <div class="card shadow-sm">
                <div class="card-header bg-primary text-white">
                    <b>Resultados encontrados</b>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                    <table class="table table-striped table-hover mb-0">
                        <thead>
                            <tr>
                                <th>Título</th>
                                <th>Precio</th>
                                <th>Año</th>
                                <th>Fuente</th>
                                <th>Enlace</th>
                            </tr>
                        </thead>
                        <tbody>
                        {% for o in oportunidades %}
                            <tr>
                                <td>{{ o['titulo'] }}</td>
                                <td>{{ o['precio'] }} €</td>
                                <td>{{ o['ano'] }}</td>
                                <td><span class="badge bg-info">{{ o['fuente'] }}</span></td>
                                <td><a href="{{ o['enlace'] }}" target="_blank" class="btn btn-outline-primary btn-sm">Ver Anuncio</a></td>
                            </tr>
                        {% endfor %}
                        </tbody>
                    </table>
                    </div>
                </div>
            </div>
        {% endif %}
    {% endif %}
    <div class="toast-container">
        {% if toast %}
        <div class="toast align-items-center text-bg-primary border-0 show" role="alert">
            <div class="d-flex">
                <div class="toast-body">{{ toast }}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
        {% endif %}
    </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

def cargar_anuncios_enviados():
    if not os.path.exists(ANUNCIOS_ENVIADOS_DB):
        return set()
    with open(ANUNCIOS_ENVIADOS_DB, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def get_hash_anuncio(titulo, precio, enlace):
    h = hashlib.sha256(f"{titulo}|{precio}|{enlace}".encode("utf-8")).hexdigest()
    return h

def extraer_dato_regex(texto, regex, default=0):
    m = re.search(regex, texto)
    if m:
        return int(m.group(1))
    return default

def contiene_palabras_clave(texto, palabras):
    if not palabras:
        return True  # No filtrar si lista vacía
    texto_l = texto.lower()
    return any(p in texto_l for p in palabras if p)

def procesar_anuncio(titulo, precio, ano, enlace, fuente, descripcion="", anuncios_enviados=set(), oportunidades=[], filtros=None):
    if ano == 0 and descripcion:
        ano = extraer_dato_regex(descripcion, r'\b(20[1-2][0-9])\b', 0)
    if precio == 0 and descripcion:
        precio_str = re.search(r'(\d{3,5})\s?€', descripcion.replace(".", "").replace(",", ""))
        precio = int(precio_str.group(1)) if precio_str else 0
    h = get_hash_anuncio(titulo, precio, enlace)
    if h in anuncios_enviados:
        return
    if filtros["palabras_clave"] and not contiene_palabras_clave(titulo + " " + descripcion, filtros["palabras_clave"]):
        return
    if filtros["precio_minimo"] <= precio <= filtros["precio_maximo"] and (ano == 0 or ano >= filtros["ano_minimo"]):
        oportunidad = {
            "titulo": titulo,
            "precio": precio,
            "ano": ano,
            "enlace": enlace,
            "fuente": fuente,
            "hash": h
        }
        oportunidades.append(oportunidad)

def buscar_en_sitios(filtros):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    anuncios_enviados = cargar_anuncios_enviados()
    oportunidades = []
    for modelo in filtros["modelos"]:
        modelo_formateado = quote_plus(modelo.lower())
        for fuente, url_template in URL_TEMPLATES.items():
            url = url_template.format(modelo=modelo_formateado)
            try:
                pagina = requests.get(url, headers=headers, timeout=20)
                pagina.raise_for_status()
                soup = BeautifulSoup(pagina.content, 'html.parser')
                if fuente == "OLX.pt":
                    anuncios = soup.find_all('div', attrs={'data-cy': 'l-card'})
                    for anuncio in anuncios:
                        enlace_tag = anuncio.find('a'); precio_tag = anuncio.find('p', attrs={'data-testid': 'ad-price'})
                        desc_tag = anuncio.find('div', attrs={'data-cy': 'l-card-description'})
                        if not all([enlace_tag, precio_tag]): continue
                        titulo = enlace_tag.get_text(strip=True)
                        descripcion = desc_tag.get_text(strip=True) if desc_tag else ""
                        precio_str = precio_tag.get_text(strip=True)
                        precio_limpio = re.sub(r'[^0-9]', '', precio_str)
                        precio = int(precio_limpio) if precio_limpio else 0
                        enlace = "https://www.olx.pt" + enlace_tag['href']
                        match_ano = re.search(r'\b(20[1-2][0-9])\b', titulo)
                        ano = int(match_ano.group(1)) if match_ano else 0
                        procesar_anuncio(titulo, precio, ano, enlace, fuente, descripcion, anuncios_enviados, oportunidades, filtros)
                elif fuente == "Standvirtual" or fuente == "CustoJusto.pt":
                    script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
                    if not script_tag: continue
                    data = json.loads(script_tag.string)
                    if fuente == "Standvirtual":
                        anuncios = []
                        urql_state = data.get('props', {}).get('pageProps', {}).get('urqlState', {})
                        for state_value in urql_state.values():
                            if state_value and 'data' in state_value and isinstance(state_value.get('data'), str):
                                try:
                                    nested_data = json.loads(state_value['data'])
                                    if 'advertSearch' in nested_data and nested_data['advertSearch'].get('edges'):
                                        anuncios = nested_data['advertSearch']['edges']
                                        break
                                except (json.JSONDecodeError, TypeError):
                                    continue
                        for edge in anuncios:
                            anuncio = edge.get('node', {})
                            titulo = anuncio.get('title', '')
                            enlace = anuncio.get('url', '')
                            precio = anuncio.get('price', {}).get('amount', {}).get('units', 0)
                            descripcion = anuncio.get('description', '')
                            ano = 0
                            for param in anuncio.get('parameters', []):
                                if param.get('key') == 'first_registration_year':
                                    ano_val = param.get('value')
                                    if ano_val and ano_val.strip().isdigit():
                                        ano = int(ano_val)
                                    break
                            procesar_anuncio(titulo, precio, ano, enlace, fuente, descripcion, anuncios_enviados, oportunidades, filtros)
                    elif fuente == "CustoJusto.pt":
                        anuncios = data.get('props', {}).get('pageProps', {}).get('listItems', [])
                        for anuncio in anuncios:
                            titulo = anuncio.get('title', '')
                            enlace = anuncio.get('url', '')
                            precio = anuncio.get('price', 0)
                            descripcion = anuncio.get('description', '')
                            match_ano = re.search(r'-\s*(\d{2})$', titulo)
                            ano = int("20" + match_ano.group(1)) if match_ano else 0
                            procesar_anuncio(titulo, precio, ano, enlace, fuente, descripcion, anuncios_enviados, oportunidades, filtros)
            except Exception as e:
                continue
    oportunidades = sorted(
        oportunidades,
        key=lambda x: (x['precio'], -x['ano'] if x['ano'] else 0)
    )
    return oportunidades[:TOP_Oportunidades]

@app.route("/", methods=["GET", "POST"])
def index():
    filtros = {
        "modelos": ["honda pcx 125", "yamaha nmax 125"],
        "precio_minimo": 2000,
        "precio_maximo": 3500,
        "ano_minimo": 2020,
        "palabras_clave": []
    }
    toast = ""
    oportunidades = None
    buscando = False
    error = ""
    # Si POST, tomar filtros y buscar
    if request.method == "POST":
        modelos = request.form.get("modelos", "")
        filtros["modelos"] = [m.strip() for m in modelos.split(",") if m.strip()]
        filtros["precio_minimo"] = int(request.form.get("precio_minimo", "2000"))
        filtros["precio_maximo"] = int(request.form.get("precio_maximo", "3500"))
        filtros["ano_minimo"] = int(request.form.get("ano_minimo", "2020"))
        palabras = request.form.get("palabras_clave", "")
        filtros["palabras_clave"] = [p.strip().lower() for p in palabras.split(",") if p.strip()]
        buscando = True
        try:
            oportunidades = buscar_en_sitios(filtros)
            toast = f"¡Búsqueda completada! {len(oportunidades)} resultados"
        except Exception as e:
            error = f"Error al buscar: {e}"
            toast = "Hubo un error en la búsqueda"
        buscando = False
    # Mostrar la página con los resultados y estados
    return render_template_string(HTML, oportunidades=oportunidades, filtros=filtros, buscando=buscando, error=error, toast=toast)

if __name__ == "__main__":
    app.run(debug=True)