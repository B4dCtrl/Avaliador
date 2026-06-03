"""
Testes da regressão OLS e estatísticas derivadas.

Dados sintéticos com resultados esperados conhecidos.
"""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

import numpy as np
import pytest

from calculadora import (
    calcular_durbin_watson,
    calcular_elasticidade,
    calcular_regressao,
    correlacao_matrix,
    detectar_outliers,
)


# ---------------------------------------------------------------------------
# Fixture de dados
# ---------------------------------------------------------------------------

@pytest.fixture
def dados_simples():
    """Dados simples com relação linear conhecida: y = 2*x1 + 3*x2 + 10 + ruido."""
    np.random.seed(42)
    n = 30
    x1 = np.random.uniform(1, 10, n)
    x2 = np.random.uniform(5, 20, n)
    y = 2 * x1 + 3 * x2 + 10 + np.random.normal(0, 0.5, n)
    X = np.column_stack([x1, x2])
    return y, X


# ---------------------------------------------------------------------------
# Testes de regressão
# ---------------------------------------------------------------------------

def test_regressao_r2_alto(dados_simples):
    y, X = dados_simples
    modelo = calcular_regressao(y, X)
    assert modelo.rsquared > 0.99, f"R² esperado > 0.99, obteve {modelo.rsquared:.4f}"


def test_regressao_coeficientes_aproximados(dados_simples):
    y, X = dados_simples
    modelo = calcular_regressao(y, X)
    coefs = modelo.params  # [intercepto, c1, c2]
    assert abs(coefs[0] - 10) < 1.0, f"Intercepto esperado ≈ 10, obteve {coefs[0]:.4f}"
    assert abs(coefs[1] - 2) < 0.2, f"β1 esperado ≈ 2, obteve {coefs[1]:.4f}"
    assert abs(coefs[2] - 3) < 0.2, f"β2 esperado ≈ 3, obteve {coefs[2]:.4f}"


def test_regressao_pvalores_significativos(dados_simples):
    y, X = dados_simples
    modelo = calcular_regressao(y, X)
    for i, p in enumerate(modelo.pvalues[1:], start=1):
        assert p < 0.05, f"p-valor da variável {i} não é significativo: {p:.4f}"


# ---------------------------------------------------------------------------
# Durbin-Watson
# ---------------------------------------------------------------------------

def test_durbin_watson_independente(dados_simples):
    y, X = dados_simples
    modelo = calcular_regressao(y, X)
    dw = calcular_durbin_watson(modelo.resid)
    assert 1.0 < dw < 3.0, f"DW fora do esperado: {dw:.4f}"


def test_durbin_watson_autocorrelado():
    """Resíduos com autocorrelação positiva devem ter DW < 1.5."""
    residuos = np.cumsum(np.random.normal(0, 1, 50))  # random walk = forte autocorrelação
    dw = calcular_durbin_watson(residuos)
    assert dw < 1.5, f"DW esperado < 1.5 para série autocorrelada, obteve {dw:.4f}"


# ---------------------------------------------------------------------------
# Outliers
# ---------------------------------------------------------------------------

def test_sem_outliers():
    residuos = np.random.normal(0, 1, 20)
    resultado = detectar_outliers(residuos, limiar=10)  # limiar alto → sem outliers
    assert resultado["detectados"] == 0


def test_com_outlier_explícito():
    residuos = np.array([0.1, -0.2, 0.3, 0.1, 10.0, -0.1, 0.2])  # índice 4 é outlier
    resultado = detectar_outliers(residuos, limiar=2.0)
    assert 4 in resultado["indices"]
    assert resultado["detectados"] >= 1


# ---------------------------------------------------------------------------
# Elasticidade
# ---------------------------------------------------------------------------

def test_elasticidade_linear():
    # nenhuma: e = coef * (media_x / media_y)
    e = calcular_elasticidade(2.0, "nenhuma", 10.0, 50.0)
    assert abs(e - 0.4) < 1e-6


def test_elasticidade_log():
    # log: e = coef
    e = calcular_elasticidade(0.75, "log", 5.0, 100.0)
    assert abs(e - 0.75) < 1e-6


# ---------------------------------------------------------------------------
# Correlação
# ---------------------------------------------------------------------------

def test_correlacao_diagonal_um():
    dados = {"x1": [1, 2, 3, 4, 5], "x2": [2, 4, 6, 8, 10]}
    resultado = correlacao_matrix(dados)
    matriz = resultado["dados"]
    assert abs(matriz[0][0] - 1.0) < 1e-6
    assert abs(matriz[1][1] - 1.0) < 1e-6


def test_correlacao_perfeita():
    dados = {"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, 4.0, 6.0, 8.0]}
    resultado = correlacao_matrix(dados)
    assert abs(resultado["dados"][0][1] - 1.0) < 1e-4
