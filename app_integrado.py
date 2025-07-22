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
        .brand { font-weight: bold; font-size: 2rem; color: #0955c3; letter-spacing: 2px; }
        .table > thead { background: #0955c3; color: #fff; }
        .table > tbody tr:hover { background: #eaf1fb; }
        .btn-custom { background: #0955c3; color: #fff; }
    </style>
</head>
<body>
    <div class="container py-4">
        <div class="brand mb-4">Vigilante de Oportunidades</div>
        <form method="POST" class="mb-4">
            <div class="row g-2">
                <div class="col-md-3">
                    <input name="filtro" class="form-control" placeholder="Palabra clave o ciudad">
                </div>
                <div class="col-md-3">
                    <select name="origen" class="form-select">
                        <option value="">Todos</option>
                        <option value="olx">OLX</option>
                        <option value="rest">Rest</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <button class="btn btn-custom w-100" type="submit">Buscar</button>
                </div>
            </div>
        </form>
        {% if resultados %}
        <div class="table-responsive">
            <table class="table">
                <thead>
                    <tr>
                        <th>Origen</th>
                        <th>Título</th>
                        <th>Ciudad</th>
                        <th>Precio</th>
                        <th>Fecha</th>
                        <th>Enlace</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in resultados %}
                    <tr>
                        <td>{{ r['origen'] }}</td>
                        <td>{{ r['titulo'] }}</td>
                        <td>{{ r['ciudad'] }}</td>
                        <td>{{ r['precio'] }}</td>
                        <td>{{ r['fecha'] }}</td>
                        <td><a href="{{ r['enlace'] }}" target="_blank">Ver</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <div class="alert alert-info mt-4">No hay resultados para mostrar.</div>
        {% endif %}
    </div>
</body>
</html>
"""

def unir_resultados(olx, rest):
    # Normaliza y une los resultados de ambos módulos
    todos = []
    for x in olx:
        todos.append({
            'origen': 'OLX',
            'titulo': x.get('titulo', ''),
            'ciudad': x.get('ciudad', ''),
            'precio': x.get('precio', ''),
            'fecha': x.get('fecha', ''),
            'enlace': x.get('enlace', ''),
        })
    for x in rest:
        todos.append({
            'origen': 'Rest',
            'titulo': x.get('titulo', ''),
            'ciudad': x.get('ciudad', ''),
            'precio': x.get('precio', ''),
            'fecha': x.get('fecha', ''),
            'enlace': x.get('enlace', ''),
        })
    return todos

@app.route("/", methods=["GET", "POST"])
def home():
    resultados = []
    filtro = ""
    origen = ""
    if request.method == "POST":
        filtro = request.form.get('filtro', '').lower()
        origen = request.form.get('origen', '')

        olx_resultados = olx_mod.buscar(filtro) if origen in ("", "olx") else []
        rest_resultados = rest_mod.buscar(filtro) if origen in ("", "rest") else []

        resultados = unir_resultados(olx_resultados, rest_resultados)
    return render_template_string(HTML, resultados=resultados)

# --- ESTE BLOQUE ES EL CAMBIO CLAVE PARA RENDER ---
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
