"""
Comparable Property Search Engine — módulo independente.

Encontra imóveis semelhantes e entrega uma base de amostras qualificadas
para o motor de avaliação existente. NÃO estima valor.

Pipeline:
1. Filtros de qualidade (descarta anúncios inválidos/duplicados/fora da curva).
2. Filtro de similaridade nível 1 (bairro, cidade, tipologia, área ±20%, padrão).
3. Expansão inteligente em 6 níveis até atingir a meta de amostras.
4. Score de similaridade por imóvel + Similaridade Territorial Score.
5. Confiabilidade da busca.

A fonte dos anúncios é injetada (lista de candidatos ou provider plugável),
o que mantém o motor testável e independente de qualquer portal.
"""

import logging
import math
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

META_MINIMA = 15
META_MAXIMA = 30

# Similaridade Territorial Score — pesos definidos na especificação
PESOS_TERRITORIAL = {
    "idh": 0.20,
    "pib_per_capita": 0.20,
    "renda_media": 0.15,
    "densidade_populacional": 0.10,
    "populacao": 0.10,
    "distancia": 0.10,
    "preco_medio_m2": 0.15,
}

NIVEIS = [
    (1, "Mesmo bairro"),
    (2, "Bairros próximos"),
    (3, "Região administrativa"),
    (4, "Cidade inteira"),
    (5, "Região metropolitana"),
    (6, "Municípios com indicadores semelhantes"),
]

IDADE_MAXIMA_ANUNCIO_DIAS = 540  # ~18 meses


def _num(x: Any) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _sim_rel(a: Optional[float], b: Optional[float], tolerancia: float = 1.0) -> Optional[float]:
    """Similaridade 0–1 por diferença relativa."""
    if a is None or b is None:
        return None
    base = max(abs(a), abs(b))
    if base == 0:
        return 1.0
    return max(0.0, 1.0 - (abs(a - b) / base) / tolerancia)


# ---------------------------------------------------------------------------
# 1. Filtros de qualidade
# ---------------------------------------------------------------------------

