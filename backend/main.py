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
from analise import analisar_amostras
from saneamento import DadosInvalidos, sanear_dataset
from viabilidade import analisar_viabilidade
from comparaveis import ranquear_comparaveis, similaridade_territorial
from location_intelligence import perfil_localizacao, buscar_cep
from comparable_search import buscar_comparaveis
from fontes_dados import buscar_em_fontes, listar_fontes
from estrategia import gerar_estrategia
from crew_bridge import processar_retorno_agente
from models import (
    AnalisarAmostrasRequest,
    AvaliarImovelRequest,
    BestfitRequest,
    DadosRegressaoRequest,
    BuscarFontesRequest,
    ComparablesRequest,
    ComparaveisRequest,
    EstrategiaRequest,
    ExportarRequest,
    LocalizacaoRequest,
    RetornoAgenteRequest,
    RegressaoResponse,
    ViabilidadeRequest,
)
from nbr_grau import (
    amplitude_pct,
    avaliar_grau_fundamentacao,
    campo_arbitrio,
    grau_precisao,
    verificar_micronumerosidade,
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

    try:
        dados_limpos, avisos_saneamento = sanear_dataset(
            request.dados, request.variavel_dependente, request.variaveis_independentes
        )
    except DadosInvalidos as e:
        raise HTTPException(status_code=422, detail=str(e))

    df = pd.DataFrame(dados_limpos)

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

    # Arbítrio do avaliador: usar o modelo escolhido do ranking, se indicado
    melhor = ranking[0]
    if request.transformacoes_escolhidas:
        escolhido = next(
            (r for r in ranking if r["transformacoes"] == request.transformacoes_escolhidas),
            None,
        )
        if escolhido is None:
            raise HTTPException(
                status_code=422,
                detail="Modelo escolhido não encontrado no ranking. Recalcule e escolha novamente.",
            )
        melhor = escolhido
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
    poder_predicao = None
    try:
        import statsmodels.api as sm
        X_pred = sm.add_constant(dados_usados[request.variaveis_independentes], has_constant="add")
        pred = modelo.get_prediction(X_pred).summary_frame(alpha=alpha)
        y_hat_t = pred["mean"].values

        y_hat = transformacao_inversa(y_hat_t, transf_y)
        # IC de 80% da MÉDIA (grau de precisão usa o IC da estimativa central — NBR 14653-2)
        y_ic_lwr = transformacao_inversa(pred["mean_ci_lower"].values, transf_y)
        y_ic_upr = transformacao_inversa(pred["mean_ci_upper"].values, transf_y)

        mean_hat = float(np.nanmean(y_hat))
        mean_lwr = float(np.nanmean(np.minimum(y_ic_lwr, y_ic_upr)))
        mean_upr = float(np.nanmean(np.maximum(y_ic_lwr, y_ic_upr)))
        amp = round(amplitude_pct(mean_hat, mean_lwr, mean_upr), 4)
        grau_prec = grau_precisao(amp)
        campo_inf, campo_sup = campo_arbitrio(mean_hat)
        campo_inf = round(campo_inf, 4)
        campo_sup = round(campo_sup, 4)

        # Poder de predição: observado × estimado no espaço original
        y_obs = dados_usados[request.variavel_dependente].values
        y_obs_orig = transformacao_inversa(np.asarray(y_obs, dtype=float), transf_y)
        obs_l = [round(float(v), 4) for v in y_obs_orig]
        est_l = [round(float(v), 4) for v in y_hat]
        desvios = [
            abs(e - o) / o * 100 if o else 0.0 for o, e in zip(obs_l, est_l)
        ]
        dentro_20 = sum(1 for d in desvios if d <= 20.0)
        poder_predicao = {
            "observado": obs_l,
            "estimado": est_l,
            "desvio_medio_pct": round(float(np.mean(desvios)), 2) if desvios else 0.0,
            "pct_dentro_20": round(dentro_20 / len(desvios) * 100, 1) if desvios else 0.0,
        }
    except Exception as e:
        logger.warning("Predição/amplitude falhou: %s", e)

    # Micronumerosidade (variáveis com poucos níveis distintos)
    micro = verificar_micronumerosidade({
        x: [float(r[x]) for r in dados_limpos] for x in request.variaveis_independentes
    })

    # Sugestões de refinamento (stepwise manual): variáveis fracas
    sugestoes: list = []
    for c in modelo.params.index:
        if c == "const":
            continue
        p = float(modelo.pvalues[c])
        if p > 0.30:
            sugestoes.append(
                f"A variável '{c}' não atinge nem o grau I (p = {p:.2%}). "
                "Considere removê-la e recalcular."
            )

    # Resíduos padronizados do modelo em uso
    _dp_resid = float(np.std(modelo.resid, ddof=1)) or 1.0
    residuos_padronizados = [round(float(r) / _dp_resid, 4) for r in modelo.resid]

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
            "residuos_padronizados": residuos_padronizados,
            "valores_ajustados": [round(float(v), 6) for v in modelo.fittedvalues],
            "modelo_escolhido_pelo_avaliador": request.transformacoes_escolhidas is not None,
        },
        "diagnosticos": diagnosticos,
        "amplitude_pct": amp,
        "grau_precisao": grau_prec,
        "campo_arbitrio_inferior": campo_inf,
        "campo_arbitrio_superior": campo_sup,
        "grau_fundamentacao": grau_fund,
        "ranking": serializar_ranking(ranking),
        "n_modelos_testados": len(ranking),
        "poder_predicao": poder_predicao,
        "micronumerosidade": micro,
        "avisos": avisos_saneamento + micro["avisos"] + sugestoes,
    }


