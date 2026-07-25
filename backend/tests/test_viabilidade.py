"""Testes da viabilidade de investimento."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app
from viabilidade import analisar_viabilidade

client = TestClient(app)


def test_desconto_na_compra():
    # compra a 450k um imóvel avaliado em 500k -> 10% de desconto
    r = analisar_viabilidade(valor_mercado=500000, preco_compra=450000)
    assert abs(r["comparacao_mercado"]["desconto_pct"] - 10.0) < 0.01
    assert r["comparacao_mercado"]["ganho_patrimonial"] == 50000


def test_cenario_renda():
    r = analisar_viabilidade(
        valor_mercado=500000, preco_compra=500000,
        aluguel_mensal=3000, despesas_mensais=500,
    )
    assert r["renda"] is not None
    # yield líquido = (2500*12)/500000 = 6%
    assert abs(r["renda"]["yield_liquido_anual_pct"] - 6.0) < 0.01
    assert r["renda"]["payback_anos"] is not None


def test_cenario_revenda_valorizacao():
    r = analisar_viabilidade(
        valor_mercado=500000, preco_compra=500000,
        valorizacao_anual_pct=10, horizonte_anos=5, custo_venda_pct=0,
    )
    # 500k * 1.1^5 ≈ 805.255
    assert abs(r["revenda"]["valor_futuro_estimado"] - 805255.0) < 500
    assert r["revenda"]["lucro_liquido"] > 0
    assert r["revenda"]["retorno_anualizado_pct"] > 0


def test_veredito_favoravel():
    r = analisar_viabilidade(
        valor_mercado=500000, preco_compra=440000,   # 12% desconto
        aluguel_mensal=3500, despesas_mensais=300,    # yield alto
        valorizacao_anual_pct=8, horizonte_anos=5,
    )
    assert r["veredito"] == "Favorável"
    assert r["pontuacao"] >= 2


def test_veredito_desfavoravel():
    r = analisar_viabilidade(
        valor_mercado=500000, preco_compra=560000,   # pagando caro
        aluguel_mensal=1500, despesas_mensais=600,    # yield baixo
        valorizacao_anual_pct=0, horizonte_anos=5,
    )
    assert r["veredito"] == "Desfavorável"


def test_endpoint_viabilidade():
    payload = {
        "valor_mercado": 500000, "preco_compra": 450000,
        "custos_aquisicao": 15000, "aluguel_mensal": 3000,
        "despesas_mensais": 500, "valorizacao_anual_pct": 6, "horizonte_anos": 5,
    }
    resp = client.post("/api/viabilidade", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "sucesso"
    assert "renda" in body and "revenda" in body and "veredito" in body


def test_endpoint_valores_invalidos():
    # preço de compra negativo é rejeitado pelo schema
    resp = client.post("/api/viabilidade", json={"valor_mercado": 500000, "preco_compra": -1})
    assert resp.status_code == 422


def test_sem_renda_quando_sem_aluguel():
    r = analisar_viabilidade(valor_mercado=500000, preco_compra=500000)
    assert r["renda"] is None
    assert r["revenda"] is not None
