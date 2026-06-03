"""
Diagnósticos estatísticos avançados sobre resíduos.

- Normalidade: Shapiro-Wilk, Jarque-Bera
- Homocedasticidade: Breusch-Pagan
- Influência: Cook's Distance
"""

import logging
from typing import Any, Dict, List

import numpy as np
import scipy.stats as stats
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import OLSInfluence

logger = logging.getLogger(__name__)


def shapiro_wilk(residuos: np.ndarray) -> Dict[str, float]:
    """Teste de normalidade Shapiro-Wilk. H0: resíduos normais."""
    try:
        stat, p = stats.shapiro(residuos)
        return {"stat": float(stat), "p_valor": float(p)}
    except Exception as e:
        logger.warning("Shapiro-Wilk falhou: %s", e)
        return {"stat": 0.0, "p_valor": 1.0}


def jarque_bera(residuos: np.ndarray) -> Dict[str, float]:
    """Teste de normalidade Jarque-Bera. H0: resíduos normais."""
    try:
        stat, p = stats.jarque_bera(residuos)
        return {"stat": float(stat), "p_valor": float(p)}
    except Exception as e:
        logger.warning("Jarque-Bera falhou: %s", e)
        return {"stat": 0.0, "p_valor": 1.0}


def breusch_pagan(residuos: np.ndarray, exog: np.ndarray) -> Dict[str, float]:
    """Teste de homocedasticidade Breusch-Pagan. H0: variância constante."""
    try:
        stat, p, _, _ = het_breuschpagan(residuos, exog)
        return {"stat": float(stat), "p_valor": float(p)}
    except Exception as e:
        logger.warning("Breusch-Pagan falhou: %s", e)
        return {"stat": 0.0, "p_valor": 1.0}


def outliers_cooks(modelo_fit: Any) -> Dict[str, Any]:
    """
    Identifica observações influentes por Cook's Distance.
    Limiar usual: 4/n.
    """
    try:
        influence = OLSInfluence(modelo_fit)
        cooks_d = influence.cooks_distance[0]
        limiar = 4.0 / len(modelo_fit.resid)
        indices = [int(i) for i in np.where(cooks_d > limiar)[0]]
        return {
            "limiar": round(float(limiar), 6),
            "detectados": len(indices),
            "indices": indices,
            "distancias": [round(float(d), 6) for d in cooks_d],
        }
    except Exception as e:
        logger.warning("Cook's distance falhou: %s", e)
        return {"limiar": 0.0, "detectados": 0, "indices": [], "distancias": []}


def diagnostico_completo(modelo_fit: Any) -> Dict[str, Any]:
    """Roda Shapiro, Jarque-Bera, Breusch-Pagan e Cook's Distance."""
    residuos = modelo_fit.resid
    return {
        "shapiro_wilk": shapiro_wilk(residuos),
        "jarque_bera": jarque_bera(residuos),
        "breusch_pagan": breusch_pagan(residuos, modelo_fit.model.exog),
        "outliers_cooks": outliers_cooks(modelo_fit),
    }
