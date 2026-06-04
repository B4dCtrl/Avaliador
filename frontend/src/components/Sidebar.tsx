import { Calculator, LayoutList, Bot, PanelLeftClose, PanelLeftOpen } from 'lucide-react'

export type Secao = 'avaliador' | 'modelos' | 'assistente'

interface Props {
  secao: Secao
  setSecao: (s: Secao) => void
  aberta: boolean
  setAberta: (v: boolean) => void
}

const ITENS: { id: Secao; nome: string; icon: React.ReactNode }[] = [
  { id: 'avaliador', nome: 'Avaliador', icon: <Calculator size={18} /> },
  { id: 'modelos', nome: 'Modelos', icon: <LayoutList size={18} /> },
  { id: 'assistente', nome: 'Assistente', icon: <Bot size={18} /> },
]

export default function Sidebar({ secao, setSecao, aberta, setAberta }: Props) {
  return (
    <div className={`shrink-0 bg-[#26344d] text-white flex flex-col transition-all duration-200 ${aberta ? 'w-44' : 'w-12'}`}>
      <button onClick={() => setAberta(!aberta)}
        className="h-9 flex items-center justify-center text-white/70 hover:text-white hover:bg-white/10"
        title={aberta ? 'Recolher menu' : 'Expandir menu'}>
        {aberta ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
      </button>
      <nav className="flex-1 py-1">
        {ITENS.map((it) => (
          <button key={it.id} onClick={() => setSecao(it.id)}
            title={it.nome}
            className={`w-full flex items-center gap-3 px-3 py-2.5 text-[13px] transition-colors
              ${secao === it.id ? 'bg-[#0a4fd6] text-white' : 'text-white/75 hover:bg-white/10'} ${aberta ? '' : 'justify-center'}`}>
            {it.icon}
            {aberta && <span>{it.nome}</span>}
          </button>
        ))}
      </nav>
      {aberta && (
        <div className="p-2 text-[10px] text-white/40 border-t border-white/10">Avaliador · NBR 14653-02</div>
      )}
    </div>
  )
}