# ---------------------------------------------------------------------------
# POST /api/analisar-amostras — detecção de outliers / desabilitar
# ---------------------------------------------------------------------------

@app.post("/api/analisar-amostras", tags=["regressao"])
def analisar_amostras_endpoint(request: AnalisarAmostrasRequest) -> Dict[str, Any]:
    """
    Analisa as amostras após o ajuste e recomenda quais desabilitar
    (outliers / atípicas), considerando o imóvel-alvo se informado.
    """
    try:
        dados_limpos, _ = sanear_dataset(
            request.dados, request.variavel_dependente, request.variaveis_independentes
        )
    except DadosInvalidos as e:
        raise HTTPException(status_code=422, detail=str(e))
    try:
        return analisar_amostras(
            dados=dados_limpos,
            variavel_dependente=request.variavel_dependente,
            variaveis_independentes=request.variaveis_independentes,
            transformacoes=request.transformacoes,
            imovel_alvo=request.imovel_alvo,
            limiar_residuo=request.limiar_residuo,
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))


# ---------------------------------------------------------------------------
# Módulo de inteligência imobiliária (independente do motor de avaliação)
# ---------------------------------------------------------------------------

@app.get("/api/cep/{cep}", tags=["inteligencia"])
def cep_endpoint(cep: str) -> Dict[str, Any]:
    """Consulta ViaCEP: preenche logradouro, cidade, UF e código IBGE."""
    r = buscar_cep(cep)
    if not r.get("ok"):
        raise HTTPException(status_code=404, detail=r.get("erro", "CEP não encontrado."))
    return r


@app.post("/api/localizacao", tags=["inteligencia"])
def localizacao_endpoint(request: LocalizacaoRequest) -> Dict[str, Any]:
    """
    Location Intelligence Engine: a partir do CEP, monta o perfil completo
    da localização (endereço, IBGE, lat/long, indicadores e infraestrutura).
    """
    r = perfil_localizacao(
        cep=request.cep,
        numero=request.numero,
        bairro=request.bairro,
        com_infraestrutura=request.com_infraestrutura,
    )
    if not r.get("ok"):
        raise HTTPException(status_code=422, detail=r.get("erro", "Não foi possível montar o perfil."))
    return r


