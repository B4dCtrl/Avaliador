"""
Validações NBR 14653-02 para laudos de avaliação imobiliária.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Limites NBR 14653-02
R2_MINIMO = 0.80
P_VALOR_SIGNIFICANCIA = 0.05
CORRELACAO_MULTICOLINEARIDADE = 0.95


def validar_nbr_14653(
    n_observacoes: int,
    n_variaveis: int,
    r_squared: float,
    p_valores_coefs: List[float],
    nomes_variaveis: List[str],
    matriz_correlacao: List[List[float]],
    nomes_correlacao: List[str],
    durbin_watson: float,
) -> Dict[str, Any]:
    """
    Valida os resultados da regressão conforme NBR 14653-02.

    Verificações realizadas:
    1. Número mínimo de observações: n ≥ 3*(p+1)
    2. R² recomendado ≥ 0.80
    3. Significância de todos os coeficientes (p < 0.05)
    4. Ausência de multicolinearidade severa (correlação > 0.95)
    5. Durbin-Watson entre 1.5 e 2.5

    Args:
        n_observacoes: Número de amostras.
        n_variaveis: Número de variáveis independentes.
        r_squared: R² do modelo.
        p_valores_coefs: Lista de p-valores dos coeficientes (sem intercepto).
        nomes_variaveis: Nomes das variáveis independentes.
        matriz_correlacao: Matriz de correlação como lista de listas.
        nomes_correlacao: Nomes das variáveis na matriz.
        durbin_watson: Estatística DW.

    Returns:
        Dicionário {'ok': bool, 'avisos': [...], 'erros': [...]}.
    """
    avisos: List[str] = []
    erros: List[str] = []

    # 1. Número mínimo de observações
    minimo_obs = 3 * (n_variaveis + 1)
    if n_observacoes < minimo_obs:
        erros.append(
            f"Número de observações insuficiente: {n_observacoes} amostras para "
            f"{n_variaveis} variável(is). NBR exige ≥ {minimo_obs}."
        )

    # 2. R²
    if r_squared < R2_MINIMO:
        avisos.append(
            f"R² = {r_squared:.4f} está abaixo do recomendado pela NBR 14653-02 (≥ {R2_MINIMO})."
        )

    # 3. Significância dos coeficientes
    for nome, p in zip(nomes_variaveis, p_valores_coefs):
        if p > P_VALOR_SIGNIFICANCIA:
            avisos.append(
                f"Variável '{nome}' não é significativa a 5% (p-valor = {p:.4f}). "
                "Considere remover ou revisar a transformação."
            )

    # 4. Multicolinearidade
    n = len(nomes_correlacao)
    for i in range(n):
        for j in range(i + 1, n):
            corr = abs(matriz_correlacao[i][j])
            if corr >= CORRELACAO_MULTICOLINEARIDADE:
                avisos.append(
                    f"Multicolinearidade severa entre '{nomes_correlacao[i]}' e "
                    f"'{nomes_correlacao[j]}': correlação = {corr:.4f} (≥ {CORRELACAO_MULTICOLINEARIDADE})."
                )

    # 5. Durbin-Watson
    if durbin_watson < 1.5:
        avisos.append(
            f"Durbin-Watson = {durbin_watson:.4f} indica autocorrelação positiva nos resíduos "
            "(valor ideal: 1.5 – 2.5)."
        )
    elif durbin_watson > 2.5:
        avisos.append(
            f"Durbin-Watson = {durbin_watson:.4f} indica autocorrelação negativa nos resíduos "
            "(valor ideal: 1.5 – 2.5)."
        )

    ok = len(erros) == 0
    logger.info("Validação NBR 14653-02: ok=%s, avisos=%d, erros=%d", ok, len(avisos), len(erros))

    return {"ok": ok, "avisos": avisos, "erros": erros}
