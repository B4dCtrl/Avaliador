"""
Análise inteligente de amostras para o Avaliador.

Detecta, após o ajuste do modelo, quais amostras (comparáveis) são
outliers ou fogem do padrão da avaliação — considerando também o
imóvel-alvo informado pelo cliente — e recomenda quais desabilitar.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import OLSInfluence

from calculadora import transformar_variavel

logger = logging.getLogger(__name__)


def analisar_amostras(
    dados: List[Dict[str, Any]],
    variavel_dependente: str,
    variaveis_independentes: List[str],
    transformacoes: Dict[str, str],
    imovel_alvo: Optional[Dict[str, float]] = None,
    limiar_residuo: float = 2.0,
) -> Dict[str, Any]:
    """
    Ajusta o modelo e avalia cada amostra.

    Métricas por amostra:
    - residuo_padronizado (studentized): desvio do valor previsto
    - cooks_distance: influência da amostra no modelo
    - leverage (hat): alavancagem
    - distancia_alvo: distância padronizada das características da amostra
      em relação ao imóvel-alvo (0 = idêntico). Só se imovel_alvo for dado.

    Recomenda desabilitar quando a amostra é influente/atípica
    (|resíduo| > limiar OU cook > 4/n OU leverage alto) — e, havendo alvo,
    dá prioridade às que também estão distantes do imóvel avaliando.
    """
    y_t = transformar_variavel(
        [float(d[variavel_dependente]) for d in dados],
        transformacoes.get(variavel_dependente, "nenhuma"),
    )
    cols = {}
    cols_orig = {}
    for x in variaveis_independentes:
        valores = [float(d[x]) for d in dados]
        cols_orig[x] = np.array(valores, dtype=float)
        cols[x] = transformar_variavel(valores, transformacoes.get(x, "nenhuma"))

    X = np.column_stack([cols[x] for x in variaveis_independentes])
    X_const = sm.add_constant(X, has_constant="add")
    modelo = sm.OLS(y_t, X_const).fit()

    influence = OLSInfluence(modelo)
    student = influence.resid_studentized_internal
    cooks = influence.cooks_distance[0]
    leverage = influence.hat_matrix_diag

    n = len(dados)
    limiar_cook = 4.0 / n
    limiar_leverage = 2.0 * (len(variaveis_independentes) + 1) / n

    # Distância ao imóvel-alvo (no espaço das variáveis originais, padronizado)
    distancias = None
    if imovel_alvo:
        medias = {x: np.mean(cols_orig[x]) for x in variaveis_independentes}
        desvios = {x: (np.std(cols_orig[x]) or 1.0) for x in variaveis_independentes}
        alvo_z = {
            x: (float(imovel_alvo.get(x, medias[x])) - medias[x]) / desvios[x]
            for x in variaveis_independentes
        }
        distancias = []
        for i in range(n):
            soma = 0.0
            for x in variaveis_independentes:
                z = (cols_orig[x][i] - medias[x]) / desvios[x]
                soma += (z - alvo_z[x]) ** 2
            distancias.append(float(np.sqrt(soma)))

    dist_max = max(distancias) if distancias else 1.0

    amostras = []
    recomendados = []
    for i in range(n):
        resid_alto = abs(float(student[i])) > limiar_residuo
        cook_alto = float(cooks[i]) > limiar_cook
        lev_alto = float(leverage[i]) > limiar_leverage
        atipica = resid_alto or cook_alto or lev_alto

        motivos = []
        if resid_alto:
            motivos.append(f"resíduo padronizado {student[i]:.2f} (>|{limiar_residuo}|)")
        if cook_alto:
            motivos.append(f"Cook {cooks[i]:.3f} (>{limiar_cook:.3f})")
        if lev_alto:
            motivos.append(f"alavancagem {leverage[i]:.3f} alta")

        dist = distancias[i] if distancias else None
        if dist is not None and dist > 0.66 * dist_max and atipica:
            motivos.append("distante do imóvel-alvo")

        amostras.append({
            "indice": i,
            "residuo_padronizado": round(float(student[i]), 4),
            "cooks_distance": round(float(cooks[i]), 4),
            "leverage": round(float(leverage[i]), 4),
            "distancia_alvo": round(dist, 4) if dist is not None else None,
            "atipica": atipica,
            "recomendar_desabilitar": atipica,
            "motivos": motivos,
        })
        if atipica:
            recomendados.append(i)

    logger.info("Análise de amostras: %d atípicas de %d", len(recomendados), n)

    # --- Simulação: como fica o modelo SE remover as amostras recomendadas ---
    from nbr_grau import avaliar_grau_fundamentacao

    def _grau(mod, n_obs):
        pvals = [float(mod.pvalues[i]) for i in range(1, len(mod.params))]
        return avaliar_grau_fundamentacao(
            amp=None, p_valores_coefs=pvals, p_valor_f=float(mod.f_pvalue),
            n=int(n_obs), k=len(variaveis_independentes),
        )["grau"]

    grau_atual = _grau(modelo, n)
    r2_atual = float(modelo.rsquared)

    comparacao = {
        "grau_atual": grau_atual,
        "r2_atual": round(r2_atual, 6),
        "grau_apos": grau_atual,
        "r2_apos": round(r2_atual, 6),
        "melhora": False,
        "piora": False,
    }
    recomendacao_texto = "Nenhuma amostra atípica detectada — o conjunto está consistente."

    if recomendados:
        manter = [i for i in range(n) if i not in set(recomendados)]
        if len(manter) >= len(variaveis_independentes) + 2:
            X_apos = X[manter]
            y_apos = y_t[manter]
            modelo_apos = sm.OLS(y_apos, sm.add_constant(X_apos, has_constant="add")).fit()
            grau_apos = _grau(modelo_apos, len(manter))
            r2_apos = float(modelo_apos.rsquared)
            ordem = {"Fora dos critérios": 0, "I": 1, "II": 2, "III": 3}
            melhora = ordem.get(grau_apos, 0) > ordem.get(grau_atual, 0) or r2_apos > r2_atual + 0.01
            piora = ordem.get(grau_apos, 0) < ordem.get(grau_atual, 0)
            comparacao.update({
                "grau_apos": grau_apos,
                "r2_apos": round(r2_apos, 6),
                "melhora": bool(melhora),
                "piora": bool(piora),
            })
            if piora:
                recomendacao_texto = (
                    f"⚠ Remover estas {len(recomendados)} amostra(s) PIORA a avaliação "
                    f"(grau {grau_atual} → {grau_apos}). O modelo atual já está melhor — "
                    "recomendo NÃO desabilitar."
                )
            elif melhora:
                recomendacao_texto = (
                    f"Remover estas {len(recomendados)} amostra(s) melhora a avaliação "
                    f"(grau {grau_atual} → {grau_apos}, R² {r2_atual:.3f} → {r2_apos:.3f})."
                )
            else:
                recomendacao_texto = (
                    f"{len(recomendados)} amostra(s) atípica(s) detectada(s), mas remover não muda "
                    f"o grau ({grau_atual}). Avalie caso a caso — a decisão é do avaliador."
                )
        else:
            recomendacao_texto = (
                "Foram detectadas amostras atípicas, mas removê-las deixaria dados de menos "
                "para a regressão. Cadastre mais amostras antes de desabilitar."
            )

    return {
        "status": "sucesso",
        "n_amostras": n,
        "limiares": {
            "residuo": limiar_residuo,
            "cooks": round(limiar_cook, 4),
            "leverage": round(limiar_leverage, 4),
        },
        "amostras": amostras,
        "recomendar_desabilitar": recomendados,
        "r2_atual": round(r2_atual, 6),
        "comparacao": comparacao,
        "recomendacao_texto": recomendacao_texto,
    }
