import { useState } from 'react'
import { TrendingUp, Home as HomeIcon, Repeat, Loader2, CheckCircle2, AlertTriangle, Minus } from 'lucide-react'
import { analisarViabilidade, type ViabilidadeResponse } from '../api'

const brl = (n: number | null | undefined) =>
  n == null || !Number.isFinite(n) ? '—' : n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })

// valor de mercado sugerido: última avaliação salva neste navegador
function valorMercadoSugerido(): number | '' {
  try {
    const raw = localStorage.getItem('avaliador_ultimo_valor')
    if (raw) return Number(raw)
  } catch { /* ignora */ }
  return ''
}

export default function Viabilidade() {
  const [form, setForm] = useState({
    valor_mercado: valorMercadoSugerido(),
    preco_compra: '' as number | '',
    custos_aquisicao: '' as number | '',
    custos_reforma: '' as number | '',
    aluguel_mensal: '' as number | '',
    despesas_mensais: '' as number | '',
    valorizacao_anual_pct: 6 as number | '',
    horizonte_anos: 5 as number | '',
  })
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [res, setRes] = useState<ViabilidadeResponse | null>(null)

  const set = (k: keyof typeof form, v: string) =>
    setForm({ ...form, [k]: v === '' ? '' : Number(v) })

  const calcular = async () => {
    setErro(null)
    if (!form.valor_mercado || !form.preco_compra) {
      setErro('Informe pelo menos o valor de mercado e o preço de compra.')
      return
    }
    setLoading(true)
    try {
      const r = await analisarViabilidade({
        valor_mercado: Number(form.valor_mercado),
        preco_compra: Number(form.preco_compra),
        custos_aquisicao: Number(form.custos_aquisicao) || 0,
        custos_reforma: Number(form.custos_reforma) || 0,
        aluguel_mensal: form.aluguel_mensal === '' ? null : Number(form.aluguel_mensal),
        despesas_mensais: Number(form.despesas_mensais) || 0,
        valorizacao_anual_pct: Number(form.valorizacao_anual_pct) || 0,
        horizonte_anos: Number(form.horizonte_anos) || 5,
      })
      setRes(r)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao calcular')
    } finally {
      setLoading(false)
    }
  }

  const vereditoClasses = res?.veredito === 'Favorável'
    ? 'border-emerald-400 bg-emerald-50 text-emerald-700'
    : res?.veredito === 'Desfavorável'
    ? 'border-red-400 bg-red-50 text-red-700'
    : 'border-amber-400 bg-amber-50 text-amber-700'
  const VereditoIcon = res?.veredito === 'Favorável' ? CheckCircle2 : res?.veredito === 'Desfavorável' ? AlertTriangle : Minus

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <TrendingUp size={24} /> Viabilidade de investimento
        </h1>
        <p className="text-sm text-slate-500">Compare o valor de mercado com o negócio e veja se o investimento compensa.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Formulário */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4 space-y-3">
          <div className="text-sm font-semibold text-slate-700">Dados do negócio</div>
          <Campo label="Valor de mercado (avaliação)" v={form.valor_mercado} on={(x) => set('valor_mercado', x)} dica="Puxamos da sua última avaliação. É o valor justo estimado pelo modelo." />
          <Campo label="Preço de compra" v={form.preco_compra} on={(x) => set('preco_compra', x)} />
          <div className="grid grid-cols-2 gap-3">
            <Campo label="Custos de aquisição (ITBI, escritura)" v={form.custos_aquisicao} on={(x) => set('custos_aquisicao', x)} />
            <Campo label="Custos de reforma" v={form.custos_reforma} on={(x) => set('custos_reforma', x)} />
          </div>

          <div className="text-sm font-semibold text-slate-700 pt-2">Renda (locação) — opcional</div>
          <div className="grid grid-cols-2 gap-3">
            <Campo label="Aluguel mensal" v={form.aluguel_mensal} on={(x) => set('aluguel_mensal', x)} />
            <Campo label="Despesas mensais (IPTU, cond.)" v={form.despesas_mensais} on={(x) => set('despesas_mensais', x)} />
          </div>

          <div className="text-sm font-semibold text-slate-700 pt-2">Revenda — opcional</div>
          <div className="grid grid-cols-2 gap-3">
            <Campo label="Valorização anual (%)" v={form.valorizacao_anual_pct} on={(x) => set('valorizacao_anual_pct', x)} />
            <Campo label="Horizonte (anos)" v={form.horizonte_anos} on={(x) => set('horizonte_anos', x)} />
          </div>

          {erro && <div className="text-[12px] text-red-600">{erro}</div>}
          <button onClick={calcular} disabled={loading}
            className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white text-sm font-medium flex items-center justify-center gap-2">
            {loading ? <Loader2 size={16} className="animate-spin" /> : <TrendingUp size={16} />}
            {loading ? 'Calculando…' : 'Analisar viabilidade'}
          </button>
        </div>

        {/* Resultado */}
        <div className="space-y-4">
          {!res ? (
            <div className="h-full flex items-center justify-center text-slate-400 bg-white border border-slate-200 rounded-xl p-8 text-center">
              <div>
                <TrendingUp size={40} className="mx-auto mb-2 opacity-40" />
                <p className="text-sm">Preencha os dados e clique em Analisar.</p>
              </div>
            </div>
          ) : (
            <>
              <div className={`rounded-xl border-2 p-4 ${vereditoClasses}`}>
                <div className="flex items-center gap-2 font-bold text-lg">
                  <VereditoIcon size={22} /> {res.veredito}
                </div>
                <ul className="mt-2 space-y-1 text-[12px] text-slate-700">
                  {res.sinais.map((s, i) => <li key={i}>• {s}</li>)}
                  {res.sinais.length === 0 && <li>Sem sinais fortes — analise caso a caso.</li>}
                </ul>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
                <div className="text-sm font-semibold text-slate-700 mb-2">Resumo</div>
                <div className="grid grid-cols-2 gap-2 text-[13px]">
                  <Box label="Investimento total" val={brl(res.investimento_total)} />
                  <Box label="Valor de mercado" val={brl(res.valor_mercado)} />
                  <Box label="Ganho patrimonial imediato" val={`${brl(res.comparacao_mercado.ganho_patrimonial)} (${res.comparacao_mercado.ganho_patrimonial_pct.toFixed(1)}%)`}
                    cor={res.comparacao_mercado.ganho_patrimonial >= 0 ? 'emerald' : 'red'} />
                  <Box label="Desconto na compra" val={`${res.comparacao_mercado.desconto_pct.toFixed(1)}%`}
                    cor={res.comparacao_mercado.desconto_pct >= 0 ? 'emerald' : 'red'} />
                </div>
              </div>

              {res.renda && (
                <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
                  <div className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1"><HomeIcon size={15} /> Cenário de renda (locação)</div>
                  <div className="grid grid-cols-2 gap-2 text-[13px]">
                    <Box label="Líquido mensal" val={brl(res.renda.liquido_mensal)} />
                    <Box label="Rentab. líquida a.a." val={`${res.renda.yield_liquido_anual_pct.toFixed(2)}%`} cor="blue" />
                    <Box label="Cap rate" val={`${res.renda.cap_rate_pct.toFixed(2)}%`} />
                    <Box label="Payback" val={res.renda.payback_anos != null ? `${res.renda.payback_anos} anos` : '—'} />
                  </div>
                </div>
              )}

              {res.revenda && (
                <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
                  <div className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1"><Repeat size={15} /> Cenário de revenda ({res.revenda.horizonte_anos} anos)</div>
                  <div className="grid grid-cols-2 gap-2 text-[13px]">
                    <Box label="Valor futuro estimado" val={brl(res.revenda.valor_futuro_estimado)} />
                    <Box label="Lucro líquido" val={brl(res.revenda.lucro_liquido)} cor={res.revenda.lucro_liquido >= 0 ? 'emerald' : 'red'} />
                    <Box label="ROI total" val={`${res.revenda.roi_total_pct.toFixed(1)}%`} />
                    <Box label="Retorno anualizado" val={`${res.revenda.retorno_anualizado_pct.toFixed(1)}%`} cor="blue" />
                  </div>
                </div>
              )}

              <p className="text-[11px] text-slate-400">{res.observacao}</p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function Campo({ label, v, on, dica }: { label: string; v: number | ''; on: (x: string) => void; dica?: string }) {
  return (
    <div>
      <label className="block text-[11px] text-slate-500 mb-0.5">{label}</label>
      <input type="number" value={v} onChange={(e) => on(e.target.value)}
        className="w-full px-2.5 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:border-blue-500" />
      {dica && <p className="text-[10px] text-slate-400 mt-0.5">{dica}</p>}
    </div>
  )
}

const COR_TEXTO: Record<string, string> = {
  slate: 'text-slate-700', emerald: 'text-emerald-700', red: 'text-red-700', blue: 'text-blue-700',
}
function Box({ label, val, cor = 'slate' }: { label: string; val: string; cor?: string }) {
  return (
    <div className="bg-slate-50 rounded-lg px-3 py-2">
      <div className="text-[10px] text-slate-500">{label}</div>
      <div className={`font-semibold ${COR_TEXTO[cor] ?? COR_TEXTO.slate}`}>{val}</div>
    </div>
  )
}
