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
  comparacao?: {
    grau_atual: string
    r2_atual: number
    grau_apos: string
    r2_apos: number
    melhora: boolean
    piora: boolean
  }
  recomendacao_texto?: string
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

// ---- Location Intelligence Engine ----
export interface PerfilLocalizacao {
  ok: boolean
  localizacao: {
    cep?: string | null; logradouro?: string | null; numero?: string | null
    bairro?: string | null; cidade?: string | null; uf?: string | null
    ibge?: string | null; latitude?: number | null; longitude?: number | null
  }
  indicadores: {
    idh?: number | null; idhm_renda?: number | null; idhm_educacao?: number | null
    idhm_longevidade?: number | null; pib?: number | null; pib_per_capita?: number | null
    populacao?: number | null; renda_media?: number | null
    densidade_populacional?: number | null; area_km2?: number | null; municipio?: string | null
  }
  infraestrutura: { ok: boolean; raio_m?: number; contagens?: Record<string, number>; indice_infraestrutura?: number; erro?: string }
  fontes: string[]
  avisos: string[]
}

export async function buscarLocalizacao(req: { cep: string; numero?: string; bairro?: string; com_infraestrutura?: boolean }): Promise<PerfilLocalizacao> {
  const resp = await fetch(`${BASE}/api/localizacao`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req),
  })
  if (!resp.ok) throw new Error(`Erro ${resp.status}: ${await resp.text()}`)
  return resp.json()
}

// ---- Estratégia de busca (regras + refino IA opcional) ----
export interface EstrategiaBusca {
  imovel_avaliando: Record<string, unknown>
  tipo_normalizado: string
  criterios_obrigatorios: string[]
  criterios_flexiveis: string[]
  raio_inicial_metros: number
  tolerancias: Record<string, number>
  meta_minima_amostras: number
  meta_maxima_amostras: number
  score_territorial_minimo: number
  regras_expansao: { ordem: number; acao: string; gatilho: string; justificativa: string }[]
  justificativa_tipologia: string
  avisos: string[]
  origem: string[]
}

export async function gerarEstrategia(req: {
  ficha: Record<string, unknown>; meta_minima?: number; refino_ia?: boolean
}): Promise<EstrategiaBusca> {
  const resp = await fetch(`${BASE}/api/estrategia`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req),
  })
  if (!resp.ok) throw new Error(`Erro ${resp.status}: ${await resp.text()}`)
  return resp.json()
}

// ---- Filtro anti-alucinação do retorno de agente de IA ----
export interface FiltroAgenteResponse {
  status: string
  candidatos: Record<string, unknown>[]
  rejeitados: { motivo: string; imovel?: string }[]
  resumo_filtro: { recebidos: number; aceitos: number; rejeitados: number; precos_m2_corrigidos: number }
  contradicoes: string[]
  campos_ignorados: string[]
  texto_agente?: string | null
  observacao: string
}

export async function filtrarRetornoAgente(retorno: unknown, exigirFonte = true): Promise<FiltroAgenteResponse> {
  const resp = await fetch(`${BASE}/api/agente/filtrar`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ retorno, exigir_fonte: exigirFonte }),
  })
  if (!resp.ok) throw new Error(`Erro ${resp.status}: ${await resp.text()}`)
  return resp.json()
}

// ---- Fontes públicas (busca automática, sem scraping) ----
export interface FonteDados { id: string; nome: string; descricao: string; legal: string }

export async function listarFontes(): Promise<{ fontes: FonteDados[] }> {
  const resp = await fetch(`${BASE}/api/fontes`)
  if (!resp.ok) throw new Error(`Erro ${resp.status}`)
  return resp.json()
}

export async function buscarEmFontes(req: {
  uf: string; cidade: string; bairro?: string; fontes?: string[]; limite?: number
}): Promise<{ status: string; total: number; candidatos: Record<string, unknown>[]; por_fonte: Record<string, number>; erros: { fonte: string; erro: string }[] }> {
  const resp = await fetch(`${BASE}/api/fontes/buscar`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req),
  })
  if (!resp.ok) throw new Error(`Erro ${resp.status}: ${await resp.text()}`)
  return resp.json()
}

// ---- Comparable Property Search Engine ----
export interface AnuncioCandidato {
  identificacao?: string | null; endereco?: string | null; tipo?: string | null
  preco?: number | null; area_construida?: number | null; area_terreno?: number | null
  quartos?: number | null; banheiros?: number | null; vagas?: number | null
  padrao_construtivo?: string | null; bairro?: string | null; cidade?: string | null
  distancia_km?: number | null; idade_anuncio_dias?: number | null; fonte?: string | null
  indicadores?: Record<string, unknown> | null
}

export interface AmostraQualificada {
  endereco?: string | null; identificacao?: string | null
  preco: number; area: number; area_terreno?: number | null; preco_m2: number
  bairro?: string | null; cidade?: string | null
  quartos?: number | null; banheiros?: number | null; vagas?: number | null
  fonte?: string | null; nivel_expansao: number
  similaridade: Record<string, number>; score: number
  territorial_score?: number | null; territorial_detalhes?: Record<string, number>
}

