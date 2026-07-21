import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import Papa from 'papaparse'
import { ChevronLeft, ChevronRight, FilePlus, Save, FolderOpen, Calculator, RotateCcw } from 'lucide-react'
import {
  calcularBestfit, avaliarImovel, analisarAmostras, exportarWord, exportarPDF, bestfitParaExport, baixarArquivo,
  type BestfitResponse, type AvaliarImovelResponse, type ExportConfig,
} from '../api'
import {
  type GridState, gridVazio, gridDeCSV, acrescentarCSV, montarPayloadBestfit, montarImovelAlvo,
  reconsiderarTodas, desabilitarIndices,
} from '../grid'
import { carregarPerfil } from './Home'
import DataGrid from '../components/DataGrid'
import PainelAvaliando from '../components/PainelAvaliando'
import ResultsPanel from '../components/ResultsPanel'
import TabelaResultados from '../components/TabelaResultados'
import Charts from '../components/Charts'

const TRANSFORMACOES = [
  { value: 'nenhuma', label: 'Sem transf.' }, { value: 'log', label: 'ln(x)' },
  { value: 'raiz_quadrada', label: '√x' }, { value: 'raiz_reciproca', label: '1/√x' },
  { value: 'reciproca', label: '1/x' }, { value: 'reciproca_quadrada', label: '1/x²' },
  { value: 'quadrada', label: 'x²' },
]
const STORAGE_KEY = 'avaliador_projeto_v1'
const brl = (n: number | null | undefined) =>
  n == null || !Number.isFinite(n)
    ? '—'
    : n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })

const PASSOS = ['Dados', 'Imóvel', 'Calcular', 'Resultado']

interface Persistido { nomeProjeto: string; grid: GridState; transfTestar: string[]; nivelConfianca: number }

