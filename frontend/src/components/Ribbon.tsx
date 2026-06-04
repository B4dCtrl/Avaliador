import {
  FilePlus, FolderOpen, Save, SaveAll, Settings, Printer,
  Eye, Plus, Minus, Pencil, Calculator, FunctionSquare, Activity,
  Table2, ListChecks, RotateCcw, Ban, SlidersHorizontal, GitCompare,
  TrendingUp, ScatterChart,
} from 'lucide-react'
import type { ReactNode } from 'react'

export type RibbonTab = 'modelo' | 'variaveis' | 'dados' | 'calcular'

export interface RibbonActions {
  // Modelo
  novo: () => void
  abrir: () => void
  salvar: () => void
  salvarComo: () => void
  propriedades: () => void
  imprimir: () => void
  // Variáveis
  exibirVariaveis: () => void
  incluirVariavel: () => void
  excluirVariavel: () => void
  renomearVariavel: () => void
  operarVariaveis: () => void
  durbinWatson: () => void
  // Dados
  editarDados: () => void
  incluirDados: () => void
  excluirDados: () => void
  operarDados: () => void
  desabilitar: () => void
  reconsiderar: () => void
  // Calcular
  calcular: () => void
  verModelos: () => void
  verEquacao: () => void
  verResiduos: () => void
  verCorrelacoes: () => void
}

interface Props {
  tab: RibbonTab
  setTab: (t: RibbonTab) => void
  actions: RibbonActions
  temResultado: boolean
  loading: boolean
}

function Big({ ico, label, onClick, disabled }: { ico: ReactNode; label: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button className="ribbon-btn" onClick={onClick} disabled={disabled}>
      <span className="ribbon-btn-ico">{ico}</span>
      <span className="leading-tight">{label}</span>
    </button>
  )
}

function Group({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="ribbon-group">
      <div className="ribbon-group-items">{children}</div>
      <div className="ribbon-group-label">{label}</div>
    </div>
  )
}

const TABS: { id: RibbonTab; nome: string }[] = [
  { id: 'modelo', nome: 'Modelo' },
  { id: 'variaveis', nome: 'Variáveis' },
  { id: 'dados', nome: 'Dados' },
  { id: 'calcular', nome: 'Calcular' },
]

export default function Ribbon({ tab, setTab, actions: a, temResultado, loading }: Props) {
  return (
    <div className="ribbon">
      <div className="ribbon-tabs">
        {TABS.map((t) => (
          <div key={t.id}
            className={`ribbon-tab ${tab === t.id ? 'ribbon-tab-active' : ''}`}
            onClick={() => setTab(t.id)}>
            {t.nome}
          </div>
        ))}
      </div>

      <div className="ribbon-body">
        {tab === 'modelo' && (
          <>
            <Group label="Modelo">
              <Big ico={<FilePlus size={26} />} label="Novo" onClick={a.novo} />
              <Big ico={<FolderOpen size={26} />} label="Abrir" onClick={a.abrir} />
              <Big ico={<Save size={26} />} label="Salvar" onClick={a.salvar} />
              <Big ico={<SaveAll size={26} />} label="Salvar como" onClick={a.salvarComo} />
              <Big ico={<Settings size={26} />} label="Propriedades" onClick={a.propriedades} />
            </Group>
            <Group label="Imprimir">
              <Big ico={<Printer size={26} />} label="Imprimir (PDF)" onClick={a.imprimir} disabled={!temResultado} />
            </Group>
          </>
        )}

        {tab === 'variaveis' && (
          <>
            <Group label="Variáveis">
              <Big ico={<Eye size={26} />} label="Exibir" onClick={a.exibirVariaveis} />
              <Big ico={<Plus size={26} />} label="Incluir" onClick={a.incluirVariavel} />
              <Big ico={<Minus size={26} />} label="Excluir" onClick={a.excluirVariavel} />
              <Big ico={<Pencil size={26} />} label="Renomear" onClick={a.renomearVariavel} />
              <Big ico={<SlidersHorizontal size={26} />} label="Operar" onClick={a.operarVariaveis} />
            </Group>
            <Group label="Análise Multivariada">
              <Big ico={<GitCompare size={26} />} label="Durbin-Watson" onClick={a.durbinWatson} disabled={!temResultado} />
            </Group>
          </>
        )}

        {tab === 'dados' && (
          <>
            <Group label="Dados">
              <Big ico={<Pencil size={26} />} label="Editar" onClick={a.editarDados} />
              <Big ico={<Plus size={26} />} label="Incluir" onClick={a.incluirDados} />
              <Big ico={<Minus size={26} />} label="Excluir" onClick={a.excluirDados} />
              <Big ico={<SlidersHorizontal size={26} />} label="Operar" onClick={a.operarDados} />
            </Group>
            <Group label="Outliers / Qualidade">
              <Big ico={<Ban size={26} />} label="Desabilitar" onClick={a.desabilitar} disabled={!temResultado} />
              <Big ico={<RotateCcw size={26} />} label="Reconsiderar" onClick={a.reconsiderar} />
            </Group>
          </>
        )}

        {tab === 'calcular' && (
          <>
            <Group label="Regressão Linear">
              <Big ico={<Calculator size={26} />} label={loading ? 'Calculando…' : 'Calcular'} onClick={a.calcular} disabled={loading} />
              <Big ico={<Table2 size={26} />} label="Modelos" onClick={a.verModelos} disabled={!temResultado} />
              <Big ico={<FunctionSquare size={26} />} label="Equação" onClick={a.verEquacao} disabled={!temResultado} />
              <Big ico={<Activity size={26} />} label="Resíduos" onClick={a.verResiduos} disabled={!temResultado} />
              <Big ico={<ScatterChart size={26} />} label="Correlações" onClick={a.verCorrelacoes} disabled={!temResultado} />
              <Big ico={<TrendingUp size={26} />} label="Diagnósticos" onClick={a.verModelos} disabled={!temResultado} />
              <Big ico={<ListChecks size={26} />} label="Aderência" onClick={a.verResiduos} disabled={!temResultado} />
            </Group>
          </>
        )}
      </div>
    </div>
  )
}
