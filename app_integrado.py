import importlib
from flask import Flask, render_template_string, request

# Importa los módulos de tus dos archivos
olx_mod = importlib.import_module("app_Version2")
rest_mod = importlib.import_module("app_Version30")

app = Flask(__name__)

# Usa el HTML de uno de los archivos, pero con una sola tabla para todos los resultados
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
                    <input name="palabras_clave" class="form-control" value="{{ filtros.palabras_clave }}">
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
    buscando = False
    error = ""
    oportunidades = []
    if request.method == "POST":
        filtros["modelos"] = request.form.get("modelos", "")
        filtros["precio_minimo"] = int(request.form.get("precio_minimo", "0") or "0")
        filtros["precio_maximo"] = int(request.form.get("precio_maximo", "99999") or "99999")
        filtros["ano_minimo"] = int(request.form.get("ano_minimo", "0") or "0")
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
            # Ejecuta ambas funciones y une resultados
            oportunidades_olx = olx_mod.buscar_en_sitios(filtros_proc)
            oportunidades_otros = rest_mod.buscar_en_sitios(filtros_proc)
            # Junta y elimina duplicados por hash
            todos = oportunidades_olx + oportunidades_otros
            ya_vistos = set()
            oportunidades = []
            for o in todos:
                h = o.get("hash")
                if h and h not in ya_vistos:
                    oportunidades.append(o)
                    ya_vistos.add(h)
            toast = f"¡Búsqueda completada! {len(oportunidades)} resultados"
        except Exception as e:
            error = f"Error al buscar: {e}"
            toast = "Hubo un error en la búsqueda"
        buscando = False
    return render_template_string(HTML, oportunidades=oportunidades, filtros=filtros, buscando=buscando, error=error, toast=toast)

if __name__ == "__main__":
    app.run(debug=True)