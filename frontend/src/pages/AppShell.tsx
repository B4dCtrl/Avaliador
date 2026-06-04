import { useState } from 'react'
import Sidebar, { type SecaoApp } from '../components/ui/sidebar-with-submenu'
import Clippy from '../components/Clippy'
import Backoffice from './Backoffice'

export default function AppShell() {
  const [secao, setSecao] = useState<SecaoApp>('avaliador')
  const [clippyAberto, setClippyAberto] = useState(false)

  const selecionar = (s: SecaoApp) => {
    setSecao(s)
    if (s === 'assistente') setClippyAberto(true)
  }

  return (
    <div className="h-screen flex bg-slate-100 overflow-hidden">
      <Sidebar secao={secao} onSelect={selecionar} />

      {/* Área principal — o "site moderno" */}
      <main className="flex-1 min-w-0 flex flex-col">
        {/* Top bar moderna */}
        <header className="h-12 bg-white border-b border-slate-200 flex items-center px-5 shrink-0">
          <h1 className="text-sm font-semibold text-slate-700">
            {secao === 'avaliador' ? 'Avaliador' : secao === 'modelos' ? 'Modelos' : 'Assistente'}
          </h1>
          <span className="ml-2 text-[11px] text-slate-400">NBR 14653-02 · Regressão linear</span>
          <div className="ml-auto flex items-center gap-2 text-[11px] text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> conectado
          </div>
        </header>

        {/* Conteúdo */}
        <div className="flex-1 overflow-auto">
          {secao === 'avaliador' && (
            // Inception: o programa Windows clássico rodando "dentro" do site
            <Backoffice />
          )}

          {secao === 'modelos' && (
            <div className="p-8 max-w-3xl mx-auto">
              <h2 className="text-lg font-bold text-slate-800 mb-1">Modelos</h2>
              <p className="text-sm text-slate-500 mb-4">O ranking de modelos testados aparece dentro do Avaliador, no Passo 4 (Resultado).</p>
              <button onClick={() => selecionar('avaliador')} className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700">Abrir Avaliador</button>
            </div>
          )}

          {secao === 'assistente' && (
            <div className="p-8 max-w-3xl mx-auto text-center">
              <h2 className="text-lg font-bold text-slate-800 mb-1">Assistente</h2>
              <p className="text-sm text-slate-500 mb-4">Tire dúvidas sobre regressão, NBR 14653-02, importação de dados e laudos. O assistente fica no canto da tela.</p>
              <button onClick={() => setClippyAberto(true)} className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700">Abrir assistente</button>
            </div>
          )}
        </div>
      </main>

      <Clippy aberto={clippyAberto} setAberto={setClippyAberto} />
    </div>
  )
}
