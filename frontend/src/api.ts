// Cliente HTTP da API Avaliador

const BASE = import.meta.env.VITE_API_URL || ''

export type Transformacao =
  | 'nenhuma' | 'log' | 'raiz_quadrada' | 'raiz_reciproca'
  | 'reciproca' | 'reciproca_quadrada' | 'quadrada'

export interface BestfitRequest {
  dados: Record<string, unknown>[]
  variavel_dependente: string
  variaveis_independentes: string[]
  transformacoes_testar: string[]
  excluir_indices?: number[]
  nivel_confianca?: number
  top_n?: number
  /** Arbítrio do avaliador: usar este modelo do ranking em vez do melhor por AIC */
  transformacoes_escolhidas?: Record<string, string> | null
}

export interface RankingItem {
  id: number
  transformacoes: Record<string, string>
  r2: number
  r2_ajustado: number
  f_stat: number
  f_p_valor: number
  aic: number
  bic: number
  max_p_valor?: number
}

export interface CoeficienteBestfit {
  variavel: string
  transformacao: string
  coeficiente: number
  erro_padrao: number
  t_stat: number
  p_valor: number
}

export interface BestfitResponse {
  status: string
  melhor_modelo: {
    transformacoes: Record<string, string>
    transformacao_y: string
    r2: number
    r2_ajustado: number
    f_stat: number
    f_p_valor: number
    aic: number
    bic: number
    intercepto: number
    coeficientes: CoeficienteBestfit[]
    residuos: number[]
    residuos_padronizados?: number[]
    valores_ajustados: number[]
    modelo_escolhido_pelo_avaliador?: boolean
  }
  diagnosticos: {
    shapiro_wilk: { stat: number; p_valor: number }
    jarque_bera: { stat: number; p_valor: number }
    breusch_pagan: { stat: number; p_valor: number }
    outliers_cooks: { limiar: number; detectados: number; indices: number[]; distancias: number[] }
  }
  amplitude_pct: number | null
  grau_precisao: string | null
  campo_arbitrio_inferior: number | null
  campo_arbitrio_superior: number | null
  grau_fundamentacao: {
    grau: string
    amplitude_pct: number | null
    max_p_valor_coef: number
    p_valor_f: number
    n_observacoes: number
    n_variaveis: number
  }
  ranking: RankingItem[]
  n_modelos_testados: number
  poder_predicao?: {
    observado: number[]
    estimado: number[]
    desvio_medio_pct: number
    pct_dentro_20: number
  } | null
  micronumerosidade?: {
    ok: boolean
    avisos: string[]
    detalhes: Record<string, { niveis: Record<string, number>; minimo_exigido: number; ok: boolean }>
  }
  avisos?: string[]
}

export async function calcularBestfit(req: BestfitRequest): Promise<BestfitResponse> {
  const resp = await fetch(`${BASE}/api/bestfit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`Erro ${resp.status}: ${text}`)
  }
  return resp.json()
}

export interface AvaliarImovelResponse {
  status: string
  valor_estimado: number
  intervalo_predicao: [number, number]
  intervalo_confianca_media: [number, number]
  nivel_confianca: number
  amplitude_pct: number
  grau_precisao: string
  campo_arbitrio: [number, number]
  transformacao_y: string
  imovel_alvo: Record<string, number>
}

export async function avaliarImovel(req: {
  dados: Record<string, unknown>[]
  variavel_dependente: string
  variaveis_independentes: string[]
  transformacoes: Record<string, string>
  imovel_alvo: Record<string, number>
  nivel_confianca?: number
}): Promise<AvaliarImovelResponse> {
  const resp = await fetch(`${BASE}/api/avaliar-imovel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`Erro ${resp.status}: ${text}`)
  }
  return resp.json()
}

/** Baixa um arquivo do backend sem abrir aba/popup do navegador. */
export async function baixarArquivo(url: string, nomeArquivo: string): Promise<void> {
  const resp = await fetch(`${BASE}${url}`)
  if (!resp.ok) throw new Error(`Erro ao baixar (${resp.status})`)
  const blob = await resp.blob()
  const objUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objUrl
  a.download = nomeArquivo
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(objUrl)
}

export interface AmostraAnalise {
  indice: number
  residuo_padronizado: number
  cooks_distance: number
  leverage: number
  distancia_alvo: number | null
  atipica: boolean
  recomendar_desabilitar: boolean
  motivos: string[]
}

export interface AnaliseResponse {
  status: string
  n_amostras: number
  limiares: { residuo: number; cooks: number; leverage: number }
  amostras: AmostraAnalise[]
  recomendar_desabilitar: number[]
  r2_atual: number
}

