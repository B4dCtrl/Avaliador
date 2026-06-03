"""Testes unitários das 7 transformações de variável."""

import numpy as np
import pytest

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from calculadora import transformar_variavel


VALORES_POSITIVOS = [100.0, 150.0, 120.0, 160.0, 130.0]
VALORES_COM_ZERO = [0.0, 150.0, 120.0]


def test_nenhuma():
    resultado = transformar_variavel(VALORES_POSITIVOS, "nenhuma")
    np.testing.assert_array_equal(resultado, VALORES_POSITIVOS)


def test_log():
    resultado = transformar_variavel(VALORES_POSITIVOS, "log")
    esperado = np.log(VALORES_POSITIVOS)
    np.testing.assert_allclose(resultado, esperado)


def test_log_rejeita_zero():
    with pytest.raises(ValueError, match="ln"):
        transformar_variavel(VALORES_COM_ZERO, "log")


def test_raiz_quadrada():
    resultado = transformar_variavel(VALORES_POSITIVOS, "raiz_quadrada")
    np.testing.assert_allclose(resultado, np.sqrt(VALORES_POSITIVOS))


def test_raiz_reciproca():
    resultado = transformar_variavel(VALORES_POSITIVOS, "raiz_reciproca")
    np.testing.assert_allclose(resultado, 1.0 / np.sqrt(VALORES_POSITIVOS))


def test_raiz_reciproca_rejeita_zero():
    with pytest.raises(ValueError):
        transformar_variavel(VALORES_COM_ZERO, "raiz_reciproca")


def test_reciproca():
    resultado = transformar_variavel(VALORES_POSITIVOS, "reciproca")
    np.testing.assert_allclose(resultado, 1.0 / np.array(VALORES_POSITIVOS))


def test_reciproca_rejeita_zero():
    with pytest.raises(ValueError):
        transformar_variavel(VALORES_COM_ZERO, "reciproca")


def test_reciproca_quadrada():
    resultado = transformar_variavel(VALORES_POSITIVOS, "reciproca_quadrada")
    np.testing.assert_allclose(resultado, 1.0 / np.array(VALORES_POSITIVOS) ** 2)


def test_quadrada():
    resultado = transformar_variavel(VALORES_POSITIVOS, "quadrada")
    np.testing.assert_allclose(resultado, np.array(VALORES_POSITIVOS) ** 2)


def test_transformacao_invalida():
    with pytest.raises(ValueError, match="desconhecida"):
        transformar_variavel(VALORES_POSITIVOS, "invalida")
