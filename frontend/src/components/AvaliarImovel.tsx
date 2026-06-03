import { useMemo, useState } from 'react'
import { Home, Loader2 } from 'lucide-react'
import { avaliarImovel, type AvaliarImovelResponse, type BestfitResponse } from '../api'

interface Props {
  resultado: BestfitResponse
  dados: Record<string, unknown>[]
  varDependente: string
  varsIndependentes: string[]
  nivelConfianca: number
}

function brl(n: number) {
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}

export default function AvaliarImovel({
  resultado, dados, varDependente, varsIndependentes, nivelConfianca,
}: Props) {
  const transformacoes = resultado.melhor_modelo.transformacoes
  const [valores, setValores] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [predicao, setPredicao] = useState<AvaliarImovelResponse | null>(null)

  // Sugere valores médios como placeholder
  const medias = useMemo(() => {
    const out: Record<string, number> = {}
    for (const v of varsIndependentes) {
      const nums = dados.map((d) => Number(d[v])).filter((n) => !isNaN(n))
      out[v] = nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : 0
    }
    return out
  }, [dados, varsIndependentes])

  const handleAvaliar = async () => {
    setErro(null)
    const imovel_alvo: Record<string, number> = {}
    for (const v of varsIndependentes) {
      const raw = valores[v]
      const n = raw === undefined || raw === '' ? medias[v] : Number(raw)
      if (isNaN(n)) { setErro(`Valor inválido para ${v}`); return }
      imovel_alvo[v] = n
    }
    setLoading(true)
    try {
      const res = await avaliarImovel({
        dados,
        variavel_dependente: varDependente,
        variaveis_independentes: varsIndependentes,
        transformacoes,
        imovel_alvo,
        nivel_confianca: nivelConfianca,
      })
      setPredicao(res)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao avaliar')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4">
      <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100 mb-1 flex items-center gap-2">
        <Home size={18} /> Avaliar imóvel-alvo
      </h3>
      <p className="text-xs text-slate-500 mb-3">
        Informe as características do imóvel para estimar o valor com o melhor modelo encontrado.
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-3">
        {varsIndependentes.map((v) => (
          <div key={v}>
            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">
              {v} <span className="text-slate-400">({transformacoes[v]})</span>
            </label>
            <input
              type="number"
              placeholder={medias[v] ? medias[v].toFixed(1) : '0'}
              value={valores[v] ?? ''}
              onChange={(e) => setValores({ ...valores, [v]: e.target.value })}
              className="w-full px-2 py-1.5 rounded border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 text-sm"
            />
          </div>
        ))}
      </div>

      <button
        onClick={handleAvaliar}
        disabled={loading}
        className="w-full py-2 rounded-lg bg-primary-600 hover:bg-primary-700 disabled:bg-slate-400 text-white text-sm font-medium flex items-center justify-center gap-2"
      >
        {loading ? <Loader2 size={16} className="animate-spin" /> : null}
        {loading ? 'Avaliando…' : 'Estimar valor'}
      </button>

      {erro && <p className="text-red-600 dark:text-red-400 text-xs mt-2">{erro}</p>}

      {predicao && (
        <div className="mt-4 p-4 rounded-lg bg-gradient-to-br from-primary-50 to-slate-50 dark:from-primary-500/10 dark:to-slate-900 border border-primary-100 dark:border-primary-500/20">
          <div className="text-xs text-slate-500 dark:text-slate-400">Valor estimado</div>
          <div className="text-3xl font-bold text-primary-700 dark:text-primary-300">
            {brl(predicao.valor_estimado)}
          </div>
          <div className="grid grid-cols-2 gap-3 mt-3 text-sm">
            <div>
              <div className="text-xs text-slate-500">Intervalo de predição ({(predicao.nivel_confianca * 100).toFixed(0)}%)</div>
              <div className="text-slate-800 dark:text-slate-100 font-medium">
                {brl(predicao.intervalo_predicao[0])} — {brl(predicao.intervalo_predicao[1])}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Campo de arbítrio</div>
              <div className="text-slate-800 dark:text-slate-100 font-medium">
                {brl(predicao.campo_arbitrio[0])} — {brl(predicao.campo_arbitrio[1])}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Amplitude</div>
              <div className="text-slate-800 dark:text-slate-100 font-medium">{predicao.amplitude_pct}%</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Grau de precisão</div>
              <div className="text-slate-800 dark:text-slate-100 font-medium">{predicao.grau_precisao}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
