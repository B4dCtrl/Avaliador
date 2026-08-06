"""
Estrategista de busca — gera a estratégia a partir da ficha técnica do imóvel.

Camada 1 (sempre): regras determinísticas por tipo de imóvel. Roda offline,
é testável e previsível.
Camada 2 (opcional): refino por LLM, aplicado SOMENTE sobre campos textuais e
listas de critério. Números vindos do LLM são validados contra limites; se
saírem da faixa aceitável, o valor das regras prevalece.

Saída: JSON de estratégia consumido pelo Comparable Search Engine.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tabela de decisão por tipologia
# ---------------------------------------------------------------------------

# Para cada tipo: variáveis obrigatórias, flexíveis, raio inicial e tolerâncias.
REGRAS_TIPO: Dict[str, Dict[str, Any]] = {
    "terreno": {
        "obrigatorias": ["tipo", "area_terreno", "zoneamento"],
        "flexiveis": ["esquina", "topografia", "distancia_km", "padrao_construtivo"],
        "raio_inicial_m": 2000,
        "tolerancias": {"area_terreno": 0.30, "preco": 0.40},
        "justificativa": ("Terreno tem valor determinado por área, zoneamento e situação. "
                          "Padrão construtivo não se aplica."),
    },
    "casa": {
        "obrigatorias": ["tipo", "area_construida", "padrao_construtivo"],
        "flexiveis": ["area_terreno", "quartos", "vagas", "idade", "esquina"],
        "raio_inicial_m": 1500,
        "tolerancias": {"area_construida": 0.25, "area_terreno": 0.40, "preco": 0.40},
        "justificativa": ("Casa: área construída e padrão comandam o valor unitário; "
                          "terreno e programa são ajustáveis."),
    },
    "apartamento": {
        "obrigatorias": ["tipo", "area_construida", "quartos"],
        "flexiveis": ["vagas", "banheiros", "idade", "padrao_construtivo", "andar"],
        "raio_inicial_m": 1000,
        "tolerancias": {"area_construida": 0.20, "preco": 0.35},
        "justificativa": ("Apartamento: mercado é segmentado por área e nº de dormitórios; "
                          "raio menor porque o valor varia muito por microrregião."),
    },
    "comercial": {
        "obrigatorias": ["tipo", "area_construida", "zoneamento"],
        "flexiveis": ["area_terreno", "vagas", "idade", "padrao_construtivo"],
        "raio_inicial_m": 2500,
        "tolerancias": {"area_construida": 0.35, "preco": 0.50},
        "justificativa": ("Comercial: uso permitido (zoneamento) e área são decisivos; "
                          "mercado mais disperso exige raio maior."),
    },
    "rural": {
        "obrigatorias": ["tipo", "area_terreno"],
        "flexiveis": ["area_construida", "topografia", "distancia_km"],
        "raio_inicial_m": 20000,
        "tolerancias": {"area_terreno": 0.50, "preco": 0.60},
        "justificativa": "Rural: área é dominante e o mercado é regional, não de bairro.",
    },
}

REGRA_PADRAO = REGRAS_TIPO["casa"]

# Ordem fixa de expansão (espelha os níveis do Comparable Search Engine)
REGRAS_EXPANSAO: List[Dict[str, Any]] = [
    {"ordem": 1, "acao": "Buscar no mesmo bairro", "gatilho": "início",
     "justificativa": "Máxima homogeneidade de mercado."},
    {"ordem": 2, "acao": "Ampliar para bairros próximos (até 3 km)",
     "gatilho": "amostra < mínimo", "justificativa": "Mantém a mesma dinâmica urbana."},
    {"ordem": 3, "acao": "Ampliar para a região administrativa (até 8 km)",
     "gatilho": "amostra < mínimo", "justificativa": "Preserva perfil socioeconômico."},
    {"ordem": 4, "acao": "Buscar na cidade inteira", "gatilho": "amostra < mínimo",
     "justificativa": "Mesmo município: mesma legislação e mercado."},
    {"ordem": 5, "acao": "Flexibilizar variáveis não obrigatórias",
     "gatilho": "amostra < mínimo após cidade",
     "justificativa": "Relaxa critérios secundários antes de trocar de praça."},
    {"ordem": 6, "acao": "Buscar municípios com indicadores semelhantes (score territorial > 85)",
     "gatilho": "amostra < mínimo após flexibilizar",
     "justificativa": "Comparar mercados equivalentes, não apenas vizinhos."},
]

# Limites de sanidade para valores que o LLM eventualmente proponha
LIMITES = {
    "raio_inicial_m": (200, 100000),
    "tolerancia": (0.05, 1.0),
    "meta_minima": (5, 60),
}


def _norm_tipo(tipo: Optional[str]) -> str:
    t = (tipo or "").strip().lower()
    if t in REGRAS_TIPO:
        return t
    if t in ("sobrado", "residencial"):
        return "casa"
    if t in ("apto", "flat", "kitnet"):
        return "apartamento"
    if t in ("loja", "sala", "galpao", "galpão", "industrial"):
        return "comercial"
    if t in ("sitio", "sítio", "chacara", "chácara", "fazenda"):
        return "rural"
    return "casa"


def _preenchidas(ficha: Dict[str, Any], campos: List[str]) -> List[str]:
    """Mantém só os campos que a ficha realmente informou."""
    out = []
    for c in campos:
        v = ficha.get(c)
        if v not in (None, "", 0):
            out.append(c)
    return out


def gerar_estrategia(
    ficha: Dict[str, Any],
    meta_minima: int = 15,
    refinador_llm: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Gera a estratégia de busca a partir da ficha técnica.

    Args:
        ficha: dados do imóvel avaliando.
        meta_minima: nº mínimo de amostras desejado.
        refinador_llm: função opcional (ficha, estrategia) -> estrategia refinada.
            Só é aplicada em campos permitidos e passa por validação.

    Returns:
        JSON de estratégia, com `origem` indicando as camadas aplicadas.
    """
    tipo = _norm_tipo(ficha.get("tipo") or ficha.get("tipo_imovel"))
    regra = REGRAS_TIPO.get(tipo, REGRA_PADRAO)

    obrigatorias = _preenchidas(ficha, regra["obrigatorias"])
    flexiveis = _preenchidas(ficha, regra["flexiveis"])

    avisos: List[str] = []
    faltando = [c for c in regra["obrigatorias"] if c not in obrigatorias]
    if faltando:
        avisos.append(
            f"Ficha não informou variável(is) obrigatória(s) para {tipo}: {', '.join(faltando)}. "
            "A comparabilidade fica mais fraca."
        )

    # Raio: ajusta pela área quando informada (imóvel grande, mercado mais disperso)
    raio = regra["raio_inicial_m"]
    area = ficha.get("area_terreno") or ficha.get("area_construida")
    try:
        area = float(area) if area else None
    except (TypeError, ValueError):
        area = None
    if area and area > 1000 and tipo != "rural":
        raio = int(raio * 1.5)
        avisos.append("Área acima de 1.000 m²: raio ampliado em 50% (mercado mais escasso).")

    estrategia: Dict[str, Any] = {
        "imovel_avaliando": {k: v for k, v in ficha.items() if v not in (None, "")},
        "tipo_normalizado": tipo,
        "criterios_obrigatorios": obrigatorias,
        "criterios_flexiveis": flexiveis,
        "raio_inicial_metros": raio,
        "tolerancias": dict(regra["tolerancias"]),
        "meta_minima_amostras": meta_minima,
        "meta_maxima_amostras": max(meta_minima * 2, 30),
        "score_territorial_minimo": 85.0,
        "regras_expansao": [dict(r) for r in REGRAS_EXPANSAO],
        "justificativa_tipologia": regra["justificativa"],
        "avisos": avisos,
        "origem": ["regras"],
    }

    if refinador_llm:
        try:
            proposta = refinador_llm(ficha, estrategia) or {}
            estrategia = aplicar_refino(estrategia, proposta)
        except Exception as e:
            logger.warning("Refino por LLM falhou, mantendo regras: %s", e)
            estrategia.setdefault("avisos", []).append(
                "Refino por IA indisponível; estratégia gerada apenas por regras."
            )

    return estrategia


