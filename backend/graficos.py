"""
Geração de imagens de gráficos para embutir em laudos Word/PDF.

Usa matplotlib internamente; o frontend usa os dados JSON para Plotly.
"""

import io
import logging
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")  # backend sem display
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as stats

logger = logging.getLogger(__name__)


def _fig_para_bytes(fig: plt.Figure) -> bytes:
    """Serializa figura matplotlib para PNG em memória."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    data = buf.read()
    plt.close(fig)
    return data


def grafico_residuos_vs_predito(preditos: List[float], residuos: List[float]) -> bytes:
    """Gráfico de resíduos vs. valores preditos (PNG)."""
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.scatter(preditos, residuos, color="#2563EB", alpha=0.7, edgecolors="white", s=60)
    ax.axhline(0, color="#EF4444", linewidth=1.5, linestyle="--")
    ax.set_xlabel("Valores Preditos")
    ax.set_ylabel("Resíduos")
    ax.set_title("Resíduos vs. Preditos")
    ax.grid(True, linestyle="--", alpha=0.4)
    return _fig_para_bytes(fig)


def grafico_qq_plot(residuos: List[float]) -> bytes:
    """Q-Q plot dos resíduos (PNG)."""
    fig, ax = plt.subplots(figsize=(6, 5))
    (teoricos, amostra), (slope, intercept, _) = stats.probplot(residuos, dist="norm")
    ax.scatter(teoricos, amostra, color="#2563EB", alpha=0.8, edgecolors="white", s=50)
    x_line = np.array([min(teoricos), max(teoricos)])
    ax.plot(x_line, slope * x_line + intercept, color="#EF4444", linewidth=1.5)
    ax.set_xlabel("Quantis Teóricos")
    ax.set_ylabel("Quantis Amostrais")
    ax.set_title("Q-Q Plot dos Resíduos")
    ax.grid(True, linestyle="--", alpha=0.4)
    return _fig_para_bytes(fig)


def grafico_scatter_variavel(
    x_orig: List[float],
    y: List[float],
    reta_x: List[float],
    reta_y: List[float],
    nome_variavel: str,
    nome_dependente: str,
) -> bytes:
    """Scatter de uma variável independente vs. dependente com reta de regressão (PNG)."""
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.scatter(x_orig, y, color="#2563EB", alpha=0.7, edgecolors="white", s=60, label="Dados")
    ax.plot(reta_x, reta_y, color="#EF4444", linewidth=1.5, label="Regressão parcial")
    ax.set_xlabel(nome_variavel)
    ax.set_ylabel(nome_dependente)
    ax.set_title(f"{nome_dependente} × {nome_variavel}")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    return _fig_para_bytes(fig)


def gerar_todos_graficos_png(
    graficos_json: Dict[str, Any],
    nome_dependente: str = "Valor",
) -> Dict[str, bytes]:
    """
    Gera todos os gráficos como PNG a partir dos dados JSON já calculados.

    Returns:
        Dicionário {nome_grafico: bytes_png}.
    """
    imagens: Dict[str, bytes] = {}

    try:
        rv = graficos_json["residuos_vs_predito"]
        imagens["residuos_vs_predito"] = grafico_residuos_vs_predito(rv["preditos"], rv["residuos"])
    except Exception as e:
        logger.warning("Erro ao gerar resíduos vs predito: %s", e)

    try:
        imagens["qq_plot"] = grafico_qq_plot(graficos_json["residuos_vs_predito"]["residuos"])
    except Exception as e:
        logger.warning("Erro ao gerar Q-Q plot: %s", e)

    for nome, dados in graficos_json.get("scatter_por_variavel", {}).items():
        try:
            imagens[f"scatter_{nome}"] = grafico_scatter_variavel(
                dados["x"], dados["y"], dados["reta_x"], dados["reta_y"],
                nome, nome_dependente,
            )
        except Exception as e:
            logger.warning("Erro ao gerar scatter de %s: %s", nome, e)

    return imagens
