import { useState } from 'react'
import {
  Search, Plus, Trash2, Loader2, MapPin, Home as HomeIcon, ClipboardPaste,
  Send, Users, TrendingUp, GraduationCap, Gauge, CheckCircle2, AlertTriangle, Layers,
  Bot, FileJson, Copy, Check, Download, ShieldCheck,
} from 'lucide-react'
import {
  buscarLocalizacao, buscarComparables, buscarEmFontes, gerarEstrategia, filtrarRetornoAgente,
  type PerfilLocalizacao, type AnuncioCandidato, type ComparablesResponse,
  type EstrategiaBusca, type FiltroAgenteResponse,
} from '../api'

const TIPOS = ['casa', 'apartamento', 'terreno', 'comercial']
const PADROES = ['baixo', 'normal', 'medio', 'alto', 'luxo']

const brl = (n?: number | null) =>
  n == null || !Number.isFinite(n) ? '—' : n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
const numf = (n?: number | null, d = 0) =>
  n == null || !Number.isFinite(n) ? '—' : n.toLocaleString('pt-BR', { maximumFractionDigits: d })

function classeIDH(idh?: number | null) {
  if (idh == null) return { rotulo: '—', cor: 'bg-slate-100 text-slate-600' }
  if (idh >= 0.8) return { rotulo: 'Muito alto', cor: 'bg-emerald-100 text-emerald-700' }
  if (idh >= 0.7) return { rotulo: 'Alto', cor: 'bg-blue-100 text-blue-700' }
  if (idh >= 0.6) return { rotulo: 'Médio', cor: 'bg-amber-100 text-amber-700' }
  return { rotulo: 'Baixo', cor: 'bg-red-100 text-red-700' }
}

interface Props {
  onEnviarParaAmostras?: (linhas: { valor: number; area: number; area_terreno: number }[]) => void
}

