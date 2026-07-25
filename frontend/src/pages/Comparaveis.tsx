import { useState } from 'react'
import {
  Search, Plus, Trash2, Link2, Loader2, ArrowRight, Target,
  MapPin, ClipboardPaste, Send,
} from 'lucide-react'
import {
  ranquearComparaveis,
  type PerfilImovel, type PerfilTerritorial, type CandidatoComparavel,
  type ComparaveisResponse,
} from '../api'

const TIPOS = ['casa', 'apartamento', 'terreno', 'comercial', 'galpao', 'rural']
const PADROES = ['baixo', 'normal', 'medio', 'alto', 'luxo']
const CONSERVACAO = ['ruim', 'regular', 'bom', 'otimo', 'novo']
const FINALIDADES = ['residencial', 'comercial', 'industrial', 'rural']

const brl = (n?: number | null) =>
  n == null || !Number.isFinite(n) ? '—' : n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })

const ROTULOS: Record<string, string> = {
  tipo_imovel: 'Tipologia', area_terreno: 'Área do terreno', area_construida: 'Área construída',
  padrao_construtivo: 'Padrão construtivo', conservacao: 'Conservação', idade: 'Idade',
  programa: 'Programa (dorm./banh./vagas)', zoneamento: 'Zoneamento',
  similaridade_territorial: 'Perfil territorial', distancia: 'Distância',
}

function classeCor(classe: string) {
  if (classe === 'Excelente') return 'bg-emerald-100 text-emerald-800 border-emerald-300'
  if (classe === 'Boa') return 'bg-blue-100 text-blue-800 border-blue-300'
  if (classe === 'Aceitável') return 'bg-amber-100 text-amber-800 border-amber-300'
  return 'bg-red-100 text-red-800 border-red-300'
}

interface Props {
  /** Envia os comparáveis escolhidos para as Amostras do Avaliador */
  onEnviarParaAmostras?: (linhas: { valor: number; area_terreno: number; area_construida: number }[]) => void
}

