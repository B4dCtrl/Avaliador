"""
Motor de busca e classificação de imóveis comparáveis (comps).

NÃO estima valor — apenas encontra e ranqueia referências por similaridade.
Módulo totalmente isolado do motor de avaliação (regressão).

Arquitetura em 3 camadas:
1. Perfil técnico do imóvel (tipologia, áreas, padrão, programa...).
2. Perfil territorial da região (IDH, renda, densidade, infraestrutura...),
   que permite comparar bairros equivalentes mesmo em cidades diferentes.
3. Score multicritério (0–100%) com pesos por critério e redistribuição
   automática quando um campo está ausente — com explicação item a item.
"""

import math
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Pesos dos critérios (somam 1.0 quando todos presentes)
# ---------------------------------------------------------------------------

PESOS: Dict[str, float] = {
    "tipo_imovel": 0.14,        # tipologia é eliminatória-chave
    "area_terreno": 0.13,
    "area_construida": 0.13,
    "padrao_construtivo": 0.10,
    "conservacao": 0.07,
    "idade": 0.07,
    "programa": 0.08,           # dormitórios/banheiros/vagas
    "zoneamento": 0.06,
    "similaridade_territorial": 0.14,
    "distancia": 0.08,
}

# Escalas ordinais
ESCALA_PADRAO = ["baixo", "normal", "medio", "médio", "alto", "luxo"]
ESCALA_CONSERVACAO = ["ruim", "regular", "bom", "otimo", "ótimo", "novo"]

# Perfil territorial: pesos internos do índice de similaridade territorial
PESOS_TERRITORIAL: Dict[str, float] = {
    "idh": 0.22,
    "renda_per_capita": 0.22,
    "densidade_populacional": 0.12,
    "escolaridade_media_anos": 0.10,
    "indice_seguranca": 0.12,
    "infraestrutura": 0.12,
    "distancia_centro_km": 0.10,
}


def _num(x: Any) -> Optional[float]:
    """Converte para float; None se ausente/inválido."""
    if x is None or x == "":
        return None
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _sim_numerica(a: Optional[float], b: Optional[float], tolerancia_rel: float = 1.0) -> Optional[float]:
    """
    Similaridade entre dois números (0–1) por diferença relativa.
    tolerancia_rel: diferença relativa que zera o score (1.0 = 100%).
    """
    if a is None or b is None:
        return None
    if a == 0 and b == 0:
        return 1.0
    base = max(abs(a), abs(b))
    if base == 0:
        return 1.0
    dif_rel = abs(a - b) / base
    return max(0.0, 1.0 - dif_rel / tolerancia_rel)


def _sim_ordinal(a: Optional[str], b: Optional[str], escala: List[str]) -> Optional[float]:
    """Similaridade entre categorias ordinais (padrão, conservação)."""
    if not a or not b:
        return None
    na, nb = str(a).strip().lower(), str(b).strip().lower()
    try:
        ia, ib = escala.index(na), escala.index(nb)
    except ValueError:
        return 1.0 if na == nb else 0.0
    amplitude = max(1, len(escala) - 1)
    return max(0.0, 1.0 - abs(ia - ib) / amplitude)


def _sim_categorica(a: Optional[str], b: Optional[str]) -> Optional[float]:
    """Similaridade exata para categorias (tipo, zoneamento)."""
    if not a or not b:
        return None
    return 1.0 if str(a).strip().lower() == str(b).strip().lower() else 0.0


# ---------------------------------------------------------------------------
# Perfil territorial e similaridade entre regiões
# ---------------------------------------------------------------------------