@app.post("/api/estrategia", tags=["inteligencia"])
def estrategia_endpoint(request: EstrategiaRequest) -> Dict[str, Any]:
    """
    Gera a estratégia de busca a partir da ficha técnica.

    Camada de regras sempre roda. O refino por IA é opcional e só altera
    campos permitidos, com validação de limites.
    """
    if not request.ficha:
        raise HTTPException(status_code=422, detail="Informe a ficha técnica do imóvel.")

    refinador = None
    if request.refino_ia:
        # Ponto de extensão: conectar aqui um LLM. Sem chave configurada,
        # a estratégia sai apenas das regras (e o aviso é registrado).
        refinador = None

    try:
        est = gerar_estrategia(request.ficha, meta_minima=request.meta_minima,
                               refinador_llm=refinador)
        if request.refino_ia and "llm" not in est.get("origem", []):
            est.setdefault("avisos", []).append(
                "Refino por IA solicitado, mas nenhum provedor está configurado. "
                "Estratégia gerada apenas por regras."
            )
        return est
    except Exception as e:
        logger.error("Erro ao gerar estratégia: %s", e)
        raise HTTPException(status_code=422, detail=f"Erro ao gerar estratégia: {e}")


@app.post("/api/agente/filtrar", tags=["inteligencia"])
def filtrar_agente_endpoint(request: RetornoAgenteRequest) -> Dict[str, Any]:
    """
    Filtro anti-alucinação: recebe o retorno bruto de um agente de IA
    (CrewAI ou outro) e devolve apenas candidatos verificáveis.

    Preço/m² é recalculado, imóveis sem fonte ou com valor implausível são
    descartados e números de laudo enviados pelo agente são ignorados.
    """
    r = processar_retorno_agente(request.retorno, exigir_fonte=request.exigir_fonte)
    if r.get("status") == "erro":
        raise HTTPException(status_code=422, detail=r["erro"])
    return r


@app.get("/api/fontes", tags=["inteligencia"])
def fontes_endpoint() -> Dict[str, Any]:
    """Lista as fontes públicas disponíveis para busca automática."""
    return {"fontes": listar_fontes()}


@app.post("/api/fontes/buscar", tags=["inteligencia"])
def buscar_fontes_endpoint(request: BuscarFontesRequest) -> Dict[str, Any]:
    """
    Busca automática de imóveis em fontes públicas (dados abertos).

    Não faz scraping: consome arquivos que a própria fonte publica.
    """
    if not request.uf or not request.cidade:
        raise HTTPException(status_code=422, detail="Informe UF e cidade.")
    try:
        r = buscar_em_fontes(
            uf=request.uf, cidade=request.cidade, bairro=request.bairro,
            fontes=request.fontes, limite=request.limite,
        )
        r["status"] = "sucesso"
        r["total"] = len(r["candidatos"])
        return r
    except Exception as e:
        logger.error("Erro na busca em fontes: %s", e)
        raise HTTPException(status_code=502, detail=f"Falha ao consultar as fontes: {e}")


@app.post("/api/comparables", tags=["inteligencia"])
def comparables_endpoint(request: ComparablesRequest) -> Dict[str, Any]:
    """
    Comparable Property Search Engine: filtra, expande em níveis e devolve
    a base de amostras qualificadas + confiabilidade da busca.

    Não estima valor — entrega as amostras para o motor de avaliação.
    """
    try:
        return buscar_comparaveis(
            alvo=request.imovel.model_dump(),
            candidatos=[c.model_dump() for c in request.candidatos],
            indicadores_alvo=request.indicadores_regiao,
            meta_minima=request.meta_minima,
            meta_maxima=request.meta_maxima,
            score_territorial_minimo=request.score_territorial_minimo,
        )
    except Exception as e:
        logger.error("Erro na busca de comparáveis: %s", e)
        raise HTTPException(status_code=422, detail=f"Erro na busca de comparáveis: {e}")


