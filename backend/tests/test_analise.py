"""Testes da análise inteligente de amostras (desabilitar)."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# 14 amostras coerentes + 1 outlier gritante (índice 14)
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
    {"preco": 999000, "area": 108, "distancia": 700},  # outlier: preço absurdo p/ a área
]


def test_analisar_detecta_outlier():
    payload = {
        "dados": DATASET,
        "variavel_dependente": "preco",
        "variaveis_independentes": ["area", "distancia"],
        "transformacoes": {"preco": "nenhuma", "area": "nenhuma", "distancia": "nenhuma"},
        "imovel_alvo": {"area": 130, "distancia": 800},
    }
    resp = client.post("/api/analisar-amostras", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["n_amostras"] == 15
    # o outlier (índice 14) deve ser recomendado para desabilitar
    assert 14 in body["recomendar_desabilitar"]
    # deve ter calculado distância ao alvo
    assert body["amostras"][0]["distancia_alvo"] is not None


def test_analisar_sem_alvo():
    payload = {
        "dados": DATASET,
        "variavel_dependente": "preco",
        "variaveis_independentes": ["area", "distancia"],
        "transformacoes": {"preco": "nenhuma", "area": "nenhuma", "distancia": "nenhuma"},
    }
    resp = client.post("/api/analisar-amostras", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["amostras"][0]["distancia_alvo"] is None
    assert "r2_atual" in body


def test_analisar_coluna_ausente():
    payload = {
        "dados": DATASET,
        "variavel_dependente": "preco",
        "variaveis_independentes": ["area", "xxx"],
        "transformacoes": {"preco": "nenhuma"},
    }
    resp = client.post("/api/analisar-amostras", json=payload)
    assert resp.status_code == 422
