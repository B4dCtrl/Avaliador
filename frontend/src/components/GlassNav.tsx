import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { cn } from '../lib/utils'

const ITEMS = [
  { id: 'inicio', label: 'Início' },
  { id: 'recursos', label: 'Recursos' },
  { id: 'preco', label: 'Preço' },
  { id: 'faq', label: 'FAQ' },
]

export default function GlassNav() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 30)
    onScroll()
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
    setOpen(false)
  }

  return (
    <header className="fixed top-3 inset-x-0 z-50 flex justify-center px-3">
      <nav
        className={cn(
          'flex items-center justify-between gap-6 px-4 py-2.5 rounded-full',
          'border border-white/20 backdrop-blur-xl transition-all duration-300',
          'w-full max-w-3xl shadow-lg',
          scrolled ? 'bg-white/70 dark:bg-slate-900/70' : 'bg-white/40 dark:bg-slate-900/40',
        )}
      >
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-bold">
            A
          </div>
          <span className="font-semibold text-slate-800 dark:text-white">Avaliador</span>
        </Link>

        <div className="hidden md:flex items-center gap-1">
          {ITEMS.map((i) => (
            <button
              key={i.id}
              onClick={() => scrollTo(i.id)}
              className="px-3 py-1.5 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-white/60 dark:hover:bg-white/10 rounded-full transition-colors"
            >
              {i.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/app"
            className="hidden md:inline-flex px-4 py-2 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-sm font-medium hover:opacity-90 transition"
          >
            Acessar
          </Link>
          <button
            onClick={() => setOpen((v) => !v)}
            className="md:hidden p-2 text-slate-700 dark:text-white"
            aria-label="Menu"
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </nav>

      {open && (
        <div className="md:hidden absolute top-16 left-3 right-3 rounded-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl border border-white/20 shadow-xl p-3 space-y-1">
          {ITEMS.map((i) => (
            <button
              key={i.id}
              onClick={() => scrollTo(i.id)}
              className="block w-full text-left px-3 py-2 rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/10"
            >
              {i.label}
            </button>
          ))}
          <Link
            to="/app"
            onClick={() => setOpen(false)}
            className="block px-3 py-2 rounded-lg bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-center font-medium"
          >
            Acessar
          </Link>
        </div>
      )}
    </header>
  )
}