def filtrar_qualidade(candidatos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Descarta anúncios inválidos:
    - sem metragem ou sem preço
    - duplicados (mesma fonte, ou mesmo endereço+preço)
    - preço/m² fora da curva (fora de 1,5×IQR)
    - anúncios muito antigos

    Returns:
        {"aceitos": [...], "descartados": [{"motivo":..., "imovel":...}]}
    """
    aceitos: List[Dict[str, Any]] = []
    descartados: List[Dict[str, Any]] = []
    vistos_fonte = set()
    vistos_chave = set()

    for c in candidatos:
        area = _num(c.get("area_construida")) or _num(c.get("area"))
        preco = _num(c.get("preco"))

        if not area or area <= 0:
            descartados.append({"motivo": "sem metragem", "imovel": c.get("identificacao")})
            continue
        if not preco or preco <= 0:
            descartados.append({"motivo": "sem preço", "imovel": c.get("identificacao")})
            continue

        fonte = (c.get("fonte") or "").strip().lower()
        if fonte and fonte in vistos_fonte:
            descartados.append({"motivo": "anúncio duplicado (mesma fonte)", "imovel": c.get("identificacao")})
            continue
        chave = f"{(c.get('endereco') or c.get('identificacao') or '').strip().lower()}|{round(preco)}"
        if chave in vistos_chave:
            descartados.append({"motivo": "anúncio duplicado", "imovel": c.get("identificacao")})
            continue

        idade_dias = _num(c.get("idade_anuncio_dias"))
        if idade_dias is not None and idade_dias > IDADE_MAXIMA_ANUNCIO_DIAS:
            descartados.append({"motivo": "anúncio muito antigo", "imovel": c.get("identificacao")})
            continue

        if fonte:
            vistos_fonte.add(fonte)
        vistos_chave.add(chave)
        item = dict(c)
        item["_area"] = area
        item["_preco"] = preco
        item["preco_m2"] = round(preco / area, 2)
        aceitos.append(item)

    # Outliers de preço/m² por IQR (só faz sentido com amostra razoável)
    if len(aceitos) >= 5:
        valores = sorted(a["preco_m2"] for a in aceitos)
        n = len(valores)
        q1 = valores[n // 4]
        q3 = valores[(3 * n) // 4]
        iqr = q3 - q1
        lim_inf, lim_sup = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        filtrados = []
        for a in aceitos:
            if a["preco_m2"] < lim_inf or a["preco_m2"] > lim_sup:
                descartados.append({
                    "motivo": f"preço/m² fora da curva (R$ {a['preco_m2']:.0f})",
                    "imovel": a.get("identificacao"),
                })
            else:
                filtrados.append(a)
        aceitos = filtrados

    return {"aceitos": aceitos, "descartados": descartados}


# ---------------------------------------------------------------------------
# 2. Similaridade Territorial Score (entre regiões)
# ---------------------------------------------------------------------------

def territorial_score(
    ind_alvo: Dict[str, Any],
    ind_cand: Dict[str, Any],
    distancia_km: Optional[float] = None,
    preco_m2_alvo: Optional[float] = None,
    preco_m2_cand: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Score 0–100 de similaridade entre duas localidades, com os pesos
    da especificação. Critérios sem dado são ignorados (peso redistribuído).
    """
    tolerancias = {
        "idh": 0.25, "pib_per_capita": 1.0, "renda_media": 1.0,
        "densidade_populacional": 1.5, "populacao": 2.0, "preco_medio_m2": 0.8,
    }
    detalhes: Dict[str, float] = {}
    soma = soma_peso = 0.0

    for campo in ("idh", "pib_per_capita", "renda_media", "densidade_populacional", "populacao"):
        s = _sim_rel(_num(ind_alvo.get(campo)), _num(ind_cand.get(campo)), tolerancias[campo])
        if s is None:
            continue
        detalhes[campo] = round(s * 100, 1)
        soma += s * PESOS_TERRITORIAL[campo]
        soma_peso += PESOS_TERRITORIAL[campo]

    if distancia_km is not None:
        s = max(0.0, 1.0 - _num(distancia_km) / 50.0)  # decai até 50 km
        detalhes["distancia"] = round(s * 100, 1)
        soma += s * PESOS_TERRITORIAL["distancia"]
        soma_peso += PESOS_TERRITORIAL["distancia"]

    s = _sim_rel(preco_m2_alvo, preco_m2_cand, tolerancias["preco_medio_m2"])
    if s is not None:
        detalhes["preco_medio_m2"] = round(s * 100, 1)
        soma += s * PESOS_TERRITORIAL["preco_medio_m2"]
        soma_peso += PESOS_TERRITORIAL["preco_medio_m2"]

    if soma_peso == 0:
        return {"score": None, "detalhes": {}}
    return {"score": round(soma / soma_peso * 100, 1), "detalhes": detalhes}


# ---------------------------------------------------------------------------
# 3. Similaridade imóvel × imóvel
# ---------------------------------------------------------------------------

def _score_imovel(alvo: Dict[str, Any], c: Dict[str, Any], territorial: Optional[float]) -> Dict[str, Any]:
    """Score de similaridade (localização, área, padrão, total)."""
    area_sim = _sim_rel(_num(alvo.get("area_construida")) or _num(alvo.get("area_terreno")),
                        c.get("_area"), 0.5)
    # padrão + programa
    padrao_igual = (str(alvo.get("padrao_construtivo") or "").lower() ==
                    str(c.get("padrao_construtivo") or "").lower())
    padrao_sim = 1.0 if padrao_igual and alvo.get("padrao_construtivo") else (
        0.6 if not c.get("padrao_construtivo") else 0.4)

    prog = []
    for campo in ("quartos", "banheiros", "vagas"):
        a, b = _num(alvo.get(campo)), _num(c.get(campo))
        if a is not None and b is not None:
            prog.append(max(0.0, 1.0 - abs(a - b) * 0.3))
    prog_sim = sum(prog) / len(prog) if prog else None

    mesmo_bairro = (str(alvo.get("bairro") or "").strip().lower() ==
                    str(c.get("bairro") or "").strip().lower() and alvo.get("bairro"))
    mesma_cidade = (str(alvo.get("cidade") or "").strip().lower() ==
                    str(c.get("cidade") or "").strip().lower() and alvo.get("cidade"))
    if territorial is not None:
        loc_sim = territorial / 100
    elif mesmo_bairro:
        loc_sim = 1.0
    elif mesma_cidade:
        loc_sim = 0.75
    else:
        loc_sim = 0.5

    partes = {"localizacao": loc_sim, "area": area_sim, "padrao": padrao_sim, "programa": prog_sim}
    pesos = {"localizacao": 0.35, "area": 0.35, "padrao": 0.15, "programa": 0.15}
    soma = soma_peso = 0.0
    detal: Dict[str, int] = {}
    for k, v in partes.items():
        if v is None:
            continue
        detal[k] = round(v * 100)
        soma += v * pesos[k]
        soma_peso += pesos[k]
    total = round(soma / soma_peso * 100) if soma_peso else 0
    detal["total"] = total
    return detal


# ---------------------------------------------------------------------------
# 4. Expansão inteligente
# ---------------------------------------------------------------------------

def _nivel_do_candidato(alvo: Dict[str, Any], c: Dict[str, Any], territorial: Optional[float]) -> int:
    """Classifica em qual nível de expansão o candidato entra."""
    mesmo_bairro = (str(alvo.get("bairro") or "").strip().lower() ==
                    str(c.get("bairro") or "").strip().lower() and alvo.get("bairro"))
    mesma_cidade = (str(alvo.get("cidade") or "").strip().lower() ==
                    str(c.get("cidade") or "").strip().lower() and alvo.get("cidade"))
    dist = _num(c.get("distancia_km"))

    if mesmo_bairro:
        return 1
    if mesma_cidade and dist is not None and dist <= 3:
        return 2
    if mesma_cidade and dist is not None and dist <= 8:
        return 3
    if mesma_cidade:
        return 4
    if dist is not None and dist <= 60:
        return 5
    return 6  # outra praça, entra por similaridade de indicadores


def _passa_nivel1(alvo: Dict[str, Any], c: Dict[str, Any]) -> bool:
    """Critérios rígidos do nível 1: tipologia igual e área ±20%."""
    tipo_a = str(alvo.get("tipo") or alvo.get("tipo_imovel") or "").lower()
    tipo_c = str(c.get("tipo") or c.get("tipo_imovel") or "").lower()
    if tipo_a and tipo_c and tipo_a != tipo_c:
        return False
    area_a = _num(alvo.get("area_construida")) or _num(alvo.get("area_terreno"))
    if area_a and c.get("_area"):
        if not (area_a * 0.8 <= c["_area"] <= area_a * 1.2):
            return False
    return True


def buscar_comparaveis(
    alvo: Dict[str, Any],
    candidatos: List[Dict[str, Any]],
    indicadores_alvo: Optional[Dict[str, Any]] = None,
    meta_minima: int = META_MINIMA,
    meta_maxima: int = META_MAXIMA,
    score_territorial_minimo: float = 85.0,
    provider: Optional[Callable[[Dict[str, Any], int], List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """
    Executa o pipeline completo e devolve as amostras qualificadas.

    Args:
        alvo: dados do imóvel de referência (tipo, áreas, quartos, bairro, cidade...).
        candidatos: anúncios disponíveis (do repositório/banco ou de um provider).
        indicadores_alvo: indicadores da região do alvo (Location Intelligence).
        provider: função opcional (alvo, nivel) -> candidatos extras, chamada
            durante a expansão quando ainda faltam amostras.
    """
    indicadores_alvo = indicadores_alvo or {}
    qualidade = filtrar_qualidade(candidatos)
    pool = qualidade["aceitos"]

    # preço/m² médio do alvo (se conhecido) para o score territorial
    preco_m2_alvo = _num(alvo.get("preco_m2_referencia"))

    # calcula territorial + score de cada candidato
    for c in pool:
        t = territorial_score(
            indicadores_alvo,
            c.get("indicadores") or {},
            distancia_km=_num(c.get("distancia_km")),
            preco_m2_alvo=preco_m2_alvo,
            preco_m2_cand=c.get("preco_m2"),
        )
        c["_territorial"] = t["score"]
        c["_territorial_detalhes"] = t["detalhes"]
        c["_nivel"] = _nivel_do_candidato(alvo, c, t["score"])
        c["_similaridade"] = _score_imovel(alvo, c, t["score"])
        c["_passa_n1"] = _passa_nivel1(alvo, c)

    selecionados: List[Dict[str, Any]] = []
    trilha: List[Dict[str, Any]] = []
    ids_sel = set()

    for nivel, nome in NIVEIS:
        if len(selecionados) >= meta_minima:
            trilha.append({"nivel": nivel, "descricao": nome, "executado": False,
                           "motivo": "meta já atingida", "encontrados": 0})
            continue

        # provider externo pode trazer mais candidatos neste nível
        if provider:
            try:
                extras = provider(alvo, nivel) or []
                if extras:
                    q = filtrar_qualidade(extras)
                    for c in q["aceitos"]:
                        t = territorial_score(indicadores_alvo, c.get("indicadores") or {},
                                              _num(c.get("distancia_km")), preco_m2_alvo, c.get("preco_m2"))
                        c["_territorial"] = t["score"]
                        c["_territorial_detalhes"] = t["detalhes"]
                        c["_nivel"] = _nivel_do_candidato(alvo, c, t["score"])
                        c["_similaridade"] = _score_imovel(alvo, c, t["score"])
                        c["_passa_n1"] = _passa_nivel1(alvo, c)
                        pool.append(c)
            except Exception as e:
                logger.warning("Provider falhou no nível %d: %s", nivel, e)

        # candidatos elegíveis neste nível
        elegiveis = []
        for i, c in enumerate(pool):
            if i in ids_sel or c["_nivel"] != nivel:
                continue
            if nivel == 1 and not c["_passa_n1"]:
                continue
            # níveis 5 e 6 exigem similaridade territorial alta
            if nivel >= 5:
                if c["_territorial"] is None or c["_territorial"] < score_territorial_minimo:
                    continue
            elegiveis.append((i, c))

        elegiveis.sort(key=lambda x: x[1]["_similaridade"]["total"], reverse=True)
        adicionados = 0
        for i, c in elegiveis:
            if len(selecionados) >= meta_maxima:
                break
            selecionados.append(c)
            ids_sel.add(i)
            adicionados += 1

        trilha.append({"nivel": nivel, "descricao": nome, "executado": True,
                       "encontrados": adicionados, "total_acumulado": len(selecionados)})

        if len(selecionados) >= meta_maxima:
            break

    selecionados.sort(key=lambda c: c["_similaridade"]["total"], reverse=True)

    # ---- Confiabilidade da busca (0–100) ----
    n = len(selecionados)
    fator_qtd = min(1.0, n / meta_minima)
    media_sim = (sum(c["_similaridade"]["total"] for c in selecionados) / n / 100) if n else 0.0
    nivel_max = max((c["_nivel"] for c in selecionados), default=6)
    fator_nivel = {1: 1.0, 2: 0.95, 3: 0.88, 4: 0.8, 5: 0.7, 6: 0.6}.get(nivel_max, 0.6)
    confiabilidade = round((fator_qtd * 0.4 + media_sim * 0.4 + fator_nivel * 0.2) * 100, 1)

    amostras = [{
        "endereco": c.get("endereco") or c.get("identificacao"),
        "identificacao": c.get("identificacao"),
        "preco": c["_preco"],
        "area": c["_area"],
        "area_terreno": _num(c.get("area_terreno")),
        "preco_m2": c["preco_m2"],
        "bairro": c.get("bairro"),
        "cidade": c.get("cidade"),
        "quartos": _num(c.get("quartos")),
        "banheiros": _num(c.get("banheiros")),
        "vagas": _num(c.get("vagas")),
        "fonte": c.get("fonte"),
        "nivel_expansao": c["_nivel"],
        "similaridade": c["_similaridade"],
        "score": c["_similaridade"]["total"],
        "territorial_score": c["_territorial"],
        "territorial_detalhes": c["_territorial_detalhes"],
    } for c in selecionados]

    suficiente = n >= meta_minima
    return {
        "status": "sucesso",
        "imovel_alvo": alvo,
        "amostras": amostras,
        "dados_regiao": indicadores_alvo,
        "confiabilidade_busca": confiabilidade,
        "resumo": {
            "total_candidatos": len(candidatos),
            "descartados_qualidade": len(qualidade["descartados"]),
            "amostras_qualificadas": n,
            "meta_minima": meta_minima,
            "suficiente_para_avaliacao": suficiente,
            "nivel_maximo_usado": nivel_max,
            "similaridade_media": round(media_sim * 100, 1),
        },
        "trilha_expansao": trilha,
        "descartados": qualidade["descartados"],
        "orientacao": (
            f"{n} amostras qualificadas — suficiente para a avaliação."
            if suficiente else
            f"Apenas {n} de {meta_minima} amostras. Amplie a busca ou cadastre "
            "mais comparáveis para atingir o grau desejado pela NBR 14653."
        ),
    }
