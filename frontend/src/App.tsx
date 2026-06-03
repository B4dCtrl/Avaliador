import { useCallback, useState } from 'react'
import Papa from 'papaparse'
import {
  calcularBestfit,
  exportarWord,
  exportarPDF,
  bestfitParaExport,
  type BestfitRequest,
  type BestfitResponse,
  type ExportConfig,
} from './api'
import ConfigPanel from './components/ConfigPanel'
import ResultsPanel from './components/ResultsPanel'
import Charts from './components/Charts'

const TRANSFORMACOES = [
  { value: 'nenhuma', label: 'Sem transformação' },
  { value: 'log', label: 'ln(x) — Logarítmica' },
  { value: 'raiz_quadrada', label: '√x — Raiz quadrada' },
  { value: 'raiz_reciproca', label: '1/√x — Recíproca raiz' },
  { value: 'reciproca', label: '1/x — Recíproca' },
  { value: 'reciproca_quadrada', label: '1/x² — Recíproca quadrada' },
  { value: 'quadrada', label: 'x² — Quadrada' },
]

export default function App() {
  const [darkMode, setDarkMode] = useState(false)
  const [dados, setDados] = useState<Record<string, unknown>[]>([])
  const [colunas, setColunas] = useState<string[]>([])
  const [varDependente, setVarDependente] = useState('')
  const [varsIndependentes, setVarsIndependentes] = useState<string[]>([])
  const [transfTestar, setTransfTestar] = useState<string[]>(['nenhuma', 'log', 'raiz_quadrada', 'raiz_reciproca'])
  const [nivelConfianca, setNivelConfianca] = useState(0.80)
  const [loading, setLoading] = useState(false)
  const [resultado, setResultado] = useState<BestfitResponse | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [exportConfig, setExportConfig] = useState<ExportConfig>({
    endereco: '',
    data_avaliacao: new Date().toISOString().slice(0, 10),
    avaliador_nome: '',
    avaliador_crea: '',
  })

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    Papa.parse(file, {
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: (results) => {
        const data = results.data as Record<string, unknown>[]
        setDados(data)
        const cols = Object.keys(data[0] || {})
        setColunas(cols)
        if (cols.length > 0) {
          setVarDependente(cols[0])
          setVarsIndependentes(cols.slice(1))
        }
        setResultado(null)
        setErro(null)
      },
      error: () => setErro('Erro ao ler arquivo CSV'),
    })
  }, [])

  const handleCalcular = useCallback(async () => {
    if (!varDependente || varsIndependentes.length === 0) {
      setErro('Selecione variável dependente e pelo menos uma independente')
      return
    }
    setLoading(true)
    setErro(null)

    const req: BestfitRequest = {
      dados,
      variavel_dependente: varDependente,
      variaveis_independentes: varsIndependentes,
      transformacoes_testar: transfTestar,
      excluir_indices: [],
      nivel_confianca: nivelConfianca,
    }

    try {
      const res = await calcularBestfit(req)
      setResultado(res)
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Erro desconhecido')
    } finally {
      setLoading(false)
    }
  }, [dados, varDependente, varsIndependentes, transfTestar, nivelConfianca])

  const handleExportWord = useCallback(async () => {
    if (!resultado) return
    try {
      const payload = bestfitParaExport(resultado, varDependente)
      const r = await exportarWord(payload, exportConfig)
      window.open(r.url_download, '_blank')
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Erro ao exportar Word')
    }
  }, [resultado, varDependente, exportConfig])

  const handleExportPDF = useCallback(async () => {
    if (!resultado) return
    try {
      const payload = bestfitParaExport(resultado, varDependente)
      const r = await exportarPDF(payload, exportConfig)
      window.open(r.url_download, '_blank')
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Erro ao exportar PDF')
    }
  }, [resultado, varDependente, exportConfig])

  const toggleTransf = (t: string) => {
    setTransfTestar((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]))
  }

  const toggleVarIndep = (col: string) => {
    setVarsIndependentes((prev) =>
      prev.includes(col) ? prev.filter((x) => x !== col) : [...prev, col],
    )
  }

  return (
    <div className={darkMode ? 'dark' : ''}>
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 transition-colors">
        <header className="bg-navy dark:bg-slate-800 text-white px-6 py-4 flex items-center justify-between shadow-lg">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-primary-500 rounded-lg flex items-center justify-center font-bold">A</div>
            <h1 className="text-xl font-bold">Avaliador</h1>
            <span className="text-xs bg-primary-600 px-2 py-0.5 rounded-full ml-2">NBR 14653-02</span>
          </div>
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="px-3 py-1 rounded bg-white/10 hover:bg-white/20 text-sm"
          >
            {darkMode ? '☀️ Claro' : '🌙 Escuro'}
          </button>
        </header>

        <main className="flex flex-col lg:flex-row gap-4 p-4 max-w-[1800px] mx-auto">
          <aside className="lg:w-[400px] shrink-0">
            <ConfigPanel
              colunas={colunas}
              varDependente={varDependente}
              setVarDependente={setVarDependente}
              varsIndependentes={varsIndependentes}
              toggleVarIndep={toggleVarIndep}
              transfTestar={transfTestar}
              toggleTransf={toggleTransf}
              nivelConfianca={nivelConfianca}
              setNivelConfianca={setNivelConfianca}
              onFileUpload={handleFileUpload}
              onCalcular={handleCalcular}
              loading={loading}
              dados={dados}
              exportConfig={exportConfig}
              setExportConfig={setExportConfig}
              resultado={resultado}
              onExportWord={handleExportWord}
              onExportPDF={handleExportPDF}
              transformacoes={TRANSFORMACOES}
            />
          </aside>

          <section className="flex-1 min-w-0">
            {erro && (
              <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg mb-4">
                {erro}
              </div>
            )}

            {resultado ? (
              <div className="space-y-4">
                <ResultsPanel resultado={resultado} />
                <Charts resultado={resultado} dados={dados} varDependente={varDependente} />
              </div>
            ) : (
              <div className="flex items-center justify-center h-96 text-slate-400 dark:text-slate-500 bg-white dark:bg-slate-800 rounded-lg shadow">
                <div className="text-center">
                  <div className="text-6xl mb-4">📊</div>
                  <p className="text-lg">Carregue um CSV e clique em Calcular</p>
                  <p className="text-sm mt-2">Auto-ranking de transformações + diagnósticos NBR 14653-02</p>
                </div>
              </div>
            )}
          </section>
        </main>
      </div>
    </div>
  )
}
