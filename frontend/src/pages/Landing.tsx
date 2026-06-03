import { Link } from 'react-router-dom'
import { ArrowRight, BarChart3, FileText, Sparkles } from 'lucide-react'
import { ContainerScroll } from '../components/ui/container-scroll-animation'
import GlassNav from '../components/GlassNav'
import FeatureCards from '../components/FeatureCards'
import PricingSection from '../components/PricingSection'
import FAQSection from '../components/FAQSection'

export default function Landing() {
  return (
    <div className="bg-white dark:bg-slate-950 min-h-screen">
      <GlassNav />

      {/* Hero */}
      <section id="inicio" className="relative">
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-primary-50 via-white to-white dark:from-slate-900 dark:via-slate-950 dark:to-slate-950" />
        <div className="absolute inset-0 -z-10 [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_70%)]">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2240%22 height=%2240%22 viewBox=%220 0 40 40%22><circle cx=%221%22 cy=%221%22 r=%221%22 fill=%22%2393c5fd%22 fill-opacity=%220.3%22/></svg>')] opacity-50" />
        </div>

        <ContainerScroll
          titleComponent={
            <div className="pt-24 md:pt-16">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-100 dark:bg-primary-500/10 text-primary-700 dark:text-primary-300 text-xs font-medium mb-6">
                <Sparkles size={14} /> Conforme NBR 14653-02
              </div>
              <h1 className="text-4xl md:text-6xl font-bold text-slate-900 dark:text-white leading-tight">
                Avaliação imobiliária <br />
                <span className="bg-gradient-to-r from-primary-600 via-primary-500 to-primary-700 bg-clip-text text-transparent">
                  feita em minutos
                </span>
              </h1>
              <p className="mt-6 text-lg md:text-xl text-slate-600 dark:text-slate-300 max-w-2xl mx-auto">
                Auto-ranking de modelos, diagnósticos estatísticos completos e laudo Word/PDF pronto para entrega — direto do navegador.
              </p>
              <div className="mt-8 flex items-center justify-center gap-3 flex-wrap">
                <Link
                  to="/app"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-full font-medium shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition"
                >
                  Acessar agora <ArrowRight size={16} />
                </Link>
                <button
                  onClick={() => document.getElementById('recursos')?.scrollIntoView({ behavior: 'smooth' })}
                  className="px-6 py-3 rounded-full border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 font-medium hover:bg-slate-50 dark:hover:bg-slate-800 transition"
                >
                  Ver recursos
                </button>
              </div>
            </div>
          }
        >
          <HeroPreview />
        </ContainerScroll>
      </section>

      <FeatureCards />
      <PricingSection />
      <FAQSection />

      {/* CTA final */}
      <section className="py-24 px-4 bg-gradient-to-br from-primary-600 via-primary-700 to-slate-900 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl md:text-5xl font-bold">Pronto para o próximo laudo?</h2>
          <p className="text-lg text-white/80 mt-4">
            Suba seu CSV agora e veja o resultado em segundos. Sem cartão de crédito.
          </p>
          <Link
            to="/app"
            className="inline-flex items-center gap-2 mt-8 px-8 py-4 bg-white text-slate-900 rounded-full font-semibold shadow-xl hover:shadow-2xl hover:-translate-y-0.5 transition"
          >
            Começar grátis <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-10 px-4 bg-slate-950 text-slate-400 text-sm border-t border-slate-900">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-primary-600 flex items-center justify-center text-white font-bold text-xs">A</div>
            <span>Avaliador © {new Date().getFullYear()}</span>
          </div>
          <div className="flex items-center gap-4">
            <a href="#preco" className="hover:text-white">Preço</a>
            <a href="#faq" className="hover:text-white">FAQ</a>
            <Link to="/app" className="hover:text-white">Acessar</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

/** Preview mockup do backoffice dentro do card scroll. */
function HeroPreview() {
  return (
    <div className="w-full h-full p-4 md:p-6 bg-gradient-to-br from-slate-900 to-slate-950 text-slate-100 grid grid-cols-12 gap-3 text-xs md:text-sm">
      <div className="col-span-12 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
          <div className="w-2.5 h-2.5 rounded-full bg-yellow-400" />
          <div className="w-2.5 h-2.5 rounded-full bg-green-400" />
        </div>
        <div className="text-slate-400 text-[10px]">avaliador.app/app</div>
        <div className="w-12" />
      </div>

      <aside className="col-span-4 bg-slate-900/80 rounded-lg p-3 space-y-2">
        <div className="text-slate-300 font-medium flex items-center gap-2"><BarChart3 size={14} /> Configuração</div>
        <div className="space-y-1">
          {['CSV: 27 linhas', 'Y: preço', 'X: área, distância, idade', 'Conf: 80%'].map((t) => (
            <div key={t} className="px-2 py-1.5 rounded bg-slate-800 text-slate-300 text-[11px]">{t}</div>
          ))}
        </div>
        <button className="w-full py-2 rounded bg-primary-600 text-white text-xs font-medium">Calcular regressão</button>
      </aside>

      <main className="col-span-8 space-y-3">
        <div className="grid grid-cols-4 gap-2">
          {[
            { l: 'R²', v: '0,989' },
            { l: 'R² aj.', v: '0,987' },
            { l: 'F', v: '240,6' },
            { l: 'AIC', v: '-283,1' },
          ].map((s) => (
            <div key={s.l} className="bg-slate-900/80 rounded-lg p-2.5">
              <div className="text-slate-400 text-[10px]">{s.l}</div>
              <div className="text-white text-base font-semibold">{s.v}</div>
            </div>
          ))}
        </div>

        <div className="bg-slate-900/80 rounded-lg p-3 h-32 flex items-end gap-1.5">
          {[40, 60, 35, 80, 55, 90, 70, 45, 65, 75, 50, 85].map((h, i) => (
            <div
              key={i}
              style={{ height: `${h}%` }}
              className="flex-1 bg-gradient-to-t from-primary-500 to-primary-300 rounded-sm opacity-80"
            />
          ))}
        </div>

        <div className="bg-slate-900/80 rounded-lg p-3 flex items-center gap-3">
          <FileText size={18} className="text-primary-400" />
          <div className="flex-1">
            <div className="text-white text-xs font-medium">Laudo gerado · 247 KB</div>
            <div className="text-slate-400 text-[10px]">Conforme NBR 14653-02 · Grau de fundamentação II</div>
          </div>
          <button className="px-2.5 py-1 rounded bg-primary-600 text-white text-[11px]">Word</button>
          <button className="px-2.5 py-1 rounded bg-red-600 text-white text-[11px]">PDF</button>
        </div>
      </main>
    </div>
  )
}
