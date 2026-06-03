import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

const FAQ = [
  {
    q: 'Preciso instalar alguma coisa?',
    a: 'Não. O Avaliador roda direto no navegador. Você só precisa subir seu CSV com os dados das amostras.',
  },
  {
    q: 'O laudo segue a NBR 14653-02?',
    a: 'Sim. Calculamos amplitude do intervalo de predição, grau de precisão (I/II/III), campo de arbítrio e grau de fundamentação conforme os critérios da norma.',
  },
  {
    q: 'Posso testar antes de pagar?',
    a: 'Sim — o plano Inicial é gratuito e permite gerar laudos com seus dados reais. Quando precisar de mais volume, é só assinar.',
  },
  {
    q: 'Quais transformações de variável estão disponíveis?',
    a: 'Sete tipos: nenhuma, logaritmo, raiz quadrada, raiz recíproca, recíproca, recíproca quadrada e quadrada. O sistema testa combinações nas variáveis dependente e independentes e indica a melhor.',
  },
  {
    q: 'Quais diagnósticos o sistema entrega?',
    a: 'Shapiro-Wilk e Jarque-Bera para normalidade dos resíduos; Breusch-Pagan para homocedasticidade; Cook’s Distance para identificar pontos influentes; Durbin-Watson para autocorrelação.',
  },
  {
    q: 'Meus dados ficam salvos?',
    a: 'No plano Profissional, sim — você terá um histórico de laudos. No plano Inicial, os dados são processados e descartados em seguida.',
  },
]

export default function FAQSection() {
  const [open, setOpen] = useState<number | null>(0)

  return (
    <section id="faq" className="py-24 px-4 bg-white dark:bg-slate-950">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-sm font-medium text-primary-600 dark:text-primary-400 uppercase tracking-wider">
            FAQ
          </span>
          <h2 className="text-4xl md:text-5xl font-bold text-slate-900 dark:text-white mt-3">
            Perguntas frequentes
          </h2>
        </div>
        <div className="space-y-3">
          {FAQ.map((item, i) => (
            <div
              key={item.q}
              className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 overflow-hidden"
            >
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full flex items-center justify-between gap-3 px-5 py-4 text-left"
              >
                <span className="font-medium text-slate-900 dark:text-white">{item.q}</span>
                <ChevronDown
                  size={20}
                  className={'text-slate-500 transition-transform ' + (open === i ? 'rotate-180' : '')}
                />
              </button>
              {open === i && (
                <div className="px-5 pb-4 text-slate-600 dark:text-slate-300 leading-relaxed">
                  {item.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