export interface ComparablesResponse {
  status: string
  imovel_alvo: Record<string, unknown>
  amostras: AmostraQualificada[]
  dados_regiao: Record<string, unknown>
  confiabilidade_busca: number
  resumo: {
    total_candidatos: number; descartados_qualidade: number
    amostras_qualificadas: number; meta_minima: number
    suficiente_para_avaliacao: boolean; nivel_maximo_usado: number
    similaridade_media: number
  }
  trilha_expansao: { nivel: number; descricao: string; executado: boolean; encontrados: number; motivo?: string; total_acumulado?: number }[]
  descartados: { motivo: string; imovel?: string | null }[]
  orientacao: string
}

export async function buscarComparables(req: {
  imovel: Record<string, unknown>
  candidatos: AnuncioCandidato[]
  indicadores_regiao?: Record<string, unknown> | null
  meta_minima?: number
  meta_maxima?: number
}): Promise<ComparablesResponse> {
  const resp = await fetch(`${BASE}/api/comparables`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req),
  })
  if (!resp.ok) throw new Error(`Erro ${resp.status}: ${await resp.text()}`)
  return resp.json()
}

// ---- Comparáveis (comps) — curadoria por similaridade ----
export interface PerfilTerritorial {
  idh?: number | null
  renda_per_capita?: number | null
  densidade_populacional?: number | null
  escolaridade_media_anos?: number | null
  indice_seguranca?: number | null
  infraestrutura?: number | null
  distancia_centro_km?: number | null
}

export interface PerfilImovel {
  tipo_imovel?: string | null
  finalidade?: string | null
  zoneamento?: string | null
  area_terreno?: number | null
  area_construida?: number | null
  idade?: number | null
  padrao_construtivo?: string | null
  conservacao?: string | null
  dormitorios?: number | null
  banheiros?: number | null
  vagas?: number | null
  endereco?: string | null
  bairro?: string | null
  cidade?: string | null
  uf?: string | null
  cep?: string | null
}

export interface CandidatoComparavel extends PerfilImovel {
  identificacao?: string | null
  fonte?: string | null
  preco?: number | null
  data_anuncio?: string | null
  distancia_km?: number | null
  perfil_territorial?: PerfilTerritorial | null
}

export interface ComparavelPontuado {
  indice: number
  identificacao: string
  fonte?: string | null
  preco?: number | null
  area_terreno?: number | null
  area_construida?: number | null
  bairro?: string | null
  cidade?: string | null
  data_anuncio?: string | null
  similaridade_pct: number
  classe: string
  detalhamento: Record<string, { similaridade_pct: number; peso: number; peso_efetivo?: number }>
  criterios_ignorados: string[]
  cobertura_pct: number
  territorial?: { indice: number; percentual: number; detalhes: Record<string, number> } | null
}

export interface ComparaveisResponse {
  status: string
  comparaveis: ComparavelPontuado[]
  resumo: {
    total_avaliados: number
    total_aceitos: number
    similaridade_media: number
    excelentes: number
    boas: number
    aceitaveis: number
    fracas: number
    orientacao: string
  }
}

export async function ranquearComparaveis(req: {
  alvo: PerfilImovel
  candidatos: CandidatoComparavel[]
  perfil_territorial_alvo?: PerfilTerritorial | null
  minimo_similaridade?: number
}): Promise<ComparaveisResponse> {
  const resp = await fetch(`${BASE}/api/comparaveis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!resp.ok) throw new Error(`Erro ${resp.status}: ${await resp.text()}`)
  return resp.json()
}

// ---- Viabilidade de investimento ----
export interface ViabilidadeRequest {
  valor_mercado: number
  preco_compra: number
  custos_aquisicao?: number
  custos_reforma?: number
  aluguel_mensal?: number | null
  despesas_mensais?: number
  valorizacao_anual_pct?: number
  horizonte_anos?: number
  custo_venda_pct?: number
}

export interface ViabilidadeResponse {
  status: string
  investimento_total: number
  valor_mercado: number
  comparacao_mercado: {
    desconto_valor: number
    desconto_pct: number
    ganho_patrimonial: number
    ganho_patrimonial_pct: number
  }
  renda: null | {
    aluguel_mensal: number
    liquido_mensal: number
    yield_bruto_anual_pct: number
    yield_liquido_anual_pct: number
    cap_rate_pct: number
    payback_anos: number | null
  }
  revenda: null | {
    horizonte_anos: number
    valor_futuro_estimado: number
    renda_acumulada: number
    lucro_liquido: number
    roi_total_pct: number
    retorno_anualizado_pct: number
  }
  veredito: string
  pontuacao: number
  sinais: string[]
  observacao: string
}

export async function analisarViabilidade(req: ViabilidadeRequest): Promise<ViabilidadeResponse> {
  const resp = await fetch(`${BASE}/api/viabilidade`, {
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
