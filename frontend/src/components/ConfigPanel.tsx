import type { ChangeEvent } from 'react'
import type { BestfitResponse, ExportConfig } from '../api'

interface Props {
  colunas: string[]
  varDependente: string
  setVarDependente: (v: string) => void
  varsIndependentes: string[]
  toggleVarIndep: (c: string) => void
  transfTestar: string[]
  toggleTransf: (t: string) => void
  nivelConfianca: number
  setNivelConfianca: (n: number) => void
  onFileUpload: (e: ChangeEvent<HTMLInputElement>) => void
  onCalcular: () => void
  loading: boolean
  dados: Record<string, unknown>[]
  exportConfig: ExportConfig
  setExportConfig: (c: ExportConfig) => void
  resultado: BestfitResponse | null
  onExportWord: () => void
  onExportPDF: () => void
  transformacoes: { value: string; label: string }[]
}

export default function ConfigPanel(props: Props) {
  const {
    colunas, varDependente, setVarDependente, varsIndependentes, toggleVarIndep,
    transfTestar, toggleTransf, nivelConfianca, setNivelConfianca,
    onFileUpload, onCalcular, loading, dados, exportConfig, setExportConfig,
    resultado, onExportWord, onExportPDF, transformacoes,
  } = props

  return (
    <div className="space-y-4">
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">1. Dados (CSV)</h2>
        <input
          type="file"
          accept=".csv"
          onChange={onFileUpload}
          className="block w-full text-sm text-slate-600 dark:text-slate-300
                     file:mr-2 file:py-1.5 file:px-3 file:rounded-md file:border-0
                     file:bg-primary-600 file:text-white file:font-medium
                     hover:file:bg-primary-700 cursor-pointer"
        />
        {dados.length > 0 && (
          <p className="text-xs text-slate-500 mt-2">
            {dados.length} linhas · {colunas.length} colunas
          </p>
        )}
      </div>

      {colunas.length > 0 && (
        <>
          <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">2. Variável dependente</h2>
            <select
              value={varDependente}
              onChange={(e) => setVarDependente(e.target.value)}
              className="w-full px-3 py-1.5 rounded border border-slate-300 dark:border-slate-600
                         dark:bg-slate-700 dark:text-slate-100 text-sm"
            >
              {colunas.map((c) => (<option key={c} value={c}>{c}</option>))}
            </select>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">3. Variáveis independentes</h2>
            <div className="space-y-1 max-h-48 overflow-auto pr-1">
              {colunas.filter((c) => c !== varDependente).map((c) => (
                <label key={c} className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={varsIndependentes.includes(c)}
                    onChange={() => toggleVarIndep(c)}
                    className="accent-primary-600"
                  />
                  {c}
                </label>
              ))}
            </div>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">
              4. Transformações a testar
            </h2>
            <p className="text-xs text-slate-500 mb-2">O servidor testa todas as combinações cartesianas.</p>
            <div className="space-y-1 max-h-44 overflow-auto pr-1">
              {transformacoes.map((t) => (
                <label key={t.value} className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={transfTestar.includes(t.value)}
                    onChange={() => toggleTransf(t.value)}
                    className="accent-primary-600"
                  />
                  {t.label}
                </label>
              ))}
            </div>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">5. Nível de confiança</h2>
            <input
              type="range"
              min="0.5"
              max="0.99"
              step="0.01"
              value={nivelConfianca}
              onChange={(e) => setNivelConfianca(parseFloat(e.target.value))}
              className="w-full accent-primary-600"
            />
            <p className="text-xs text-slate-600 dark:text-slate-300">{(nivelConfianca * 100).toFixed(0)}%</p>
          </div>

          <button
            onClick={onCalcular}
            disabled={loading || !varDependente || varsIndependentes.length === 0}
            className="w-full py-2.5 rounded-lg bg-primary-600 hover:bg-primary-700 disabled:bg-slate-400
                       text-white font-medium shadow transition-colors"
          >
            {loading ? 'Calculando…' : 'Calcular regressão'}
          </button>
        </>
      )}

      {resultado && (
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4 space-y-2">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Dados do laudo</h2>
          <input
            type="text"
            placeholder="Endereço do imóvel"
            value={exportConfig.endereco}
            onChange={(e) => setExportConfig({ ...exportConfig, endereco: e.target.value })}
            className="w-full px-3 py-1.5 rounded border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 text-sm"
          />
          <input
            type="date"
            value={exportConfig.data_avaliacao}
            onChange={(e) => setExportConfig({ ...exportConfig, data_avaliacao: e.target.value })}
            className="w-full px-3 py-1.5 rounded border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 text-sm"
          />
          <input
            type="text"
            placeholder="Avaliador (nome)"
            value={exportConfig.avaliador_nome}
            onChange={(e) => setExportConfig({ ...exportConfig, avaliador_nome: e.target.value })}
            className="w-full px-3 py-1.5 rounded border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 text-sm"
          />
          <input
            type="text"
            placeholder="CREA"
            value={exportConfig.avaliador_crea}
            onChange={(e) => setExportConfig({ ...exportConfig, avaliador_crea: e.target.value })}
            className="w-full px-3 py-1.5 rounded border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 text-sm"
          />
          <div className="grid grid-cols-2 gap-2 pt-2">
            <button onClick={onExportWord} className="py-2 rounded bg-slate-700 hover:bg-slate-800 text-white text-sm">Word</button>
            <button onClick={onExportPDF} className="py-2 rounded bg-red-600 hover:bg-red-700 text-white text-sm">PDF</button>
          </div>
        </div>
      )}
    </div>
  )
}