# ---------------------------------------------------------------------------
# POST /api/comparaveis — ranqueia comps por similaridade (não estima valor)
# ---------------------------------------------------------------------------

@app.post("/api/comparaveis", tags=["comparaveis"])
def comparaveis_endpoint(request: ComparaveisRequest) -> Dict[str, Any]:
    """
    Pontua e ordena imóveis candidatos por similaridade com o imóvel de
    referência (score multicritério 0–100%, com explicação por critério).

    Não realiza estimativa de valor — apenas curadoria de comparáveis.
    """
    if not request.candidatos:
        raise HTTPException(status_code=422, detail="Informe ao menos um imóvel candidato.")
    try:
        candidatos = [c.model_dump() for c in request.candidatos]
        return ranquear_comparaveis(
            alvo=request.alvo.model_dump(),
            candidatos=candidatos,
            perfil_territorial_alvo=(
                request.perfil_territorial_alvo.model_dump()
                if request.perfil_territorial_alvo else None
            ),
            minimo_similaridade=request.minimo_similaridade,
        )
    except Exception as e:
        logger.error("Erro ao ranquear comparáveis: %s", e)
        raise HTTPException(status_code=422, detail=f"Erro ao ranquear comparáveis: {e}")


# ---------------------------------------------------------------------------
# POST /api/viabilidade — análise de viabilidade de investimento
# ---------------------------------------------------------------------------

@app.post("/api/viabilidade", tags=["investimento"])
def viabilidade_endpoint(request: ViabilidadeRequest) -> Dict[str, Any]:
    """
    Calcula indicadores de viabilidade (renda e revenda) a partir do valor
    de mercado avaliado e dos dados do negócio informados.
    """
    try:
        return analisar_viabilidade(
            valor_mercado=request.valor_mercado,
            preco_compra=request.preco_compra,
            custos_aquisicao=request.custos_aquisicao,
            custos_reforma=request.custos_reforma,
            aluguel_mensal=request.aluguel_mensal,
            despesas_mensais=request.despesas_mensais,
            valorizacao_anual_pct=request.valorizacao_anual_pct,
            horizonte_anos=request.horizonte_anos,
            custo_venda_pct=request.custo_venda_pct,
        )
    except Exception as e:
        logger.error("Erro na viabilidade: %s", e)
        raise HTTPException(status_code=422, detail=f"Erro no cálculo de viabilidade: {e}")


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

    y_name = request.variavel_dependente
    x_names = request.variaveis_independentes

    try:
        dados_limpos, _ = sanear_dataset(request.dados, y_name, x_names)
    except DadosInvalidos as e:
        raise HTTPException(status_code=422, detail=str(e))

    df = pd.DataFrame(dados_limpos)

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

    # Integridade: nenhum valor do laudo pode ser NaN/infinito
    import math as _math
    if any(_math.isnan(v) or _math.isinf(v) for v in
           [valor, ic_pred_inf, ic_pred_sup, ic_conf_inf, ic_conf_sup]):
        raise HTTPException(
            status_code=422,
            detail=("Não foi possível estimar o valor com este modelo para o imóvel "
                    "informado (a transformação gerou um resultado inválido). "
                    "Tente outro modelo no ranking ou revise as características do imóvel."),
        )

    # Ordena limites (transformações inversas podem inverter ordem)
    pred_inf, pred_sup = sorted([ic_pred_inf, ic_pred_sup])
    conf_inf, conf_sup = sorted([ic_conf_inf, ic_conf_sup])

    # Grau de precisão: amplitude do IC da MÉDIA (estimativa central) — NBR 14653-2
    amp = amplitude_pct(valor, conf_inf, conf_sup)
    grau = grau_precisao(amp)
    campo_inf, campo_sup = campo_arbitrio(valor)  # ±15% fixo (NBR 14653-1)

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
