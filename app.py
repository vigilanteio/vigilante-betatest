import importlib
from flask import Flask, render_template_string, request, redirect, url_for
from email_utils import enviar_email

scrapers_mod = importlib.import_module("scrapers")

app = Flask(__name__)

EMAIL_REMITENTE = "vigilante.io2025@gmail.com"

HTML = """
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Vigilante de Oportunidades - {{ vehicle_type|capitalize }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #f8fafc; }
        .brand { font-weight: bold; font-size: 2rem; color: #0d6efd; letter-spacing: 1px; }
        .table thead th { background: #0d6efd; color: #fff; }
        .table-hover tbody tr:hover { background: #e3f2fd; }
        .filters-card { margin-top:2rem; box-shadow:0 3px 12px #0001; }
        .badge-source { font-size: 0.9em;}
        .toast-container { position:fixed; top:1rem; right:1rem; z-index:9999;}
        .nav-pills .nav-link.active { background-color: #0d6efd; }
        @media (max-width: 600px) {
            .brand { font-size:1.3rem; }
            .filters-card { margin-top:1rem; }
            .table-responsive { font-size: 0.95rem; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="d-flex justify-content-between align-items-center my-3">
        <span class="brand">🔎 Vigilante de Oportunidades</span>
    </div>

    <ul class="nav nav-pills nav-fill">
        <li class="nav-item">
            <a class="nav-link {% if vehicle_type == 'motos' %}active{% endif %}" href="/motos">Motos</a>
        </li>
        <li class="nav-item">
            <a class="nav-link {% if vehicle_type == 'autos' %}active{% endif %}" href="/autos">Autos</a>
        </li>
    </ul>

    <div class="card filters-card">
        <div class="card-body">
            <form method="post" class="row g-3">
                <div class="col-md-4 col-6">
                    <label class="form-label">Modelo(s):</label>
                    <input name="modelos" class="form-control" placeholder="{{ 'ej. PCX, NMAX' if vehicle_type == 'motos' else 'ej. Civic, Corolla, Fiat 500' }}" value="{{ filtros.modelos }}">
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
                    <input name="palabras_clave" class="form-control" placeholder="{{ 'Ex: ABS, top case, baú' if vehicle_type == 'motos' else 'Ex: automático, sedán, baúl' }}" value="{{ filtros.palabras_clave }}">
                </div>
                <div class="col-md-12">
                    <label class="form-label">Correo del cliente:</label>
                    <input name="cliente_email" type="email" class="form-control" placeholder="cliente@email.com" value="{{ filtros.cliente_email }}">
                </div>
                <div class="col-md-12">
                    <label class="form-label">¿Desea recibir notificaciones al correo?</label>
                    <div class="form-check form-switch">
                        <input name="notificar_email" class="form-check-input" type="checkbox" id="notificar_email" {% if filtros.notificar_email %}checked{% endif %}>
                        <label class="form-check-label" for="notificar_email">Sí, enviarme oportunidades al correo</label>
                    </div>
                </div>
                <div class="col-md-12 d-grid gap-2">
                    <button type="submit" name="buscar" value="buscar" class="btn btn-primary py-2 fs-5">
                        <span class="bi bi-search"></span> Buscar oportunidades
                    </button>
                </div>
            </form>
        </div>
    </div>
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
                                <th>Origen</th>
                                <th>Título</th>
                                <th>Precio</th>
                                <th>Año</th>
                                <th>Enlace</th>
                            </tr>
                        </thead>
                        <tbody>
                        {% for o in oportunidades %}
                            <tr>
                                <td><span class="badge bg-info badge-source">{{ o['origen'] }}</span></td>
                                <td>{{ o['titulo'] }}</td>
                                <td>{{ o['precio'] }} €</td>
                                <td>{{ o['ano'] }}</td>
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
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

def unir_resultados(*resultados):
    return [item for sublist in resultados for item in sublist]

@app.route("/")
def index():
    return redirect(url_for("search", vehicle_type="motos"))

@app.route("/<vehicle_type>", methods=["GET", "POST"])
def search(vehicle_type):
    if vehicle_type not in ["motos", "autos"]:
        return "Tipo de vehículo no válido", 404

    default_models = "pcx, nmax" if vehicle_type == "motos" else "civic, corolla, fiat 500"

    filtros = {
        "modelos": default_models,
        "precio_minimo": 0,
        "precio_maximo": 99999,
        "ano_minimo": 0,
        "palabras_clave": "",
        "cliente_email": "",
        "notificar_email": True
    }
    oportunidades = None
    error = ""

    if request.method == "POST":
        filtros["modelos"] = request.form.get("modelos", default_models)
        precio_minimo_val = request.form.get("precio_minimo", "0")
        filtros["precio_minimo"] = int(precio_minimo_val) if precio_minimo_val.strip() else 0
        precio_maximo_val = request.form.get("precio_maximo", "99999")
        filtros["precio_maximo"] = int(precio_maximo_val) if precio_maximo_val.strip() else 99999
        ano_minimo_val = request.form.get("ano_minimo", "0")
        filtros["ano_minimo"] = int(ano_minimo_val) if ano_minimo_val.strip() else 0
        filtros["palabras_clave"] = request.form.get("palabras_clave", "")
        filtros["cliente_email"] = request.form.get("cliente_email", "")
        filtros["notificar_email"] = bool(request.form.get("notificar_email"))

        filtros_proc = {
            "modelos": [m.strip().lower() for m in filtros["modelos"].split(",") if m.strip()],
            "precio_minimo": filtros["precio_minimo"],
            "precio_maximo": filtros["precio_maximo"],
            "ano_minimo": filtros["ano_minimo"],
            "palabras_clave": [p.strip().lower() for p in filtros["palabras_clave"].split(",") if p.strip()],
            "vehicle_type": vehicle_type
        }
        try:
            resultados = scrapers_mod.buscar(filtros_proc)
            oportunidades = unir_resultados(resultados)

            if filtros["notificar_email"] and filtros["cliente_email"] and oportunidades:
                cuerpo = f"¡Se encontraron nuevas oportunidades de {vehicle_type}!\n\n"
                for o in oportunidades:
                    cuerpo += f"- {o['origen']}: {o['titulo']} | {o['precio']}€ | Año: {o['ano']} | {o['enlace']}\n"
                enviar_email(
                    filtros["cliente_email"],
                    f"Nuevas oportunidades de {vehicle_type} encontradas",
                    cuerpo,
                    EMAIL_REMITENTE
                )
        except Exception as e:
            error = f"Error al buscar: {e}"

    return render_template_string(HTML, oportunidades=oportunidades, filtros=filtros, error=error, vehicle_type=vehicle_type)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
