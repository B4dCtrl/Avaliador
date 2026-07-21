"""
Critérios da NBR 14653-2:2011 para modelos de regressão linear:

- Grau de Fundamentação (Tabela 1/2) — itens quantificáveis:
    item 2: quantidade mínima de dados de mercado efetivamente utilizados
            III: n ≥ 6(k+1) | II: n ≥ 4(k+1) | I: n ≥ 3(k+1)
    item 5: nível de significância máximo dos regressores (teste t bicaudal)
            III: 10% | II: 20% | I: 30%
    item 6: significância do modelo (teste F)
            III: 1% | II: 2% | I: 5%
  Itens qualitativos (caracterização do imóvel, identificação dos dados,
  extrapolação) são de responsabilidade do avaliador e não são pontuados aqui.

- Grau de Precisão (Tabela 5) — amplitude do intervalo de confiança de 80%
  em torno da estimativa central:
            III: ≤ 30% | II: ≤ 40% | I: ≤ 50%

- Campo de Arbítrio (NBR 14653-1): intervalo de ±15% em torno da
  estimativa pontual (valor fixo, independente do grau).

- Micronumerosidade: nº mínimo de dados com mesma característica
  (aplicável a variáveis com poucos valores distintos, ex.: dicotômicas):
            n ≤ 30 → 3 | 30 < n ≤ 100 → 10% de n | n > 100 → 10
"""

import math
from typing import Any, Dict, List, Optional, Tuple

CAMPO_ARBITRIO_PCT = 0.15  # ±15% — NBR 14653-1


# ---------------------------------------------------------------------------
# Amplitude e Grau de Precisão
# ---------------------------------------------------------------------------

def amplitude_pct(y_hat: float, y_lwr: float, y_upr: float) -> float:
    """Amplitude percentual do intervalo em torno da estimativa central."""
    if y_hat == 0:
        return 0.0
    return abs((y_upr - y_lwr) / y_hat) * 100.0


def grau_precisao(amp: float) -> str:
    """
    Grau de precisão (NBR 14653-2, Tabela 5) pela amplitude do IC de 80%:
    III ≤ 30% | II ≤ 40% | I ≤ 50%.
    """
    if amp <= 30:
        return "III"
    if amp <= 40:
        return "II"
    if amp <= 50:
        return "I"
    return "Fora dos critérios"


# ---------------------------------------------------------------------------
# Campo de Arbítrio (±15% fixo)
# ---------------------------------------------------------------------------

def campo_arbitrio(y_hat: float, grau: str = "") -> Tuple[float, float]:
    """
    Campo de arbítrio: ±15% em torno da estimativa pontual (NBR 14653-1).
    O parâmetro `grau` é aceito por compatibilidade e ignorado.
    """
    return y_hat * (1 - CAMPO_ARBITRIO_PCT), y_hat * (1 + CAMPO_ARBITRIO_PCT)


# ---------------------------------------------------------------------------
# Grau de Fundamentação (itens quantificáveis 2, 5 e 6)
# ---------------------------------------------------------------------------

def _grau_item_quantidade(n: int, k: int) -> int:
    """Item 2 — quantidade de dados: retorna 3, 2, 1 ou 0 (fora)."""
    if n >= 6 * (k + 1):
        return 3
    if n >= 4 * (k + 1):
        return 2
    if n >= 3 * (k + 1):
        return 1
    return 0


def _grau_item_significancia_t(max_p: float) -> int:
    """Item 5 — significância máxima dos regressores (t bicaudal)."""
    if max_p <= 0.10:
        return 3
    if max_p <= 0.20:
        return 2
    if max_p <= 0.30:
        return 1
    return 0


def _grau_item_significancia_f(p_f: float) -> int:
    """Item 6 — significância do modelo (F)."""
    if p_f <= 0.01:
        return 3
    if p_f <= 0.02:
        return 2
    if p_f <= 0.05:
        return 1
    return 0


_ROMANO = {3: "III", 2: "II", 1: "I", 0: "Fora dos critérios"}


