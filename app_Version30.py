import requests
from bs4 import BeautifulSoup
import re
import json
import os
import hashlib
from urllib.parse import quote_plus
from flask import Flask, render_template_string, request

URL_TEMPLATES = {
    "OLX.pt": "https://www.olx.pt/d/ads/q-{modelo}/",
    "Standvirtual": "https://www.standvirtual.com/motos/pesquisa?q={modelo}",
    "CustoJusto.pt": "https://www.custojusto.pt/portugal/motos/q/{modelo}"
}

ANUNCIOS_ENVIADOS_DB = "anuncios_enviados.txt"

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Vigilante de Oportunidades</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #f8fafc; }
        .brand { font-weight: bold; font-size: 2rem; color: #0056b3; letter-spacing:-1px;}
        .table thead th { background: #0d6efd; color: #fff; }
        .table-hover tbody tr:hover { background: #e3f2fd; }
        .filters-card { margin-top:2rem; box-shadow:0 3px 12px #0001; }
        .badge-source { font-size: 0.9em;}
        .toast-container { position:fixed; top:1rem; right:1rem; z-index:9999;}
        .img-thumb { width:80px; height:60px; object-fit:cover; border-radius:6px; background:#eee; border:1px solid #ddd; }
        @media (max-width: 600px) {
            .brand { font-size:1.3rem; }
            .filters-card { margin-top:1rem; }
            .table-responsive { font-size: 0.95rem; }
            .img-thumb { width:48px; height:36px; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="d-flex justify-content-between align-items-center my-3">
        <span class="brand">🔎 Vigilante de Oportunidades</span>
        <span class="text-muted">Motos Portugal</span>
    </div>
    <div class="card filters-card">
        <div class="card-body">
            <form method="post" class="row g-3">
                <div class="col-md-4 col-6">
                    <label class="form-label">Modelo(s):</label>
                    <input name="modelos" class="form-control" placeholder="ej. PCX, NMAX" value="{{ filtros.modelos }}">
                </div>
                <div class="col-md-2 col-6">
                    <label class="form-label">Año mínimo:</label>
                    <input name="ano_minimo" type="number" class="form-control" value="{{ filtros.ano_minimo }}">
                </div>
                <div class="col-md-2 col-6">
                    <label class="form-label">Precio min:</label>
                    <input name="precio_minimo" type="number" class="form-control" value="{{ filtros.precio_minimo }}">
                </div>
                <div class="col-md-2 col-6">
                    <label class="form-label">Precio máx:</label>
                    <input name="precio_maximo" type="number" class="form-control" value="{{ filtros.precio_maximo }}">
                </div>
                <div class="col-md-12">
                    <label class="form-label">Palabras clave (coma):</label>
                    <input name="palabras_clave" class="form-control" placeholder="Ex: ABS, top case, baú, revisões (usa portugués)" value="{{ filtros.palabras_clave }}">
                </div>
                <div class="col-md-12 d-grid gap-2">
                    <button type="submit" name="buscar" value="buscar" class="btn btn-primary py-2 fs-5">
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
            <div class="card shadow-sm mt-3">
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
                                <td><span class="badge bg-info badge-source">{{ o['fuente'] }}</span></td>
                                <td><a href="{{ o['enlace'] }}" target="_blank" class="btn btn-outline-primary btn-sm">Ver</a></td>
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

def contiene_palabras_clave(texto, palabras):
    if not palabras:
        return True
    texto_l = texto.lower()
    return any(p in texto_l for p in palabras if p)

def normaliza(texto):
    # Quita espacios y guiones, convierte a minúsculas
    return re.sub(r'[\s\-]', '', texto.lower())

def procesar_anuncio(titulo, precio, ano, enlace, fuente, anuncios_enviados=set(), oportunidades=[], filtros=None):
    h = get_hash_anuncio(titulo, precio, enlace)
    if h in anuncios_enviados:
        return
    # Filtrado de modelo flexible: substring normalizado
    modelo_ok = any(normaliza(modelo) in normaliza(titulo) for modelo in filtros["modelos"])
    if not modelo_ok:
        return
    if filtros["palabras_clave"] and not contiene_palabras_clave(titulo, filtros["palabras_clave"]):
        return
    if not (filtros["precio_minimo"] <= precio <= filtros["precio_maximo"]):
        return
    if ano != 0 and ano < filtros["ano_minimo"]:
        return

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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0'
    }
    anuncios_enviados = set()
    oportunidades = []

    for modelo in filtros["modelos"]:
        modelo_formateado = quote_plus(modelo.lower())
        for fuente, url_template in URL_TEMPLATES.items():
            url = url_template.format(modelo=modelo_formateado)
            try:
                resp = requests.get(url, headers=headers, timeout=20)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.content, 'html.parser')
                if fuente == "OLX.pt":
                    anuncios = soup.find_all('div', attrs={'data-cy': 'l-card'})
                    if not anuncios:
                        anuncios = soup.select("div[data-testid='ad-card']")
                    for anuncio in anuncios:
                        enlace_tag = anuncio.find('a')
                        precio_tag = anuncio.find('p', attrs={'data-testid': 'ad-price'})
                        titulo = enlace_tag.get_text(strip=True) if enlace_tag else ""
                        precio_str = precio_tag.get_text(strip=True) if precio_tag else ""
                        precio_limpio = re.sub(r'[^0-9]', '', precio_str)
                        precio = int(precio_limpio) if precio_limpio else 0
                        enlace = "https://www.olx.pt" + enlace_tag['href'] if enlace_tag else ""
                        match_ano = re.search(r'\b(20[1-2][0-9])\b', titulo)
                        ano = int(match_ano.group(1)) if match_ano else 0
                        procesar_anuncio(titulo, precio, ano, enlace, fuente, anuncios_enviados, oportunidades, filtros)
                elif fuente == "Standvirtual":
                    script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
                    if not script_tag:
                        continue
                    try:
                        data = json.loads(script_tag.string)
                    except Exception:
                        continue
                    anuncios = []
                    urql_state = data.get('props', {}).get('pageProps', {}).get('urqlState', {})
                    for state_value in urql_state.values():
                        if state_value and 'data' in state_value and isinstance(state_value.get('data'), str):
                            try:
                                nested_data = json.loads(state_value['data'])
                                if 'advertSearch' in nested_data and nested_data['advertSearch'].get('edges'):
                                    anuncios = nested_data['advertSearch']['edges']
                                    break
                            except Exception:
                                continue
                    for edge in anuncios:
                        anuncio = edge.get('node', {})
                        titulo = anuncio.get('title', '')
                        enlace = anuncio.get('url', '')
                        precio = anuncio.get('price', {}).get('amount', {}).get('units', 0)
                        ano = 0
                        for param in anuncio.get('parameters', []):
                            if param.get('key') == 'first_registration_year':
                                ano_val = param.get('value')
                                if ano_val and ano_val.strip().isdigit():
                                    ano = int(ano_val)
                                break
                        procesar_anuncio(titulo, precio, ano, enlace, fuente, anuncios_enviados, oportunidades, filtros)
                elif fuente == "CustoJusto.pt":
                    script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
                    if not script_tag:
                        continue
                    try:
                        data = json.loads(script_tag.string)
                    except Exception:
                        continue
                    anuncios = data.get('props', {}).get('pageProps', {}).get('listItems', [])
                    for anuncio in anuncios:
                        titulo = anuncio.get('title', '')
                        precio = anuncio.get('price', 0)
                        enlace = anuncio.get('url', '')
                        if enlace and enlace.startswith('/'):
                            enlace = "https://www.custojusto.pt" + enlace
                        elif enlace and not enlace.startswith('http'):
                            enlace = "https://www.custojusto.pt/" + enlace
                        ano = 0
                        if 'year' in anuncio and str(anuncio['year']).isdigit():
                            ano = int(anuncio['year'])
                        else:
                            match_ano = re.search(r'\b(20[1-2][0-9])\b', titulo)
                            ano = int(match_ano.group(1)) if match_ano else 0
                        procesar_anuncio(titulo, precio, ano, enlace, fuente, anuncios_enviados, oportunidades, filtros)
            except Exception:
                continue
    oportunidades = sorted(
        oportunidades,
        key=lambda x: (x['precio'], -x['ano'] if x['ano'] else 0)
    )
    return oportunidades

@app.route("/", methods=["GET", "POST"])
def index():
    filtros = {
        "modelos": "pcx",
        "precio_minimo": 0,
        "precio_maximo": 99999,
        "ano_minimo": 0,
        "palabras_clave": ""
    }
    toast = ""
    oportunidades = None
    buscando = False
    error = ""
    if request.method == "POST":
        filtros["modelos"] = request.form.get("modelos", "")
        precio_minimo_val = request.form.get("precio_minimo", "0")
        filtros["precio_minimo"] = int(precio_minimo_val) if precio_minimo_val.strip() else 0
        precio_maximo_val = request.form.get("precio_maximo", "99999")
        filtros["precio_maximo"] = int(precio_maximo_val) if precio_maximo_val.strip() else 99999
        ano_minimo_val = request.form.get("ano_minimo", "0")
        filtros["ano_minimo"] = int(ano_minimo_val) if ano_minimo_val.strip() else 0
        filtros["palabras_clave"] = request.form.get("palabras_clave", "")
        filtros_proc = {
            "modelos": [m.strip().lower() for m in filtros["modelos"].split(",") if m.strip()],
            "precio_minimo": filtros["precio_minimo"],
            "precio_maximo": filtros["precio_maximo"],
            "ano_minimo": filtros["ano_minimo"],
            "palabras_clave": [p.strip().lower() for p in filtros["palabras_clave"].split(",") if p.strip()]
        }
        buscando = True
        try:
            oportunidades = buscar_en_sitios(filtros_proc)
            toast = f"¡Búsqueda completada! {len(oportunidades)} resultados"
        except Exception as e:
            error = f"Error al buscar: {e}"
            toast = "Hubo un error en la búsqueda"
        buscando = False
    return render_template_string(HTML, oportunidades=oportunidades, filtros=filtros, buscando=buscando, error=error, toast=toast)

if __name__ == "__main__":
    app.run(debug=True)