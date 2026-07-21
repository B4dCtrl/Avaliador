import type { BestfitResponse } from '../api'
import type { GridState } from '../grid'

interface Props {
  resultado: BestfitResponse
  grid: GridState
}

function fmt(n: number | null | undefined, casas = 2) {
  if (n == null || !Number.isFinite(n)) return '—'
  return n.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })
}

/** Planilha de resultados: valor real x estimado x resíduo, por amostra ativa. */
export default function TabelaResultados({ resultado, grid }: Props) {
  const dep = grid.colunas.find((c) => c.papel === 'dependente')
  const ativas = grid.linhas.filter((l) => !l.excluida)
  const ajustados = resultado.melhor_modelo.valores_ajustados
  const residuos = resultado.melhor_modelo.residuos

  // valor real (Y) de cada amostra ativa, na ordem enviada ao motor
  const reais = dep ? ativas.map((l) => Number(l.valores[dep.id])) : []

  return (
    <div className="win-panel p-3">
      <div className="text-[12px] font-semibold text-[#0a3fb0] mb-2">Planilha de resultados (por amostra)</div>
      <div className="overflow-auto max-h-[320px]">
        <table className="w-full text-[12px] border-collapse">
          <thead className="sticky top-0">
            <tr className="bg-[#dde6f2] text-[#1b3a6b] text-left">
              <th className="px-2 py-1 border border-[#c2d0e4]">#</th>
              <th className="px-2 py-1 border border-[#c2d0e4] text-right">Valor real</th>
              <th className="px-2 py-1 border border-[#c2d0e4] text-right">Valor estimado</th>
              <th className="px-2 py-1 border border-[#c2d0e4] text-right">Resíduo</th>
              <th className="px-2 py-1 border border-[#c2d0e4] text-right">Desvio %</th>
            </tr>
          </thead>
          <tbody>
            {ajustados.map((aj, i) => {
              const real = reais[i]
              const res = residuos[i] ?? 0
              const desvio = real ? (res / real) * 100 : 0
              const fora = Math.abs(desvio) > 15
              return (
                <tr key={i} className={fora ? 'bg-[#fff3f3]' : i % 2 ? 'bg-[#f7f6f0]' : 'bg-white'}>
                  <td className="px-2 py-1 border border-[#e4ddc9]">{i + 1}</td>
                  <td className="px-2 py-1 border border-[#e4ddc9] text-right">{isFinite(real) ? fmt(real) : '—'}</td>
                  <td className="px-2 py-1 border border-[#e4ddc9] text-right">{fmt(aj)}</td>
                  <td className="px-2 py-1 border border-[#e4ddc9] text-right">{fmt(res)}</td>
                  <td className={`px-2 py-1 border border-[#e4ddc9] text-right ${fora ? 'text-[#c22] font-semibold' : 'text-[#555]'}`}>
                    {fmt(desvio, 1)}%
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="text-[10px] text-[#888] mt-1">Linhas em vermelho: desvio acima de 15% (candidatas a desabilitar).</div>
    </div>
  )
}
