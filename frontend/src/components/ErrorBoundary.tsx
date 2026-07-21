import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { erro: Error | null }

/**
 * Blindagem global: qualquer erro de renderização mostra um painel
 * amigável em vez de tela branca.
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { erro: null }

  static getDerivedStateFromError(erro: Error): State {
    return { erro }
  }

  componentDidCatch(erro: Error, info: ErrorInfo) {
    console.error('[Avaliador] erro de renderização:', erro, info.componentStack)
  }

  render() {
    if (this.state.erro) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-100 p-6">
          <div className="max-w-md w-full bg-white border-2 border-red-300 rounded-lg shadow-lg overflow-hidden">
            <div className="px-4 py-2 bg-red-600 text-white text-sm font-semibold">
              Ocorreu um erro inesperado
            </div>
            <div className="p-4 space-y-3">
              <p className="text-sm text-slate-600">
                O Avaliador encontrou um problema ao exibir esta tela. Seus dados
                estão salvos automaticamente — nada foi perdido.
              </p>
              <pre className="text-[11px] bg-slate-50 border border-slate-200 rounded p-2 overflow-auto max-h-28 text-red-700">
                {this.state.erro.message}
              </pre>
              <div className="flex gap-2">
                <button
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium">
                  Recarregar
                </button>
                <button
                  onClick={() => this.setState({ erro: null })}
                  className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-slate-700 text-sm">
                  Tentar continuar
                </button>
              </div>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