export default function Comparaveis({ onEnviarParaAmostras }: Props) {
  const [alvo, setAlvo] = useState<PerfilImovel>({ tipo_imovel: 'casa', finalidade: 'residencial' })
  const [territorio, setTerritorio] = useState<PerfilTerritorial>({})
  const [candidatos, setCandidatos] = useState<CandidatoComparavel[]>([{}])
  const [minSim, setMinSim] = useState(65)
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [res, setRes] = useState<ComparaveisResponse | null>(null)
  const [expandido, setExpandido] = useState<number | null>(null)
  const [selecionados, setSelecionados] = useState<Set<number>>(new Set())
  const [colarAberto, setColarAberto] = useState(false)
  const [textoColado, setTextoColado] = useState('')

  const setA = (k: keyof PerfilImovel, v: string) =>
    setAlvo({ ...alvo, [k]: v === '' ? null : (isNaN(Number(v)) ? v : Number(v)) })
  const setT = (k: keyof PerfilTerritorial, v: string) =>
    setTerritorio({ ...territorio, [k]: v === '' ? null : Number(v) })
  const setC = (i: number, k: string, v: string) => {
    const lista = [...candidatos]
    lista[i] = { ...lista[i], [k]: v === '' ? null : (isNaN(Number(v)) ? v : Number(v)) }
    setCandidatos(lista)
  }

  const buscar = async () => {
    setErro(null)
    const validos = candidatos.filter((c) => c.tipo_imovel || c.area_terreno || c.area_construida || c.identificacao)
    if (!validos.length) { setErro('Informe ao menos um imóvel candidato.'); return }
    setLoading(true)
    try {
      const r = await ranquearComparaveis({
        alvo,
        candidatos: validos.map((c) => ({ ...c, perfil_territorial: c.perfil_territorial ?? territorio })),
        perfil_territorial_alvo: Object.keys(territorio).length ? territorio : null,
        minimo_similaridade: minSim,
      })
      setRes(r); setSelecionados(new Set(r.comparaveis.map((c) => c.indice)))
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao ranquear')
    } finally { setLoading(false) }
  }

  /** Cola linhas "identificação; preço; área terreno; área construída; fonte" */
  const processarColagem = () => {
    const linhas = textoColado.split('\n').map((l) => l.trim()).filter(Boolean)
    const novos: CandidatoComparavel[] = linhas.map((l) => {
      const p = l.split(/[;\t]/).map((x) => x.trim())
      return {
        identificacao: p[0] || null,
        preco: p[1] ? Number(p[1].replace(/[^\d.,]/g, '').replace(',', '.')) : null,
        area_terreno: p[2] ? Number(p[2].replace(',', '.')) : null,
        area_construida: p[3] ? Number(p[3].replace(',', '.')) : null,
        fonte: p[4] || null,
        tipo_imovel: alvo.tipo_imovel,
      }
    })
    setCandidatos([...candidatos.filter((c) => Object.keys(c).length > 0), ...novos])
    setColarAberto(false); setTextoColado('')
  }

  const enviarAmostras = () => {
    if (!res || !onEnviarParaAmostras) return
    const linhas = res.comparaveis
      .filter((c) => selecionados.has(c.indice) && c.preco)
      .map((c) => ({
        valor: c.preco as number,
        area_terreno: c.area_terreno ?? 0,
        area_construida: c.area_construida ?? 0,
      }))
    if (!linhas.length) { setErro('Os comparáveis selecionados precisam ter preço informado.'); return }
    onEnviarParaAmostras(linhas)
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <Search size={24} /> Comparáveis
        </h1>
        <p className="text-sm text-slate-500">
          Curadoria de comps por similaridade multicritério. <b>Não estima valor</b> — encontra e
          ranqueia referências confiáveis para alimentar a avaliação.
        </p>
      </div>

      {/* 01 — Perfil do imóvel */}
      <Secao numero="01" titulo="Perfil técnico do imóvel de referência" icone={<Target size={16} />}>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Select label="Tipo do imóvel" v={alvo.tipo_imovel ?? ''} opts={TIPOS} on={(x) => setA('tipo_imovel', x)} />
          <Select label="Finalidade" v={alvo.finalidade ?? ''} opts={FINALIDADES} on={(x) => setA('finalidade', x)} />
          <Campo label="Zoneamento" v={alvo.zoneamento ?? ''} on={(x) => setA('zoneamento', x)} ph="ZR-1" texto />
          <Campo label="Área terreno (m²)" v={alvo.area_terreno ?? ''} on={(x) => setA('area_terreno', x)} ph="360" />
          <Campo label="Área construída (m²)" v={alvo.area_construida ?? ''} on={(x) => setA('area_construida', x)} ph="220" />
          <Campo label="Idade (anos)" v={alvo.idade ?? ''} on={(x) => setA('idade', x)} ph="10" />
          <Select label="Padrão construtivo" v={alvo.padrao_construtivo ?? ''} opts={PADROES} on={(x) => setA('padrao_construtivo', x)} />
          <Select label="Conservação" v={alvo.conservacao ?? ''} opts={CONSERVACAO} on={(x) => setA('conservacao', x)} />
          <Campo label="Dorm." v={alvo.dormitorios ?? ''} on={(x) => setA('dormitorios', x)} />
          <Campo label="Banh." v={alvo.banheiros ?? ''} on={(x) => setA('banheiros', x)} />
          <Campo label="Vagas" v={alvo.vagas ?? ''} on={(x) => setA('vagas', x)} />
          <Campo label="Bairro" v={alvo.bairro ?? ''} on={(x) => setA('bairro', x)} ph="Centro" texto />
          <Campo label="Cidade" v={alvo.cidade ?? ''} on={(x) => setA('cidade', x)} texto />
          <Campo label="UF" v={alvo.uf ?? ''} on={(x) => setA('uf', x)} texto />
        </div>
      </Secao>

      {/* 02 — Contexto territorial */}
      <Secao numero="02" titulo="Contexto territorial da região" icone={<MapPin size={16} />}>
        <p className="text-[11px] text-slate-500 mb-2">
          Indicadores públicos (IBGE, IDHM, dados municipais). Permitem comparar bairros
          <b> equivalentes mesmo em outra cidade</b> — não só vizinhos. Campos vazios são ignorados.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Campo label="IDH" v={territorio.idh ?? ''} on={(x) => setT('idh', x)} ph="0.82" />
          <Campo label="Renda per capita" v={territorio.renda_per_capita ?? ''} on={(x) => setT('renda_per_capita', x)} ph="4500" />
          <Campo label="Densidade (hab/km²)" v={territorio.densidade_populacional ?? ''} on={(x) => setT('densidade_populacional', x)} ph="4000" />
          <Campo label="Escolaridade (anos)" v={territorio.escolaridade_media_anos ?? ''} on={(x) => setT('escolaridade_media_anos', x)} ph="11" />
          <Campo label="Segurança (0-10)" v={territorio.indice_seguranca ?? ''} on={(x) => setT('indice_seguranca', x)} ph="7" />
          <Campo label="Infraestrutura (0-10)" v={territorio.infraestrutura ?? ''} on={(x) => setT('infraestrutura', x)} ph="8" />
          <Campo label="Dist. centro (km)" v={territorio.distancia_centro_km ?? ''} on={(x) => setT('distancia_centro_km', x)} ph="3" />
        </div>
      </Secao>

      {/* 03 — Candidatos */}
      <Secao numero="03" titulo="Imóveis candidatos" icone={<Link2 size={16} />}>
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <button onClick={() => setCandidatos([...candidatos, {}])}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 hover:bg-slate-50 flex items-center gap-1">
            <Plus size={13} /> Candidato
          </button>
          <button onClick={() => setColarAberto(!colarAberto)}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 hover:bg-slate-50 flex items-center gap-1">
            <ClipboardPaste size={13} /> Colar lista
          </button>
          <div className="ml-auto flex items-center gap-2 text-xs text-slate-600">
            Similaridade mínima:
            <input type="number" value={minSim} onChange={(e) => setMinSim(Number(e.target.value))}
              className="w-16 px-2 py-1 border border-slate-300 rounded" />%
          </div>
        </div>

        {colarAberto && (
          <div className="mb-3 p-3 rounded-lg bg-blue-50 border border-blue-200">
            <p className="text-[11px] text-blue-800 mb-1">
              Uma linha por imóvel, separando com <b>;</b> — identificação; preço; área terreno; área construída; fonte (link)
            </p>
            <textarea value={textoColado} onChange={(e) => setTextoColado(e.target.value)} rows={4}
              placeholder="Casa Rua A, 120; 650000; 360; 200; https://portal.com/1"
              className="w-full px-2 py-1.5 text-xs border border-slate-300 rounded font-mono" />
            <div className="flex gap-2 mt-2">
              <button onClick={processarColagem} className="px-3 py-1.5 rounded bg-blue-600 text-white text-xs">Adicionar</button>
              <button onClick={() => setColarAberto(false)} className="px-3 py-1.5 rounded text-slate-500 text-xs">Cancelar</button>
            </div>
          </div>
        )}

        <div className="overflow-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-100 text-slate-600 text-left">
                <th className="px-2 py-1.5">Identificação</th>
                <th className="px-2 py-1.5">Preço</th>
                <th className="px-2 py-1.5">Á. terreno</th>
                <th className="px-2 py-1.5">Á. constr.</th>
                <th className="px-2 py-1.5">Dist. (km)</th>
                <th className="px-2 py-1.5">Fonte (link)</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {candidatos.map((c, i) => (
                <tr key={i} className="border-b border-slate-100">
                  <td className="px-1 py-1"><Cel v={c.identificacao ?? ''} on={(x) => setC(i, 'identificacao', x)} texto /></td>
                  <td className="px-1 py-1"><Cel v={c.preco ?? ''} on={(x) => setC(i, 'preco', x)} /></td>
                  <td className="px-1 py-1"><Cel v={c.area_terreno ?? ''} on={(x) => setC(i, 'area_terreno', x)} /></td>
                  <td className="px-1 py-1"><Cel v={c.area_construida ?? ''} on={(x) => setC(i, 'area_construida', x)} /></td>
                  <td className="px-1 py-1"><Cel v={c.distancia_km ?? ''} on={(x) => setC(i, 'distancia_km', x)} /></td>
                  <td className="px-1 py-1"><Cel v={c.fonte ?? ''} on={(x) => setC(i, 'fonte', x)} texto /></td>
                  <td className="px-1 py-1 text-center">
                    <button onClick={() => setCandidatos(candidatos.filter((_, j) => j !== i))}
                      className="text-slate-300 hover:text-red-500"><Trash2 size={13} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {erro && <div className="text-[12px] text-red-600 mt-2">{erro}</div>}
        <button onClick={buscar} disabled={loading}
          className="mt-3 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white text-sm flex items-center gap-2">
          {loading ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
          {loading ? 'Analisando…' : 'Ranquear comparáveis'}
        </button>
      </Secao>

      {/* Resultado */}
      {res && (
        <Secao numero="04" titulo="Comparáveis ranqueados" icone={<ArrowRight size={16} />}>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-3 text-[12px]">
            <Kpi label="Aceitos" v={`${res.resumo.total_aceitos}/${res.resumo.total_avaliados}`} />
            <Kpi label="Similaridade média" v={`${res.resumo.similaridade_media}%`} />
            <Kpi label="Excelentes" v={String(res.resumo.excelentes)} />
            <Kpi label="Boas" v={String(res.resumo.boas)} />
            <Kpi label="Aceitáveis" v={String(res.resumo.aceitaveis)} />
          </div>
          <p className="text-[11px] text-slate-500 mb-3">{res.resumo.orientacao}</p>

          <div className="space-y-2">
            {res.comparaveis.map((c) => (
              <div key={c.indice} className="border border-slate-200 rounded-lg overflow-hidden">
                <div className="flex flex-wrap items-center gap-2 p-2.5 bg-white">
                  <input type="checkbox" checked={selecionados.has(c.indice)}
                    onChange={() => {
                      const s = new Set(selecionados)
                      s.has(c.indice) ? s.delete(c.indice) : s.add(c.indice)
                      setSelecionados(s)
                    }} className="accent-blue-600" />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-slate-800 truncate">{c.identificacao}</div>
                    <div className="text-[11px] text-slate-500">
                      {brl(c.preco)} · {c.area_terreno ?? '—'} m² terreno · {c.area_construida ?? '—'} m² constr.
                      {c.fonte && <> · <a href={c.fonte} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">fonte</a></>}
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${classeCor(c.classe)}`}>
                    {c.similaridade_pct}% · {c.classe}
                  </span>
                  <button onClick={() => setExpandido(expandido === c.indice ? null : c.indice)}
                    className="text-[11px] text-blue-600 hover:underline">
                    {expandido === c.indice ? 'ocultar' : 'por quê?'}
                  </button>
                </div>
                {expandido === c.indice && (
                  <div className="p-3 bg-slate-50 border-t border-slate-200">
                    <div className="text-[11px] font-semibold text-slate-600 mb-1">Por que é comparável</div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
                      {Object.entries(c.detalhamento).map(([k, d]) => (
                        <div key={k} className="flex items-center gap-2 text-[11px]">
                          <span className="w-44 text-slate-500 shrink-0">{ROTULOS[k] ?? k}</span>
                          <div className="flex-1 h-1.5 bg-slate-200 rounded overflow-hidden">
                            <div className="h-full bg-blue-500" style={{ width: `${d.similaridade_pct}%` }} />
                          </div>
                          <span className="w-10 text-right font-medium text-slate-700">{d.similaridade_pct}%</span>
                        </div>
                      ))}
                    </div>
                    {c.criterios_ignorados.length > 0 && (
                      <p className="text-[10px] text-slate-400 mt-2">
                        Sem dados (peso redistribuído): {c.criterios_ignorados.map((k) => ROTULOS[k] ?? k).join(', ')}.
                        Cobertura dos critérios: {c.cobertura_pct}%.
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {onEnviarParaAmostras && (
            <button onClick={enviarAmostras}
              className="mt-4 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium flex items-center gap-2">
              <Send size={15} /> Enviar {selecionados.size} selecionado(s) para as Amostras
            </button>
          )}
        </Secao>
      )}
    </div>
  )
}

/* ---------- UI helpers ---------- */

function Secao({ numero, titulo, icone, children }: { numero: string; titulo: string; icone: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="w-7 h-7 rounded-lg bg-slate-800 text-white text-[11px] font-bold flex items-center justify-center">{numero}</span>
        <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5">{icone} {titulo}</h2>
      </div>
      {children}
    </div>
  )
}

function Campo({ label, v, on, ph, texto }: { label: string; v: string | number; on: (x: string) => void; ph?: string; texto?: boolean }) {
  return (
    <div>
      <label className="block text-[11px] text-slate-500 mb-0.5">{label}</label>
      <input type={texto ? 'text' : 'number'} value={v} placeholder={ph} onChange={(e) => on(e.target.value)}
        className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:border-blue-500" />
    </div>
  )
}

function Select({ label, v, opts, on }: { label: string; v: string; opts: string[]; on: (x: string) => void }) {
  return (
    <div>
      <label className="block text-[11px] text-slate-500 mb-0.5">{label}</label>
      <select value={v} onChange={(e) => on(e.target.value)}
        className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded-lg bg-white focus:outline-none focus:border-blue-500">
        <option value="">—</option>
        {opts.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  )
}

function Cel({ v, on, texto }: { v: string | number; on: (x: string) => void; texto?: boolean }) {
  return (
    <input type={texto ? 'text' : 'number'} value={v} onChange={(e) => on(e.target.value)}
      className="w-full px-2 py-1 text-xs border border-transparent hover:border-slate-200 focus:border-blue-400 rounded focus:outline-none" />
  )
}

function Kpi({ label, v }: { label: string; v: string }) {
  return (
    <div className="bg-slate-50 rounded-lg px-3 py-2">
      <div className="text-[10px] text-slate-500">{label}</div>
      <div className="font-semibold text-slate-800">{v}</div>
    </div>
  )
}
