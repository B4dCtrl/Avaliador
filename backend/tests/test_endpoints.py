"""
Testes de integração dos endpoints FastAPI.
"""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Payload de teste reutilizável
# ---------------------------------------------------------------------------

PAYLOAD_REGRESSAO = {
    "dados": {
        "variavel_dependente": "preco",
        "valores_dependentes": [
            150000, 200000, 175000, 220000, 185000,
            160000, 210000, 195000, 230000, 170000,
            155000, 215000, 180000, 225000, 190000,
        ],
        "variaveis_independentes": {
            "area_total": {
                "valores": [100, 150, 120, 160, 130, 105, 155, 135, 165, 110, 102, 158, 125, 162, 132],
                "transformacao": "nenhuma",
            },
            "distancia_polo": {
                "valores": [500, 1000, 800, 1200, 900, 600, 1100, 850, 1300, 700, 550, 1050, 820, 1250, 920],
                "transformacao": "log",
            },
            "garagens": {
                "valores": [1, 2, 1, 2, 1, 1, 2, 2, 2, 1, 1, 2, 1, 2, 2],
                "transformacao": "nenhuma",
            },
        },
    }
}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Calcular regressão
# ---------------------------------------------------------------------------

def test_calcular_regressao_sucesso():
    resp = client.post("/api/calcular-regressao", json=PAYLOAD_REGRESSAO)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "sucesso"
    assert "regressao" in body
    assert "coeficientes" in body
    assert "graficos" in body
    assert "validacao_nbr" in body


def test_calcular_regressao_r2_positivo():
    resp = client.post("/api/calcular-regressao", json=PAYLOAD_REGRESSAO)
    r2 = resp.json()["regressao"]["r_squared"]
    assert 0 <= r2 <= 1, f"R² fora do intervalo [0,1]: {r2}"


def test_calcular_regressao_tem_coeficientes():
    resp = client.post("/api/calcular-regressao", json=PAYLOAD_REGRESSAO)
    coefs = resp.json()["coeficientes"]
    assert len(coefs) == 3
    for c in coefs:
        assert "variavel" in c
        assert "coeficiente" in c
        assert "p_valor" in c
        assert "elasticidade" in c


def test_calcular_regressao_graficos_presentes():
    resp = client.post("/api/calcular-regressao", json=PAYLOAD_REGRESSAO)
    graficos = resp.json()["graficos"]
    assert "residuos_vs_predito" in graficos
    assert "qq_plot" in graficos
    assert "scatter_por_variavel" in graficos


def test_calcular_regressao_transformacao_invalida():
    payload = {
        "dados": {
            "variavel_dependente": "preco",
            "valores_dependentes": [100, 200, 150],
            "variaveis_independentes": {
                "x": {"valores": [1, 2, 3], "transformacao": "inexistente"}
            },
        }
    }
    resp = client.post("/api/calcular-regressao", json=payload)
    assert resp.status_code == 422


def test_calcular_regressao_log_valores_negativos():
    """ln(x) não pode ser aplicado em valores ≤ 0."""
    payload = {
        "dados": {
            "variavel_dependente": "preco",
            "valores_dependentes": [100000, 200000, 150000, 180000, 130000,
                                     120000, 190000, 160000, 210000, 140000,
                                     115000, 195000, 155000, 205000, 135000],
            "variaveis_independentes": {
                "x": {
                    "valores": [-1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                    "transformacao": "log",
                }
            },
        }
    }
    resp = client.post("/api/calcular-regressao", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Export Word
# ---------------------------------------------------------------------------

def test_exportar_word():
    # Primeiro calcular
    reg_resp = client.post("/api/calcular-regressao", json=PAYLOAD_REGRESSAO)
    resultado = reg_resp.json()

    export_payload = {
        "resultado_regressao": resultado,
        "imovel": {
            "endereco": "Rua Teste, 123",
            "area_terreno": 300,
            "area_construida": 200,
            "data_avaliacao": "2025-06-03",
            "finalidade": "Avaliação de garantia",
        },
        "avaliador": {
            "nome": "João Silva",
            "crea": "99999/SP",
            "empresa": "Avaliações Teste",
        },
    }

    resp = client.post("/api/exportar-word", json=export_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "sucesso"
    assert body["arquivo"].endswith(".docx")
    assert body["tamanho_kb"] > 0


# ---------------------------------------------------------------------------
# Export PDF
# ---------------------------------------------------------------------------

def test_exportar_pdf():
    reg_resp = client.post("/api/calcular-regressao", json=PAYLOAD_REGRESSAO)
    resultado = reg_resp.json()

    export_payload = {
        "resultado_regressao": resultado,
        "imovel": {
            "endereco": "Av. Central, 456",
            "area_terreno": 400,
            "area_construida": 250,
            "data_avaliacao": "2025-06-03",
            "finalidade": "Compra e venda",
        },
        "avaliador": {
            "nome": "Maria Souza",
            "crea": "12345/RJ",
            "empresa": "Perícia Imóveis",
        },
    }

    resp = client.post("/api/exportar-pdf", json=export_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "sucesso"
    assert body["arquivo"].endswith(".pdf")
    assert body["tamanho_kb"] > 0
