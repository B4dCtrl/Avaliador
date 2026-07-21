import { useState, type ReactNode } from 'react'
import {
  LayoutDashboard, Calculator, Database, GraduationCap, LayoutList, Bot,
  Wrench, HelpCircle, Settings, ChevronDown, Pin, PinOff, LogOut, Home,
} from 'lucide-react'
import { Link } from 'react-router-dom'

export type SecaoApp = 'inicio' | 'avaliador' | 'modelos' | 'banco' | 'aprender' | 'assistente'

interface MenuItem { id: SecaoApp; name: string; icon: ReactNode }

const navigation: MenuItem[] = [
  { id: 'inicio', name: 'Início', icon: <LayoutDashboard className="w-5 h-5" /> },
  { id: 'avaliador', name: 'Avaliador', icon: <Calculator className="w-5 h-5" /> },
  { id: 'modelos', name: 'Modelos', icon: <LayoutList className="w-5 h-5" /> },
  { id: 'banco', name: 'Banco de imóveis', icon: <Database className="w-5 h-5" /> },
  { id: 'aprender', name: 'Aprender', icon: <GraduationCap className="w-5 h-5" /> },
  { id: 'assistente', name: 'Assistente', icon: <Bot className="w-5 h-5" /> },
]

const ferramentas = ['Variáveis', 'Dados', 'Diagnósticos', 'Gráficos']

interface SubMenuProps { aberto: boolean; label: string; icon: ReactNode; itens: string[] }
function SubMenu({ aberto, label, icon, itens }: SubMenuProps) {
  const [open, setOpen] = useState(false)
  if (!aberto) {
    return (
      <button className="w-full flex items-center justify-center text-slate-500 p-2 rounded-lg hover:bg-slate-100" title={label}>
        {icon}
      </button>
    )
  }
  return (
    <div>
      <button onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between text-slate-600 p-2 rounded-lg hover:bg-slate-100 duration-150">
        <span className="flex items-center gap-x-2">{icon}<span className="text-sm">{label}</span></span>
        <ChevronDown className={`w-4 h-4 duration-150 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <ul className="mx-4 px-2 border-l border-slate-200 text-sm">
          {itens.map((it) => (
            <li key={it}>
              <span className="block text-slate-500 p-2 rounded-lg hover:bg-slate-100 cursor-default">{it}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

interface Props {
  secao: SecaoApp
  onSelect: (s: SecaoApp) => void
}

export default function Sidebar({ secao, onSelect }: Props) {
  const [fixado, setFixado] = useState(false) // "pino": mantém aberto
  const [hover, setHover] = useState(false)
  const aberto = fixado || hover

  return (
    <nav
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      className={`h-full border-r border-slate-200 bg-white flex flex-col shrink-0 transition-[width] duration-200 ${aberto ? 'w-60 shadow-xl' : 'w-16'}`}>
      {/* Cabeçalho / perfil */}
      <div className="h-16 flex items-center px-3 border-b border-slate-100">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 text-white flex items-center justify-center font-black shrink-0">A</div>
        {aberto && (
          <div className="ml-3 min-w-0">
            <div className="text-sm font-semibold text-slate-700 truncate">Avaliador</div>
            <div className="text-[11px] text-slate-400">Plano Pro</div>
          </div>
        )}
        {aberto && (
          <button onClick={() => setFixado(!fixado)}
            className={`ml-auto p-1.5 rounded-md hover:bg-slate-100 ${fixado ? 'text-blue-600' : 'text-slate-400'}`}
            title={fixado ? 'Desafixar (abrir só ao passar o mouse)' : 'Fixar aberto'}>
            {fixado ? <Pin className="w-4 h-4" /> : <PinOff className="w-4 h-4" />}
          </button>
        )}
      </div>

      {/* Navegação principal */}
      <div className="flex-1 overflow-auto px-2 py-3">
        {aberto && <div className="px-2 text-[10px] font-semibold text-slate-400 uppercase mb-1">Principal</div>}
        <ul className="space-y-0.5">
          {navigation.map((item) => (
            <li key={item.id}>
              <button onClick={() => onSelect(item.id)} title={item.name}
                className={`group w-full flex items-center gap-x-2 p-2 rounded-lg duration-150 relative
                  ${secao === item.id ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100'}
                  ${aberto ? '' : 'justify-center'}`}>
                {item.icon}
                {aberto && <span className="text-sm">{item.name}</span>}
                {!aberto && (
                  <span className="absolute left-14 z-20 px-2 py-1 rounded-md whitespace-nowrap text-xs text-white bg-slate-800 hidden group-hover:block">
                    {item.name}
                  </span>
                )}
              </button>
            </li>
          ))}
          <li><SubMenu aberto={aberto} label="Ferramentas" icon={<Wrench className="w-5 h-5" />} itens={ferramentas} /></li>
        </ul>
      </div>

      {/* Rodapé */}
      <div className="px-2 py-3 border-t border-slate-100 space-y-0.5">
        <button onClick={() => onSelect('assistente')} title="Ajuda"
          className={`w-full flex items-center gap-x-2 p-2 rounded-lg text-slate-600 hover:bg-slate-100 ${aberto ? '' : 'justify-center'}`}>
          <HelpCircle className="w-5 h-5" />{aberto && <span className="text-sm">Ajuda</span>}
        </button>
        <button title="Configurações"
          className={`w-full flex items-center gap-x-2 p-2 rounded-lg text-slate-600 hover:bg-slate-100 ${aberto ? '' : 'justify-center'}`}>
          <Settings className="w-5 h-5" />{aberto && <span className="text-sm">Configurações</span>}
        </button>
        <Link to="/" title="Sair para o site"
          className={`w-full flex items-center gap-x-2 p-2 rounded-lg text-slate-600 hover:bg-slate-100 ${aberto ? '' : 'justify-center'}`}>
          <Home className="w-5 h-5" />{aberto && <span className="text-sm">Site</span>}
        </Link>
        {aberto && (
          <div className="flex items-center gap-2 px-2 pt-2 mt-1 border-t border-slate-100">
            <img src="https://randomuser.me/api/portraits/men/32.jpg" className="w-8 h-8 rounded-full" alt="" />
            <div className="min-w-0">
              <div className="text-xs font-medium text-slate-700 truncate">ozanchet</div>
              <div className="text-[10px] text-slate-400 truncate">ozanchet@gmail.com</div>
            </div>
            <button className="ml-auto p-1.5 text-slate-400 hover:text-slate-600" title="Sair"><LogOut className="w-4 h-4" /></button>
          </div>
        )}
      </div>
    </nav>
  )
}
