"""Testes do endpoint de predição pontual de imóvel-alvo."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

DATASET = [
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


def test_avaliar_imovel_sucesso():
    payload = {
        "dados": DATASET,
        "variavel_dependente": "preco",
        "variaveis_independentes": ["area", "distancia"],
        "transformacoes": {"preco": "nenhuma", "area": "nenhuma", "distancia": "log"},
        "imovel_alvo": {"area": 140, "distancia": 950},
        "nivel_confianca": 0.80,
    }
    resp = client.post("/api/avaliar-imovel", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "sucesso"
    # Valor estimado deve estar na faixa plausível do dataset
    assert 140000 < body["valor_estimado"] < 250000
    assert len(body["intervalo_predicao"]) == 2
    assert body["intervalo_predicao"][0] < body["valor_estimado"] < body["intervalo_predicao"][1]
    assert body["grau_precisao"] in ("I", "II", "III", "Fora dos critérios")


def test_avaliar_imovel_falta_variavel_alvo():
    payload = {
        "dados": DATASET,
        "variavel_dependente": "preco",
        "variaveis_independentes": ["area", "distancia"],
        "transformacoes": {"preco": "nenhuma", "area": "nenhuma", "distancia": "nenhuma"},
        "imovel_alvo": {"area": 140},  # falta distancia
    }
    resp = client.post("/api/avaliar-imovel", json=payload)
    assert resp.status_code == 422


def test_avaliar_imovel_coluna_ausente():
    payload = {
        "dados": DATASET,
        "variavel_dependente": "preco",
        "variaveis_independentes": ["area", "inexistente"],
        "transformacoes": {"preco": "nenhuma"},
        "imovel_alvo": {"area": 140, "inexistente": 1},
    }
    resp = client.post("/api/avaliar-imovel", json=payload)
    assert resp.status_code == 422


def test_avaliar_imovel_com_transformacao_y_log():
    payload = {
        "dados": DATASET,
        "variavel_dependente": "preco",
        "variaveis_independentes": ["area"],
        "transformacoes": {"preco": "log", "area": "nenhuma"},
        "imovel_alvo": {"area": 140},
        "nivel_confianca": 0.80,
    }
    resp = client.post("/api/avaliar-imovel", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["transformacao_y"] == "log"
    assert body["valor_estimado"] > 0
