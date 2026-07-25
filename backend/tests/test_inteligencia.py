"""
Testes do módulo de inteligência imobiliária.

Location Intelligence: testes de lógica pura + mocks (sem depender de rede).
Comparable Search: pipeline completo determinístico.
"""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app
import location_intelligence as li
from comparable_search import (
    buscar_comparaveis, filtrar_qualidade, territorial_score, META_MINIMA,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Location Intelligence
# ---------------------------------------------------------------------------

def test_cep_invalido():
    r = li.buscar_cep("123")
    assert r["ok"] is False
    assert "8 dígitos" in r["erro"]


def test_cep_com_mock():
    fake = {"cep": "79002-000", "logradouro": "Avenida Calógeras", "bairro": "Centro",
            "localidade": "Campo Grande", "uf": "MS", "ibge": "5002704"}
    with patch.object(li, "_http_json", return_value=fake):
        r = li.buscar_cep("79002000")
    assert r["ok"] is True
    assert r["cidade"] == "Campo Grande"
    assert r["ibge"] == "5002704"


def test_idhm_dataset_local():
    # Campo Grande está no dataset local
    assert "5002704" in li.IDHM_MUNICIPIOS
    assert li.IDHM_MUNICIPIOS["5002704"]["idhm"] == 0.784


def test_indicadores_usa_idhm_local_com_mock():
    with patch.object(li, "_http_json", return_value=None):
        ind = li.indicadores_municipio("5002704", "MS")
    assert ind["idhm"] == 0.784          # veio do dataset local
    assert ind["populacao"] is None      # API mockada como indisponível


def test_indicadores_fallback_uf():
    with patch.object(li, "_http_json", return_value=None):
        ind = li.indicadores_municipio("9999999", "SP")
    assert ind["idhm"] == li.IDHM_UF_MEDIO["SP"]
    assert ind.get("idhm_estimado_por_uf") is True


def test_extrair_valor_sidra():
    resp = [{"resultados": [{"series": [{"serie": {"2021": "962883", "2020": "906092"}}]}]}]
    assert li._extrair_valor_sidra(resp) == 962883.0
    assert li._extrair_valor_sidra([{"resultados": [{"series": [{"serie": {"2021": "-"}}]}]}]) is None


# ---------------------------------------------------------------------------
# Filtros de qualidade
# ---------------------------------------------------------------------------

def test_filtra_sem_metragem_e_sem_preco():
    r = filtrar_qualidade([
        {"identificacao": "A", "preco": 500000, "area_construida": 100},
        {"identificacao": "B", "preco": 500000},                       # sem área
        {"identificacao": "C", "area_construida": 100},                # sem preço
    ])
    assert len(r["aceitos"]) == 1
    motivos = [d["motivo"] for d in r["descartados"]]
    assert "sem metragem" in motivos and "sem preço" in motivos


def test_filtra_duplicados_por_fonte():
    r = filtrar_qualidade([
        {"identificacao": "A", "preco": 500000, "area_construida": 100, "fonte": "http://x/1"},
        {"identificacao": "B", "preco": 600000, "area_construida": 120, "fonte": "http://x/1"},
    ])
    assert len(r["aceitos"]) == 1
    assert any("duplicado" in d["motivo"] for d in r["descartados"])


def test_filtra_anuncio_antigo():
    r = filtrar_qualidade([
        {"identificacao": "velho", "preco": 500000, "area_construida": 100, "idade_anuncio_dias": 900},
    ])
    assert not r["aceitos"]
    assert "antigo" in r["descartados"][0]["motivo"]


def test_filtra_preco_m2_fora_da_curva():
    base = [{"identificacao": f"n{i}", "preco": 500000, "area_construida": 100} for i in range(8)]
    base.append({"identificacao": "absurdo", "preco": 50_000_000, "area_construida": 100})
    r = filtrar_qualidade(base)
    ids = [a["identificacao"] for a in r["aceitos"]]
    assert "absurdo" not in ids
    assert any("fora da curva" in d["motivo"] for d in r["descartados"])


def test_calcula_preco_m2():
    r = filtrar_qualidade([{"identificacao": "A", "preco": 500000, "area_construida": 100}])
    assert r["aceitos"][0]["preco_m2"] == 5000.0


# ---------------------------------------------------------------------------
# Similaridade Territorial Score
# ---------------------------------------------------------------------------

IND_ALVO = {"idh": 0.82, "pib_per_capita": 43000, "renda_media": 3600,
            "densidade_populacional": 119, "populacao": 960000}


def test_territorial_score_regiao_igual():
    t = territorial_score(IND_ALVO, IND_ALVO, distancia_km=0)
    assert t["score"] == 100.0


def test_territorial_score_regiao_distinta():
    outra = {"idh": 0.60, "pib_per_capita": 12000, "renda_media": 1100,
             "densidade_populacional": 900, "populacao": 30000}
    t = territorial_score(IND_ALVO, outra, distancia_km=40)
    assert t["score"] < 60


def test_territorial_score_ignora_campos_ausentes():
    t = territorial_score(IND_ALVO, {"idh": 0.82})
    assert t["score"] == 100.0            # só o critério presente
    assert list(t["detalhes"].keys()) == ["idh"]


# ---------------------------------------------------------------------------
# Pipeline de busca / expansão
# ---------------------------------------------------------------------------

ALVO = {"tipo": "casa", "area_construida": 150, "quartos": 3, "vagas": 2,
        "padrao_construtivo": "medio", "bairro": "Agua Verde", "cidade": "Curitiba"}


def _cand(i, **kw):
    base = {"identificacao": f"Casa {i}", "tipo": "casa", "preco": 750000 + i * 1000,
            "area_construida": 150, "quartos": 3, "vagas": 2,
            "padrao_construtivo": "medio", "bairro": "Agua Verde", "cidade": "Curitiba",
            "distancia_km": 1, "indicadores": IND_ALVO, "fonte": f"http://p/{i}"}
    base.update(kw)
    return base


def test_meta_atingida_no_nivel1():
    candidatos = [_cand(i) for i in range(18)]
    r = buscar_comparaveis(ALVO, candidatos, IND_ALVO)
    assert r["resumo"]["amostras_qualificadas"] >= META_MINIMA
    assert r["resumo"]["suficiente_para_avaliacao"] is True
    assert r["resumo"]["nivel_maximo_usado"] == 1
    # nível 2+ não deve nem executar
    n2 = next(t for t in r["trilha_expansao"] if t["nivel"] == 2)
    assert n2["executado"] is False


def test_expansao_quando_faltam_amostras():
    # 5 no bairro + 15 em outra cidade com indicadores iguais (nível 5/6)
    candidatos = [_cand(i) for i in range(5)]
    candidatos += [_cand(100 + i, bairro="Outro", cidade="Maringa", distancia_km=45) for i in range(15)]
    r = buscar_comparaveis(ALVO, candidatos, IND_ALVO)
    assert r["resumo"]["amostras_qualificadas"] >= META_MINIMA
    assert r["resumo"]["nivel_maximo_usado"] >= 5   # precisou expandir


def test_nivel1_respeita_area_20pct():
    # área 250 está fora de ±20% de 150 -> não entra no nível 1
    candidatos = [_cand(1, area_construida=250)]
    r = buscar_comparaveis(ALVO, candidatos, IND_ALVO, meta_minima=1)
    niveis = [a["nivel_expansao"] for a in r["amostras"]]
    assert 1 not in niveis


def test_tipologia_diferente_nao_entra_nivel1():
    candidatos = [_cand(1, tipo="apartamento")]
    r = buscar_comparaveis(ALVO, candidatos, IND_ALVO, meta_minima=1)
    assert all(a["nivel_expansao"] != 1 for a in r["amostras"])


def test_teto_maximo_de_amostras():
    candidatos = [_cand(i) for i in range(60)]
    r = buscar_comparaveis(ALVO, candidatos, IND_ALVO, meta_maxima=30)
    assert r["resumo"]["amostras_qualificadas"] <= 30


def test_confiabilidade_alta_com_muitas_amostras_proximas():
    r_bom = buscar_comparaveis(ALVO, [_cand(i) for i in range(20)], IND_ALVO)
    r_ruim = buscar_comparaveis(ALVO, [_cand(i) for i in range(3)], IND_ALVO)
    assert r_bom["confiabilidade_busca"] > r_ruim["confiabilidade_busca"]


def test_amostras_ordenadas_por_score():
    candidatos = [_cand(1, area_construida=250, bairro="Longe", cidade="X", distancia_km=40),
                  _cand(2)]
    r = buscar_comparaveis(ALVO, candidatos, IND_ALVO, meta_minima=1)
    scores = [a["score"] for a in r["amostras"]]
    assert scores == sorted(scores, reverse=True)


def test_provider_e_chamado_na_expansao():
    chamado = {"n": 0}

    def provider(alvo, nivel):
        chamado["n"] += 1
        return [_cand(200 + nivel)]

    buscar_comparaveis(ALVO, [_cand(1)], IND_ALVO, provider=provider)
    assert chamado["n"] > 0   # foi chamado porque faltavam amostras


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def test_endpoint_comparables():
    payload = {
        "imovel": ALVO,
        "candidatos": [_cand(i) for i in range(16)],
        "indicadores_regiao": IND_ALVO,
    }
    resp = client.post("/api/comparables", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "sucesso"
    assert "amostras" in body and "confiabilidade_busca" in body and "dados_regiao" in body
    a = body["amostras"][0]
    assert {"endereco", "preco", "area", "preco_m2", "score"} <= set(a.keys())


def test_endpoint_cep_invalido():
    resp = client.get("/api/cep/123")
    assert resp.status_code == 404


def test_endpoint_localizacao_cep_invalido():
    resp = client.post("/api/localizacao", json={"cep": "000"})
    assert resp.status_code == 422
