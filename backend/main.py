"""
Avaliador — Backend FastAPI
Regressão linear para avaliação imobiliária conforme NBR 14653-02.
"""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import pandas as pd

from bestfit import bestfit, serializar_ranking
from calculadora import (
    aplicar_transformacoes,
    calcular_durbin_watson,
    calcular_elasticidade,
    calcular_regressao,
    correlacao_matrix,
    detectar_outliers,
    preparar_dados_graficos,
    transformacao_inversa,
    transformar_variavel,
)
from diagnosticos import diagnostico_completo
from exportador import gerar_pdf, gerar_word
from models import (
    AvaliarImovelRequest,
    BestfitRequest,
    DadosRegressaoRequest,
    ExportarRequest,
    RegressaoResponse,
)
from nbr_grau import (
    amplitude_pct,
    avaliar_grau_fundamentacao,
    campo_arbitrio,
    grau_precisao,
)
from validador import validar_nbr_14653

# ---------------------------------------------------------------------------
# Configuração de logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("avaliador")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Avaliador API",
    description="Backend para avaliação imobiliária com regressão linear OLS — NBR 14653-02",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pasta temporária para exports
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)
app.mount("/download", StaticFiles(directory=str(DOWNLOADS_DIR)), name="download")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["util"])
def health():
    """Verifica se o serviço está no ar."""
    return {"status": "ok", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# POST /api/calcular-regressao
# ---------------------------------------------------------------------------

@app.post("/api/calcular-regressao", tags=["regressao"])
def calcular_regressao_endpoint(request: DadosRegressaoRequest) -> Dict[str, Any]:
    """
    Executa regressão linear OLS com transformações de variáveis.

    Retorna todos os cálculos estatísticos + dados para gráficos Plotly.
    """
    dados = request.dados
    logger.info(
        "Calculando regressão: dep=%s, vars=%s, n=%d",
        dados.variavel_dependente,
        list(dados.variaveis_independentes.keys()),
        len(dados.valores_dependentes),
    )

    # Variável dependente
    y = np.array(dados.valores_dependentes, dtype=float)

    # Aplicar transformações às independentes
    try:
        variaveis_dict = {
            nome: {"valores": vi.valores, "transformacao": vi.transformacao}
            for nome, vi in dados.variaveis_independentes.items()
        }
        X, nomes_vars = aplicar_transformacoes(variaveis_dict)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Regressão OLS
    try:
        modelo_fit = calcular_regressao(y, X)
    except Exception as e:
        logger.error("Erro na regressão: %s", e)
        raise HTTPException(status_code=500, detail=f"Erro no cálculo OLS: {e}")

    # Extrair resultados
    coefs_sem_intercepto = modelo_fit.params[1:]  # índice 0 é const
    erros_sem_intercepto = modelo_fit.bse[1:]
    pvalores_sem_intercepto = modelo_fit.pvalues[1:]
    tvalores_sem_intercepto = modelo_fit.tvalues[1:]
    ic_sem_intercepto = modelo_fit.conf_int()[1:]

    media_y = float(np.mean(y))

    coeficientes_response = []
    for i, nome in enumerate(nomes_vars):
        vi = dados.variaveis_independentes[nome]
        coef = float(coefs_sem_intercepto[i])
        media_x_transf = float(np.mean(X[:, i]))
        media_x_orig = float(np.mean(vi.valores))

        elasticidade = calcular_elasticidade(
            coef, vi.transformacao, media_x_transf, media_y, media_x_orig
        )

        coeficientes_response.append({
            "variavel": nome,
            "transformacao": vi.transformacao,
            "coeficiente": round(coef, 6),
            "elasticidade": round(elasticidade, 6),
            "t_calculado": round(float(tvalores_sem_intercepto[i]), 4),
            "p_valor": round(float(pvalores_sem_intercepto[i]), 6),
            "significancia_percent": round(float(pvalores_sem_intercepto[i]) * 100, 4),
            "erro_padrao": round(float(erros_sem_intercepto[i]), 6),
            "intervalo_confianca_95": [
                round(float(np.asarray(ic_sem_intercepto)[i, 0]), 4),
                round(float(np.asarray(ic_sem_intercepto)[i, 1]), 4),
            ],
        })

    # Durbin-Watson
    dw = calcular_durbin_watson(modelo_fit.resid)

    # Outliers
    outliers = detectar_outliers(modelo_fit.resid)

    # Correlação — incluir dependente e independentes (originais)
    dados_corr: Dict[str, Any] = {dados.variavel_dependente: dados.valores_dependentes}
    for nome, vi in dados.variaveis_independentes.items():
        dados_corr[nome] = vi.valores
    matriz_corr = correlacao_matrix(dados_corr)

    # Validação NBR
    validacao = validar_nbr_14653(
        n_observacoes=len(y),
        n_variaveis=len(nomes_vars),
        r_squared=float(modelo_fit.rsquared),
        p_valores_coefs=pvalores_sem_intercepto.tolist(),
        nomes_variaveis=nomes_vars,
        matriz_correlacao=matriz_corr["dados"],
        nomes_correlacao=matriz_corr["variaveis"],
        durbin_watson=dw,
    )

    # Dados para gráficos
    valores_originais = {n: vi.valores for n, vi in dados.variaveis_independentes.items()}
    graficos = preparar_dados_graficos(y, X, modelo_fit, nomes_vars, valores_originais)

    diagnosticos = diagnostico_completo(modelo_fit)
    grau_fund = avaliar_grau_fundamentacao(
        amp=None,
        p_valores_coefs=pvalores_sem_intercepto.tolist(),
        p_valor_f=float(modelo_fit.f_pvalue),
        n=int(modelo_fit.nobs),
        k=len(nomes_vars),
    )

    resposta = {
        "status": "sucesso",
        "regressao": {
            "r_squared": round(float(modelo_fit.rsquared), 6),
            "r_ajustado": round(float(modelo_fit.rsquared_adj), 6),
            "f_calculado": round(float(modelo_fit.fvalue), 4),
            "p_valor_f": round(float(modelo_fit.f_pvalue), 8),
            "durbin_watson": round(dw, 4),
            "desvio_padrao": round(float(modelo_fit.mse_resid ** 0.5), 6),
            "aic": round(float(modelo_fit.aic), 4),
            "bic": round(float(modelo_fit.bic), 4),
            "observacoes": int(modelo_fit.nobs),
            "variaveis": len(nomes_vars),
        },
        "coeficientes": coeficientes_response,
        "intercepto": round(float(modelo_fit.params[0]), 6),
        "correlacao_matrix": matriz_corr,
        "outliers": outliers,
        "diagnosticos": diagnosticos,
        "grau_fundamentacao": grau_fund,
        "validacao_nbr": validacao,
        "graficos": graficos,
    }

    logger.info("Regressão concluída: R²=%.4f, DW=%.4f", modelo_fit.rsquared, dw)
    return resposta


# ---------------------------------------------------------------------------
# POST /api/bestfit — auto-ranking de transformações
# ---------------------------------------------------------------------------

@app.post("/api/bestfit", tags=["regressao"])
def bestfit_endpoint(request: BestfitRequest) -> Dict[str, Any]:
    """
    Testa todas as combinações de transformação para as variáveis e
    ranqueia os modelos por AIC, retornando também o melhor com diagnóstico
    completo, intervalos de predição e grau de fundamentação NBR.
    """
    logger.info(
        "Bestfit: dep=%s, indep=%s, transf=%s, n=%d",
        request.variavel_dependente,
        request.variaveis_independentes,
        request.transformacoes_testar,
        len(request.dados),
    )

    df = pd.DataFrame(request.dados)
    faltando = [c for c in [request.variavel_dependente, *request.variaveis_independentes] if c not in df.columns]
    if faltando:
        raise HTTPException(status_code=422, detail=f"Colunas ausentes nos dados: {faltando}")

    ranking = bestfit(
        df,
        request.variavel_dependente,
        request.variaveis_independentes,
        transformacoes=request.transformacoes_testar,
        excluir_indices=request.excluir_indices,
        top_n=request.top_n,
    )

    if not ranking:
        raise HTTPException(status_code=422, detail="Nenhum modelo válido encontrado.")

    melhor = ranking[0]
    modelo = melhor["_modelo"]
    dados_usados = melhor["_dados_usados"]
    transf_y = melhor["transformacoes"][request.variavel_dependente]

    # Diagnósticos completos
    diagnosticos = diagnostico_completo(modelo)

    # Predição com intervalo no espaço original
    alpha = 1.0 - request.nivel_confianca
    grau_fund = None
    amp = None
    grau_prec = None
    campo_inf = None
    campo_sup = None
    try:
        import statsmodels.api as sm
        X_pred = sm.add_constant(dados_usados[request.variaveis_independentes], has_constant="add")
        pred = modelo.get_prediction(X_pred).summary_frame(alpha=alpha)
        y_hat_t = pred["mean"].values
        y_lwr_t = pred["obs_ci_lower"].values
        y_upr_t = pred["obs_ci_upper"].values

        y_hat = transformacao_inversa(y_hat_t, transf_y)
        y_lwr = transformacao_inversa(y_lwr_t, transf_y)
        y_upr = transformacao_inversa(y_upr_t, transf_y)

        mean_hat = float(np.nanmean(y_hat))
        mean_lwr = float(np.nanmean(y_lwr))
        mean_upr = float(np.nanmean(y_upr))
        amp = round(amplitude_pct(mean_hat, mean_lwr, mean_upr), 4)
        grau_prec = grau_precisao(amp)
        campo_inf, campo_sup = campo_arbitrio(mean_hat, grau_prec)
        campo_inf = round(campo_inf, 4)
        campo_sup = round(campo_sup, 4)
    except Exception as e:
        logger.warning("Predição/amplitude falhou: %s", e)

    # Grau de fundamentação completo
    pvalores_indep = [
        float(modelo.pvalues[c]) for c in modelo.params.index if c != "const"
    ]
    grau_fund = avaliar_grau_fundamentacao(
        amp=amp,
        p_valores_coefs=pvalores_indep,
        p_valor_f=float(modelo.f_pvalue),
        n=int(modelo.nobs),
        k=len(request.variaveis_independentes),
    )

    return {
        "status": "sucesso",
        "melhor_modelo": {
            "transformacoes": melhor["transformacoes"],
            "transformacao_y": transf_y,
            "r2": melhor["r2"],
            "r2_ajustado": melhor["r2_ajustado"],
            "f_stat": melhor["f_stat"],
            "f_p_valor": melhor["f_p_valor"],
            "aic": melhor["aic"],
            "bic": melhor["bic"],
            "intercepto": round(float(modelo.params.get("const", 0.0)), 6),
            "coeficientes": [
                {
                    "variavel": nome,
                    "transformacao": melhor["transformacoes"].get(nome, "nenhuma"),
                    "coeficiente": round(float(modelo.params[nome]), 6),
                    "erro_padrao": round(float(modelo.bse[nome]), 6),
                    "t_stat": round(float(modelo.tvalues[nome]), 4),
                    "p_valor": round(float(modelo.pvalues[nome]), 6),
                }
                for nome in modelo.params.index if nome != "const"
            ],
            "residuos": [round(float(r), 6) for r in modelo.resid],
            "valores_ajustados": [round(float(v), 6) for v in modelo.fittedvalues],
        },
        "diagnosticos": diagnosticos,
        "amplitude_pct": amp,
        "grau_precisao": grau_prec,
        "campo_arbitrio_inferior": campo_inf,
        "campo_arbitrio_superior": campo_sup,
        "grau_fundamentacao": grau_fund,
        "ranking": serializar_ranking(ranking),
        "n_modelos_testados": len(ranking),
    }


# ---------------------------------------------------------------------------
# POST /api/avaliar-imovel — predição pontual de um imóvel-alvo
# ---------------------------------------------------------------------------

@app.post("/api/avaliar-imovel", tags=["regressao"])
def avaliar_imovel(request: AvaliarImovelRequest) -> Dict[str, Any]:
    """
    Estima o valor de um imóvel-alvo a partir de um modelo (transformações
    dadas) ajustado ao dataset. Retorna valor estimado + intervalo de
    confiança/predição no espaço original da variável dependente.
    """
    import statsmodels.api as sm
    from calculadora import transformar_variavel

    df = pd.DataFrame(request.dados)
    y_name = request.variavel_dependente
    x_names = request.variaveis_independentes

    faltando = [c for c in [y_name, *x_names] if c not in df.columns]
    if faltando:
        raise HTTPException(status_code=422, detail=f"Colunas ausentes: {faltando}")

    if request.excluir_indices:
        df = df.drop(index=[i for i in request.excluir_indices if i in df.index])

    transf_y = request.transformacoes.get(y_name, "nenhuma")

    # Monta matriz transformada
    try:
        y_t = transformar_variavel(df[y_name].astype(float).tolist(), transf_y)
        cols = {}
        for x in x_names:
            tx = request.transformacoes.get(x, "nenhuma")
            cols[x] = transformar_variavel(df[x].astype(float).tolist(), tx)
        X_df = pd.DataFrame(cols)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Remove linhas inválidas
    X_df["_y"] = y_t
    X_df = X_df.replace([np.inf, -np.inf], np.nan).dropna()
    if len(X_df) < len(x_names) + 2:
        raise HTTPException(status_code=422, detail="Dados insuficientes após transformação.")

    y_fit = X_df["_y"]
    X_fit = sm.add_constant(X_df[x_names], has_constant="add")
    modelo = sm.OLS(y_fit, X_fit).fit()

    # Transforma o imóvel-alvo
    try:
        linha = {"const": 1.0}
        for x in x_names:
            if x not in request.imovel_alvo:
                raise HTTPException(status_code=422, detail=f"Falta valor de '{x}' no imóvel-alvo.")
            tx = request.transformacoes.get(x, "nenhuma")
            linha[x] = float(transformar_variavel([request.imovel_alvo[x]], tx)[0])
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    X_alvo = pd.DataFrame([linha])[["const", *x_names]]

    alpha = 1.0 - request.nivel_confianca
    pred = modelo.get_prediction(X_alvo).summary_frame(alpha=alpha)
    y_hat_t = float(pred["mean"].iloc[0])
    y_lwr_t = float(pred["obs_ci_lower"].iloc[0])
    y_upr_t = float(pred["obs_ci_upper"].iloc[0])
    mean_lwr_t = float(pred["mean_ci_lower"].iloc[0])
    mean_upr_t = float(pred["mean_ci_upper"].iloc[0])

    valor = float(transformacao_inversa(np.array([y_hat_t]), transf_y)[0])
    ic_pred_inf = float(transformacao_inversa(np.array([y_lwr_t]), transf_y)[0])
    ic_pred_sup = float(transformacao_inversa(np.array([y_upr_t]), transf_y)[0])
    ic_conf_inf = float(transformacao_inversa(np.array([mean_lwr_t]), transf_y)[0])
    ic_conf_sup = float(transformacao_inversa(np.array([mean_upr_t]), transf_y)[0])

    # Ordena limites (transformações inversas podem inverter ordem)
    pred_inf, pred_sup = sorted([ic_pred_inf, ic_pred_sup])
    conf_inf, conf_sup = sorted([ic_conf_inf, ic_conf_sup])

    amp = amplitude_pct(valor, pred_inf, pred_sup)
    grau = grau_precisao(amp)
    campo_inf, campo_sup = campo_arbitrio(valor, grau)

    logger.info("Imóvel-alvo avaliado: valor=%.2f, grau=%s", valor, grau)

    return {
        "status": "sucesso",
        "valor_estimado": round(valor, 2),
        "intervalo_predicao": [round(pred_inf, 2), round(pred_sup, 2)],
        "intervalo_confianca_media": [round(conf_inf, 2), round(conf_sup, 2)],
        "nivel_confianca": request.nivel_confianca,
        "amplitude_pct": round(amp, 2),
        "grau_precisao": grau,
        "campo_arbitrio": [round(campo_inf, 2), round(campo_sup, 2)],
        "transformacao_y": transf_y,
        "imovel_alvo": request.imovel_alvo,
    }


# ---------------------------------------------------------------------------
# POST /api/exportar-word
# ---------------------------------------------------------------------------

@app.post("/api/exportar-word", tags=["export"])
def exportar_word(request: ExportarRequest):
    """Gera laudo completo em formato Word (.docx)."""
    logger.info("Gerando DOCX para imóvel: %s", request.imovel.endereco)
    try:
        conteudo = gerar_word(
            request.resultado_regressao,
            request.imovel.model_dump(),
            request.avaliador.model_dump(),
        )
    except Exception as e:
        logger.error("Erro ao gerar Word: %s", e)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar DOCX: {e}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:6]
    nome_arquivo = f"laudo_{timestamp}_{uid}.docx"
    caminho = DOWNLOADS_DIR / nome_arquivo

    caminho.write_bytes(conteudo)
    tamanho_kb = round(len(conteudo) / 1024, 2)

    return {
        "status": "sucesso",
        "arquivo": nome_arquivo,
        "tamanho_kb": tamanho_kb,
        "url_download": f"/download/{nome_arquivo}",
    }


# ---------------------------------------------------------------------------
# POST /api/exportar-pdf
# ---------------------------------------------------------------------------

@app.post("/api/exportar-pdf", tags=["export"])
def exportar_pdf(request: ExportarRequest):
    """Gera laudo completo em formato PDF."""
    logger.info("Gerando PDF para imóvel: %s", request.imovel.endereco)
    try:
        conteudo = gerar_pdf(
            request.resultado_regressao,
            request.imovel.model_dump(),
            request.avaliador.model_dump(),
        )
    except Exception as e:
        logger.error("Erro ao gerar PDF: %s", e)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {e}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:6]
    nome_arquivo = f"laudo_{timestamp}_{uid}.pdf"
    caminho = DOWNLOADS_DIR / nome_arquivo

    caminho.write_bytes(conteudo)
    tamanho_kb = round(len(conteudo) / 1024, 2)

    return {
        "status": "sucesso",
        "arquivo": nome_arquivo,
        "tamanho_kb": tamanho_kb,
        "url_download": f"/download/{nome_arquivo}",
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
