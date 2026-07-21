"""
Auto-ranking de modelos: testa combinações de transformações
em todas as variáveis (dep + indep) e ranqueia por AIC, BIC e R²-ajustado.

Inspirado no `appraiseR::bestfit()`.
"""

import logging
from itertools import product
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm

from calculadora import normalizar_transformacao, transformar_variavel

logger = logging.getLogger(__name__)

# Conjunto padrão de transformações testadas
TRANSF_PADRAO = ["nenhuma", "log", "raiz_quadrada", "raiz_reciproca"]


def _aplicar_seguro(valores: np.ndarray, transformacao: str) -> Optional[np.ndarray]:
    """Aplica transformação retornando None se inválida (≤0 em log/raiz/recíproca)."""
    try:
        return transformar_variavel(valores.tolist(), transformacao)
    except ValueError:
        return None


def bestfit(
    df: pd.DataFrame,
    y_name: str,
    x_names: List[str],
    transformacoes: List[str] = None,
    excluir_indices: List[int] = None,
    top_n: int = 20,
) -> List[Dict[str, Any]]:
    """
    Testa combinações cartesianas de transformações e retorna ranking.

    Args:
        df: DataFrame com colunas y + x.
        y_name: Nome da variável dependente.
        x_names: Lista de variáveis independentes.
        transformacoes: Quais transformações testar (canônicas).
        excluir_indices: Índices a excluir (outliers).
        top_n: Quantidade máxima a retornar no ranking.

    Returns:
        Lista de dicts ordenada por AIC crescente.
    """
    if transformacoes is None:
        transformacoes = TRANSF_PADRAO
    transformacoes = [normalizar_transformacao(t) for t in transformacoes]
    if "nenhuma" not in transformacoes:
        transformacoes = ["nenhuma"] + transformacoes

    data = df.copy()
    if excluir_indices:
        data = data.drop(index=[i for i in excluir_indices if i in data.index])

    var_names = [y_name] + x_names
    combos = list(product(transformacoes, repeat=len(var_names)))
    logger.info("Testando %d combinações de transformação", len(combos))

    results: List[Dict[str, Any]] = []
    for combo in combos:
        try:
            transformado = pd.DataFrame(index=data.index)
            valido = True

            for i, var in enumerate(var_names):
                col = data[var].values.astype(float)
                t_aplicada = _aplicar_seguro(col, combo[i])
                if t_aplicada is None:
                    valido = False
                    break
                if np.any(np.isinf(t_aplicada)) or np.all(np.isnan(t_aplicada)):
                    valido = False
                    break
                transformado[var] = t_aplicada

            if not valido:
                continue

            transformado = transformado.replace([np.inf, -np.inf], np.nan).dropna()
            if len(transformado) < len(x_names) + 2:
                continue

            y = transformado[y_name]
            X = sm.add_constant(transformado[x_names], has_constant="add")
            modelo = sm.OLS(y, X).fit()

            # p-valor máximo dos regressores (sem intercepto) — dá o grau t do modelo
            pvals_indep = [
                float(modelo.pvalues[c]) for c in modelo.params.index if c != "const"
            ]
            max_p = max(pvals_indep) if pvals_indep else 1.0

            results.append({
                "id": len(results) + 1,
                "transformacoes": {var: combo[i] for i, var in enumerate(var_names)},
                "r2": round(float(modelo.rsquared), 6),
                "r2_ajustado": round(float(modelo.rsquared_adj), 6),
                "f_stat": round(float(modelo.fvalue), 4),
                "f_p_valor": round(float(modelo.f_pvalue), 8),
                "aic": round(float(modelo.aic), 4),
                "bic": round(float(modelo.bic), 4),
                "max_p_valor": round(max_p, 4),
                "_modelo": modelo,
                "_dados_usados": transformado,
            })
        except Exception:
            continue

    results.sort(key=lambda r: r["aic"])
    logger.info("Modelos válidos: %d", len(results))
    return results[:top_n] if top_n else results


def serializar_ranking(ranking: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove campos internos (_modelo, _dados_usados) para retorno JSON."""
    return [
        {k: v for k, v in r.items() if not k.startswith("_")}
        for r in ranking
    ]
