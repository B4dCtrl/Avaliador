// Modelo de dados da grade do Avaliador

export type PapelColuna = 'dependente' | 'independente' | 'ignorar'

export interface Coluna {
  id: string
  nome: string
  papel: PapelColuna
}

export interface Linha {
  id: string
  valores: Record<string, string> // colId -> valor (string p/ edição)
  excluida: boolean
}

export interface GridState {
  colunas: Coluna[]
  linhas: Linha[]
  avaliando: Record<string, string> // colId -> valor do imóvel-alvo
}

let _seq = 0
export const novoId = (p = 'id') => `${p}_${Date.now().toString(36)}_${_seq++}`

export function gridVazio(): GridState {
  const cValor: Coluna = { id: novoId('col'), nome: 'valor', papel: 'dependente' }
  const c1: Coluna = { id: novoId('col'), nome: 'area', papel: 'independente' }
  const c2: Coluna = { id: novoId('col'), nome: 'distancia', papel: 'independente' }
  const colunas = [cValor, c1, c2]
  const linhas: Linha[] = Array.from({ length: 3 }).map(() => ({
    id: novoId('lin'),
    valores: Object.fromEntries(colunas.map((c) => [c.id, ''])),
    excluida: false,
  }))
  const avaliando = Object.fromEntries(colunas.map((c) => [c.id, '']))
  return { colunas, linhas, avaliando }
}

/** Acrescenta linhas de um CSV à grade atual, casando pelos nomes das colunas. */
export function acrescentarCSV(g: GridState, registros: Record<string, unknown>[]): GridState {
  const novas: Linha[] = registros.map((reg) => {
    const valores: Record<string, string> = {}
    for (const c of g.colunas) {
      const v = reg[c.nome]
      valores[c.id] = v === undefined || v === null ? '' : String(v)
    }
    return { id: novoId('lin'), valores, excluida: false }
  })
  return { ...g, linhas: [...g.linhas, ...novas] }
}

export function gridDeCSV(registros: Record<string, unknown>[]): GridState {
  const nomes = Object.keys(registros[0] || {})
  const colunas: Coluna[] = nomes.map((nome, i) => ({
    id: novoId('col'),
    nome,
    papel: i === 0 ? 'dependente' : 'independente',
  }))
  const linhas: Linha[] = registros.map((reg) => ({
    id: novoId('lin'),
    valores: Object.fromEntries(colunas.map((c) => [c.id, String(reg[c.nome] ?? '')])),
    excluida: false,
  }))
  const avaliando = Object.fromEntries(colunas.map((c) => [c.id, '']))
  return { colunas, linhas, avaliando }
}

// ---- operações puras sobre a grade ----

export function addLinha(g: GridState): GridState {
  const valores = Object.fromEntries(g.colunas.map((c) => [c.id, '']))
  return { ...g, linhas: [...g.linhas, { id: novoId('lin'), valores, excluida: false }] }
}

export function addColuna(g: GridState): GridState {
  const col: Coluna = { id: novoId('col'), nome: `var_${g.colunas.length}`, papel: 'independente' }
  return {
    ...g,
    colunas: [...g.colunas, col],
    linhas: g.linhas.map((l) => ({ ...l, valores: { ...l.valores, [col.id]: '' } })),
    avaliando: { ...g.avaliando, [col.id]: '' },
  }
}

export function removerUltimaColuna(g: GridState): GridState {
  if (g.colunas.length <= 1) return g
  const ultima = g.colunas[g.colunas.length - 1]
  return {
    ...g,
    colunas: g.colunas.slice(0, -1),
    linhas: g.linhas.map((l) => {
      const v = { ...l.valores }; delete v[ultima.id]; return { ...l, valores: v }
    }),
  }
}

export function removerUltimaLinha(g: GridState): GridState {
  if (g.linhas.length === 0) return g
  return { ...g, linhas: g.linhas.slice(0, -1) }
}

export function reconsiderarTodas(g: GridState): GridState {
  return { ...g, linhas: g.linhas.map((l) => ({ ...l, excluida: false })) }
}

export function desabilitarIndices(g: GridState, indices: number[]): GridState {
  const set = new Set(indices)
  return { ...g, linhas: g.linhas.map((l, i) => (set.has(i) ? { ...l, excluida: true } : l)) }
}

/** Constrói payload do /api/bestfit a partir da grade. Lança Error se inválido. */
export function montarPayloadBestfit(
  grid: GridState,
  transformacoesTestar: string[],
  nivelConfianca: number,
) {
  const dep = grid.colunas.find((c) => c.papel === 'dependente')
  if (!dep) throw new Error('Defina uma coluna como Valor (dependente).')
  const indeps = grid.colunas.filter((c) => c.papel === 'independente')
  if (indeps.length === 0) throw new Error('Defina ao menos uma coluna como Variável.')

  const ativas = [dep, ...indeps]
  const dados: Record<string, number>[] = []
  grid.linhas.forEach((lin, idx) => {
    if (lin.excluida) return
    const reg: Record<string, number> = {}
    for (const c of ativas) {
      const raw = lin.valores[c.id]
      const n = Number(raw)
      if (raw === '' || raw == null || isNaN(n)) {
        throw new Error(`Linha ${idx + 1}: valor inválido na coluna "${c.nome}".`)
      }
      reg[c.nome] = n
    }
    dados.push(reg)
  })

  if (dados.length < indeps.length + 2) {
    throw new Error(`Poucas amostras: precisa de pelo menos ${indeps.length + 2}.`)
  }

  return {
    dados,
    variavel_dependente: dep.nome,
    variaveis_independentes: indeps.map((c) => c.nome),
    transformacoes_testar: transformacoesTestar,
    nivel_confianca: nivelConfianca,
  }
}

/** Extrai o imóvel-alvo (avaliando) como {nomeVar: valor}. Retorna null se incompleto. */
export function montarImovelAlvo(grid: GridState): Record<string, number> | null {
  const indeps = grid.colunas.filter((c) => c.papel === 'independente')
  const out: Record<string, number> = {}
  for (const c of indeps) {
    const raw = grid.avaliando[c.id]
    const n = Number(raw)
    if (raw === '' || raw == null || isNaN(n)) return null
    out[c.nome] = n
  }
  return out
}