export async function analisarAmostras(req: {
  dados: Record<string, unknown>[]
  variavel_dependente: string
  variaveis_independentes: string[]
  transformacoes: Record<string, string>
  imovel_alvo?: Record<string, number> | null
}): Promise<AnaliseResponse> {
  const resp = await fetch(`${BASE}/api/analisar-amostras`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!resp.ok) throw new Error(`Erro ${resp.status}: ${await resp.text()}`)
  return resp.json()
}

export interface ExportConfig {
  endereco: string
  area_terreno?: number
  area_construida?: number
  data_avaliacao: string
  finalidade?: string
  avaliador_nome: string
  avaliador_crea: string
  avaliador_empresa?: string
}

export async function exportarWord(
  resultadoLegado: object,
  cfg: ExportConfig,
): Promise<{ arquivo: string; url_download: string }> {
  const payload = {
    resultado_regressao: resultadoLegado,
    imovel: {
      endereco: cfg.endereco,
      area_terreno: cfg.area_terreno,
      area_construida: cfg.area_construida,
      data_avaliacao: cfg.data_avaliacao,
      finalidade: cfg.finalidade,
    },
    avaliador: {
      nome: cfg.avaliador_nome,
      crea: cfg.avaliador_crea,
      empresa: cfg.avaliador_empresa,
    },
  }
  const resp = await fetch(`${BASE}/api/exportar-word`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!resp.ok) throw new Error(`Erro ao exportar Word: ${resp.status}`)
  return resp.json()
}

export async function exportarPDF(
  resultadoLegado: object,
  cfg: ExportConfig,
): Promise<{ arquivo: string; url_download: string }> {
  const payload = {
    resultado_regressao: resultadoLegado,
    imovel: {
      endereco: cfg.endereco,
      area_terreno: cfg.area_terreno,
      area_construida: cfg.area_construida,
      data_avaliacao: cfg.data_avaliacao,
      finalidade: cfg.finalidade,
    },
    avaliador: {
      nome: cfg.avaliador_nome,
      crea: cfg.avaliador_crea,
      empresa: cfg.avaliador_empresa,
    },
  }
  const resp = await fetch(`${BASE}/api/exportar-pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!resp.ok) throw new Error(`Erro ao exportar PDF: ${resp.status}`)
  return resp.json()
}

/**
 * Converte response do bestfit em payload aceito pelos endpoints
 * de export do backend (que esperam o formato do /api/calcular-regressao).
 */
export function bestfitParaExport(
  b: BestfitResponse,
  varDep: string,
  avaliacao?: AvaliarImovelResponse | null,
  valorAdotado?: number | null,
): object {
  const m = b.melhor_modelo
  return {
    status: 'sucesso',
    grau_fundamentacao: b.grau_fundamentacao,
    poder_predicao: b.poder_predicao ?? undefined,
    avaliacao_imovel: avaliacao
      ? {
          valor_estimado: avaliacao.valor_estimado,
          valor_adotado: valorAdotado ?? undefined,
          intervalo_confianca_media: avaliacao.intervalo_confianca_media,
          intervalo_predicao: avaliacao.intervalo_predicao,
          campo_arbitrio: avaliacao.campo_arbitrio,
          amplitude_pct: avaliacao.amplitude_pct,
          grau_precisao: avaliacao.grau_precisao,
        }
      : undefined,
    regressao: {
      r_squared: m.r2,
      r_ajustado: m.r2_ajustado,
      f_calculado: m.f_stat,
      p_valor_f: m.f_p_valor,
      durbin_watson: 0,
      desvio_padrao: 0,
      aic: m.aic,
      bic: m.bic,
      observacoes: m.residuos.length,
      variaveis: m.coeficientes.length,
    },
    coeficientes: m.coeficientes.map((c) => ({
      variavel: c.variavel,
      transformacao: c.transformacao,
      coeficiente: c.coeficiente,
      elasticidade: 0,
      t_calculado: c.t_stat,
      p_valor: c.p_valor,
      significancia_percent: c.p_valor * 100,
      erro_padrao: c.erro_padrao,
      intervalo_confianca_95: [0, 0],
    })),
    intercepto: m.intercepto,
    correlacao_matrix: { variaveis: [], dados: [] },
    outliers: {
      detectados: b.diagnosticos.outliers_cooks.detectados,
      percentual: 0,
      indices: b.diagnosticos.outliers_cooks.indices,
      residuos_standardizados: [],
    },
    validacao_nbr: { ok: true, avisos: [], erros: [] },
    graficos: {
      residuos_vs_predito: {
        preditos: m.valores_ajustados,
        residuos: m.residuos,
      },
      qq_plot: { teoricos: [], amostra: [] },
      scatter_por_variavel: {},
    },
  }
}
