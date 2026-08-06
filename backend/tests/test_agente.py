"""Testes do estrategista e do filtro anti-alucinação."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app
from estrategia import gerar_estrategia, aplicar_refino
from crew_bridge import (
    extrair_json, filtrar_imoveis, detectar_contradicoes, processar_retorno_agente,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Estrategista
# ---------------------------------------------------------------------------

def test_terreno_prioriza_area_e_zoneamento():
    e = gerar_estrategia({"tipo": "terreno", "area_terreno": 450, "zoneamento": "ZM"})
    assert e["tipo_normalizado"] == "terreno"
    assert "area_terreno" in e["criterios_obrigatorios"]
    assert "zoneamento" in e["criterios_obrigatorios"]


def test_apartamento_prioriza_quartos():
    e = gerar_estrategia({"tipo": "apartamento", "area_construida": 70, "quartos": 3})
    assert "quartos" in e["criterios_obrigatorios"]
    assert e["raio_inicial_metros"] == 1000  # raio menor que casa


def test_tipo_desconhecido_cai_em_casa():
    e = gerar_estrategia({"tipo": "sobrado", "area_construida": 150,
                          "padrao_construtivo": "medio"})
    assert e["tipo_normalizado"] == "casa"


def test_criterio_nao_informado_nao_entra_como_obrigatorio():
    # zoneamento não informado: não pode virar critério obrigatório
    e = gerar_estrategia({"tipo": "terreno", "area_terreno": 450})
    assert "zoneamento" not in e["criterios_obrigatorios"]
    assert any("zoneamento" in a for a in e["avisos"])


def test_area_grande_amplia_raio():
    p = gerar_estrategia({"tipo": "casa", "area_construida": 150, "padrao_construtivo": "medio"})
    g = gerar_estrategia({"tipo": "casa", "area_construida": 150,
                          "padrao_construtivo": "medio", "area_terreno": 5000})
    assert g["raio_inicial_metros"] > p["raio_inicial_metros"]


def test_regras_expansao_ordenadas():
    e = gerar_estrategia({"tipo": "casa", "area_construida": 150})
    ordens = [r["ordem"] for r in e["regras_expansao"]]
    assert ordens == sorted(ordens)
    assert len(ordens) == 6


# ---------------------------------------------------------------------------
# Refino por LLM (validação)
# ---------------------------------------------------------------------------

BASE = {
    "imovel_avaliando": {"tipo": "casa", "area_construida": 150},
    "criterios_obrigatorios": ["tipo", "area_construida"],
    "criterios_flexiveis": [],
    "raio_inicial_metros": 1500,
    "tolerancias": {"area_construida": 0.25},
    "origem": ["regras"],
}


def test_refino_rejeita_variavel_inexistente():
    r = aplicar_refino(BASE, {"criterios_obrigatorios": ["tipo", "piscina_olimpica"]})
    assert "piscina_olimpica" not in r["criterios_obrigatorios"]
    assert any("inexistentes" in x for x in r["refino_ia"]["rejeitados"])


def test_refino_rejeita_raio_absurdo():
    r = aplicar_refino(BASE, {"raio_inicial_metros": 5_000_000})
    assert r["raio_inicial_metros"] == 1500          # manteve a regra
    assert any("raio_inicial_metros" in x for x in r["refino_ia"]["rejeitados"])


def test_refino_aceita_raio_valido():
    r = aplicar_refino(BASE, {"raio_inicial_metros": 3000})
    assert r["raio_inicial_metros"] == 3000
    assert "raio_inicial_metros" in r["refino_ia"]["aplicados"]


def test_refino_ignora_campo_nao_refinavel():
    r = aplicar_refino(BASE, {"grau_fundamentacao": "III"})
    assert "grau_fundamentacao" not in r
    assert any("não refinável" in x for x in r["refino_ia"]["rejeitados"])


def test_refino_rejeita_tolerancia_fora_da_faixa():
    r = aplicar_refino(BASE, {"tolerancias": {"area_construida": 9.0}})
    assert r["tolerancias"]["area_construida"] == 0.25


# ---------------------------------------------------------------------------
# Extração de JSON
# ---------------------------------------------------------------------------

def test_extrai_json_de_bloco_markdown():
    txt = 'Segue:\n```json\n{"a": 1}\n```\nfim'
    assert extrair_json(txt) == {"a": 1}


def test_extrai_json_cru():
    assert extrair_json('{"a": 2}') == {"a": 2}


def test_extrai_json_com_texto_ao_redor():
    assert extrair_json('bla bla {"a": 3} tchau') == {"a": 3}


def test_extrai_json_invalido_retorna_none():
    assert extrair_json("sem json aqui") is None


# ---------------------------------------------------------------------------
# Filtro de imóveis
# ---------------------------------------------------------------------------

BOM = {"endereco": "Rua A, 100", "preco": 500000, "area_construida": 100,
       "url": "https://portal.com/1"}


def test_aceita_imovel_completo():
    r = filtrar_imoveis([BOM])
    assert len(r["aceitos"]) == 1
    assert r["aceitos"][0]["preco_m2"] == 5000.0


def test_rejeita_sem_fonte():
    r = filtrar_imoveis([{k: v for k, v in BOM.items() if k != "url"}])
    assert not r["aceitos"]
    assert "sem fonte" in r["rejeitados"][0]["motivo"]


def test_rejeita_fonte_que_nao_e_url():
    r = filtrar_imoveis([{**BOM, "url": "achei no google"}])
    assert not r["aceitos"]
    assert "não é URL" in r["rejeitados"][0]["motivo"]


def test_rejeita_preco_implausivel():
    r = filtrar_imoveis([{**BOM, "preco": 12}])
    assert not r["aceitos"]


def test_rejeita_area_implausivel():
    r = filtrar_imoveis([{**BOM, "area_construida": 0.5}])
    assert not r["aceitos"]


def test_rejeita_preco_m2_absurdo():
    # 500 milhões em 100 m² => R$ 5 mi/m²
    r = filtrar_imoveis([{**BOM, "preco": 500_000_000}])
    assert not r["aceitos"]
    assert "preço/m²" in r["rejeitados"][0]["motivo"]


def test_recalcula_preco_m2_ignorando_valor_do_agente():
    # agente diz 9999/m²; real é 5000/m²
    r = filtrar_imoveis([{**BOM, "preco_m2": 9999}])
    a = r["aceitos"][0]
    assert a["preco_m2"] == 5000.0
    assert a["divergencia_corrigida"] is not None
    assert r["resumo"]["precos_m2_corrigidos"] == 1


def test_aceita_numero_em_formato_br():
    r = filtrar_imoveis([{**BOM, "preco": "R$ 500.000,00"}])
    assert r["aceitos"][0]["preco"] == 500000.0


def test_usa_area_terreno_quando_nao_ha_construida():
    r = filtrar_imoveis([{"endereco": "Lote", "preco": 300000,
                          "area_terreno": 450, "url": "https://x.com/1"}])
    assert r["aceitos"][0]["preco_m2"] == round(300000 / 450, 2)


# ---------------------------------------------------------------------------
# Contradições — caso real observado na crew
# ---------------------------------------------------------------------------

CREW_REAL = {
    "amostra_final": {
        "grau_fundamentacao": "III",
        "n_elementos": 0,
        "elementos": [],
        "metricas_amostra": {"media_preco_m2": None, "cv": None},
    }
}


def test_detecta_grau_iii_com_zero_elementos():
    p = detectar_contradicoes(CREW_REAL)
    assert any("grau III com apenas 0" in x for x in p)


def test_detecta_n_elementos_divergente():
    p = detectar_contradicoes({"amostra_final": {"n_elementos": 12, "elementos": [{"a": 1}]}})
    assert any("difere da lista" in x for x in p)


def test_processa_retorno_real_da_crew():
    r = processar_retorno_agente(CREW_REAL)
    assert r["status"] == "sucesso"
    assert r["candidatos"] == []                      # nada aproveitável
    assert any("grau III" in c for c in r["contradicoes"])
    assert "grau_fundamentacao" in r["campos_ignorados"]


def test_processa_retorno_util():
    payload = {"amostra_final": {"grau_fundamentacao": "III", "n_elementos": 1,
                                 "elementos": [BOM]}}
    r = processar_retorno_agente(payload)
    assert len(r["candidatos"]) == 1
    assert r["candidatos"][0]["preco_m2"] == 5000.0


def test_processa_lista_direta():
    r = processar_retorno_agente([BOM])
    assert len(r["candidatos"]) == 1


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def test_endpoint_estrategia():
    resp = client.post("/api/estrategia", json={
        "ficha": {"tipo": "terreno", "area_terreno": 450, "zoneamento": "ZM"}})
    assert resp.status_code == 200, resp.text
    b = resp.json()
    assert b["tipo_normalizado"] == "terreno"
    assert len(b["regras_expansao"]) == 6


def test_endpoint_estrategia_ficha_vazia():
    assert client.post("/api/estrategia", json={"ficha": {}}).status_code == 422


def test_endpoint_estrategia_refino_sem_provedor_avisa():
    resp = client.post("/api/estrategia", json={
        "ficha": {"tipo": "casa", "area_construida": 150}, "refino_ia": True})
    assert resp.status_code == 200
    assert any("nenhum provedor" in a for a in resp.json()["avisos"])


def test_endpoint_filtrar_agente():
    resp = client.post("/api/agente/filtrar", json={"retorno": {"elementos": [BOM]}})
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["candidatos"]) == 1


def test_endpoint_filtrar_texto_markdown():
    txt = '```json\n{"elementos": [{"endereco":"R X","preco":400000,"area_construida":80,"url":"https://a.com/1"}]}\n```'
    resp = client.post("/api/agente/filtrar", json={"retorno": txt})
    assert resp.status_code == 200
    assert resp.json()["candidatos"][0]["preco_m2"] == 5000.0


def test_endpoint_filtrar_sem_json_da_422():
    assert client.post("/api/agente/filtrar",
                       json={"retorno": "não tem json"}).status_code == 422
