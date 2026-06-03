import {
  BarChart3,
  CheckCircle2,
  FileText,
  Layers,
  ShieldCheck,
  Zap,
} from 'lucide-react'

const FEATURES = [
  {
    Icon: BarChart3,
    title: 'Auto-ranking inteligente',
    desc: 'Testa todas as combinações de transformações nas suas variáveis e ranqueia os modelos por AIC e BIC.',
  },
  {
    Icon: ShieldCheck,
    title: 'Conformidade NBR 14653-02',
    desc: 'Validação automática: amplitude do IC, grau de precisão e grau de fundamentação calculados para você.',
  },
  {
    Icon: Layers,
    title: '7 transformações de variável',
    desc: 'Log, raiz, recíproca, quadrada e variações — aplicadas em variáveis dependente e independentes.',
  },
  {
    Icon: CheckCircle2,
    title: 'Diagnósticos avançados',
    desc: 'Shapiro-Wilk, Jarque-Bera, Breusch-Pagan e Cook’s Distance para validar o modelo escolhido.',
  },
  {
    Icon: FileText,
    title: 'Laudo em Word e PDF',
    desc: 'Exporte o laudo completo com tabelas, gráficos e resultados estatísticos prontos para entrega.',
  },
  {
    Icon: Zap,
    title: 'Resultado em segundos',
    desc: 'Suba o CSV, escolha as variáveis e veja o melhor modelo na hora — sem instalação, sem fricção.',
  },
]

export default function FeatureCards() {
  return (
    <section id="recursos" className="py-24 px-4 bg-white dark:bg-slate-950">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <span className="text-sm font-medium text-primary-600 dark:text-primary-400 uppercase tracking-wider">
            Recursos
          </span>
          <h2 className="text-4xl md:text-5xl font-bold text-slate-900 dark:text-white mt-3">
            Tudo o que um avaliador precisa
          </h2>
          <p className="text-lg text-slate-600 dark:text-slate-300 mt-4 max-w-2xl mx-auto">
            Da modelagem estatística até o laudo final — em uma única ferramenta moderna e em português.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map(({ Icon, title, desc }) => (
            <div
              key={title}
              className="group p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 hover:shadow-xl hover:-translate-y-1 transition-all duration-300"
            >
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 text-white flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Icon size={22} />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">{title}</h3>
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