export default function Backoffice() {
  const [passo, setPasso] = useState(1) // 1..4
  const [nomeProjeto, setNomeProjeto] = useState('Nova avaliação')
  const [grid, setGrid] = useState<GridState>(() => gridVazio())
  const [transfTestar, setTransfTestar] = useState<string[]>(['nenhuma', 'log', 'raiz_quadrada', 'raiz_reciproca'])
  const [nivelConfianca, setNivelConfianca] = useState(0.80)
  const [avancado, setAvancado] = useState(false)

  const [loading, setLoading] = useState(false)
  const [resultado, setResultado] = useState<BestfitResponse | null>(null)
  const [avaliacao, setAvaliacao] = useState<AvaliarImovelResponse | null>(null)
  // Arbítrio do avaliador: valor final escolhido dentro do campo de arbítrio (±15%)
  const [valorArbitrado, setValorArbitrado] = useState<number | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [salvoEm, setSalvoEm] = useState<string | null>(null)
  const [exportConfig, setExportConfig] = useState<ExportConfig>(() => {
    const perfil = carregarPerfil()
    return {
      endereco: '', data_avaliacao: new Date().toISOString().slice(0, 10),
      avaliador_nome: perfil.nome, avaliador_crea: perfil.crea, avaliador_empresa: perfil.empresa,
    }
  })
  const fileJSON = useRef<HTMLInputElement>(null)

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const p: Persistido = JSON.parse(raw)
        if (p.grid) setGrid(p.grid); if (p.nomeProjeto) setNomeProjeto(p.nomeProjeto)
        if (p.transfTestar) setTransfTestar(p.transfTestar); if (typeof p.nivelConfianca === 'number') setNivelConfianca(p.nivelConfianca)
      }
    } catch { /* ignora */ }
  }, [])

  useEffect(() => {
    const p: Persistido = { nomeProjeto, grid, transfTestar, nivelConfianca }
    const t = setTimeout(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify(p)); setSalvoEm(new Date().toLocaleTimeString('pt-BR')) }, 600)
    return () => clearTimeout(t)
  }, [nomeProjeto, grid, transfTestar, nivelConfianca])

  const flash = (m: string) => { setMsg(m); setErro(null); setTimeout(() => setMsg(null), 2500) }

  const handleImportCSV = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return
    Papa.parse(file, {
      header: true, dynamicTyping: false, skipEmptyLines: true,
      complete: (res) => {
        const data = res.data as Record<string, unknown>[]
        if (!data.length) { setErro('CSV vazio'); return }
        setGrid(gridDeCSV(data)); setResultado(null); setAvaliacao(null); setErro(null); flash(`${data.length} amostras importadas`)
      },
      error: () => setErro('Erro ao ler CSV'),
    })
    e.target.value = ''
  }, [])

  const handleAppendCSV = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return
    Papa.parse(file, {
      header: true, dynamicTyping: false, skipEmptyLines: true,
      complete: (res) => {
        const data = res.data as Record<string, unknown>[]
        if (!data.length) { setErro('CSV vazio'); return }
        setGrid((g) => acrescentarCSV(g, data)); flash(`${data.length} amostras acrescentadas`)
      },
      error: () => setErro('Erro ao ler CSV'),
    })
    e.target.value = ''
  }, [])

  // Calcular + (se possível) estimar o imóvel automaticamente.
  // transformacoesEscolhidas: arbítrio do avaliador (usar modelo do ranking).
  const handleCalcular = useCallback(async (
    transformacoesEscolhidas?: Record<string, string>,
  ) => {
    setErro(null)
    let payload
    try { payload = montarPayloadBestfit(grid, transfTestar, nivelConfianca) }
    catch (e) { setErro(e instanceof Error ? e.message : 'Dados inválidos'); return }
    if (transformacoesEscolhidas) payload = { ...payload, transformacoes_escolhidas: transformacoesEscolhidas }
    setLoading(true)
    try {
      const res = await calcularBestfit(payload)
      setResultado(res)
      setValorArbitrado(null)
      const alvo = montarImovelAlvo(grid)
      if (alvo) {
        try {
          const dep = grid.colunas.find((c) => c.papel === 'dependente')!
          const indeps = grid.colunas.filter((c) => c.papel === 'independente')
          const av = await avaliarImovel({
            dados: payload.dados, variavel_dependente: dep.nome,
            variaveis_independentes: indeps.map((c) => c.nome),
            transformacoes: res.melhor_modelo.transformacoes, imovel_alvo: alvo, nivel_confianca: nivelConfianca,
          })
          setAvaliacao(av)
        } catch { setAvaliacao(null) }
      } else { setAvaliacao(null) }
      setPasso(4)
      if (transformacoesEscolhidas) flash('Avaliação recalculada com o modelo escolhido')
    } catch (e) { setErro(e instanceof Error ? e.message : 'Erro no cálculo') }
    finally { setLoading(false) }
  }, [grid, transfTestar, nivelConfianca])

  const handleDesabilitar = useCallback(async () => {
    if (!resultado) return
    setLoading(true); setErro(null)
    try {
      const dep = grid.colunas.find((c) => c.papel === 'dependente')!
      const indeps = grid.colunas.filter((c) => c.papel === 'independente')
      const payload = montarPayloadBestfit(grid, transfTestar, nivelConfianca)
      const an = await analisarAmostras({
        dados: payload.dados, variavel_dependente: dep.nome,
        variaveis_independentes: indeps.map((c) => c.nome),
        transformacoes: resultado.melhor_modelo.transformacoes, imovel_alvo: montarImovelAlvo(grid),
      })
      const ativos = grid.linhas.map((l, i) => ({ l, i })).filter((x) => !x.l.excluida)
      const reais = an.recomendar_desabilitar.map((idx) => ativos[idx]?.i).filter((x): x is number => x != null)
      if (!reais.length) { flash('Nenhuma amostra atípica detectada ✓'); return }
      setGrid(desabilitarIndices(grid, reais)); setPasso(1)
      flash(`${reais.length} amostra(s) atípica(s) desabilitada(s). Calcule novamente.`)
    } catch (e) { setErro(e instanceof Error ? e.message : 'Erro na análise') }
    finally { setLoading(false) }
  }, [resultado, grid, transfTestar, nivelConfianca])

  const handleExport = useCallback(async (tipo: 'word' | 'pdf') => {
    if (!resultado) return
    try {
      const dep = grid.colunas.find((c) => c.papel === 'dependente')!
      const payload = bestfitParaExport(resultado, dep.nome, avaliacao, valorArbitrado)
      const r = await (tipo === 'word' ? exportarWord : exportarPDF)(payload, exportConfig)
      await baixarArquivo(r.url_download, r.arquivo); flash(`Laudo ${tipo.toUpperCase()} baixado`)
    } catch (e) { setErro(e instanceof Error ? e.message : 'Erro ao exportar') }
  }, [resultado, grid, exportConfig, avaliacao, valorArbitrado])

  const novo = () => { setGrid(gridVazio()); setResultado(null); setAvaliacao(null); setNomeProjeto('Nova avaliação'); setPasso(1); flash('Novo projeto') }
  const salvar = () => { localStorage.setItem(STORAGE_KEY, JSON.stringify({ nomeProjeto, grid, transfTestar, nivelConfianca })); flash('Projeto salvo') }
  const abrirJSON = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; if (!f) return
    const r = new FileReader()
    r.onload = () => {
      try {
        const p: Persistido = JSON.parse(String(r.result))
        if (p.grid) setGrid(p.grid); if (p.nomeProjeto) setNomeProjeto(p.nomeProjeto)
        if (p.transfTestar) setTransfTestar(p.transfTestar); if (p.nivelConfianca) setNivelConfianca(p.nivelConfianca)
        setResultado(null); setAvaliacao(null); setPasso(1); flash('Projeto carregado')
      } catch { setErro('Arquivo inválido') }
    }
    r.readAsText(f); e.target.value = ''
  }

  const toggleTransf = (t: string) => setTransfTestar((p) => (p.includes(t) ? p.filter((x) => x !== t) : [...p, t]))
  const m = resultado?.melhor_modelo
  const nAtivas = grid.linhas.filter((l) => !l.excluida).length
  const nIndeps = grid.colunas.filter((c) => c.papel === 'independente').length

  const podeAvancar = passo < 4
  const podeVoltar = passo > 1

  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_30%_20%,#6b8eb5,#3f5d80)] py-6 px-3 flex flex-col items-center">
      <div className="win-window w-full max-w-[1000px]">
        {/* Título */}
        <div className="win-titlebar">
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 bg-white/90 rounded-sm text-[#0a4fd6] text-[10px] font-black flex items-center justify-center">A</span>
            Avaliador — {nomeProjeto || 'sem título'} · NBR 14653-02
          </div>
          <Link to="/" title="Voltar ao site" className="w-5 h-5 flex items-center justify-center bg-[#d24] hover:bg-[#e35] rounded-[3px] text-white text-xs leading-none">×</Link>
        </div>

        {/* Barra de ações simples */}
        <div className="win-menubar gap-2">
          <button onClick={novo} className="win-btn flex items-center gap-1"><FilePlus size={13} /> Novo</button>
          <button onClick={() => fileJSON.current?.click()} className="win-btn flex items-center gap-1"><FolderOpen size={13} /> Abrir</button>
          <button onClick={salvar} className="win-btn flex items-center gap-1"><Save size={13} /> Salvar</button>
          <input value={nomeProjeto} onChange={(e) => setNomeProjeto(e.target.value)} className="win-field flex-1 max-w-[240px] ml-2" placeholder="Nome do projeto" />
          <span className="ml-auto text-[#666] text-[11px]">{salvoEm ? `salvo ${salvoEm}` : ''}</span>
        </div>

        {/* Indicador de passos */}
        <div className="flex items-stretch bg-[#dfe7f2] border-b border-[#9bb0cd]">
          {PASSOS.map((nome, i) => {
            const n = i + 1
            const ativo = n === passo
            const feito = n < passo
            return (
              <button key={nome} onClick={() => (n <= passo || (n === 4 && resultado)) && setPasso(n)}
                className={`flex-1 px-2 py-2 text-[12px] flex items-center justify-center gap-1.5 border-r border-[#c2d0e4] last:border-r-0
                  ${ativo ? 'bg-[#0a4fd6] text-white font-semibold' : feito ? 'bg-white text-[#0a3fb0]' : 'text-[#7385a3]'}`}>
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold
                  ${ativo ? 'bg-white text-[#0a4fd6]' : feito ? 'bg-[#0a4fd6] text-white' : 'bg-[#c2d0e4] text-white'}`}>{n}</span>
                {nome}
              </button>
            )
          })}
        </div>

        {/* Mensagens */}
        {(erro || msg) && (
          <div className={`px-3 py-1.5 text-[12px] ${erro ? 'bg-[#ffe9e9] text-[#a22] border-b border-[#d88]' : 'bg-[#e7f6e7] text-[#262] border-b border-[#9c9]'}`}>
            {erro ? `⚠ ${erro}` : `✓ ${msg}`}
          </div>
        )}

        {/* Conteúdo do passo */}
        <div className="p-4 bg-[#ece9d8] min-h-[360px]">
          {passo === 1 && (
            <div className="space-y-2">
              <h2 className="text-[14px] font-bold text-[#0a3fb0]">Passo 1 — Informe as amostras</h2>
              <p className="text-[12px] text-[#555]">Cada linha é um imóvel comparável. Importe um <b>CSV</b> ou digite os dados. Marque o papel de cada coluna no cabeçalho (Valor Y / Variável X).</p>
              <DataGrid grid={grid} setGrid={setGrid} onImportCSV={handleImportCSV} onAppendCSV={handleAppendCSV} />
            </div>
          )}

          {passo === 2 && (
            <div className="space-y-2">
              <h2 className="text-[14px] font-bold text-[#0a3fb0]">Passo 2 — Imóvel a avaliar</h2>
              <p className="text-[12px] text-[#555]">Informe as características do imóvel que você quer avaliar.</p>
              <PainelAvaliando grid={grid} setGrid={setGrid} />
            </div>
          )}

          {passo === 3 && (
            <div className="space-y-3">
              <h2 className="text-[14px] font-bold text-[#0a3fb0]">Passo 3 — Calcular</h2>
              <div className="win-panel p-3 text-[12px] text-[#444]">
                Vou ajustar a regressão com <b>{nAtivas}</b> amostras e <b>{nIndeps}</b> variável(is),
                testando automaticamente as transformações e escolhendo o melhor modelo (NBR 14653-02).
              </div>

              <button onClick={() => setAvancado(!avancado)} className="text-[12px] text-[#0a4fd6] underline">
                {avancado ? '▼ Ocultar opções avançadas' : '▸ Opções avançadas'}
              </button>
              {avancado && (
                <div className="win-panel p-3 space-y-2">
                  <div className="text-[11px] text-[#555]">Transformações a testar:</div>
                  <div className="flex flex-wrap gap-1">
                    {TRANSFORMACOES.map((t) => (
                      <button key={t.value} onClick={() => toggleTransf(t.value)}
                        className={`px-2 py-0.5 text-[11px] rounded-[2px] border ${transfTestar.includes(t.value) ? 'bg-[#0a4fd6] text-white border-[#0a3fb0]' : 'bg-white text-[#444] border-[#aca899]'}`}>
                        {t.label}
                      </button>
                    ))}
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-[12px]">Nível de confiança:</label>
                    <select value={nivelConfianca} onChange={(e) => setNivelConfianca(parseFloat(e.target.value))} className="win-field">
                      <option value={0.80}>80% (padrão NBR)</option><option value={0.90}>90%</option><option value={0.95}>95%</option>
                    </select>
                  </div>
                </div>
              )}

              <button onClick={() => handleCalcular()} disabled={loading} className="win-btn win-btn-primary flex items-center gap-2 text-[13px] px-5 py-2">
                <Calculator size={16} /> {loading ? 'Calculando…' : 'Calcular regressão'}
              </button>
            </div>
          )}

          {passo === 4 && resultado && m && (
            <div className="space-y-3">
              <h2 className="text-[14px] font-bold text-[#0a3fb0]">Passo 4 — Resultado</h2>

              {avaliacao ? (
                <div className="rounded-[4px] border-2 border-amber-400 bg-gradient-to-b from-amber-50 to-amber-100/60 p-4">
                  <div className="flex flex-wrap items-start gap-6">
                    <div>
                      <div className="text-[12px] text-amber-800 font-semibold">Valor estimado (modelo)</div>
                      <div className="text-[30px] font-bold text-[#0a3fb0] leading-tight">{brl(avaliacao.valor_estimado)}</div>
                    </div>
                    <div className="flex-1 min-w-[260px]">
                      <div className="text-[12px] text-amber-800 font-semibold">
                        Valor adotado pelo avaliador <span className="font-normal">(campo de arbítrio ±15%)</span>
                      </div>
                      <div className="text-[24px] font-bold text-emerald-700 leading-tight">
                        {brl(valorArbitrado ?? avaliacao.valor_estimado)}
                        {valorArbitrado != null && valorArbitrado !== avaliacao.valor_estimado && (
                          <span className="ml-2 text-[11px] font-medium text-emerald-800 bg-emerald-100 border border-emerald-300 rounded px-1.5 py-0.5 align-middle">
                            {(((valorArbitrado - avaliacao.valor_estimado) / avaliacao.valor_estimado) * 100).toFixed(1)}% vs. modelo
                          </span>
                        )}
                      </div>
                      <input
                        type="range"
                        min={Math.round(avaliacao.campo_arbitrio[0])}
                        max={Math.round(avaliacao.campo_arbitrio[1])}
                        step={100}
                        value={valorArbitrado ?? avaliacao.valor_estimado}
                        onChange={(e) => setValorArbitrado(Number(e.target.value))}
                        className="w-full accent-emerald-600 mt-1"
                      />
                      <div className="flex justify-between text-[10px] text-amber-800">
                        <span>{brl(avaliacao.campo_arbitrio[0])}</span>
                        <button onClick={() => setValorArbitrado(null)} className="underline hover:text-amber-950">voltar ao valor do modelo</button>
                        <span>{brl(avaliacao.campo_arbitrio[1])}</span>
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 text-[12px]">
                    <Mini label={`Predição ${(avaliacao.nivel_confianca * 100).toFixed(0)}%`} value={`${brl(avaliacao.intervalo_predicao[0])} – ${brl(avaliacao.intervalo_predicao[1])}`} />
                    <Mini label="IC da média" value={`${brl(avaliacao.intervalo_confianca_media[0])} – ${brl(avaliacao.intervalo_confianca_media[1])}`} />
                    <Mini label="Amplitude" value={`${avaliacao.amplitude_pct}%`} />
                    <Mini label="Grau precisão" value={avaliacao.grau_precisao} />
                  </div>
                </div>
              ) : (
                <div className="win-panel p-3 text-[12px] text-[#777]">
                  Modelo calculado. Para estimar o valor, preencha o imóvel no Passo 2 e calcule de novo.
                </div>
              )}

              <div className="win-panel p-2 flex flex-wrap items-center gap-3 text-[12px]">
                <span>R²: <b>{m.r2.toFixed(4)}</b></span>
                <span>R² aj.: <b>{m.r2_ajustado.toFixed(4)}</b></span>
                <span>Fundamentação: <b>{resultado.grau_fundamentacao.grau}</b></span>
                <button onClick={handleDesabilitar} disabled={loading} className="win-btn ml-auto flex items-center gap-1">
                  <RotateCcw size={13} /> Desabilitar atípicas
                </button>
              </div>

              {resultado.avisos && resultado.avisos.length > 0 && (
                <div className="win-panel p-3 border-l-4 border-l-amber-500">
                  <div className="text-[12px] font-semibold text-[#8a6d00] mb-1">⚠ Avisos da norma</div>
                  <ul className="text-[12px] text-[#6b5500] list-disc pl-4 space-y-0.5">
                    {resultado.avisos.map((a, i) => <li key={i}>{a}</li>)}
                  </ul>
                </div>
              )}

              <ResultsPanel resultado={resultado} onUsarModelo={(t) => handleCalcular(t)} loading={loading} />
              <TabelaResultados resultado={resultado} grid={grid} />
              <Charts resultado={resultado} dados={[]} varDependente="" />

              <div className="win-panel p-3">
                <div className="text-[12px] font-semibold text-[#0a3fb0] mb-2">Gerar laudo</div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-2">
                  <input className="win-field" placeholder="Endereço" value={exportConfig.endereco} onChange={(e) => setExportConfig({ ...exportConfig, endereco: e.target.value })} />
                  <input className="win-field" placeholder="Avaliador" value={exportConfig.avaliador_nome} onChange={(e) => setExportConfig({ ...exportConfig, avaliador_nome: e.target.value })} />
                  <input className="win-field" placeholder="CREA" value={exportConfig.avaliador_crea} onChange={(e) => setExportConfig({ ...exportConfig, avaliador_crea: e.target.value })} />
                </div>
                <div className="flex gap-2">
                  <button onClick={() => handleExport('word')} className="win-btn">📄 Baixar Word</button>
                  <button onClick={() => handleExport('pdf')} className="win-btn">📕 Baixar PDF</button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Navegação */}
        <div className="flex items-center justify-between px-4 py-2 bg-[#e3e0d0] border-t border-[#aca899]">
          <button onClick={() => setPasso((p) => Math.max(1, p - 1))} disabled={!podeVoltar}
            className="win-btn flex items-center gap-1 disabled:opacity-40"><ChevronLeft size={14} /> Voltar</button>
          <span className="text-[11px] text-[#666]">Passo {passo} de 4 — {PASSOS[passo - 1]}</span>
          {passo < 3 && (
            <button onClick={() => setPasso((p) => Math.min(4, p + 1))} disabled={!podeAvancar}
              className="win-btn win-btn-primary flex items-center gap-1">Avançar <ChevronRight size={14} /></button>
          )}
          {passo === 3 && (
            <button onClick={() => handleCalcular()} disabled={loading}
              className="win-btn win-btn-primary flex items-center gap-1">{loading ? 'Calculando…' : 'Calcular ▶'}</button>
          )}
          {passo === 4 && (
            <button onClick={novo} className="win-btn flex items-center gap-1"><FilePlus size={13} /> Nova avaliação</button>
          )}
        </div>
      </div>

      <input ref={fileJSON} type="file" accept=".json" className="hidden" onChange={abrirJSON} />
      <p className="text-white/70 text-[11px] mt-3">Avaliador · projeto salvo automaticamente neste navegador</p>
    </div>
  )
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-[#d8d4c4] rounded-[3px] px-2 py-1">
      <div className="text-[10px] text-[#888]">{label}</div>
      <div className="text-[#333] font-medium">{value}</div>
    </div>
  )
}
