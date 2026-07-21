import { useEffect, useState } from 'react'
import {
  Plus, FileText, Database, GraduationCap, IdCard, Pencil, Check,
  Clock, TrendingUp, Link2, Sparkles, ArrowRight,
} from 'lucide-react'
import type { SecaoApp } from '../components/ui/sidebar-with-submenu'

const PERFIL_KEY = 'avaliador_perfil_v1'

export interface PerfilAvaliador {
  nome: string
  crea: string
  empresa: string
  cidade: string
}

export function carregarPerfil(): PerfilAvaliador {
  try {
    const raw = localStorage.getItem(PERFIL_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignora */ }
  return { nome: '', crea: '', empresa: '', cidade: '' }
}

interface Props {
  irPara: (s: SecaoApp) => void
  novaAvaliacao: () => void
}

// Laudos salvos (localStorage) — começa vazio; sem dados fictícios.
interface LaudoSalvo { id: string; titulo: string; data: string; grau: string; valor: string }
function carregarLaudos(): LaudoSalvo[] {
  try {
    const raw = localStorage.getItem('avaliador_laudos_v1')
    if (raw) return JSON.parse(raw)
  } catch { /* ignora */ }
  return []
}

export default function Home({ irPara, novaAvaliacao }: Props) {
  const [perfil, setPerfil] = useState<PerfilAvaliador>(carregarPerfil)
  const [editando, setEditando] = useState(false)
  const [laudos] = useState<LaudoSalvo[]>(carregarLaudos)

  useEffect(() => {
    localStorage.setItem(PERFIL_KEY, JSON.stringify(perfil))
  }, [perfil])

  const saudacao = perfil.nome ? `Olá, ${perfil.nome.split(' ')[0]}` : 'Bem-vindo ao Avaliador'

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Cabeçalho */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800">{saudacao} 👋</h1>
        <p className="text-sm text-slate-500">Central de avaliações imobiliárias — NBR 14653</p>
      </div>

      {/* Perfil do avaliador */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <IdCard size={16} /> Dados do avaliador
          </h2>
          <button onClick={() => setEditando(!editando)}
            className="text-xs flex items-center gap-1 text-blue-600 hover:text-blue-800">
            {editando ? <><Check size={13} /> Salvar</> : <><Pencil size={13} /> Editar</>}
          </button>
        </div>
        {editando ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {([['nome', 'Nome completo'], ['crea', 'CREA/CAU'], ['empresa', 'Empresa'], ['cidade', 'Cidade/UF']] as const).map(([campo, label]) => (
              <div key={campo}>
                <label className="block text-[11px] text-slate-500 mb-0.5">{label}</label>
                <input value={perfil[campo]} onChange={(e) => setPerfil({ ...perfil, [campo]: e.target.value })}
                  className="w-full px-2.5 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:border-blue-500" />
              </div>
            ))}
          </div>
        ) : perfil.nome ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <Info label="Nome" value={perfil.nome} />
            <Info label="CREA/CAU" value={perfil.crea || '—'} />
            <Info label="Empresa" value={perfil.empresa || '—'} />
            <Info label="Cidade/UF" value={perfil.cidade || '—'} />
          </div>
        ) : (
          <p className="text-sm text-slate-400">Preencha seus dados — eles vão automaticamente para os laudos.</p>
        )}
      </div>

      {/* Ações rápidas */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <button onClick={novaAvaliacao}
          className="group text-left bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-xl p-5 shadow-sm hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <Plus size={26} />
            <ArrowRight size={18} className="opacity-60 group-hover:translate-x-1 transition-transform" />
          </div>
          <div className="mt-3 text-lg font-semibold">Nova avaliação</div>
          <div className="text-xs text-blue-100">Regressão linear + laudo NBR 14653</div>
        </button>

        <button onClick={() => irPara('banco')}
          className="group text-left bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between text-emerald-600">
            <Database size={26} />
            <span className="text-[10px] font-bold bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">PREMIUM</span>
          </div>
          <div className="mt-3 text-lg font-semibold text-slate-800">Banco de imóveis</div>
          <div className="text-xs text-slate-500">Amostras verificáveis compartilhadas</div>
        </button>

        <button onClick={() => irPara('aprender')}
          className="group text-left bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between text-amber-600">
            <GraduationCap size={26} />
            <ArrowRight size={18} className="opacity-40 group-hover:translate-x-1 transition-transform" />
          </div>
          <div className="mt-3 text-lg font-semibold text-slate-800">Aprender</div>
          <div className="text-xs text-slate-500">Tutoriais de avaliação e da norma</div>
        </button>
      </div>

      {/* Laudos salvos */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <FileText size={16} /> Laudos recentes
          </h2>
          <button onClick={novaAvaliacao} className="text-xs text-blue-600 hover:text-blue-800">+ Novo</button>
        </div>
        {laudos.length === 0 ? (
          <div className="text-center py-10 text-slate-400">
            <FileText size={40} className="mx-auto mb-2 opacity-40" />
            <p className="text-sm">Você ainda não salvou laudos.</p>
            <button onClick={novaAvaliacao} className="mt-3 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700">
              Criar primeira avaliação
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {laudos.map((l) => (
              <div key={l.id} className="border border-slate-200 rounded-lg p-3 hover:border-blue-300 cursor-pointer">
                <div className="text-sm font-medium text-slate-800 truncate">{l.titulo}</div>
                <div className="flex items-center gap-1 text-[11px] text-slate-400 mt-1"><Clock size={11} /> {l.data}</div>
                <div className="flex items-center justify-between mt-2 text-xs">
                  <span className="bg-slate-100 px-2 py-0.5 rounded">Grau {l.grau}</span>
                  <span className="font-semibold text-slate-700">{l.valor}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Banner do banco de imóveis (diferencial) */}
      <div className="rounded-xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-5">
        <div className="flex items-start gap-4">
          <div className="w-11 h-11 rounded-lg bg-emerald-600 text-white flex items-center justify-center shrink-0">
            <Database size={22} />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-slate-800">Banco colaborativo de imóveis verificáveis</h3>
              <span className="text-[10px] font-bold bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">PREMIUM</span>
            </div>
            <p className="text-sm text-slate-600 mt-1">
              Cada amostra é cadastrada com sua <b>fonte</b> (link de anúncio, escritura, etc.) que serve de
              verificação. Assim o banco cresce coletivamente: você não precisa correr atrás de todos os
              comparáveis — cadastra alguns, e o sistema <b>sugere imóveis próximos para aumentar o grau</b> da sua avaliação.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
              <MiniStat icon={<Link2 size={14} />} label="Imóveis com fonte" value="—" />
              <MiniStat icon={<TrendingUp size={14} />} label="Sugeridos p/ você" value="—" />
              <MiniStat icon={<Sparkles size={14} />} label="Ganho de grau médio" value="—" />
              <MiniStat icon={<Clock size={14} />} label="Última atualização" value="—" />
            </div>
            <button onClick={() => irPara('banco')}
              className="mt-3 px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm hover:bg-emerald-700 flex items-center gap-1">
              Explorar banco <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] text-slate-400">{label}</div>
      <div className="text-slate-800 font-medium truncate">{value}</div>
    </div>
  )
}

function MiniStat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg px-3 py-2">
      <div className="flex items-center gap-1 text-[11px] text-slate-500">{icon} {label}</div>
      <div className="text-slate-800 font-semibold">{value}</div>
    </div>
  )
}
