"""
Location Intelligence Engine — módulo independente.

Coleta automática de dados de localização e indicadores socioeconômicos.
NÃO avalia imóveis: apenas enriquece a localização para alimentar a busca
de comparáveis e, depois, o motor de avaliação.

Fontes:
- ViaCEP (pública, sem chave): logradouro, cidade, UF, código IBGE.
- IBGE (pública): município, população, PIB, PIB per capita, área.
- OpenStreetMap/Overpass (pública): equipamentos urbanos próximos.
- Atlas Brasil (IDHM): dataset local consolidado (sem API pública estável).

Todas as chamadas externas têm timeout curto e degradam com elegância:
se uma fonte falhar, o restante do perfil continua sendo entregue.
"""

import json
import logging
import math
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TIMEOUT = 8  # segundos por chamada externa

# ---------------------------------------------------------------------------
# Dataset local de IDHM (Atlas Brasil) — capitais e principais municípios.
# Fallback por UF quando o município não está na lista.
# ---------------------------------------------------------------------------

IDHM_MUNICIPIOS: Dict[str, Dict[str, float]] = {
    # código IBGE : indicadores
    "5002704": {"idhm": 0.784, "idhm_renda": 0.802, "idhm_educacao": 0.723, "idhm_longevidade": 0.833},  # Campo Grande/MS
    "4106902": {"idhm": 0.823, "idhm_renda": 0.850, "idhm_educacao": 0.768, "idhm_longevidade": 0.855},  # Curitiba/PR
    "3550308": {"idhm": 0.805, "idhm_renda": 0.843, "idhm_educacao": 0.725, "idhm_longevidade": 0.855},  # São Paulo/SP
    "3304557": {"idhm": 0.799, "idhm_renda": 0.840, "idhm_educacao": 0.719, "idhm_longevidade": 0.845},  # Rio de Janeiro/RJ
    "3106200": {"idhm": 0.810, "idhm_renda": 0.841, "idhm_educacao": 0.737, "idhm_longevidade": 0.856},  # Belo Horizonte/MG
    "4314902": {"idhm": 0.805, "idhm_renda": 0.867, "idhm_educacao": 0.702, "idhm_longevidade": 0.857},  # Porto Alegre/RS
    "5300108": {"idhm": 0.824, "idhm_renda": 0.863, "idhm_educacao": 0.742, "idhm_longevidade": 0.873},  # Brasília/DF
    "4205407": {"idhm": 0.847, "idhm_renda": 0.870, "idhm_educacao": 0.800, "idhm_longevidade": 0.873},  # Florianópolis/SC
    "2927408": {"idhm": 0.759, "idhm_renda": 0.769, "idhm_educacao": 0.690, "idhm_longevidade": 0.829},  # Salvador/BA
    "2304400": {"idhm": 0.754, "idhm_renda": 0.770, "idhm_educacao": 0.679, "idhm_longevidade": 0.824},  # Fortaleza/CE
    "2611606": {"idhm": 0.772, "idhm_renda": 0.796, "idhm_educacao": 0.698, "idhm_longevidade": 0.831},  # Recife/PE
    "5208707": {"idhm": 0.799, "idhm_renda": 0.832, "idhm_educacao": 0.739, "idhm_longevidade": 0.833},  # Goiânia/GO
    "1302603": {"idhm": 0.737, "idhm_renda": 0.720, "idhm_educacao": 0.686, "idhm_longevidade": 0.815},  # Manaus/AM
    "1501402": {"idhm": 0.746, "idhm_renda": 0.734, "idhm_educacao": 0.690, "idhm_longevidade": 0.823},  # Belém/PA
    "5103403": {"idhm": 0.785, "idhm_renda": 0.800, "idhm_educacao": 0.726, "idhm_longevidade": 0.834},  # Cuiabá/MT
}

