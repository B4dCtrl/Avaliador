"""Testes do motor de comparáveis (score multicritério)."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app
from comparaveis import pontuar_comparavel, ranquear_comparaveis, similaridade_territorial

client = TestClient(app)

ALVO = {
    "tipo_imovel": "casa", "area_terreno": 360, "area_construida": 220,
    "padrao_construtivo": "medio", "conservacao": "bom", "idade": 10,
    "dormitorios": 3, "banheiros": 2, "vagas": 2, "zoneamento": "ZR-1",
    "bairro": "Centro", "cidade": "Curitiba",
}

TERRITORIO_ALVO = {
    "idh": 0.82, "renda_per_capita": 4500, "densidade_populacional": 4000,
    "escolaridade_media_anos": 11, "indice_seguranca": 7, "infraestrutura": 8,
    "distancia_centro_km": 3,
}


def test_identico_da_100():
    r = pontuar_comparavel(ALVO, {**ALVO, "distancia_km": 0}, TERRITORIO_ALVO)
    # sem perfil territorial do candidato o critério é ignorado, mas o resto é 100
    assert r["similaridade_pct"] == 100.0
    assert r["classe"] == "Excelente"


def test_tipologia_diferente_derruba():
    r = pontuar_comparavel(ALVO, {**ALVO, "tipo_imovel": "apartamento"}, TERRITORIO_ALVO)
    assert r["similaridade_pct"] < 100
    assert r["detalhamento"]["tipo_imovel"]["similaridade_pct"] == 0.0


def test_area_muito_diferente_reduz_score():
    r = pontuar_comparavel(ALVO, {**ALVO, "area_construida": 60}, TERRITORIO_ALVO)
    assert r["detalhamento"]["area_construida"]["similaridade_pct"] < 40


def test_campos_ausentes_redistribuem_peso():
    # candidato só com tipo e área do terreno
    r = pontuar_comparavel(ALVO, {"tipo_imovel": "casa", "area_terreno": 360}, TERRITORIO_ALVO)
    assert "conservacao" in r["criterios_ignorados"]
    assert r["cobertura_pct"] < 100          # menos critérios avaliados
    assert r["similaridade_pct"] == 100.0    # os presentes batem 100%
    # pesos efetivos somam ~1
    soma = sum(d["peso_efetivo"] for d in r["detalhamento"].values())
    assert abs(soma - 1.0) < 1e-6


def test_similaridade_territorial_bairros_equivalentes():
    # outra cidade, mas perfil quase igual
    outro = {**TERRITORIO_ALVO, "renda_per_capita": 4600, "idh": 0.83}
    t = similaridade_territorial(TERRITORIO_ALVO, outro)
    assert t is not None
    assert t["percentual"] > 90


def test_similaridade_territorial_perfil_distinto():
    pobre = {"idh": 0.55, "renda_per_capita": 1200, "densidade_populacional": 12000,
             "escolaridade_media_anos": 6, "indice_seguranca": 3, "infraestrutura": 3,
             "distancia_centro_km": 20}
    t = similaridade_territorial(TERRITORIO_ALVO, pobre)
    assert t["percentual"] < 60


def test_distancia_penaliza():
    perto = pontuar_comparavel(ALVO, {**ALVO, "distancia_km": 1}, TERRITORIO_ALVO)
    longe = pontuar_comparavel(ALVO, {**ALVO, "distancia_km": 25}, TERRITORIO_ALVO)
    assert perto["similaridade_pct"] > longe["similaridade_pct"]


def test_ranqueamento_ordena_e_resume():
    candidatos = [
        {**ALVO, "identificacao": "A", "distancia_km": 20, "area_construida": 120},
        {**ALVO, "identificacao": "B", "distancia_km": 1},
        {**ALVO, "identificacao": "C", "tipo_imovel": "terreno"},
    ]
    r = ranquear_comparaveis(ALVO, candidatos, TERRITORIO_ALVO)
    ids = [c["identificacao"] for c in r["comparaveis"]]
    assert ids[0] == "B"  # o mais parecido primeiro
    assert r["resumo"]["total_avaliados"] == 3
    assert r["resumo"]["similaridade_media"] > 0


def test_filtro_minimo_similaridade():
    candidatos = [
        {**ALVO, "identificacao": "bom", "distancia_km": 1},
        {"identificacao": "ruim", "tipo_imovel": "galpao", "area_terreno": 5000, "area_construida": 3000},
    ]
    r = ranquear_comparaveis(ALVO, candidatos, TERRITORIO_ALVO, minimo_similaridade=80)
    assert all(c["similaridade_pct"] >= 80 for c in r["comparaveis"])
    assert r["resumo"]["total_aceitos"] < r["resumo"]["total_avaliados"]


def test_endpoint_comparaveis():
    payload = {
        "alvo": ALVO,
        "perfil_territorial_alvo": TERRITORIO_ALVO,
        "candidatos": [
            {**ALVO, "identificacao": "Casa X", "fonte": "https://exemplo.com/1",
             "preco": 700000, "distancia_km": 2, "perfil_territorial": TERRITORIO_ALVO},
        ],
    }
    resp = client.post("/api/comparaveis", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "sucesso"
    c = body["comparaveis"][0]
    assert c["similaridade_pct"] > 90
    assert c["fonte"] == "https://exemplo.com/1"
    assert "detalhamento" in c


def test_endpoint_sem_candidatos_da_422():
    resp = client.post("/api/comparaveis", json={"alvo": ALVO, "candidatos": []})
    assert resp.status_code == 422
