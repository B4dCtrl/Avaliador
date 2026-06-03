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

from calculadora import (
    aplicar_transformacoes,
    calcular_durbin_watson,
    calcular_elasticidade,
    calcular_regressao,
    correlacao_matrix,
    detectar_outliers,
    preparar_dados_graficos,
    transformar_variavel,
)
from exportador import gerar_pdf, gerar_word
from models import DadosRegressaoRequest, ExportarRequest, RegressaoResponse
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

    resposta = {
        "status": "sucesso",
        "regressao": {
            "r_squared": round(float(modelo_fit.rsquared), 6),
            "r_ajustado": round(float(modelo_fit.rsquared_adj), 6),
            "f_calculado": round(float(modelo_fit.fvalue), 4),
            "p_valor_f": round(float(modelo_fit.f_pvalue), 8),
            "durbin_watson": round(dw, 4),
            "desvio_padrao": round(float(modelo_fit.mse_resid ** 0.5), 6),
            "observacoes": int(modelo_fit.nobs),
            "variaveis": len(nomes_vars),
        },
        "coeficientes": coeficientes_response,
        "intercepto": round(float(modelo_fit.params[0]), 6),
        "correlacao_matrix": matriz_corr,
        "outliers": outliers,
        "validacao_nbr": validacao,
        "graficos": graficos,
    }

    logger.info("Regressão concluída: R²=%.4f, DW=%.4f", modelo_fit.rsquared, dw)
    return resposta


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