IDHM_UF_MEDIO: Dict[str, float] = {
    "AC": 0.719, "AL": 0.683, "AP": 0.740, "AM": 0.733, "BA": 0.714, "CE": 0.735,
    "DF": 0.850, "ES": 0.771, "GO": 0.769, "MA": 0.687, "MT": 0.774, "MS": 0.766,
    "MG": 0.774, "PA": 0.698, "PB": 0.722, "PR": 0.792, "PE": 0.727, "PI": 0.697,
    "RJ": 0.796, "RN": 0.731, "RS": 0.787, "RO": 0.725, "RR": 0.752, "SC": 0.808,
    "SP": 0.806, "SE": 0.702, "TO": 0.743,
}


def _http_json(url: str) -> Optional[Any]:
    """GET JSON com timeout, tratando gzip. Retorna None em qualquer falha."""
    import gzip
    import io
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Avaliador/1.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, identity",
        })
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            bruto = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                bruto = gzip.GzipFile(fileobj=io.BytesIO(bruto)).read()
            return json.loads(bruto.decode("utf-8"))
    except Exception as e:
        logger.warning("Falha ao consultar %s: %s", url.split("?")[0], e)
        return None


# ---------------------------------------------------------------------------
# 1. Endereço por CEP (ViaCEP)
# ---------------------------------------------------------------------------

def buscar_cep(cep: str) -> Dict[str, Any]:
    """
    Consulta ViaCEP e devolve o endereço + código IBGE do município.

    Returns:
        {"ok": bool, "erro": str|None, "logradouro", "bairro", "cidade",
         "uf", "ibge", "cep"}
    """
    limpo = "".join(c for c in str(cep) if c.isdigit())
    if len(limpo) != 8:
        return {"ok": False, "erro": "CEP deve ter 8 dígitos."}

    dados = _http_json(f"https://viacep.com.br/ws/{limpo}/json/")
    if not dados or dados.get("erro"):
        return {"ok": False, "erro": "CEP não encontrado."}

    return {
        "ok": True,
        "erro": None,
        "cep": dados.get("cep"),
        "logradouro": dados.get("logradouro"),
        "bairro": dados.get("bairro"),
        "cidade": dados.get("localidade"),
        "uf": dados.get("uf"),
        "ibge": dados.get("ibge"),
    }


# ---------------------------------------------------------------------------
# 2. Geocodificação (Nominatim/OSM)
# ---------------------------------------------------------------------------

