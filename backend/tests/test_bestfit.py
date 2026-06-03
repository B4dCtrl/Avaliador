"""Testes do auto-ranking e do endpoint /api/bestfit."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bestfit import bestfit
from main import app

client = TestClient(app)


@pytest.fixture
def dataset_imovel():
    return [
        {"preco": 150000, "area": 100, "distancia": 500},
        {"preco": 200000, "area": 150, "distancia": 1000},
        {"preco": 175000, "area": 120, "distancia": 800},
        {"preco": 220000, "area": 160, "distancia": 1200},
        {"preco": 185000, "area": 130, "distancia": 900},
        {"preco": 160000, "area": 105, "distancia": 600},
        {"preco": 210000, "area": 155, "distancia": 1100},
        {"preco": 195000, "area": 135, "distancia": 850},
        {"preco": 230000, "area": 165, "distancia": 1300},
        {"preco": 170000, "area": 110, "distancia": 700},
        {"preco": 155000, "area": 102, "distancia": 550},
        {"preco": 215000, "area": 158, "distancia": 1050},
        {"preco": 180000, "area": 125, "distancia": 820},
        {"preco": 225000, "area": 162, "distancia": 1250},
        {"preco": 190000, "area": 132, "distancia": 920},
    ]


def test_bestfit_retorna_ranking_ordenado(dataset_imovel):
    df = pd.DataFrame(dataset_imovel)
    ranking = bestfit(df, "preco", ["area", "distancia"], top_n=10)
    assert len(ranking) > 0
    aics = [r["aic"] for r in ranking]
    assert aics == sorted(aics), "Ranking deve estar ordenado por AIC"


def test_bestfit_inclui_modelo_identidade(dataset_imovel):
    df = pd.DataFrame(dataset_imovel)
    ranking = bestfit(df, "preco", ["area"], transformacoes=["nenhuma"], top_n=5)
    assert any(r["transformacoes"]["preco"] == "nenhuma" for r in ranking)


def test_endpoint_bestfit(dataset_imovel):
    payload = {
        "dados": dataset_imovel,
        "variavel_dependente": "preco",
        "variaveis_independentes": ["area", "distancia"],
        "transformacoes_testar": ["nenhuma", "log"],
        "nivel_confianca": 0.80,
    }
    resp = client.post("/api/bestfit", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "sucesso"
    assert "melhor_modelo" in body
    assert "ranking" in body
    assert "diagnosticos" in body
    assert "grau_fundamentacao" in body
    assert body["melhor_modelo"]["r2"] > 0
    assert len(body["ranking"]) > 0


def test_endpoint_bestfit_coluna_ausente(dataset_imovel):
    payload = {
        "dados": dataset_imovel,
        "variavel_dependente": "preco",
        "variaveis_independentes": ["area", "inexistente"],
    }
    resp = client.post("/api/bestfit", json=payload)
    assert resp.status_code == 422


def test_endpoint_calcular_regressao_inclui_diagnosticos():
    payload = {
        "dados": {
            "variavel_dependente": "preco",
            "valores_dependentes": [150000, 200000, 175000, 220000, 185000,
                                     160000, 210000, 195000, 230000, 170000,
                                     155000, 215000, 180000, 225000, 190000],
            "variaveis_independentes": {
                "area": {
                    "valores": [100, 150, 120, 160, 130, 105, 155, 135, 165, 110, 102, 158, 125, 162, 132],
                    "transformacao": "nenhuma",
                },
            },
        }
    }
    resp = client.post("/api/calcular-regressao", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "diagnosticos" in body
    assert "shapiro_wilk" in body["diagnosticos"]
    assert "jarque_bera" in body["diagnosticos"]
    assert "breusch_pagan" in body["diagnosticos"]
    assert "outliers_cooks" in body["diagnosticos"]
    assert "grau_fundamentacao" in body
    assert body["regressao"]["aic"] != 0
