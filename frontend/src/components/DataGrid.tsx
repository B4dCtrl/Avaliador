import { useState } from 'react'
import { Plus, Trash2, Upload, FilePlus2, Eraser, Tag, Sigma } from 'lucide-react'
import type { ChangeEvent } from 'react'
import { type Coluna, type GridState, type PapelColuna, novoId, operarVariaveis } from '../grid'

interface Props {
  grid: GridState
  setGrid: (g: GridState) => void
  onImportCSV: (e: ChangeEvent<HTMLInputElement>) => void
  onAppendCSV: (e: ChangeEvent<HTMLInputElement>) => void
}

const PAPEL_LABEL: Record<PapelColuna, string> = {
  dependente: 'Valor (Y)',
  independente: 'Variável (X)',
  ignorar: 'Ignorar',
}

const PAPEL_COR: Record<PapelColuna, string> = {
  dependente: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-300',
  independente: 'bg-primary-100 text-primary-800 dark:bg-primary-500/20 dark:text-primary-300',
  ignorar: 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400',
}

export default function DataGrid({ grid, setGrid, onImportCSV, onAppendCSV }: Props) {
  const { colunas, linhas } = grid
  const [operarAberto, setOperarAberto] = useState(false)
  const [opNome, setOpNome] = useState('')
  const [opExpr, setOpExpr] = useState('')
  const [opErro, setOpErro] = useState<string | null>(null)

  const aplicarOperacao = () => {
    setOpErro(null)
    try {
      setGrid(operarVariaveis(grid, opNome, opExpr))
      setOperarAberto(false); setOpNome(''); setOpExpr('')
    } catch (e) {
      setOpErro(e instanceof Error ? e.message : 'Expressão inválida')
    }
  }

  // ---- operações ----
  const setCelula = (linId: string, colId: string, valor: string) => {
    setGrid({
      ...grid,
      linhas: linhas.map((l) =>
        l.id === linId ? { ...l, valores: { ...l.valores, [colId]: valor } } : l,
      ),
    })
  }

  const addLinha = () => {
    const valores = Object.fromEntries(colunas.map((c) => [c.id, '']))
    setGrid({ ...grid, linhas: [...linhas, { id: novoId('lin'), valores, excluida: false }] })
  }

  const removerLinha = (id: string) => {
    setGrid({ ...grid, linhas: linhas.filter((l) => l.id !== id) })
  }

  const toggleExcluir = (id: string) => {
    setGrid({
      ...grid,
      linhas: linhas.map((l) => (l.id === id ? { ...l, excluida: !l.excluida } : l)),
    })
  }

  const addColuna = () => {
    const col: Coluna = { id: novoId('col'), nome: `var_${colunas.length}`, papel: 'independente' }
    setGrid({
      ...grid,
      colunas: [...colunas, col],
      linhas: linhas.map((l) => ({ ...l, valores: { ...l.valores, [col.id]: '' } })),
      avaliando: { ...grid.avaliando, [col.id]: '' },
    })
  }

  const removerColuna = (colId: string) => {
    setGrid({
      ...grid,
      colunas: colunas.filter((c) => c.id !== colId),
      linhas: linhas.map((l) => {
        const v = { ...l.valores }
        delete v[colId]
        return { ...l, valores: v }
      }),
    })
  }

  const setNomeColuna = (colId: string, nome: string) => {
    setGrid({ ...grid, colunas: colunas.map((c) => (c.id === colId ? { ...c, nome } : c)) })
  }

  const setPapelColuna = (colId: string, papel: PapelColuna) => {
    // Só pode haver uma dependente
    setGrid({
      ...grid,
      colunas: colunas.map((c) => {
        if (c.id === colId) return { ...c, papel }
        if (papel === 'dependente' && c.papel === 'dependente') return { ...c, papel: 'independente' }
        return c
      }),
    })
  }

  const limpar = () => {
    setGrid({
      ...grid,
      linhas: linhas.map((l) => ({
        ...l,
        valores: Object.fromEntries(colunas.map((c) => [c.id, ''])),
        excluida: false,
      })),
    })
  }

  const nAtivas = linhas.filter((l) => !l.excluida).length

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mr-auto flex items-center gap-2">
          <Tag size={16} /> Amostras
          <span className="text-xs font-normal text-slate-400">({nAtivas} ativas de {linhas.length})</span>
        </h2>
        <button onClick={addLinha} className="btn-grid"><Plus size={14} /> Amostra</button>
        <button onClick={addColuna} className="btn-grid"><Plus size={14} /> Variável</button>
        <label className="btn-grid cursor-pointer" title="Substituir tudo pelo CSV">
          <Upload size={14} /> CSV
          <input type="file" accept=".csv" onChange={onImportCSV} className="hidden" />
        </label>
        <label className="btn-grid cursor-pointer" title="Acrescentar linhas do CSV">
          <FilePlus2 size={14} /> CSV +
          <input type="file" accept=".csv" onChange={onAppendCSV} className="hidden" />
        </label>
        <button onClick={() => setOperarAberto(!operarAberto)} className="btn-grid" title="Criar variável calculada">
          <Sigma size={14} /> Operar
        </button>
        <button onClick={limpar} className="btn-grid"><Eraser size={14} /> Limpar</button>
      </div>

      {/* Painel Operar variáveis */}
      {operarAberto && (
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-blue-50/60 dark:bg-blue-500/10">
          <div className="text-[12px] font-semibold text-slate-700 dark:text-slate-200 mb-1.5 flex items-center gap-1.5">
            <Sigma size={14} /> Criar variável calculada
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <div>
              <label className="block text-[10px] text-slate-500 mb-0.5">Nome da nova variável</label>
              <input value={opNome} onChange={(e) => setOpNome(e.target.value)}
                placeholder="valor_unitario"
                className="px-2 py-1 text-[12px] border border-slate-300 rounded w-[160px] dark:bg-slate-700 dark:text-slate-100 dark:border-slate-600" />
            </div>
            <div className="flex-1 min-w-[200px]">
              <label className="block text-[10px] text-slate-500 mb-0.5">
                Expressão (use os nomes das colunas: {colunas.map((c) => c.nome).join(', ')})
              </label>
              <input value={opExpr} onChange={(e) => setOpExpr(e.target.value)}
                placeholder={`${colunas[0]?.nome ?? 'valor'} / ${colunas[1]?.nome ?? 'area'}`}
                className="px-2 py-1 text-[12px] border border-slate-300 rounded w-full font-mono dark:bg-slate-700 dark:text-slate-100 dark:border-slate-600" />
            </div>
            <button onClick={aplicarOperacao}
              className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white text-[12px] font-medium">
              Criar coluna
            </button>
            <button onClick={() => { setOperarAberto(false); setOpErro(null) }}
              className="px-3 py-1.5 rounded text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 text-[12px]">
              Cancelar
            </button>
          </div>
          {opErro && <div className="text-[11px] text-red-600 mt-1">{opErro}</div>}
        </div>
      )}

      {/* Tabela */}
      <div className="overflow-auto max-h-[480px]">
        <table className="w-full text-sm border-collapse">
          <thead className="sticky top-0 z-10">
            <tr className="bg-white dark:bg-slate-800">
              <th className="w-10 px-2 py-2 border-b border-slate-200 dark:border-slate-700"></th>
              {colunas.map((c) => (
                <th key={c.id} className="px-2 py-2 border-b border-slate-200 dark:border-slate-700 min-w-[140px] align-top">
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-1">
                      <input
                        value={c.nome}
                        onChange={(e) => setNomeColuna(c.id, e.target.value)}
                        className="w-full px-1.5 py-1 rounded border border-slate-200 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 text-xs font-medium"
                      />
                      <button onClick={() => removerColuna(c.id)} title="Remover coluna"
                        className="text-slate-300 hover:text-red-500 shrink-0"><Trash2 size={13} /></button>
                    </div>
                    <select
                      value={c.papel}
                      onChange={(e) => setPapelColuna(c.id, e.target.value as PapelColuna)}
                      className={`text-[11px] px-1.5 py-0.5 rounded font-medium border-0 cursor-pointer ${PAPEL_COR[c.papel]}`}
                    >
                      <option value="dependente">{PAPEL_LABEL.dependente}</option>
                      <option value="independente">{PAPEL_LABEL.independente}</option>
                      <option value="ignorar">{PAPEL_LABEL.ignorar}</option>
                    </select>
                  </div>
                </th>
              ))}
              <th className="w-10 px-2 py-2 border-b border-slate-200 dark:border-slate-700"></th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.id} className={l.excluida ? 'opacity-40' : ''}>
                <td className="px-2 py-1 text-center border-b border-slate-100 dark:border-slate-700/50">
                  <input type="checkbox" checked={!l.excluida} onChange={() => toggleExcluir(l.id)}
                    title="Incluir no modelo" className="accent-primary-600" />
                </td>
                {colunas.map((c) => (
                  <td key={c.id} className="px-1 py-1 border-b border-slate-100 dark:border-slate-700/50">
                    <input
                      type="number"
                      value={l.valores[c.id] ?? ''}
                      onChange={(e) => setCelula(l.id, c.id, e.target.value)}
                      className="w-full px-2 py-1 rounded border border-transparent hover:border-slate-200 focus:border-primary-400 dark:bg-slate-700/50 dark:text-slate-100 text-sm focus:outline-none"
                    />
                  </td>
                ))}
                <td className="px-2 py-1 text-center border-b border-slate-100 dark:border-slate-700/50">
                  <button onClick={() => removerLinha(l.id)} title="Excluir linha"
                    className="text-slate-300 hover:text-red-500"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="px-4 py-2 text-[11px] text-slate-400 border-t border-slate-200 dark:border-slate-700">
        Cada linha é uma amostra/comparável. Desmarque a caixa para excluir uma amostra do cálculo.
      </div>
    </div>
  )
}