def geocodificar(endereco: str, numero: str = "", cidade: str = "", uf: str = "") -> Dict[str, Any]:
    """Obtém latitude/longitude a partir do endereço (OpenStreetMap)."""
    partes = [p for p in [f"{endereco} {numero}".strip(), cidade, uf, "Brasil"] if p]
    q = urllib.parse.quote(", ".join(partes))
    dados = _http_json(f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1")
    if not dados or not isinstance(dados, list) or not dados:
        return {"ok": False, "latitude": None, "longitude": None}
    return {
        "ok": True,
        "latitude": float(dados[0]["lat"]),
        "longitude": float(dados[0]["lon"]),
    }


# ---------------------------------------------------------------------------
# 3. Indicadores do município (IBGE + dataset IDHM)
# ---------------------------------------------------------------------------

def indicadores_municipio(codigo_ibge: str, uf: str = "") -> Dict[str, Any]:
    """
    Busca população, PIB e PIB per capita no IBGE e complementa com IDHM local.

    Degrada com elegância: campos que a API não devolver ficam None.
    """
    cod = str(codigo_ibge).strip()
    out: Dict[str, Any] = {
        "codigo_ibge": cod, "municipio": None, "uf": uf or None,
        "populacao": None, "pib": None, "pib_per_capita": None,
        "area_km2": None, "densidade_populacional": None,
        "idhm": None, "idhm_renda": None, "idhm_educacao": None, "idhm_longevidade": None,
        "fontes": [],
    }

    # Município e UF
    m = _http_json(f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{cod}")
    if isinstance(m, dict):
        out["municipio"] = m.get("nome")
        try:
            out["uf"] = m["microrregiao"]["mesorregiao"]["UF"]["sigla"]
        except (KeyError, TypeError):
            pass
        out["fontes"].append("IBGE Localidades")

    # População estimada (agregado 6579)
    pop = _http_json(
        f"https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/-1/"
        f"variaveis/9324?localidades=N6[{cod}]"
    )
    out["populacao"] = _extrair_valor_sidra(pop)
    if out["populacao"]:
        out["fontes"].append("IBGE População")

    # PIB total (agregado 5938, variável 37 — em mil reais)
    pib_total = _extrair_valor_sidra(_http_json(
        f"https://servicodados.ibge.gov.br/api/v3/agregados/5938/periodos/-1/"
        f"variaveis/37?localidades=N6[{cod}]"
    ))
    if pib_total:
        out["pib"] = pib_total * 1000
        out["fontes"].append("IBGE PIB municipal")

    # PIB per capita (agregado 5938, variável 593)
    pib_pc = _extrair_valor_sidra(_http_json(
        f"https://servicodados.ibge.gov.br/api/v3/agregados/5938/periodos/-1/"
        f"variaveis/593?localidades=N6[{cod}]"
    ))
    if pib_pc:
        out["pib_per_capita"] = pib_pc
    elif out["pib"] and out["populacao"]:
        out["pib_per_capita"] = round(out["pib"] / out["populacao"], 2)

    # Área e densidade
    area = _http_json(
        f"https://servicodados.ibge.gov.br/api/v3/agregados/1301/periodos/-1/"
        f"variaveis/615?localidades=N6[{cod}]"
    )
    out["area_km2"] = _extrair_valor_sidra(area)
    if out["area_km2"] and out["populacao"]:
        out["densidade_populacional"] = round(out["populacao"] / out["area_km2"], 2)

    # IDHM (dataset local; fallback pela média da UF)
    idh = IDHM_MUNICIPIOS.get(cod)
    if idh:
        out.update(idh)
        out["fontes"].append("Atlas Brasil (dataset local)")
    else:
        sigla = out.get("uf") or uf
        if sigla and sigla in IDHM_UF_MEDIO:
            out["idhm"] = IDHM_UF_MEDIO[sigla]
            out["idhm_estimado_por_uf"] = True
            out["fontes"].append(f"IDHM médio de {sigla} (estimativa)")

    # Renda média aproximada (PIB per capita não é renda, mas serve de proxy)
    if out["pib_per_capita"]:
        out["renda_media_proxy"] = round(out["pib_per_capita"] / 12, 2)

    return out


def _extrair_valor_sidra(resposta: Any) -> Optional[float]:
    """Extrai o valor numérico de uma resposta da API de agregados do IBGE."""
    try:
        serie = resposta[0]["resultados"][0]["series"][0]["serie"]
        for _, v in sorted(serie.items(), reverse=True):
            if v not in ("-", "...", "..", None, ""):
                return float(str(v).replace(",", "."))
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return None


# ---------------------------------------------------------------------------
# 4. Infraestrutura próxima (Overpass/OSM)
# ---------------------------------------------------------------------------

CATEGORIAS_OSM = {
    "escolas": '["amenity"="school"]',
    "hospitais": '["amenity"~"hospital|clinic"]',
    "mercados": '["shop"~"supermarket|convenience"]',
    "farmacias": '["amenity"="pharmacy"]',
    "transporte": '["public_transport"="station"]',
    "parques": '["leisure"="park"]',
}


def infraestrutura_proxima(lat: float, lon: float, raio_m: int = 1500) -> Dict[str, Any]:
    """
    Conta equipamentos urbanos num raio (padrão 1,5 km) via Overpass.

    Retorna as contagens e um índice de infraestrutura (0–10).
    """
    if lat is None or lon is None:
        return {"ok": False, "erro": "Sem coordenadas."}

    partes = [f'node(around:{raio_m},{lat},{lon}){filtro};' for filtro in CATEGORIAS_OSM.values()]
    query = f"[out:json][timeout:{TIMEOUT}];({''.join(partes)});out count;"
    # Overpass count agrupado não separa por categoria — consulta uma a uma
    contagens: Dict[str, int] = {}
    for nome, filtro in CATEGORIAS_OSM.items():
        q = f"[out:json][timeout:{TIMEOUT}];node(around:{raio_m},{lat},{lon}){filtro};out count;"
        url = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(q)
        r = _http_json(url)
        try:
            contagens[nome] = int(r["elements"][0]["tags"]["total"])
        except (KeyError, IndexError, TypeError, ValueError):
            contagens[nome] = 0

    if not any(contagens.values()):
        return {"ok": False, "erro": "Overpass indisponível ou área sem dados.", "contagens": contagens}

    # Índice 0–10: saturação logarítmica por categoria
    pontos = 0.0
    for n in contagens.values():
        pontos += min(1.0, math.log1p(n) / math.log1p(10))
    indice = round(pontos / len(contagens) * 10, 1)

    return {"ok": True, "raio_m": raio_m, "contagens": contagens, "indice_infraestrutura": indice}


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------

def perfil_localizacao(
    cep: str,
    numero: str = "",
    bairro: Optional[str] = None,
    com_infraestrutura: bool = True,
) -> Dict[str, Any]:
    """
    Monta o perfil completo da localização a partir do CEP.

    Returns:
        {"localizacao": {...}, "indicadores": {...}, "infraestrutura": {...},
         "avisos": [...]}
    """
    avisos: List[str] = []

    end = buscar_cep(cep)
    if not end.get("ok"):
        return {"ok": False, "erro": end.get("erro", "CEP inválido."), "avisos": avisos}

    bairro_final = bairro or end.get("bairro")
    cod = end.get("ibge") or ""

    ind = indicadores_municipio(cod, end.get("uf") or "")
    if not ind.get("populacao"):
        avisos.append("População não obtida no IBGE — indicador ficará vazio.")
    if ind.get("idhm_estimado_por_uf"):
        avisos.append("IDHM do município não consta na base local: usada a média da UF.")

    geo = geocodificar(end.get("logradouro") or "", numero, end.get("cidade") or "", end.get("uf") or "")
    if not geo.get("ok"):
        avisos.append("Não foi possível geocodificar o endereço (sem lat/long).")

    infra: Dict[str, Any] = {"ok": False}
    if com_infraestrutura and geo.get("ok"):
        infra = infraestrutura_proxima(geo["latitude"], geo["longitude"])
        if not infra.get("ok"):
            avisos.append("Infraestrutura próxima indisponível no momento.")

    return {
        "ok": True,
        "localizacao": {
            "cep": end.get("cep"),
            "logradouro": end.get("logradouro"),
            "numero": numero or None,
            "bairro": bairro_final,
            "cidade": end.get("cidade"),
            "uf": end.get("uf"),
            "ibge": cod,
            "latitude": geo.get("latitude"),
            "longitude": geo.get("longitude"),
        },
        "indicadores": {
            "idh": ind.get("idhm"),
            "idhm_renda": ind.get("idhm_renda"),
            "idhm_educacao": ind.get("idhm_educacao"),
            "idhm_longevidade": ind.get("idhm_longevidade"),
            "pib": ind.get("pib"),
            "pib_per_capita": ind.get("pib_per_capita"),
            "populacao": ind.get("populacao"),
            "renda_media": ind.get("renda_media_proxy"),
            "densidade_populacional": ind.get("densidade_populacional"),
            "area_km2": ind.get("area_km2"),
            "municipio": ind.get("municipio"),
        },
        "infraestrutura": infra,
        "fontes": ind.get("fontes", []) + (["ViaCEP"] if end.get("ok") else []) +
                  (["OpenStreetMap"] if infra.get("ok") else []),
        "avisos": avisos,
    }
