import requests
from bs4 import BeautifulSoup
import re
import json
import os
import hashlib
from urllib.parse import quote_plus

URL_TEMPLATES = {
    "OLX.pt": "https://www.olx.pt/d/ads/q-{modelo}/",
    "Standvirtual": "https://www.standvirtual.com/motos/pesquisa?q={modelo}",
    "CustoJusto.pt": "https://www.custojusto.pt/portugal/motos/q/{modelo}"
}

ANUNCIOS_ENVIADOS_DB = "anuncios_enviados.txt"

TOP_Oportunidades = 5

def cargar_anuncios_enviados():
    if not os.path.exists(ANUNCIOS_ENVIADOS_DB):
        return set()
    with open(ANUNCIOS_ENVIADOS_DB, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def get_hash_anuncio(titulo, precio, enlace):
    return hashlib.sha256(f"{titulo}|{precio}|{enlace}".encode("utf-8")).hexdigest()

def contiene_palabras_clave(texto, palabras):
    if not palabras:
        return True
    texto_l = texto.lower()
    return any(p in texto_l for p in palabras if p)

def procesar_anuncio(titulo, precio, ano, enlace, fuente, descripcion, anuncios_enviados, oportunidades, filtros):
    h = get_hash_anuncio(titulo, precio, enlace)
    if h in anuncios_enviados:
        return
    if filtros["palabras_clave"] and not contiene_palabras_clave(titulo + " " + descripcion, filtros["palabras_clave"]):
        return
    if not (filtros["precio_minimo"] <= precio <= filtros["precio_maximo"]):
        return
    if ano != 0 and ano < filtros["ano_minimo"]:
        return
    oportunidad = {
        "origen": fuente,
        "titulo": titulo,
        "ciudad": "",
        "precio": precio,
        "fecha": "",
        "enlace": enlace,
        "ano": ano
    }
    oportunidades.append(oportunidad)

def buscar(filtros):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    anuncios_enviados = cargar_anuncios_enviados()
    oportunidades = []
    for modelo in filtros.get("modelos", []):
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
                elif fuente == "Standvirtual":
                    script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
                    if not script_tag: continue
                    data = json.loads(script_tag.string)
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
                    script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
                    if not script_tag: continue
                    data = json.loads(script_tag.string)
                    anuncios = data.get('props', {}).get('pageProps', {}).get('listItems', [])
                    for anuncio in anuncios:
                        titulo = anuncio.get('title', '')
                        enlace = anuncio.get('url', '')
                        precio = anuncio.get('price', 0)
                        descripcion = anuncio.get('description', '')
                        match_ano = re.search(r'-\s*(\d{2})$', titulo)
                        ano = int("20" + match_ano.group(1)) if match_ano else 0
                        procesar_anuncio(titulo, precio, ano, enlace, fuente, descripcion, anuncios_enviados, oportunidades, filtros)
            except Exception:
                continue
    # Ordena por precio y año descendente
    oportunidades = sorted(oportunidades, key=lambda x: (x['precio'], -x['ano'] if x['ano'] else 0))
    return oportunidades[:TOP_Oportunidades]
