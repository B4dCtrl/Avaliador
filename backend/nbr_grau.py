"""
Critérios complementares NBR 14653-02:
- Amplitude do intervalo de predição
- Grau de Precisão (I, II, III)
- Campo de Arbítrio
- Grau de Fundamentação
"""

from typing import Optional, Tuple


def amplitude_pct(y_hat: float, y_lwr: float, y_upr: float) -> float:
    """
    Amplitude percentual do intervalo de predição.
    Quanto menor, mais preciso é o modelo.
    """
    if y_hat == 0:
        return 0.0
    return ((y_upr - y_lwr) / abs(y_hat)) * 100.0


def grau_precisao(amp: float) -> str:
    """
    Grau de precisão pela NBR 14653-02 baseado na amplitude:
    - III: amp ≤ 30%
    - II:  30% < amp ≤ 40%
    - I:   40% < amp ≤ 50%
    - Fora dos critérios: amp > 50%
    """
    if amp <= 30:
        return "III"
    if amp <= 40:
        return "II"
    if amp <= 50:
        return "I"
    return "Fora dos critérios"


def campo_arbitrio(y_hat: float, grau: str) -> Tuple[float, float]:
    """
    Campo de arbítrio do avaliador. Percentuais:
    - III: ±15%
    - II:  ±20%
    - I:   ±25%
    """
    pct = {"III": 0.15, "II": 0.20, "I": 0.25}.get(grau, 0.25)
    return y_hat * (1 - pct), y_hat * (1 + pct)


def grau_fundamentacao(
    amp: float,
    max_p_valor_coef: float,
    p_valor_f: float,
    n_observacoes: int,
    n_variaveis: int,
) -> str:
    """
    Grau de fundamentação combinando amplitude, significância e nº de amostras.
    """
    k = n_variaveis
    n_min_iii = 6 * (k + 1)
    n_min_ii = 5 * (k + 1)
    n_min_i = 4 * (k + 1)

    if amp <= 30 and max_p_valor_coef <= 0.10 and p_valor_f <= 0.01 and n_observacoes >= n_min_iii:
        return "III"
    if amp <= 40 and max_p_valor_coef <= 0.20 and p_valor_f <= 0.01 and n_observacoes >= n_min_ii:
        return "II"
    if amp <= 50 and max_p_valor_coef <= 0.30 and p_valor_f <= 0.05 and n_observacoes >= n_min_i:
        return "I"
    return "Fora dos critérios"


def significancia_label(p_valor: float) -> str:
    """Estrelas de significância conforme convenção NBR."""
    if p_valor <= 0.10:
        return "***"
    if p_valor <= 0.20:
        return "**"
    if p_valor <= 0.30:
        return "*"
    return ""


def avaliar_grau_fundamentacao(
    amp: Optional[float],
    p_valores_coefs: list,
    p_valor_f: float,
    n: int,
    k: int,
) -> dict:
    """Retorna grau + checklist completo de critérios NBR."""
    max_p = max(p_valores_coefs) if p_valores_coefs else 1.0
    grau = grau_fundamentacao(amp or 100.0, max_p, p_valor_f, n, k)
    return {
        "grau": grau,
        "amplitude_pct": round(amp, 2) if amp is not None else None,
        "max_p_valor_coef": round(max_p, 4),
        "p_valor_f": round(p_valor_f, 6),
        "n_observacoes": n,
        "n_variaveis": k,
    }