export default function Comparaveis({ onEnviarParaAmostras }: Props) {
  // 01 — imóvel
  const [cep, setCep] = useState('')
  const [numero, setNumero] = useState('')
  const [imovel, setImovel] = useState<Record<string, string>>({ tipo: 'casa' })
  // 02 — localização
  const [loc, setLoc] = useState<PerfilLocalizacao | null>(null)
  const [buscandoLoc, setBuscandoLoc] = useState(false)
  // 03 — candidatos
  const [candidatos, setCandidatos] = useState<AnuncioCandidato[]>([{}])
  const [colarAberto, setColarAberto] = useState(false)
  const [textoColado, setTextoColado] = useState('')
  // 04 — resultado
  const [res, setRes] = useState<ComparablesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [selec, setSelec] = useState<Set<number>>(new Set())
  const [detalhe, setDetalhe] = useState<number | null>(null)

  const setI = (k: string, v: string) => setImovel({ ...imovel, [k]: v })
  const setC = (i: number, k: string, v: string) => {
    const l = [...candidatos]
    l[i] = { ...l[i], [k]: v === '' ? null : (isNaN(Number(v)) ? v : Number(v)) }
    setCandidatos(l)
  }

  const buscarLoc = async () => {
    setErro(null); setBuscandoLoc(true)
    try {
      const r = await buscarLocalizacao({ cep, numero, bairro: imovel.bairro || undefined })
      setLoc(r)
      if (r.localizacao.bairro && !imovel.bairro) setImovel({ ...imovel, bairro: r.localizacao.bairro })
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao buscar localização')
    } finally { setBuscandoLoc(false) }
  }

  const [buscandoFontes, setBuscandoFontes] = useState(false)
  const [infoFontes, setInfoFontes] = useState<string | null>(null)

  // --- Ponte com agente de IA (CrewAI) ---
  const [estrategia, setEstrategia] = useState<EstrategiaBusca | null>(null)
  const [gerandoEst, setGerandoEst] = useState(false)
  const [copiado, setCopiado] = useState(false)
  const [retornoAgente, setRetornoAgente] = useState('')
  const [filtro, setFiltro] = useState<FiltroAgenteResponse | null>(null)
  const [filtrando, setFiltrando] = useState(false)

  /** Monta a ficha técnica a partir do formulário + localização. */
  const montarFicha = () => ({
    tipo: imovel.tipo || null,
    area_construida: imovel.area_construida ? Number(imovel.area_construida) : null,
    area_terreno: imovel.area_terreno ? Number(imovel.area_terreno) : null,
    quartos: imovel.quartos ? Number(imovel.quartos) : null,
    banheiros: imovel.banheiros ? Number(imovel.banheiros) : null,
    vagas: imovel.vagas ? Number(imovel.vagas) : null,
    padrao_construtivo: imovel.padrao_construtivo || null,
    zoneamento: imovel.zoneamento || null,
    endereco: loc?.localizacao.logradouro || null,
    numero: numero || null,
    bairro: imovel.bairro || loc?.localizacao.bairro || null,
    cidade: loc?.localizacao.cidade || null,
    uf: loc?.localizacao.uf || null,
    cep: loc?.localizacao.cep || cep || null,
  })

  /** Pacote JSON entregue ao pesquisador (ficha + estratégia + região). */
  const pacotePesquisa = () => ({
    ficha_tecnica: montarFicha(),
    estrategia_busca: estrategia,
    dados_regiao: loc?.indicadores ?? null,
    instrucoes: {
      formato_esperado: 'JSON com lista "elementos"',
      campos_por_imovel: ['endereco', 'preco', 'area_construida', 'area_terreno',
                          'quartos', 'banheiros', 'vagas', 'bairro', 'cidade', 'url'],
      regra: 'Todo imóvel precisa de URL de origem. Não estimar valor nem grau de fundamentação.',
    },
  })

  const gerarPacote = async () => {
    setErro(null); setGerandoEst(true)
    try {
      const e = await gerarEstrategia({ ficha: montarFicha(), meta_minima: 15 })
      setEstrategia(e)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao gerar estratégia')
    } finally { setGerandoEst(false) }
  }

  const copiarPacote = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(pacotePesquisa(), null, 2))
      setCopiado(true); setTimeout(() => setCopiado(false), 2000)
    } catch { setErro('Não foi possível copiar. Selecione o texto manualmente.') }
  }

  const baixarPacote = () => {
    const blob = new Blob([JSON.stringify(pacotePesquisa(), null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'ficha_pesquisa.json'; a.click()
    URL.revokeObjectURL(url)
  }

  /** Passa o retorno do agente pelo filtro e joga o que sobrou na tabela. */
  const processarRetorno = async () => {
    if (!retornoAgente.trim()) { setErro('Cole o retorno do pesquisador.'); return }
    setErro(null); setFiltrando(true)
    try {
      const r = await filtrarRetornoAgente(retornoAgente)
      setFiltro(r)
      if (r.candidatos.length) {
        setCandidatos([...candidatos.filter((c) => Object.keys(c).length > 0),
                       ...(r.candidatos as AnuncioCandidato[])])
      }
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao processar retorno')
    } finally { setFiltrando(false) }
  }

  /** Busca automática em fontes públicas (dados abertos — sem scraping). */
  const buscarAutomatico = async () => {
    if (!loc?.localizacao.uf || !loc?.localizacao.cidade) {
      setErro('Busque o CEP primeiro para identificar a cidade.')
      return
    }
    setErro(null); setBuscandoFontes(true); setInfoFontes(null)
    try {
      const r = await buscarEmFontes({
        uf: loc.localizacao.uf,
        cidade: loc.localizacao.cidade,
        bairro: imovel.bairro || '',
        limite: 200,
      })
      if (!r.total) {
        // tenta de novo sem o filtro de bairro
        const r2 = await buscarEmFontes({ uf: loc.localizacao.uf, cidade: loc.localizacao.cidade, limite: 200 })
        if (!r2.total) { setInfoFontes('Nenhum imóvel encontrado nas fontes públicas para esta cidade.'); return }
        setCandidatos([...(candidatos.filter((c) => Object.keys(c).length > 0)), ...(r2.candidatos as AnuncioCandidato[])])
        setInfoFontes(`${r2.total} imóveis encontrados na cidade (sem filtro de bairro).`)
      } else {
        setCandidatos([...(candidatos.filter((c) => Object.keys(c).length > 0)), ...(r.candidatos as AnuncioCandidato[])])
        setInfoFontes(`${r.total} imóveis encontrados: ${Object.entries(r.por_fonte).map(([k, v]) => `${k} (${v})`).join(', ')}.`)
      }
      if (r.erros?.length) setErro(`Algumas fontes falharam: ${r.erros.map((e) => e.fonte).join(', ')}`)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao buscar nas fontes')
    } finally { setBuscandoFontes(false) }
  }

  const processarColagem = () => {
    const linhas = textoColado.split('\n').map((l) => l.trim()).filter(Boolean)
    const novos: AnuncioCandidato[] = linhas.map((l) => {
      const p = l.split(/[;\t]/).map((x) => x.trim())
      const n = (s?: string) => (s ? Number(s.replace(/[^\d.,-]/g, '').replace(',', '.')) : null)
      return {
        identificacao: p[0] || null, preco: n(p[1]), area_construida: n(p[2]),
        area_terreno: n(p[3]), fonte: p[4] || null,
        tipo: imovel.tipo, bairro: imovel.bairro || null, cidade: loc?.localizacao.cidade || null,
        indicadores: loc?.indicadores as Record<string, unknown> | undefined,
      }
    })
    setCandidatos([...candidatos.filter((c) => Object.keys(c).length > 0), ...novos])
    setColarAberto(false); setTextoColado('')
  }

  const buscar = async () => {
    setErro(null)
    const validos = candidatos.filter((c) => c.preco || c.area_construida || c.identificacao)
    if (!validos.length) { setErro('Adicione ao menos um imóvel candidato (ou cole uma lista).'); return }
    setLoading(true)
    try {
      const r = await buscarComparables({
        imovel: {
          tipo: imovel.tipo || null,
          area_construida: imovel.area_construida ? Number(imovel.area_construida) : null,
          area_terreno: imovel.area_terreno ? Number(imovel.area_terreno) : null,
          quartos: imovel.quartos ? Number(imovel.quartos) : null,
          banheiros: imovel.banheiros ? Number(imovel.banheiros) : null,
          vagas: imovel.vagas ? Number(imovel.vagas) : null,
          padrao_construtivo: imovel.padrao_construtivo || null,
          bairro: imovel.bairro || loc?.localizacao.bairro || null,
          cidade: loc?.localizacao.cidade || null,
          uf: loc?.localizacao.uf || null,
        },
        candidatos: validos.map((c) => ({
          ...c,
          indicadores: c.indicadores ?? (loc?.indicadores as Record<string, unknown> | undefined),
        })),
        indicadores_regiao: loc?.indicadores as Record<string, unknown> | undefined,
      })
      setRes(r)
      setSelec(new Set(r.amostras.map((_, i) => i)))
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro na busca')
    } finally { setLoading(false) }
  }

  const enviar = () => {
    if (!res || !onEnviarParaAmostras) return
    const linhas = res.amostras
      .filter((_, i) => selec.has(i))
      .map((a) => ({ valor: a.preco, area: a.area, area_terreno: a.area_terreno ?? 0 }))
    if (!linhas.length) { setErro('Selecione ao menos uma amostra.'); return }
    onEnviarParaAmostras(linhas)
  }

  const idh = classeIDH(loc?.indicadores.idh)

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <Search size={24} /> Comparáveis
        </h1>
        <p className="text-sm text-slate-500">
          Inteligência imobiliária: coleta os dados da região e monta a base de amostras.
          <b> Não estima valor</b> — entrega os comparáveis para a avaliação.
        </p>
      </div>

      {/* 01 — Imóvel */}
      <Secao n="01" titulo="Dados do imóvel" icone={<HomeIcon size={16} />}>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div>
            <label className="block text-[11px] text-slate-500 mb-0.5">CEP</label>
            <div className="flex gap-1">
              <input value={cep} onChange={(e) => setCep(e.target.value)} placeholder="79002-000"
                className="flex-1 px-2 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:border-blue-500" />
              <button onClick={buscarLoc} disabled={buscandoLoc || cep.replace(/\D/g, '').length !== 8}
                className="px-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white"
                title="Buscar endereço e indicadores">
                {buscandoLoc ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
              </button>
            </div>
          </div>
          <Campo label="Número" v={numero} on={setNumero} texto ph="1000" />
          <Select label="Tipo" v={imovel.tipo ?? ''} opts={TIPOS} on={(x) => setI('tipo', x)} />
          <Select label="Padrão construtivo" v={imovel.padrao_construtivo ?? ''} opts={PADROES} on={(x) => setI('padrao_construtivo', x)} />
          <Campo label="Área construída (m²)" v={imovel.area_construida ?? ''} on={(x) => setI('area_construida', x)} ph="150" />
          <Campo label="Área do terreno (m²)" v={imovel.area_terreno ?? ''} on={(x) => setI('area_terreno', x)} ph="360" />
          <Campo label="Quartos" v={imovel.quartos ?? ''} on={(x) => setI('quartos', x)} ph="3" />
          <Campo label="Banheiros" v={imovel.banheiros ?? ''} on={(x) => setI('banheiros', x)} ph="2" />
          <Campo label="Vagas" v={imovel.vagas ?? ''} on={(x) => setI('vagas', x)} ph="2" />
          <Campo label="Bairro" v={imovel.bairro ?? ''} on={(x) => setI('bairro', x)} texto ph="Centro" />
          <Campo label="Zoneamento" v={imovel.zoneamento ?? ''} on={(x) => setI('zoneamento', x)} texto ph="ZR-1" />
        </div>
        {loc && (
          <p className="text-[11px] text-slate-500 mt-2">
            📍 {loc.localizacao.logradouro}{numero && `, ${numero}`} — {loc.localizacao.bairro}, {loc.localizacao.cidade}/{loc.localizacao.uf}
            {loc.localizacao.ibge && <> · IBGE {loc.localizacao.ibge}</>}
          </p>
        )}
      </Secao>

      {/* 02 — Contexto territorial */}
      <Secao n="02" titulo="Contexto territorial" icone={<MapPin size={16} />}>
        {!loc ? (
          <p className="text-sm text-slate-400">Informe o CEP e clique na lupa para carregar o perfil territorial.</p>
        ) : (
          <>
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="text-lg font-bold text-slate-800">
                  {loc.indicadores.municipio || loc.localizacao.cidade} / {loc.localizacao.uf}
                </div>
                <div className="text-xs text-slate-500">Bairro: {loc.localizacao.bairro || '—'}</div>
              </div>
              <div className="flex flex-wrap gap-1 justify-end">
                {loc.fontes.map((f) => (
                  <span key={f} className="text-[10px] font-mono bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full border border-slate-200">{f}</span>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Ind icone={<Users size={14} />} label="População" v={loc.indicadores.populacao ? `${numf(loc.indicadores.populacao / 1000)} mil` : '—'} />
              <Ind icone={<TrendingUp size={14} />} label="PIB per capita" v={loc.indicadores.pib_per_capita ? `${brl(loc.indicadores.pib_per_capita)}/ano` : '—'}
                sub={loc.indicadores.renda_media ? `Renda proxy ${brl(loc.indicadores.renda_media)}/mês` : undefined} />
              <Ind icone={<GraduationCap size={14} />} label="IDH-M" v={loc.indicadores.idh != null ? loc.indicadores.idh.toFixed(3) : '—'}
                badge={idh.rotulo} badgeCor={idh.cor} />
              <Ind icone={<Gauge size={14} />} label="Densidade" v={loc.indicadores.densidade_populacional ? `${numf(loc.indicadores.densidade_populacional, 1)} hab/km²` : '—'}
                sub={loc.indicadores.area_km2 ? `${numf(loc.indicadores.area_km2)} km²` : undefined} />
            </div>
            {loc.infraestrutura?.ok && (
              <div className="mt-3 p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                <div className="text-[11px] text-slate-600 mb-1">
                  Infraestrutura num raio de {loc.infraestrutura.raio_m}m — índice <b>{loc.infraestrutura.indice_infraestrutura}/10</b>
                </div>
                <div className="flex flex-wrap gap-2 text-[11px]">
                  {Object.entries(loc.infraestrutura.contagens ?? {}).map(([k, v]) => (
                    <span key={k} className="bg-white border border-slate-200 rounded px-2 py-0.5">{k}: <b>{v}</b></span>
                  ))}
                </div>
              </div>
            )}
            {loc.avisos.length > 0 && (
              <ul className="mt-2 text-[11px] text-amber-700 list-disc pl-4">
                {loc.avisos.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            )}
            <p className="text-[11px] text-slate-400 mt-2">
              Indicadores de bases públicas (ViaCEP, IBGE, Atlas Brasil, OpenStreetMap). Usados como perfil
              socioeconômico para ranquear regiões similares na expansão da busca.
            </p>
          </>
        )}
      </Secao>

      {/* 03 — Pesquisador externo (CrewAI) */}
      <Secao n="03" titulo="Pesquisador externo (opcional)" icone={<Bot size={16} />}>
        <p className="text-[12px] text-slate-500 mb-3">
          Gere o pacote JSON da pesquisa, rode no seu agente de IA e cole o retorno aqui.
          Tudo que voltar passa por um filtro: imóvel sem link de origem, preço ou área implausível
          é descartado, e o preço por m² é recalculado. <b>Grau e métricas nunca vêm do agente</b> —
          são calculados pelo motor.
        </p>

        <div className="flex flex-wrap items-center gap-2 mb-3">
          <button onClick={gerarPacote} disabled={gerandoEst}
            className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-900 disabled:bg-slate-300 text-white flex items-center gap-1.5 font-medium">
            {gerandoEst ? <Loader2 size={13} className="animate-spin" /> : <FileJson size={13} />}
            {gerandoEst ? 'Gerando…' : '1. Gerar JSON da pesquisa'}
          </button>
          {estrategia && (
            <>
              <button onClick={copiarPacote} className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 hover:bg-slate-50 flex items-center gap-1">
                {copiado ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}
                {copiado ? 'Copiado!' : 'Copiar'}
              </button>
              <button onClick={baixarPacote} className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 hover:bg-slate-50 flex items-center gap-1">
                <Download size={13} /> Baixar .json
              </button>
            </>
          )}
        </div>

        {estrategia && (
          <div className="mb-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-2 text-[12px]">
              <Kpi label="Tipologia" v={estrategia.tipo_normalizado} />
              <Kpi label="Raio inicial" v={`${(estrategia.raio_inicial_metros / 1000).toFixed(1)} km`} />
              <Kpi label="Meta de amostras" v={`${estrategia.meta_minima_amostras}–${estrategia.meta_maxima_amostras}`} />
              <Kpi label="Obrigatórias" v={String(estrategia.criterios_obrigatorios.length)} />
            </div>
            <div className="text-[11px] text-slate-600 mb-1">
              <b>Obrigatórios:</b> {estrategia.criterios_obrigatorios.join(', ') || '—'} ·{' '}
              <b>Flexíveis:</b> {estrategia.criterios_flexiveis.join(', ') || '—'}
            </div>
            <p className="text-[11px] text-slate-500 italic">{estrategia.justificativa_tipologia}</p>
            {estrategia.avisos.length > 0 && (
              <ul className="mt-1 text-[11px] text-amber-700 list-disc pl-4">
                {estrategia.avisos.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            )}
            <details className="mt-2">
              <summary className="text-[11px] text-blue-600 cursor-pointer">Ver JSON completo</summary>
              <pre className="mt-1 p-2 bg-slate-900 text-slate-100 rounded text-[10px] overflow-auto max-h-56">
{JSON.stringify(pacotePesquisa(), null, 2)}
              </pre>
            </details>
          </div>
        )}

        <label className="block text-[11px] text-slate-500 mb-1">2. Cole aqui o retorno do pesquisador</label>
        <textarea value={retornoAgente} onChange={(e) => setRetornoAgente(e.target.value)} rows={5}
          placeholder='{"elementos": [{"endereco": "...", "preco": 500000, "area_construida": 100, "url": "https://..."}]}'
          className="w-full px-2 py-1.5 text-[11px] border border-slate-300 rounded font-mono" />
        <button onClick={processarRetorno} disabled={filtrando || !retornoAgente.trim()}
          className="mt-2 px-3 py-1.5 text-xs rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white flex items-center gap-1.5 font-medium">
          {filtrando ? <Loader2 size={13} className="animate-spin" /> : <ShieldCheck size={13} />}
          {filtrando ? 'Filtrando…' : '3. Filtrar e adicionar aos candidatos'}
        </button>

        {filtro && (
          <div className="mt-3 space-y-2">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[12px]">
              <Kpi label="Recebidos" v={String(filtro.resumo_filtro.recebidos)} />
              <Kpi label="Aceitos" v={String(filtro.resumo_filtro.aceitos)} />
              <Kpi label="Rejeitados" v={String(filtro.resumo_filtro.rejeitados)} />
              <Kpi label="R$/m² corrigidos" v={String(filtro.resumo_filtro.precos_m2_corrigidos)} />
            </div>

            {filtro.contradicoes.length > 0 && (
              <div className="p-2.5 rounded-lg bg-red-50 border border-red-200">
                <div className="text-[11px] font-semibold text-red-700 mb-1 flex items-center gap-1">
                  <AlertTriangle size={13} /> Contradições no retorno do agente
                </div>
                <ul className="text-[11px] text-red-700 list-disc pl-4">
                  {filtro.contradicoes.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            )}

            {filtro.rejeitados.length > 0 && (
              <details>
                <summary className="text-[11px] text-slate-500 cursor-pointer">
                  {filtro.rejeitados.length} imóvel(is) descartado(s) pelo filtro
                </summary>
                <ul className="mt-1 text-[11px] text-slate-500 list-disc pl-4">
                  {filtro.rejeitados.map((r, i) => <li key={i}>{r.imovel || 'sem nome'} — {r.motivo}</li>)}
                </ul>
              </details>
            )}

            {filtro.campos_ignorados.length > 0 && (
              <p className="text-[10px] text-slate-400">
                Campos ignorados do agente (calculados pelo motor): {filtro.campos_ignorados.join(', ')}.
              </p>
            )}
          </div>
        )}
      </Secao>

      {/* 04 — Candidatos */}
      <Secao n="04" titulo="Imóveis candidatos" icone={<Layers size={16} />}>
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <button onClick={buscarAutomatico} disabled={buscandoFontes || !loc}
            title={loc ? 'Buscar em bases públicas (Caixa)' : 'Busque o CEP primeiro'}
            className="px-3 py-1.5 text-xs rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white flex items-center gap-1.5 font-medium">
            {buscandoFontes ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
            {buscandoFontes ? 'Buscando…' : 'Buscar automaticamente'}
          </button>
          <button onClick={() => setCandidatos([...candidatos, {}])} className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 hover:bg-slate-50 flex items-center gap-1">
            <Plus size={13} /> Candidato
          </button>
          <button onClick={() => setColarAberto(!colarAberto)} className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 hover:bg-slate-50 flex items-center gap-1">
            <ClipboardPaste size={13} /> Colar lista
          </button>
          <span className="ml-auto text-[11px] text-slate-500">Meta: 15 a 30 amostras qualificadas</span>
        </div>

        {infoFontes && (
          <div className="mb-2 text-[11px] text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-2.5 py-1.5">
            ✓ {infoFontes} <span className="text-emerald-600">Fonte: dados públicos oficiais (valor de avaliação, com link de verificação).</span>
          </div>
        )}

        {colarAberto && (
          <div className="mb-3 p-3 rounded-lg bg-blue-50 border border-blue-200">
            <p className="text-[11px] text-blue-800 mb-1">
              Uma linha por imóvel: <b>identificação; preço; área construída; área terreno; fonte</b>
            </p>
            <textarea value={textoColado} onChange={(e) => setTextoColado(e.target.value)} rows={4}
              placeholder="Casa Rua A 120; 650000; 150; 360; https://portal.com/1"
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
                <th className="px-2 py-1.5">Á. constr.</th>
                <th className="px-2 py-1.5">Á. terreno</th>
                <th className="px-2 py-1.5">Bairro</th>
                <th className="px-2 py-1.5">Dist. km</th>
                <th className="px-2 py-1.5">Fonte</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {candidatos.map((c, i) => (
                <tr key={i} className="border-b border-slate-100">
                  <td className="px-1 py-1"><Cel v={c.identificacao ?? ''} on={(x) => setC(i, 'identificacao', x)} texto /></td>
                  <td className="px-1 py-1"><Cel v={c.preco ?? ''} on={(x) => setC(i, 'preco', x)} /></td>
                  <td className="px-1 py-1"><Cel v={c.area_construida ?? ''} on={(x) => setC(i, 'area_construida', x)} /></td>
                  <td className="px-1 py-1"><Cel v={c.area_terreno ?? ''} on={(x) => setC(i, 'area_terreno', x)} /></td>
                  <td className="px-1 py-1"><Cel v={c.bairro ?? ''} on={(x) => setC(i, 'bairro', x)} texto /></td>
                  <td className="px-1 py-1"><Cel v={c.distancia_km ?? ''} on={(x) => setC(i, 'distancia_km', x)} /></td>
                  <td className="px-1 py-1"><Cel v={c.fonte ?? ''} on={(x) => setC(i, 'fonte', x)} texto /></td>
                  <td className="px-1 py-1 text-center">
                    <button onClick={() => setCandidatos(candidatos.filter((_, j) => j !== i))} className="text-slate-300 hover:text-red-500"><Trash2 size={13} /></button>
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
          {loading ? 'Buscando…' : 'Montar base de amostras'}
        </button>
      </Secao>

      {/* 04 — Resultado */}
      {res && (
        <Secao n="05" titulo="Amostras qualificadas" icone={<CheckCircle2 size={16} />}>
          <div className={`rounded-lg border-2 p-3 mb-3 ${res.resumo.suficiente_para_avaliacao ? 'border-emerald-300 bg-emerald-50' : 'border-amber-300 bg-amber-50'}`}>
            <div className="flex items-center gap-2 font-semibold text-slate-800">
              {res.resumo.suficiente_para_avaliacao ? <CheckCircle2 size={18} className="text-emerald-600" /> : <AlertTriangle size={18} className="text-amber-600" />}
              Confiabilidade da busca: {res.confiabilidade_busca}%
            </div>
            <p className="text-[12px] text-slate-600 mt-1">{res.orientacao}</p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-3 text-[12px]">
            <Kpi label="Qualificadas" v={`${res.resumo.amostras_qualificadas}/${res.resumo.meta_minima}`} />
            <Kpi label="Candidatos" v={String(res.resumo.total_candidatos)} />
            <Kpi label="Descartados" v={String(res.resumo.descartados_qualidade)} />
            <Kpi label="Similaridade média" v={`${res.resumo.similaridade_media}%`} />
            <Kpi label="Nível usado" v={String(res.resumo.nivel_maximo_usado)} />
          </div>

          {/* Trilha de expansão */}
          <div className="mb-3 p-2.5 rounded-lg bg-slate-50 border border-slate-200">
            <div className="text-[11px] font-semibold text-slate-600 mb-1">Expansão inteligente</div>
            <div className="flex flex-wrap gap-1.5">
              {res.trilha_expansao.map((t) => (
                <span key={t.nivel}
                  className={`text-[10px] px-2 py-0.5 rounded-full border ${
                    !t.executado ? 'bg-slate-100 text-slate-400 border-slate-200'
                    : t.encontrados > 0 ? 'bg-blue-100 text-blue-700 border-blue-300'
                    : 'bg-white text-slate-500 border-slate-200'}`}>
                  {t.nivel}. {t.descricao} {t.executado ? `(+${t.encontrados})` : '— não precisou'}
                </span>
              ))}
            </div>
          </div>

          {/* Lista de amostras */}
          <div className="space-y-2 max-h-[420px] overflow-auto">
            {res.amostras.map((a, i) => (
              <div key={i} className="border border-slate-200 rounded-lg overflow-hidden">
                <div className="flex flex-wrap items-center gap-2 p-2.5 bg-white">
                  <input type="checkbox" checked={selec.has(i)} onChange={() => {
                    const s = new Set(selec); s.has(i) ? s.delete(i) : s.add(i); setSelec(s)
                  }} className="accent-blue-600" />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-slate-800 truncate">{a.endereco || a.identificacao}</div>
                    <div className="text-[11px] text-slate-500">
                      {brl(a.preco)} · {numf(a.area)} m² · {brl(a.preco_m2)}/m²
                      {a.bairro && ` · ${a.bairro}`}
                      {a.fonte && <> · <a href={a.fonte} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">fonte</a></>}
                    </div>
                  </div>
                  <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">nível {a.nivel_expansao}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${
                    a.score >= 90 ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    : a.score >= 80 ? 'bg-blue-100 text-blue-800 border-blue-300'
                    : a.score >= 65 ? 'bg-amber-100 text-amber-800 border-amber-300'
                    : 'bg-red-100 text-red-800 border-red-300'}`}>{a.score}%</span>
                  <button onClick={() => setDetalhe(detalhe === i ? null : i)} className="text-[11px] text-blue-600 hover:underline">
                    {detalhe === i ? 'ocultar' : 'por quê?'}
                  </button>
                </div>
                {detalhe === i && (
                  <div className="p-3 bg-slate-50 border-t border-slate-200 grid grid-cols-2 gap-x-4 gap-y-1">
                    {Object.entries(a.similaridade).filter(([k]) => k !== 'total').map(([k, v]) => (
                      <div key={k} className="flex items-center gap-2 text-[11px]">
                        <span className="w-24 text-slate-500 capitalize shrink-0">{k}</span>
                        <div className="flex-1 h-1.5 bg-slate-200 rounded overflow-hidden">
                          <div className="h-full bg-blue-500" style={{ width: `${v}%` }} />
                        </div>
                        <span className="w-9 text-right font-medium text-slate-700">{v}%</span>
                      </div>
                    ))}
                    {a.territorial_score != null && (
                      <div className="col-span-2 text-[10px] text-slate-500 mt-1">
                        Similaridade territorial: <b>{a.territorial_score}%</b>
                        {a.territorial_detalhes && ` (${Object.entries(a.territorial_detalhes).map(([k, v]) => `${k}: ${v}%`).join(' · ')})`}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {res.descartados.length > 0 && (
            <details className="mt-3">
              <summary className="text-[11px] text-slate-500 cursor-pointer">
                {res.descartados.length} descartado(s) na triagem de qualidade
              </summary>
              <ul className="mt-1 text-[11px] text-slate-500 list-disc pl-4">
                {res.descartados.map((d, i) => <li key={i}>{d.imovel || 'sem nome'} — {d.motivo}</li>)}
              </ul>
            </details>
          )}

          {onEnviarParaAmostras && (
            <button onClick={enviar}
              className="mt-4 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium flex items-center gap-2">
              <Send size={15} /> Enviar {selec.size} amostra(s) para o Avaliador
            </button>
          )}
        </Secao>
      )}
    </div>
  )
}

/* ---------- UI ---------- */

function Secao({ n, titulo, icone, children }: { n: string; titulo: string; icone: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg font-bold text-amber-500">{n}</span>
        <h2 className="text-base font-bold text-slate-800 flex items-center gap-1.5">{icone} {titulo}</h2>
      </div>
      {children}
    </div>
  )
}

function Campo({ label, v, on, ph, texto }: { label: string; v: string; on: (x: string) => void; ph?: string; texto?: boolean }) {
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

function Ind({ icone, label, v, sub, badge, badgeCor }: { icone: React.ReactNode; label: string; v: string; sub?: string; badge?: string; badgeCor?: string }) {
  return (
    <div className="border border-slate-200 rounded-lg px-3 py-2 bg-slate-50/60">
      <div className="flex items-center gap-1.5 text-[11px] text-slate-500">{icone} {label}</div>
      <div className="text-lg font-bold text-slate-800 leading-tight">{v}</div>
      {badge && <span className={`inline-block text-[10px] px-1.5 py-0.5 rounded mt-1 ${badgeCor}`}>{badge}</span>}
      {sub && <div className="text-[10px] text-slate-400 mt-0.5">{sub}</div>}
    </div>
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
