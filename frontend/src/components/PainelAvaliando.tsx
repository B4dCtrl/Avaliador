import { Target } from 'lucide-react'
import type { GridState } from '../grid'

interface Props {
  grid: GridState
  setGrid: (g: GridState) => void
  onEstimar?: () => void
  podeEstimar?: boolean
  loading?: boolean
}

/** Campo dedicado para informar o imóvel a ser avaliado (fora da planilha). */
export default function PainelAvaliando({ grid, setGrid, onEstimar, podeEstimar, loading }: Props) {
  const indeps = grid.colunas.filter((c) => c.papel === 'independente')
  const dep = grid.colunas.find((c) => c.papel === 'dependente')

  const setValor = (colId: string, v: string) =>
    setGrid({ ...grid, avaliando: { ...grid.avaliando, [colId]: v } })

  return (
    <div className="rounded-[4px] border-2 border-amber-400 bg-gradient-to-b from-amber-50 to-amber-100/60 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-400 text-amber-950 text-[12px] font-bold">
        <Target size={15} /> IMÓVEL A AVALIAR
      </div>
      <div className="p-3">
        {indeps.length === 0 ? (
          <div className="text-[12px] text-amber-800">Defina ao menos uma variável (X) na planilha para informar o imóvel.</div>
        ) : (
          <div className="flex flex-wrap items-end gap-3">
            {indeps.map((c) => (
              <div key={c.id} className="flex flex-col">
                <label className="text-[11px] text-amber-900 font-medium mb-0.5">{c.nome}</label>
                <input
                  type="number"
                  value={grid.avaliando[c.id] ?? ''}
                  onChange={(e) => setValor(c.id, e.target.value)}
                  placeholder="0"
                  className="w-[120px] px-2 py-1.5 rounded-md border-2 border-amber-300 bg-white text-sm font-semibold text-center focus:outline-none focus:border-amber-500 shadow-sm"
                />
              </div>
            ))}
            <div className="flex flex-col">
              <label className="text-[11px] text-amber-900 font-medium mb-0.5">{dep ? dep.nome : 'valor'}</label>
              <div className="w-[120px] px-2 py-1.5 rounded-md border-2 border-dashed border-amber-300 bg-amber-50 text-sm text-amber-700 text-center italic">
                a estimar
              </div>
            </div>
            {onEstimar && (
              <button onClick={onEstimar} disabled={!podeEstimar || loading}
                className="win-btn win-btn-primary ml-auto h-[34px]">
                {loading ? '…' : '◎ Estimar valor'}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
