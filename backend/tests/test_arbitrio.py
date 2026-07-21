"""Testes do arbítrio do avaliador: escolher modelo do ranking."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

DADOS = [
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
]

BASE = {
    "dados": DADOS,
    "variavel_dependente": "preco",
    "variaveis_independentes": ["area", "distancia"],
    "transformacoes_testar": ["nenhuma", "log"],
    "nivel_confianca": 0.80,
}


def test_escolher_modelo_do_ranking():
    # 1º cálculo: pega o ranking
    r1 = client.post("/api/bestfit", json=BASE).json()
    assert len(r1["ranking"]) >= 2
    segundo = r1["ranking"][1]

    # 2º cálculo: pede exatamente o segundo modelo
    payload = dict(BASE)
    payload["transformacoes_escolhidas"] = segundo["transformacoes"]
    r2 = client.post("/api/bestfit", json=payload)
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["melhor_modelo"]["transformacoes"] == segundo["transformacoes"]
    assert body["melhor_modelo"]["modelo_escolhido_pelo_avaliador"] is True
    assert abs(body["melhor_modelo"]["r2"] - segundo["r2"]) < 1e-9


def test_modelo_escolhido_inexistente_da_422():
    payload = dict(BASE)
    payload["transformacoes_escolhidas"] = {"preco": "quadrada", "area": "quadrada", "distancia": "quadrada"}
    r = client.post("/api/bestfit", json=payload)
    assert r.status_code == 422


def test_ranking_traz_max_p_valor():
    r = client.post("/api/bestfit", json=BASE).json()
    assert all("max_p_valor" in item for item in r["ranking"])


def test_residuos_padronizados_presentes():
    r = client.post("/api/bestfit", json=BASE).json()
    rp = r["melhor_modelo"]["residuos_padronizados"]
    assert len(rp) == len(r["melhor_modelo"]["residuos"])
