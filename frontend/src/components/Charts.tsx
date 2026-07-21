import Plot from 'react-plotly.js'
import type { BestfitResponse } from '../api'

interface Props {
  resultado: BestfitResponse
  dados: Record<string, unknown>[]
  varDependente: string
}

export default function Charts({ resultado }: Props) {
  const m = resultado.melhor_modelo
  const residuos = m.residuos
  const ajustados = m.valores_ajustados

  // Q-Q plot (quantis teóricos vs amostrais)
  const ordenados = [...residuos].sort((a, b) => a - b)
  const n = ordenados.length
  const teoricos = ordenados.map((_, i) => {
    const p = (i + 0.5) / n
    return Math.sqrt(2) * inverseErf(2 * p - 1)
  })

  const pp = resultado.poder_predicao
  // Resíduos padronizados (do backend; fallback: calcula localmente)
  const dp = stdev(residuos) || 1
  const rp = m.residuos_padronizados ?? residuos.map((r) => r / dp)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {pp && pp.observado.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4 lg:col-span-2">
          <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1">
            Poder de predição — Observado × Estimado
          </h4>
          <p className="text-[11px] text-slate-500 mb-2">
            Desvio médio: <b>{pp.desvio_medio_pct}%</b> · Dentro de ±20%: <b>{pp.pct_dentro_20}%</b> das amostras.
            Quanto mais próximos da reta de 45°, melhor o modelo.
          </p>
          <Plot
            data={[
              {
                x: pp.observado,
                y: pp.estimado,
                mode: 'markers',
                type: 'scatter',
                marker: { color: '#2563EB', size: 8 },
                name: 'Amostras',
              },
              {
                x: [Math.min(...pp.observado), Math.max(...pp.observado)],
                y: [Math.min(...pp.observado), Math.max(...pp.observado)],
                mode: 'lines',
                type: 'scatter',
                line: { color: '#ef4444', dash: 'dash' },
                name: 'Reta 45° (ideal)',
              },
            ]}
            layout={{
              margin: { t: 10, l: 60, r: 10, b: 40 },
              xaxis: { title: { text: 'Valor observado' } },
              yaxis: { title: { text: 'Valor estimado' } },
              autosize: true,
              height: 300,
              showlegend: false,
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor: 'rgba(0,0,0,0)',
              font: { color: '#475569' },
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%' }}
            useResizeHandler
          />
        </div>
      )}

      <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">Resíduos × Ajustados</h4>
        <Plot
          data={[{
            x: ajustados,
            y: residuos,
            mode: 'markers',
            type: 'scatter',
            marker: { color: '#2563EB', size: 8 },
            name: 'Resíduos',
          }]}
          layout={{
            margin: { t: 10, l: 50, r: 10, b: 40 },
            xaxis: { title: { text: 'Ajustados' } },
            yaxis: { title: { text: 'Resíduos' }, zeroline: true, zerolinecolor: '#ef4444' },
            autosize: true,
            height: 280,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#475569' },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
          useResizeHandler
        />
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">Q-Q Plot dos resíduos</h4>
        <Plot
          data={[
            {
              x: teoricos,
              y: ordenados,
              mode: 'markers',
              type: 'scatter',
              marker: { color: '#2563EB', size: 8 },
              name: 'Resíduos',
            },
            {
              x: [Math.min(...teoricos), Math.max(...teoricos)],
              y: [Math.min(...ordenados), Math.max(...ordenados)],
              mode: 'lines',
              type: 'scatter',
              line: { color: '#ef4444' },
              name: 'Linha ideal',
            },
          ]}
          layout={{
            margin: { t: 10, l: 50, r: 10, b: 40 },
            xaxis: { title: { text: 'Quantis teóricos' } },
            yaxis: { title: { text: 'Quantis amostrais' } },
            autosize: true,
            height: 280,
            showlegend: false,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#475569' },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
          useResizeHandler
        />
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4 lg:col-span-2">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1">Resíduos padronizados por amostra</h4>
        <p className="text-[11px] text-slate-500 mb-2">
          Pontos fora das faixas de ±2 desvios-padrão são candidatos a outlier (norma recomenda investigar).
        </p>
        <Plot
          data={[
            {
              x: rp.map((_, i) => i + 1),
              y: rp,
              mode: 'markers',
              type: 'scatter',
              marker: {
                size: 9,
                color: rp.map((r) => (Math.abs(r) > 2 ? '#ef4444' : '#2563EB')),
              },
              name: 'Resíduo padronizado',
            },
          ]}
          layout={{
            margin: { t: 10, l: 50, r: 10, b: 40 },
            xaxis: { title: { text: 'Amostra' }, dtick: 1 },
            yaxis: { title: { text: 'Resíduo padronizado' }, zeroline: true },
            shapes: [
              { type: 'line', x0: 0.5, x1: rp.length + 0.5, y0: 2, y1: 2, line: { color: '#ef4444', dash: 'dash', width: 1 } },
              { type: 'line', x0: 0.5, x1: rp.length + 0.5, y0: -2, y1: -2, line: { color: '#ef4444', dash: 'dash', width: 1 } },
            ],
            autosize: true,
            height: 260,
            showlegend: false,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#475569' },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
          useResizeHandler
        />
      </div>
    </div>
  )
}

function stdev(arr: number[]): number {
  const mean = arr.reduce((a, b) => a + b, 0) / arr.length
  return Math.sqrt(arr.reduce((s, x) => s + (x - mean) ** 2, 0) / Math.max(1, arr.length - 1))
}

// Aproximação Winitzki para a função inversa do erf
function inverseErf(x: number): number {
  const a = 0.147
  const ln = Math.log(1 - x * x)
  const part1 = 2 / (Math.PI * a) + ln / 2
  const part2 = ln / a
  return Math.sign(x) * Math.sqrt(Math.sqrt(part1 * part1 - part2) - part1)
}
