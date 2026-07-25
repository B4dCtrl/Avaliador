import { useEffect, useState } from 'react'
import Sidebar, { type SecaoApp } from '../components/ui/sidebar-with-submenu'
import Clippy, { setContextoAssistente } from '../components/Clippy'
import Backoffice from './Backoffice'
import Home from './Home'
import Comparaveis from './Comparaveis'
import Viabilidade from './Viabilidade'
import BancoImoveis from './BancoImoveis'
import Aprender from './Aprender'

const TITULOS: Record<SecaoApp, string> = {
  inicio: 'Início',
  comparaveis: 'Comparáveis',
  avaliador: 'Avaliador',
  viabilidade: 'Viabilidade de investimento',
  modelos: 'Modelos',
  banco: 'Banco de imóveis',
  aprender: 'Aprender',
  assistente: 'Assistente',
}

export default function AppShell() {
  const [secao, setSecao] = useState<SecaoApp>('inicio')
  const [clippyAberto, setClippyAberto] = useState(false)

  const selecionar = (s: SecaoApp) => {
    setSecao(s)
    if (s === 'assistente') setClippyAberto(true)
  }

  // Contexto do assistente para as seções que não são o Avaliador
  // (o Avaliador emite o contexto por passo, de dentro do Backoffice).
  useEffect(() => {
    if (secao !== 'avaliador') setContextoAssistente(secao)
  }, [secao])

  return (
    <div className="h-screen flex bg-slate-100 overflow-hidden">
      <Sidebar secao={secao} onSelect={selecionar} />

      <main className="flex-1 min-w-0 flex flex-col">
        <header className="h-12 bg-white border-b border-slate-200 flex items-center px-5 shrink-0">
          <h1 className="text-sm font-semibold text-slate-700">{TITULOS[secao]}</h1>
          <span className="ml-2 text-[11px] text-slate-400">NBR 14653 · Avaliação imobiliária</span>
          <div className="ml-auto flex items-center gap-2 text-[11px] text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> conectado
          </div>
        </header>

        <div className="flex-1 overflow-auto">
          {secao === 'inicio' && <Home irPara={selecionar} novaAvaliacao={() => selecionar('avaliador')} />}

          {secao === 'comparaveis' && (
            <Comparaveis onEnviarParaAmostras={(linhas) => {
              // Ponte: grava os comparáveis e leva o usuário para o Avaliador
              localStorage.setItem('avaliador_comps_pendentes', JSON.stringify(linhas))
              setSecao('avaliador')
              window.dispatchEvent(new CustomEvent('avaliador-importar-comps'))
            }} />
          )}

          {secao === 'avaliador' && <Backoffice />}

          {secao === 'viabilidade' && <Viabilidade />}

          {secao === 'banco' && <BancoImoveis />}

          {secao === 'aprender' && <Aprender />}

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
              <p className="text-sm text-slate-500 mb-4">Tire dúvidas sobre regressão, NBR 14653, importação de dados e laudos. O assistente fica no canto da tela.</p>
              <button onClick={() => setClippyAberto(true)} className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700">Abrir assistente</button>
            </div>
          )}
        </div>
      </main>

      <Clippy aberto={clippyAberto} setAberto={setClippyAberto} />
    </div>
  )
}
