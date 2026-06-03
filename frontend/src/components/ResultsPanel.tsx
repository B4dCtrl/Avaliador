import type { BestfitResponse } from '../api'

interface Props { resultado: BestfitResponse }

function fmt(n: number, d = 4) { return Number.isFinite(n) ? n.toFixed(d) : '—' }

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="bg-slate-50 dark:bg-slate-700 px-3 py-2 rounded">
      <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>
      <div className="text-base font-semibold text-slate-800 dark:text-slate-100">{value}</div>
      {hint && <div className="text-[10px] text-slate-500">{hint}</div>}
    </div>
  )
}

export default function ResultsPanel({ resultado }: Props) {
  const m = resultado.melhor_modelo
  const d = resultado.diagnosticos

  return (
    <div className="space-y-4">
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4">
        <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3">Melhor modelo</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Stat label="R²" value={fmt(m.r2, 4)} />
          <Stat label="R² ajustado" value={fmt(m.r2_ajustado, 4)} />
          <Stat label="F" value={fmt(m.f_stat, 2)} hint={`p = ${fmt(m.f_p_valor, 6)}`} />
          <Stat label="AIC / BIC" value={`${fmt(m.aic, 1)} / ${fmt(m.bic, 1)}`} />
        </div>
        <p className="text-sm mt-3 text-slate-600 dark:text-slate-300">
          Transformação Y: <code className="font-mono">{m.transformacao_y}</code>
          {' · '}{resultado.n_modelos_testados} modelos testados.
        </p>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4">
        <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100 mb-2">Coeficientes</h3>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-left">
                <th className="px-2 py-1.5">Variável</th>
                <th className="px-2 py-1.5">Transf.</th>
                <th className="px-2 py-1.5 text-right">Coef.</th>
                <th className="px-2 py-1.5 text-right">Erro padr.</th>
                <th className="px-2 py-1.5 text-right">t</th>
                <th className="px-2 py-1.5 text-right">p-valor</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-slate-100 dark:border-slate-700">
                <td className="px-2 py-1.5 italic">Intercepto</td><td className="px-2 py-1.5">—</td>
                <td className="px-2 py-1.5 text-right">{fmt(m.intercepto, 4)}</td>
                <td className="px-2 py-1.5 text-right">—</td><td className="px-2 py-1.5 text-right">—</td><td className="px-2 py-1.5 text-right">—</td>
              </tr>
              {m.coeficientes.map((c) => (
                <tr key={c.variavel} className="border-b border-slate-100 dark:border-slate-700">
                  <td className="px-2 py-1.5">{c.variavel}</td>
                  <td className="px-2 py-1.5">{c.transformacao}</td>
                  <td className="px-2 py-1.5 text-right">{fmt(c.coeficiente, 4)}</td>
                  <td className="px-2 py-1.5 text-right">{fmt(c.erro_padrao, 4)}</td>
                  <td className="px-2 py-1.5 text-right">{fmt(c.t_stat, 3)}</td>
                  <td className={`px-2 py-1.5 text-right ${c.p_valor < 0.05 ? 'text-green-700 dark:text-green-400 font-medium' : 'text-slate-500'}`}>
                    {fmt(c.p_valor, 5)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4">
        <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100 mb-2">Diagnósticos</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <Stat label="Shapiro-Wilk (normalidade)" value={fmt(d.shapiro_wilk.stat, 4)} hint={`p = ${fmt(d.shapiro_wilk.p_valor, 4)}`} />
          <Stat label="Jarque-Bera (normalidade)" value={fmt(d.jarque_bera.stat, 4)} hint={`p = ${fmt(d.jarque_bera.p_valor, 4)}`} />
          <Stat label="Breusch-Pagan (homocedast.)" value={fmt(d.breusch_pagan.stat, 4)} hint={`p = ${fmt(d.breusch_pagan.p_valor, 4)}`} />
          <Stat label="Outliers Cook's" value={String(d.outliers_cooks.detectados)} hint={`limiar ${fmt(d.outliers_cooks.limiar, 4)}`} />
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4">
        <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100 mb-2">Conformidade NBR 14653-02</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Stat label="Amplitude IC" value={resultado.amplitude_pct != null ? `${fmt(resultado.amplitude_pct, 2)}%` : '—'} />
          <Stat label="Grau precisão" value={resultado.grau_precisao || '—'} />
          <Stat label="Grau fundamentação" value={resultado.grau_fundamentacao.grau} />
          <Stat
            label="Campo arbítrio"
            value={
              resultado.campo_arbitrio_inferior != null && resultado.campo_arbitrio_superior != null
                ? `${fmt(resultado.campo_arbitrio_inferior, 0)} … ${fmt(resultado.campo_arbitrio_superior, 0)}`
                : '—'
            }
          />
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4">
        <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100 mb-2">Ranking (top {resultado.ranking.length})</h3>
        <div className="overflow-auto max-h-72">
          <table className="w-full text-xs">
            <thead className="sticky top-0">
              <tr className="bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-left">
                <th className="px-2 py-1.5">#</th>
                <th className="px-2 py-1.5">Transformações</th>
                <th className="px-2 py-1.5 text-right">R²</th>
                <th className="px-2 py-1.5 text-right">R² aj.</th>
                <th className="px-2 py-1.5 text-right">AIC</th>
                <th className="px-2 py-1.5 text-right">BIC</th>
              </tr>
            </thead>
            <tbody>
              {resultado.ranking.map((r) => (
                <tr key={r.id} className="border-b border-slate-100 dark:border-slate-700">
                  <td className="px-2 py-1.5">{r.id}</td>
                  <td className="px-2 py-1.5">
                    {Object.entries(r.transformacoes).map(([v, t]) => (
                      <span key={v} className="inline-block bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded mr-1 mb-0.5">
                        {v}:{t}
                      </span>
                    ))}
                  </td>
                  <td className="px-2 py-1.5 text-right">{fmt(r.r2, 4)}</td>
                  <td className="px-2 py-1.5 text-right">{fmt(r.r2_ajustado, 4)}</td>
                  <td className="px-2 py-1.5 text-right">{fmt(r.aic, 1)}</td>
                  <td className="px-2 py-1.5 text-right">{fmt(r.bic, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
