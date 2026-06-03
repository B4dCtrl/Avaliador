"""
Módulo de cálculos estatísticos do Avaliador.

Implementa regressão linear OLS, 7 transformações de variáveis,
elasticidade, Durbin-Watson, outliers e dados para gráficos.
Referência: https://lfpdroubi.github.io/appraiseR/
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Transformações (7 tipos obrigatórios)
# ---------------------------------------------------------------------------

def transformar_variavel(valores: List[float], tipo_transformacao: str) -> np.ndarray:
    """
    Aplica uma das 7 transformações de variável.

    Args:
        valores: Lista de valores originais.
        tipo_transformacao: Uma de ['nenhuma', 'raiz_reciproca', 'log',
            'raiz_quadrada', 'reciproca', 'reciproca_quadrada', 'quadrada'].

    Returns:
        Array numpy com os valores transformados.

    Raises:
        ValueError: Se os valores forem inválidos para a transformação escolhida.
    """
    x = np.array(valores, dtype=float)

    if tipo_transformacao == "nenhuma":
        return x

    if tipo_transformacao == "log":
        if np.any(x <= 0):
            raise ValueError("Transformação ln(x) exige todos os valores > 0.")
        return np.log(x)

    if tipo_transformacao == "raiz_quadrada":
        if np.any(x < 0):
            raise ValueError("Transformação √x exige todos os valores ≥ 0.")
        return np.sqrt(x)

    if tipo_transformacao == "raiz_reciproca":
        if np.any(x <= 0):
            raise ValueError("Transformação 1/√x exige todos os valores > 0.")
        return 1.0 / np.sqrt(x)

    if tipo_transformacao == "reciproca":
        if np.any(x == 0):
            raise ValueError("Transformação 1/x exige todos os valores ≠ 0.")
        return 1.0 / x

    if tipo_transformacao == "reciproca_quadrada":
        if np.any(x == 0):
            raise ValueError("Transformação 1/x² exige todos os valores ≠ 0.")
        return 1.0 / (x ** 2)

    if tipo_transformacao == "quadrada":
        return x ** 2

    raise ValueError(f"Transformação desconhecida: {tipo_transformacao}")


def aplicar_transformacoes(dados_dict: Dict[str, Any]) -> Tuple[np.ndarray, List[str]]:
    """
    Aplica as transformações a todas as variáveis independentes.

    Args:
        dados_dict: Dicionário com 'variaveis_independentes' (nome → {valores, transformacao}).

    Returns:
        Tupla (X_transformado, nomes_colunas).
    """
    colunas = []
    nomes = []
    for nome, info in dados_dict.items():
        transformado = transformar_variavel(info["valores"], info["transformacao"])
        colunas.append(transformado)
        nomes.append(nome)
    X = np.column_stack(colunas) if len(colunas) > 1 else colunas[0].reshape(-1, 1)
    return X, nomes


# ---------------------------------------------------------------------------
# Regressão OLS
# ---------------------------------------------------------------------------

def calcular_regressao(
    y: np.ndarray, X: np.ndarray
) -> Any:
    """
    Executa regressão linear OLS usando statsmodels.

    Args:
        y: Variável dependente.
        X: Matriz de variáveis independentes (sem constante).

    Returns:
        Objeto RegressionResultsWrapper do statsmodels.
    """
    X_const = sm.add_constant(X)
    modelo = sm.OLS(y, X_const)
    resultado = modelo.fit()
    logger.info(
        "Regressão calculada: R²=%.4f, F=%.2f, n=%d",
        resultado.rsquared,
        resultado.fvalue,
        int(resultado.nobs),
    )
    return resultado


# ---------------------------------------------------------------------------
# Elasticidade
# ---------------------------------------------------------------------------

def calcular_elasticidade(
    coef: float,
    tipo_transformacao: str,
    media_x: float,
    media_y: float,
    media_x_orig: Optional[float] = None,
) -> float:
    """
    Calcula a elasticidade do coeficiente no ponto médio.

    Fórmulas:
    - nenhuma (linear): e = coef * (media_x / media_y)
    - log: e = coef  (elasticidade direta)
    - demais: derivada da transformação no ponto médio * (media_x_orig / media_y)

    Args:
        coef: Coeficiente estimado.
        tipo_transformacao: Tipo de transformação aplicada.
        media_x: Média da variável transformada.
        media_y: Média da variável dependente.
        media_x_orig: Média da variável original (necessária para derivadas).

    Returns:
        Valor da elasticidade.
    """
    if media_y == 0:
        return 0.0

    if tipo_transformacao == "nenhuma":
        return coef * (media_x / media_y)

    if tipo_transformacao == "log":
        return coef

    # Para as demais, calcular derivada de f(x) em relação a x_orig no ponto médio
    mx = media_x_orig if media_x_orig is not None else media_x
    if mx == 0:
        return 0.0

    derivadas = {
        "raiz_quadrada":     0.5 / np.sqrt(abs(mx)) if mx > 0 else 0.0,
        "raiz_reciproca":   -0.5 / (abs(mx) ** 1.5) if mx > 0 else 0.0,
        "reciproca":        -1.0 / (mx ** 2),
        "reciproca_quadrada": -2.0 / (mx ** 3),
        "quadrada":          2.0 * mx,
    }
    derivada = derivadas.get(tipo_transformacao, 0.0)
    return coef * derivada * (mx / media_y)


# ---------------------------------------------------------------------------
# Durbin-Watson
# ---------------------------------------------------------------------------

def calcular_durbin_watson(residuos: np.ndarray) -> float:
    """
    Calcula a estatística de Durbin-Watson para autocorrelação de resíduos.

    Valor ideal entre 1.5 e 2.5.

    Args:
        residuos: Array de resíduos da regressão.

    Returns:
        Estatística DW (float entre 0 e 4).
    """
    dw = float(durbin_watson(residuos))
    logger.debug("Durbin-Watson: %.4f", dw)
    return dw


# ---------------------------------------------------------------------------
# Outliers
# ---------------------------------------------------------------------------

def detectar_outliers(residuos: np.ndarray, limiar: float = 2.0) -> Dict[str, Any]:
    """
    Detecta outliers pelos resíduos padronizados.

    Um ponto é outlier se |resíduo padronizado| > limiar (padrão: 2σ).

    Args:
        residuos: Array de resíduos.
        limiar: Limiar em desvios-padrão.

    Returns:
        Dicionário com detectados, percentual, indices e residuos_standardizados.
    """
    desvio = np.std(residuos, ddof=1)
    if desvio == 0:
        padronizados = np.zeros_like(residuos)
    else:
        padronizados = residuos / desvio

    indices_outliers = [int(i) for i in np.where(np.abs(padronizados) > limiar)[0]]
    n = len(residuos)
    percentual = len(indices_outliers) / n * 100 if n > 0 else 0.0

    logger.debug("Outliers detectados: %d de %d (%.1f%%)", len(indices_outliers), n, percentual)

    return {
        "detectados": len(indices_outliers),
        "percentual": round(percentual, 2),
        "indices": indices_outliers,
        "residuos_standardizados": [round(float(r), 4) for r in padronizados],
    }


# ---------------------------------------------------------------------------
# Matriz de correlação
# ---------------------------------------------------------------------------

def correlacao_matrix(dados: Dict[str, List[float]]) -> Dict[str, Any]:
    """
    Calcula a matriz de correlação de Pearson entre todas as variáveis.

    Args:
        dados: Dicionário {nome_variavel: [valores]}.

    Returns:
        Dicionário com 'variaveis' (lista de nomes) e 'dados' (matriz como lista de listas).
    """
    df = pd.DataFrame(dados)
    matriz = df.corr(method="pearson").round(4)
    return {
        "variaveis": list(matriz.columns),
        "dados": matriz.values.tolist(),
    }


# ---------------------------------------------------------------------------
# Dados para gráficos (Plotly-ready)
# ---------------------------------------------------------------------------

def preparar_dados_graficos(
    y: np.ndarray,
    X: np.ndarray,
    modelo_fit: Any,
    nomes_variaveis: List[str],
    valores_originais: Dict[str, List[float]],
) -> Dict[str, Any]:
    """
    Prepara todos os dados necessários para renderização de gráficos no frontend.

    Inclui:
    - Resíduos vs. preditos
    - Q-Q plot dos resíduos
    - Scatter por variável com reta de regressão

    Args:
        y: Variável dependente original.
        X: Matriz de variáveis independentes (transformadas, sem constante).
        modelo_fit: Resultado do OLS.
        nomes_variaveis: Nomes das colunas de X.
        valores_originais: Dicionário {nome: [valores originais não transformados]}.

    Returns:
        Dicionário com as três seções de gráficos.
    """
    preditos = modelo_fit.fittedvalues
    residuos = modelo_fit.resid

    # Resíduos vs. preditos
    residuos_vs_predito = {
        "preditos": [round(float(v), 4) for v in preditos],
        "residuos": [round(float(v), 4) for v in residuos],
    }

    # Q-Q plot
    (teoricos, amostra), _ = stats.probplot(residuos, dist="norm")
    qq_plot = {
        "teoricos": [round(float(v), 4) for v in teoricos],
        "amostra": [round(float(v), 4) for v in amostra],
    }

    # Scatter por variável
    scatter = {}
    for i, nome in enumerate(nomes_variaveis):
        xi_orig = valores_originais.get(nome, X[:, i].tolist())
        xi_transf = X[:, i]

        # Reta de regressão: min e max da variável transformada
        x_min, x_max = float(xi_transf.min()), float(xi_transf.max())
        X_linha = np.array([[x_min], [x_max]])
        # Montar X completo com médias das outras colunas para reta parcial
        X_reta = np.tile(X.mean(axis=0), (2, 1))
        X_reta[:, i] = [x_min, x_max]
        X_reta_const = sm.add_constant(X_reta, has_constant="add")
        y_reta = modelo_fit.predict(X_reta_const)

        scatter[nome] = {
            "x": [round(float(v), 4) for v in xi_orig],
            "y": [round(float(v), 4) for v in y],
            "reta_x": [round(x_min, 4), round(x_max, 4)],
            "reta_y": [round(float(y_reta[0]), 4), round(float(y_reta[1]), 4)],
        }

    return {
        "residuos_vs_predito": residuos_vs_predito,
        "qq_plot": qq_plot,
        "scatter_por_variavel": scatter,
    }
