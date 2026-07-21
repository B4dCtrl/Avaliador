import { GraduationCap, PlayCircle, FileText, BookOpen } from 'lucide-react'

const TRILHAS = [
  { icon: <BookOpen size={20} />, titulo: 'NBR 14653 na prática', desc: 'Graus de fundamentação e precisão, campo de arbítrio.', tag: 'Norma' },
  { icon: <FileText size={20} />, titulo: 'Montando a amostra', desc: 'Como escolher comparáveis e registrar a fonte.', tag: 'Dados' },
  { icon: <PlayCircle size={20} />, titulo: 'Regressão linear passo a passo', desc: 'Transformações, R², resíduos e diagnóstico.', tag: 'Estatística' },
  { icon: <GraduationCap size={20} />, titulo: 'Arbitrando o valor', desc: 'Quando aceitar grau II e definir o valor final.', tag: 'Avançado' },
]

export default function Aprender() {
  return (
    <div className="p-6 max-w-5xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Aprender</h1>
        <p className="text-sm text-slate-500">Trilhas curtas para dominar a avaliação e a norma.</p>
      </div>

      <div className="text-[12px] bg-blue-50 border border-blue-200 text-blue-700 rounded-lg px-3 py-2">
        🖼️ <b>Pré-visualização</b> — conteúdo das trilhas será adicionado em seguida.
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {TRILHAS.map((t) => (
          <div key={t.titulo} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer flex gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">{t.icon}</div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-slate-800">{t.titulo}</h3>
                <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">{t.tag}</span>
              </div>
              <p className="text-xs text-slate-500 mt-1">{t.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
