"""Testes do sistema de fontes de dados (busca automática legal)."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app
from fontes_dados import CaixaImoveis, listar_fontes, buscar_em_fontes, _num_br, _num_decimal

client = TestClient(app)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def test_num_br_moeda():
    assert _num_br("105.481,84") == 105481.84
    assert _num_br("90.746,77") == 90746.77
    assert _num_br("") is None


def test_num_decimal_descricao():
    # a descrição da Caixa usa ponto como decimal
    assert _num_decimal("60.27") == 60.27
    assert _num_decimal("109.8") == 109.8
    assert _num_decimal("200.0") == 200.0


def test_parse_descricao_areas():
    d = "Casa, 57.97 de área total, 57.97 de área privativa, 120.00 de área do terreno, 2 qto(s)"
    r = CaixaImoveis._parse_descricao(d)
    assert r["area_total"] == 57.97
    assert r["area_privativa"] == 57.97
    assert r["area_terreno"] == 120.0
    assert r["quartos"] == 2.0
    assert r["tipo"] == "casa"


def test_parse_descricao_apartamento():
    d = "Apartamento, 40.26 de área privativa, 3 qto(s)"
    r = CaixaImoveis._parse_descricao(d)
    assert r["tipo"] == "apartamento"
    assert r["area_privativa"] == 40.26


def test_parse_descricao_vazia():
    r = CaixaImoveis._parse_descricao("")
    assert all(v is None for v in r.values())


# ---------------------------------------------------------------------------
# Conector Caixa (com CSV simulado)
# ---------------------------------------------------------------------------

CSV_FAKE = [
    {"N° do imóvel": "1", "UF": "MS", "Cidade": "CAMPO GRANDE", "Bairro": "CENTRO",
     "Endereço": "RUA A, N. 10", "Preço": "87.141,03", "Valor de avaliação": "173.000,00",
     "Descrição": "Casa, 57.97 de área total, 57.97 de área privativa, 120.00 de área do terreno, 2 qto(s)",
     "Link de acesso": "https://venda-imoveis.caixa.gov.br/x/1"},
    {"N° do imóvel": "2", "UF": "MS", "Cidade": "DOURADOS", "Bairro": "JARDIM",
     "Endereço": "RUA B, N. 20", "Preço": "50.000,00", "Valor de avaliação": "100.000,00",
     "Descrição": "Apartamento, 45.00 de área privativa, 2 qto(s)",
     "Link de acesso": "https://venda-imoveis.caixa.gov.br/x/2"},
]


def test_caixa_filtra_por_cidade():
    fonte = CaixaImoveis()
    with patch.object(CaixaImoveis, "_baixar", return_value=CSV_FAKE):
        r = fonte.buscar("MS", "Campo Grande")
    assert len(r) == 1
    assert r[0]["cidade"] == "CAMPO GRANDE"


def test_caixa_usa_valor_de_avaliacao_como_preco():
    fonte = CaixaImoveis()
    with patch.object(CaixaImoveis, "_baixar", return_value=CSV_FAKE):
        r = fonte.buscar("MS", "Campo Grande")
    # o preço de leilão tem deságio; a referência de mercado é a avaliação
    assert r[0]["preco"] == 173000.0
    assert r[0]["preco_leilao"] == 87141.03
    assert r[0]["valor_avaliacao"] == 173000.0


def test_caixa_extrai_areas_e_fonte():
    fonte = CaixaImoveis()
    with patch.object(CaixaImoveis, "_baixar", return_value=CSV_FAKE):
        r = fonte.buscar("MS", "Campo Grande")
    assert r[0]["area_construida"] == 57.97
    assert r[0]["area_terreno"] == 120.0
    assert r[0]["fonte"].startswith("https://venda-imoveis.caixa.gov.br")


def test_caixa_filtra_por_bairro():
    fonte = CaixaImoveis()
    with patch.object(CaixaImoveis, "_baixar", return_value=CSV_FAKE):
        achou = fonte.buscar("MS", "Campo Grande", bairro="centro")
        nao = fonte.buscar("MS", "Campo Grande", bairro="inexistente")
    assert len(achou) == 1
    assert len(nao) == 0


def test_caixa_respeita_limite():
    fonte = CaixaImoveis()
    with patch.object(CaixaImoveis, "_baixar", return_value=CSV_FAKE * 10):
        r = fonte.buscar("MS", "Campo Grande", limite=3)
    assert len(r) == 3


# ---------------------------------------------------------------------------
# Registro e orquestrador
# ---------------------------------------------------------------------------

def test_listar_fontes_traz_base_legal():
    fs = listar_fontes()
    assert any(f["id"] == "caixa" for f in fs)
    assert all("legal" in f and f["legal"] for f in fs)


def test_buscar_em_fontes_agrega():
    with patch.object(CaixaImoveis, "_baixar", return_value=CSV_FAKE):
        r = buscar_em_fontes("MS", "Campo Grande")
    assert r["por_fonte"]["caixa"] == 1
    assert not r["erros"]


def test_buscar_em_fontes_fonte_desconhecida():
    r = buscar_em_fontes("MS", "Campo Grande", fontes=["inexistente"])
    assert r["erros"] and "desconhecida" in r["erros"][0]["erro"]


def test_falha_de_fonte_nao_derruba_busca():
    with patch.object(CaixaImoveis, "_baixar", side_effect=OSError("rede fora")):
        r = buscar_em_fontes("MS", "Campo Grande")
    assert r["candidatos"] == []
    assert r["erros"][0]["fonte"] == "caixa"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def test_endpoint_lista_fontes():
    resp = client.get("/api/fontes")
    assert resp.status_code == 200
    assert any(f["id"] == "caixa" for f in resp.json()["fontes"])


def test_endpoint_buscar_fontes():
    with patch.object(CaixaImoveis, "_baixar", return_value=CSV_FAKE):
        resp = client.post("/api/fontes/buscar", json={"uf": "MS", "cidade": "Campo Grande"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert body["candidatos"][0]["preco"] == 173000.0


def test_endpoint_buscar_sem_cidade():
    resp = client.post("/api/fontes/buscar", json={"uf": "MS", "cidade": ""})
    assert resp.status_code == 422