# Campos que o LLM pode alterar. Qualquer outro é ignorado.
CAMPOS_REFINAVEIS = {
    "criterios_obrigatorios", "criterios_flexiveis", "raio_inicial_metros",
    "tolerancias", "justificativa_tipologia", "observacoes_ia",
}


def aplicar_refino(base: Dict[str, Any], proposta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica o refino do LLM sobre a estratégia de regras, com validação.

    - Ignora campos fora de CAMPOS_REFINAVEIS.
    - Números fora dos limites de sanidade são descartados (regra prevalece).
    - Critérios propostos precisam existir na ficha (não inventa variável).
    """
    out = dict(base)
    aplicados: List[str] = []
    rejeitados: List[str] = []
    campos_ficha = set(base.get("imovel_avaliando", {}).keys())

    for chave, valor in (proposta or {}).items():
        if chave not in CAMPOS_REFINAVEIS:
            rejeitados.append(f"{chave} (campo não refinável)")
            continue

        if chave in ("criterios_obrigatorios", "criterios_flexiveis"):
            if not isinstance(valor, list):
                rejeitados.append(f"{chave} (não é lista)")
                continue
            validos = [c for c in valor if c in campos_ficha]
            invalidos = [c for c in valor if c not in campos_ficha]
            if invalidos:
                rejeitados.append(f"{chave}: variáveis inexistentes na ficha {invalidos}")
            if validos:
                out[chave] = validos
                aplicados.append(chave)
            continue

        if chave == "raio_inicial_metros":
            try:
                v = float(valor)
            except (TypeError, ValueError):
                rejeitados.append("raio_inicial_metros (não numérico)")
                continue
            lo, hi = LIMITES["raio_inicial_m"]
            if lo <= v <= hi:
                out[chave] = int(v)
                aplicados.append(chave)
            else:
                rejeitados.append(f"raio_inicial_metros={v} fora de [{lo}, {hi}]")
            continue

        if chave == "tolerancias":
            if not isinstance(valor, dict):
                rejeitados.append("tolerancias (não é objeto)")
                continue
            lo, hi = LIMITES["tolerancia"]
            novas = dict(out.get("tolerancias", {}))
            for k, v in valor.items():
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    rejeitados.append(f"tolerancia {k} (não numérica)")
                    continue
                if lo <= fv <= hi:
                    novas[k] = fv
                else:
                    rejeitados.append(f"tolerancia {k}={fv} fora de [{lo}, {hi}]")
            out["tolerancias"] = novas
            aplicados.append("tolerancias")
            continue

        # textos livres
        out[chave] = str(valor)
        aplicados.append(chave)

    out["origem"] = list(base.get("origem", [])) + ["llm"]
    out["refino_ia"] = {"aplicados": aplicados, "rejeitados": rejeitados}
    return out
