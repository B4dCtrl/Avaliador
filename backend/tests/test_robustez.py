"""Testes de robustez: dados ruins devem retornar 422 com mensagem clara, nunca 500."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app
from saneamento import sanear_dataset, DadosInvalidos, num_seguro
import pytest

client = TestClient(app)

BOM = [
    {"preco": 150000, "area": 100, "distancia": 500},
    {"preco": 200000, "area": 150, "distancia": 1000},
    {"preco": 175000, "area": 120, "distancia": 800},
    {"preco": 220000, "area": 160, "distancia": 1200},
    {"preco": 185000, "area": 130, "distancia": 900},
    {"preco": 160000, "area": 105, "distancia": 600},
    {"preco": 210000, "area": 155, "distancia": 1100},
]


def _payload(dados):
    return {
        "dados": dados,
        "variavel_dependente": "preco",
        "variaveis_independentes": ["area", "distancia"],
        "transformacoes_testar": ["nenhuma", "log"],
        "nivel_confianca": 0.80,
    }


def test_texto_em_coluna_nao_quebra():
    dados = [dict(d) for d in BOM]
    dados[2]["area"] = "abc"  # texto
    r = client.post("/api/bestfit", json=_payload(dados))
    assert r.status_code == 200, r.text  # linha descartada, segue rodando
    assert any("descartada" in a for a in r.json()["avisos"])


def test_valor_vazio_descartado():
    dados = [dict(d) for d in BOM]
    dados[1]["distancia"] = ""
    r = client.post("/api/bestfit", json=_payload(dados))
    assert r.status_code == 200
    assert r.json()["avisos"]


def test_poucas_amostras_erro_claro():
    r = client.post("/api/bestfit", json=_payload(BOM[:2]))
    assert r.status_code == 422
    assert "insuficiente" in r.json()["detail"].lower()


def test_coluna_constante_erro_claro():
    dados = [dict(d) for d in BOM]
    for d in dados:
        d["area"] = 100  # constante
    r = client.post("/api/bestfit", json=_payload(dados))
    assert r.status_code == 422
    assert "mesmo valor" in r.json()["detail"].lower()


def test_coluna_ausente_erro_claro():
    dados = [{"preco": 1, "area": 2} for _ in range(7)]
    r = client.post("/api/bestfit", json=_payload(dados))
    assert r.status_code == 422
    assert "ausente" in r.json()["detail"].lower()


def test_virgula_decimal_aceita():
    dados = [{"preco": "150000", "area": "100,5", "distancia": "500"} for _ in range(3)]
    dados += [
        {"preco": "200000", "area": "150,2", "distancia": "1000"},
        {"preco": "175000", "area": "120,8", "distancia": "800"},
        {"preco": "220000", "area": "160,1", "distancia": "1200"},
        {"preco": "185000", "area": "130,3", "distancia": "900"},
    ]
    r = client.post("/api/bestfit", json=_payload(dados))
    assert r.status_code == 200, r.text


def test_num_seguro_troca_nan():
    assert num_seguro(float("nan")) == 0.0
    assert num_seguro(float("inf")) == 0.0
    assert num_seguro(3.14159, 2) == 3.14
    assert num_seguro("xyz") == 0.0


def test_sanear_direto_ok():
    limpos, avisos = sanear_dataset(BOM, "preco", ["area", "distancia"])
    assert len(limpos) == 7
    assert avisos == []


def test_sanear_lista_vazia():
    with pytest.raises(DadosInvalidos):
        sanear_dataset([], "preco", ["area"])