def avaliar_grau_fundamentacao(
    amp: Optional[float],
    p_valores_coefs: List[float],
    p_valor_f: float,
    n: int,
    k: int,
) -> Dict[str, Any]:
    """
    Avalia os itens quantificáveis do grau de fundamentação.

    O grau final informado é o MENOR grau entre os itens computados
    (critério conservador — a norma exige que itens essenciais atinjam
    o grau pretendido). Itens qualitativos ficam a cargo do avaliador.
    """
    max_p = max(p_valores_coefs) if p_valores_coefs else 1.0

    g_qtd = _grau_item_quantidade(n, k)
    g_t = _grau_item_significancia_t(max_p)
    g_f = _grau_item_significancia_f(p_valor_f)

    grau_final = min(g_qtd, g_t, g_f)
    pontos = g_qtd + g_t + g_f

    return {
        "grau": _ROMANO[grau_final],
        "pontos_itens_quantificaveis": pontos,
        "itens": {
            "quantidade_dados": {
                "grau": _ROMANO[g_qtd],
                "n": n,
                "exigido_III": 6 * (k + 1),
                "exigido_II": 4 * (k + 1),
                "exigido_I": 3 * (k + 1),
            },
            "significancia_regressores": {
                "grau": _ROMANO[g_t],
                "max_p_valor": round(max_p, 4),
                "limites": {"III": 0.10, "II": 0.20, "I": 0.30},
            },
            "significancia_modelo_f": {
                "grau": _ROMANO[g_f],
                "p_valor_f": round(p_valor_f, 6),
                "limites": {"III": 0.01, "II": 0.02, "I": 0.05},
            },
        },
        "amplitude_pct": round(amp, 2) if amp is not None else None,
        "max_p_valor_coef": round(max_p, 4),
        "p_valor_f": round(p_valor_f, 6),
        "n_observacoes": n,
        "n_variaveis": k,
        "observacao": (
            "Itens qualitativos (caracterização do imóvel, identificação dos dados, "
            "extrapolação) devem ser verificados pelo responsável técnico."
        ),
    }


# Compatibilidade com chamadas antigas
def grau_fundamentacao(
    amp: float, max_p_valor_coef: float, p_valor_f: float,
    n_observacoes: int, n_variaveis: int,
) -> str:
    return avaliar_grau_fundamentacao(
        amp, [max_p_valor_coef], p_valor_f, n_observacoes, n_variaveis
    )["grau"]


def significancia_label(p_valor: float) -> str:
    """Estrelas de significância conforme convenção usual."""
    if p_valor <= 0.10:
        return "***"
    if p_valor <= 0.20:
        return "**"
    if p_valor <= 0.30:
        return "*"
    return ""


# ---------------------------------------------------------------------------
# Micronumerosidade
# ---------------------------------------------------------------------------

def minimo_por_caracteristica(n: int) -> int:
    """Nº mínimo de dados com mesma característica (NBR 14653-2)."""
    if n <= 30:
        return 3
    if n <= 100:
        return math.ceil(0.10 * n)
    return 10


def verificar_micronumerosidade(
    valores_por_variavel: Dict[str, List[float]],
    max_niveis_qualitativa: int = 6,
) -> Dict[str, Any]:
    """
    Verifica micronumerosidade nas variáveis de poucos valores distintos
    (tratadas como qualitativas/dicotômicas, ex.: nº de garagens, padrão).

    Para cada nível dessas variáveis, o nº de dados deve ser ≥ mínimo
    da norma. Variáveis contínuas (muitos valores distintos) são ignoradas.

    Returns:
        {"ok": bool, "avisos": [...], "detalhes": {...}}
    """
    avisos: List[str] = []
    detalhes: Dict[str, Any] = {}

    for nome, valores in valores_por_variavel.items():
        n = len(valores)
        minimo = minimo_por_caracteristica(n)
        distintos: Dict[float, int] = {}
        for v in valores:
            distintos[v] = distintos.get(v, 0) + 1

        if len(distintos) > max_niveis_qualitativa:
            continue  # variável contínua — regra não se aplica

        niveis_ruins = {
            str(nivel): cont for nivel, cont in distintos.items() if cont < minimo
        }
        detalhes[nome] = {
            "niveis": {str(k): v for k, v in distintos.items()},
            "minimo_exigido": minimo,
            "ok": not niveis_ruins,
        }
        if niveis_ruins:
            desc = ", ".join(f"{niv} ({cont} dado(s))" for niv, cont in niveis_ruins.items())
            avisos.append(
                f"Micronumerosidade na variável '{nome}': os níveis {desc} têm menos "
                f"que o mínimo de {minimo} dados exigido pela NBR 14653-2."
            )

    return {"ok": not avisos, "avisos": avisos, "detalhes": detalhes}