def similaridade_territorial(
    perfil_alvo: Optional[Dict[str, Any]],
    perfil_candidato: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Índice de similaridade territorial (0–1) entre duas regiões.

    Permite comparar bairros equivalentes mesmo em municípios diferentes:
    o que importa é o perfil socioeconômico/urbano, não a proximidade.

    Campos ausentes são ignorados e seu peso é redistribuído.
    """
    if not perfil_alvo or not perfil_candidato:
        return None

    # Tolerâncias por indicador (diferença relativa que zera o critério)
    tolerancias = {
        "idh": 0.25,
        "renda_per_capita": 1.0,
        "densidade_populacional": 1.5,
        "escolaridade_media_anos": 0.6,
        "indice_seguranca": 0.8,
        "infraestrutura": 0.8,
        "distancia_centro_km": 1.5,
    }

    detalhes: Dict[str, float] = {}
    soma_peso = 0.0
    soma = 0.0
    for campo, peso in PESOS_TERRITORIAL.items():
        s = _sim_numerica(_num(perfil_alvo.get(campo)), _num(perfil_candidato.get(campo)),
                          tolerancias.get(campo, 1.0))
        if s is None:
            continue
        detalhes[campo] = round(s * 100, 1)
        soma += s * peso
        soma_peso += peso

    if soma_peso == 0:
        return None
    indice = soma / soma_peso
    return {"indice": round(indice, 4), "percentual": round(indice * 100, 1), "detalhes": detalhes}


# ---------------------------------------------------------------------------
# Score de similaridade imóvel × imóvel
# ---------------------------------------------------------------------------

def _sim_programa(alvo: Dict[str, Any], cand: Dict[str, Any]) -> Optional[float]:
    """Similaridade do programa (dormitórios, banheiros, vagas)."""
    partes = []
    for campo in ("dormitorios", "banheiros", "vagas"):
        a, b = _num(alvo.get(campo)), _num(cand.get(campo))
        if a is None or b is None:
            continue
        # cada unidade de diferença custa 35%
        partes.append(max(0.0, 1.0 - abs(a - b) * 0.35))
    if not partes:
        return None
    return sum(partes) / len(partes)


def pontuar_comparavel(
    alvo: Dict[str, Any],
    candidato: Dict[str, Any],
    perfil_territorial_alvo: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calcula o Índice de Similaridade (0–100%) de um candidato em relação ao alvo.

    Retorna o score final, o detalhamento por critério (explicando o porquê)
    e a lista de critérios ignorados por falta de dados.
    """
    criterios: Dict[str, Optional[float]] = {
        "tipo_imovel": _sim_categorica(alvo.get("tipo_imovel"), candidato.get("tipo_imovel")),
        "area_terreno": _sim_numerica(_num(alvo.get("area_terreno")), _num(candidato.get("area_terreno")), 0.6),
        "area_construida": _sim_numerica(_num(alvo.get("area_construida")), _num(candidato.get("area_construida")), 0.6),
        "padrao_construtivo": _sim_ordinal(alvo.get("padrao_construtivo"), candidato.get("padrao_construtivo"), ESCALA_PADRAO),
        "conservacao": _sim_ordinal(alvo.get("conservacao"), candidato.get("conservacao"), ESCALA_CONSERVACAO),
        "idade": _sim_numerica(_num(alvo.get("idade")), _num(candidato.get("idade")), 1.2),
        "programa": _sim_programa(alvo, candidato),
        "zoneamento": _sim_categorica(alvo.get("zoneamento"), candidato.get("zoneamento")),
    }

    # Similaridade territorial: usa o perfil da região do candidato, se houver
    territorial = similaridade_territorial(
        perfil_territorial_alvo, candidato.get("perfil_territorial")
    )
    criterios["similaridade_territorial"] = territorial["indice"] if territorial else None

    # Distância geográfica (km): 0 km = 1.0; decai até 30 km
    dist = _num(candidato.get("distancia_km"))
    criterios["distancia"] = max(0.0, 1.0 - dist / 30.0) if dist is not None else None

    # Soma ponderada com redistribuição de peso dos ausentes
    detalhamento: Dict[str, Dict[str, Any]] = {}
    ignorados: List[str] = []
    soma_peso = 0.0
    soma = 0.0
    for campo, valor in criterios.items():
        peso = PESOS[campo]
        if valor is None:
            ignorados.append(campo)
            continue
        soma += valor * peso
        soma_peso += peso
        detalhamento[campo] = {"similaridade_pct": round(valor * 100, 1), "peso": peso}

    if soma_peso == 0:
        score = 0.0
    else:
        score = soma / soma_peso
        # Peso efetivo de cada critério após redistribuição
        for campo in detalhamento:
            detalhamento[campo]["peso_efetivo"] = round(PESOS[campo] / soma_peso, 4)

    # Classificação de confiança
    pct = score * 100
    if pct >= 90:
        classe = "Excelente"
    elif pct >= 80:
        classe = "Boa"
    elif pct >= 65:
        classe = "Aceitável"
    else:
        classe = "Fraca"

    return {
        "similaridade_pct": round(pct, 1),
        "classe": classe,
        "detalhamento": detalhamento,
        "criterios_ignorados": ignorados,
        "cobertura_pct": round(soma_peso * 100, 1),  # quanto dos pesos foi avaliado
        "territorial": territorial,
    }


def ranquear_comparaveis(
    alvo: Dict[str, Any],
    candidatos: List[Dict[str, Any]],
    perfil_territorial_alvo: Optional[Dict[str, Any]] = None,
    minimo_similaridade: float = 0.0,
) -> Dict[str, Any]:
    """
    Pontua e ordena candidatos por similaridade (maior primeiro).

    Args:
        alvo: perfil técnico do imóvel de referência.
        candidatos: lista de imóveis encontrados (cada um pode ter
            'perfil_territorial', 'distancia_km', 'preco', 'fonte', etc.).
        perfil_territorial_alvo: perfil da região do imóvel de referência.
        minimo_similaridade: descarta candidatos abaixo deste % (0–100).

    Returns:
        {"comparaveis": [...ordenados...], "resumo": {...}}
    """
    resultados: List[Dict[str, Any]] = []
    for i, cand in enumerate(candidatos):
        score = pontuar_comparavel(alvo, cand, perfil_territorial_alvo)
        if score["similaridade_pct"] < minimo_similaridade:
            continue
        resultados.append({
            "indice": i,
            "identificacao": cand.get("identificacao") or cand.get("endereco") or f"Imóvel {i + 1}",
            "fonte": cand.get("fonte"),
            "preco": _num(cand.get("preco")),
            "area_terreno": _num(cand.get("area_terreno")),
            "area_construida": _num(cand.get("area_construida")),
            "bairro": cand.get("bairro"),
            "cidade": cand.get("cidade"),
            "data_anuncio": cand.get("data_anuncio"),
            **score,
        })

    resultados.sort(key=lambda r: r["similaridade_pct"], reverse=True)

    scores = [r["similaridade_pct"] for r in resultados]
    resumo = {
        "total_avaliados": len(candidatos),
        "total_aceitos": len(resultados),
        "similaridade_media": round(sum(scores) / len(scores), 1) if scores else 0.0,
        "excelentes": sum(1 for s in scores if s >= 90),
        "boas": sum(1 for s in scores if 80 <= s < 90),
        "aceitaveis": sum(1 for s in scores if 65 <= s < 80),
        "fracas": sum(1 for s in scores if s < 65),
    }

    # Orientação: nº de comparáveis para atingir graus da NBR (k variáveis)
    resumo["orientacao"] = (
        "Para a regressão, o grau III da NBR 14653 pede 6·(k+1) dados. "
        "Com 2 variáveis são 18 comparáveis; com 3, 24."
    )

    return {"status": "sucesso", "comparaveis": resultados, "resumo": resumo}
