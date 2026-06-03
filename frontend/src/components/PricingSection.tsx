import { Check } from 'lucide-react'
import { Link } from 'react-router-dom'

const PLANS = [
  {
    name: 'Inicial',
    price: 'R$ 0',
    period: '/sempre',
    desc: 'Para testar a ferramenta com seus dados reais.',
    features: [
      'Até 3 laudos por mês',
      'Auto-ranking de modelos',
      'Diagnósticos completos',
      'Export Word + PDF',
    ],
    cta: 'Começar grátis',
    highlight: false,
  },
  {
    name: 'Profissional',
    price: 'R$ 79',
    period: '/mês',
    desc: 'O melhor para o avaliador que entrega laudos toda semana.',
    features: [
      'Laudos ilimitados',
      'Histórico de projetos',
      'Suporte por e-mail',
      'Modelos salvos',
      'Atualizações da norma incluídas',
    ],
    cta: 'Assinar plano',
    highlight: true,
  },
  {
    name: 'Escritório',
    price: 'Sob consulta',
    period: '',
    desc: 'Para equipes e escritórios com múltiplos avaliadores.',
    features: [
      'Tudo do Profissional',
      'Usuários ilimitados',
      'Logotipo no laudo',
      'Onboarding dedicado',
      'SLA garantido',
    ],
    cta: 'Falar com vendas',
    highlight: false,
  },
]

export default function PricingSection() {
  return (
    <section id="preco" className="py-24 px-4 bg-slate-50 dark:bg-slate-900">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <span className="text-sm font-medium text-primary-600 dark:text-primary-400 uppercase tracking-wider">
            Planos
          </span>
          <h2 className="text-4xl md:text-5xl font-bold text-slate-900 dark:text-white mt-3">
            Preço simples, sem pegadinha
          </h2>
          <p className="text-lg text-slate-600 dark:text-slate-300 mt-4">
            Pague apenas pelo que usar. Cancele quando quiser.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={
                plan.highlight
                  ? 'p-8 rounded-2xl bg-slate-900 dark:bg-primary-600 text-white shadow-2xl scale-105 relative ring-4 ring-primary-500/30'
                  : 'p-8 rounded-2xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm'
              }
            >
              {plan.highlight && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-yellow-400 text-slate-900 text-xs font-bold px-3 py-1 rounded-full">
                  MAIS POPULAR
                </span>
              )}
              <h3 className={'text-xl font-bold ' + (plan.highlight ? 'text-white' : 'text-slate-900 dark:text-white')}>
                {plan.name}
              </h3>
              <div className="mt-4 flex items-baseline gap-1">
                <span className={'text-4xl font-bold ' + (plan.highlight ? 'text-white' : 'text-slate-900 dark:text-white')}>
                  {plan.price}
                </span>
                <span className={plan.highlight ? 'text-white/70' : 'text-slate-500'}>{plan.period}</span>
              </div>
              <p className={'mt-3 text-sm ' + (plan.highlight ? 'text-white/80' : 'text-slate-600 dark:text-slate-300')}>
                {plan.desc}
              </p>
              <ul className="mt-6 space-y-3">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2">
                    <Check size={18} className={plan.highlight ? 'text-yellow-300 mt-0.5' : 'text-primary-600 mt-0.5'} />
                    <span className={'text-sm ' + (plan.highlight ? 'text-white' : 'text-slate-700 dark:text-slate-200')}>
                      {f}
                    </span>
                  </li>
                ))}
              </ul>
              <Link
                to="/app"
                className={
                  'mt-8 block w-full text-center py-2.5 rounded-lg font-medium transition ' +
                  (plan.highlight
                    ? 'bg-white text-slate-900 hover:bg-slate-100'
                    : 'bg-slate-900 dark:bg-primary-600 text-white hover:opacity-90')
                }
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
