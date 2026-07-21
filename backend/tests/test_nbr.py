"""
Testes dos critérios normativos (NBR 14653-1/2):
grau de fundamentação, grau de precisão, campo de arbítrio, micronumerosidade.
"""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from nbr_grau import (
    amplitude_pct,
    avaliar_grau_fundamentacao,
    campo_arbitrio,
    grau_precisao,
    minimo_por_caracteristica,
    verificar_micronumerosidade,
)


# ---------------------------------------------------------------------------
# Grau de fundamentação — Tabela da NBR 14653-2
# ---------------------------------------------------------------------------

def test_fundamentacao_item_quantidade_limites():
    # k=2 → III: n>=18 | II: n>=12 | I: n>=9
    r = avaliar_grau_fundamentacao(None, [0.01], 0.001, n=18, k=2)
    assert r["itens"]["quantidade_dados"]["grau"] == "III"
    r = avaliar_grau_fundamentacao(None, [0.01], 0.001, n=17, k=2)
    assert r["itens"]["quantidade_dados"]["grau"] == "II"
    r = avaliar_grau_fundamentacao(None, [0.01], 0.001, n=12, k=2)
    assert r["itens"]["quantidade_dados"]["grau"] == "II"
    r = avaliar_grau_fundamentacao(None, [0.01], 0.001, n=11, k=2)
    assert r["itens"]["quantidade_dados"]["grau"] == "I"
    r = avaliar_grau_fundamentacao(None, [0.01], 0.001, n=9, k=2)
    assert r["itens"]["quantidade_dados"]["grau"] == "I"
    r = avaliar_grau_fundamentacao(None, [0.01], 0.001, n=8, k=2)
    assert r["itens"]["quantidade_dados"]["grau"] == "Fora dos critérios"


def test_fundamentacao_item_t_limites():
    base = dict(amp=None, p_valor_f=0.001, n=30, k=2)
    assert avaliar_grau_fundamentacao(p_valores_coefs=[0.10], **base)["itens"]["significancia_regressores"]["grau"] == "III"
    assert avaliar_grau_fundamentacao(p_valores_coefs=[0.11], **base)["itens"]["significancia_regressores"]["grau"] == "II"
    assert avaliar_grau_fundamentacao(p_valores_coefs=[0.20], **base)["itens"]["significancia_regressores"]["grau"] == "II"
    assert avaliar_grau_fundamentacao(p_valores_coefs=[0.30], **base)["itens"]["significancia_regressores"]["grau"] == "I"
    assert avaliar_grau_fundamentacao(p_valores_coefs=[0.31], **base)["itens"]["significancia_regressores"]["grau"] == "Fora dos critérios"


def test_fundamentacao_item_f_limites():
    base = dict(amp=None, p_valores_coefs=[0.01], n=30, k=2)
    assert avaliar_grau_fundamentacao(p_valor_f=0.01, **base)["itens"]["significancia_modelo_f"]["grau"] == "III"
    assert avaliar_grau_fundamentacao(p_valor_f=0.02, **base)["itens"]["significancia_modelo_f"]["grau"] == "II"
    assert avaliar_grau_fundamentacao(p_valor_f=0.05, **base)["itens"]["significancia_modelo_f"]["grau"] == "I"
    assert avaliar_grau_fundamentacao(p_valor_f=0.06, **base)["itens"]["significancia_modelo_f"]["grau"] == "Fora dos critérios"


def test_fundamentacao_grau_final_conservador():
    # item t no grau I derruba o grau final para I mesmo com os outros em III
    r = avaliar_grau_fundamentacao(None, [0.25], 0.001, n=30, k=2)
    assert r["grau"] == "I"


# ---------------------------------------------------------------------------
# Grau de precisão
# ---------------------------------------------------------------------------

def test_grau_precisao_limites():
    assert grau_precisao(30.0) == "III"
    assert grau_precisao(30.1) == "II"
    assert grau_precisao(40.0) == "II"
    assert grau_precisao(40.1) == "I"
    assert grau_precisao(50.0) == "I"
    assert grau_precisao(50.1) == "Fora dos critérios"


def test_amplitude_pct():
    # IC de 90–110 em torno de 100 → amplitude 20%
    assert abs(amplitude_pct(100.0, 90.0, 110.0) - 20.0) < 1e-9


# ---------------------------------------------------------------------------
# Campo de arbítrio (±15% fixo — NBR 14653-1)
# ---------------------------------------------------------------------------

def test_campo_arbitrio_15pct():
    inf, sup = campo_arbitrio(200000.0)
    assert abs(inf - 170000.0) < 1e-6
    assert abs(sup - 230000.0) < 1e-6
    # grau é ignorado (compatibilidade)
    inf2, sup2 = campo_arbitrio(200000.0, "I")
    assert (inf2, sup2) == (inf, sup)


# ---------------------------------------------------------------------------
# Micronumerosidade
# ---------------------------------------------------------------------------

def test_minimo_por_caracteristica():
    assert minimo_por_caracteristica(10) == 3
    assert minimo_por_caracteristica(30) == 3
    assert minimo_por_caracteristica(31) == 4    # ceil(3.1)
    assert minimo_por_caracteristica(50) == 5
    assert minimo_por_caracteristica(100) == 10
    assert minimo_por_caracteristica(101) == 10
    assert minimo_por_caracteristica(500) == 10


def test_micronumerosidade_detecta_nivel_raro():
    # 'garagens' com nível 3 aparecendo só 1 vez em 10 dados (mínimo 3)
    valores = {"garagens": [1, 1, 1, 2, 2, 2, 2, 1, 2, 3]}
    r = verificar_micronumerosidade(valores)
    assert not r["ok"]
    assert any("garagens" in a for a in r["avisos"])


def test_micronumerosidade_ok():
    valores = {"garagens": [1, 1, 1, 2, 2, 2]}
    r = verificar_micronumerosidade(valores)
    assert r["ok"]


def test_micronumerosidade_ignora_continua():
    # variável contínua (muitos valores distintos) não entra na regra
    valores = {"area": [100.5, 120.3, 130.1, 145.9, 152.2, 161.7, 170.4, 181.1]}
    r = verificar_micronumerosidade(valores)
    assert r["ok"]
    assert "area" not in r["detalhes"]
