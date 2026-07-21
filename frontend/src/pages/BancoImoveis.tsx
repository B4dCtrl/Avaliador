import { useState } from 'react'
import { Search, Plus, Link2, MapPin, CheckCircle2, Sparkles, Lock, Filter } from 'lucide-react'

/**
 * SKETCH — Banco colaborativo de imóveis verificáveis.
 * Ainda sem backend: mostra a interface pretendida (busca, cadastro com fonte,
 * sugestões para aumentar o grau). Marcado como pré-visualização.
 */
export default function BancoImoveis() {
  const [busca, setBusca] = useState('')
  const [addAberto, setAddAberto] = useState(false)

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            Banco de imóveis <span className="text-[11px] font-bold bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">PREMIUM</span>
          </h1>
          <p className="text-sm text-slate-500">Amostras verificáveis compartilhadas entre avaliadores.</p>
        </div>
        <button onClick={() => setAddAberto(!addAberto)}
          className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm hover:bg-emerald-700 flex items-center gap-1.5">
          <Plus size={16} /> Cadastrar imóvel
        </button>
      </div>

      {/* Aviso de sketch */}
      <div className="text-[12px] bg-blue-50 border border-blue-200 text-blue-700 rounded-lg px-3 py-2">
        🖼️ <b>Pré-visualização</b> — esta é a interface pretendida. O banco de dados e a cobrança ainda serão implementados (Supabase).
      </div>

      {/* Cadastro com fonte */}
      {addAberto && (
        <div className="bg-white border border-emerald-200 rounded-xl p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Novo imóvel verificável</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <Campo label="Endereço / bairro" placeholder="Ex.: Jd. Botânico" />
            <Campo label="Área (m²)" placeholder="360" />
            <Campo label="Valor (R$)" placeholder="540000" />
            <Campo label="Data do anúncio" placeholder="2026-07" />
          </div>
          <div className="mt-3">
            <label className="block text-[11px] text-slate-500 mb-0.5 flex items-center gap-1">
              <Link2 size={12} /> Fonte (link de verificação — anúncio, escritura, portal)
            </label>
            <input placeholder="https://…" className="w-full px-2.5 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:border-emerald-500" />
            <p className="text-[11px] text-slate-400 mt-1">A fonte é o que torna a amostra confiável e reutilizável por outros avaliadores.</p>
          </div>
          <div className="flex gap-2 mt-3">
            <button className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm hover:bg-emerald-700">Salvar no banco</button>
            <button onClick={() => setAddAberto(false)} className="px-4 py-2 rounded-lg text-slate-500 hover:bg-slate-100 text-sm">Cancelar</button>
          </div>
        </div>
      )}

      {/* Busca */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="flex-1 flex items-center gap-2 border border-slate-300 rounded-lg px-3">
            <Search size={16} className="text-slate-400" />
            <input value={busca} onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar por bairro, cidade, faixa de área…"
              className="flex-1 py-2 text-sm focus:outline-none" />
          </div>
          <button className="px-3 py-2 rounded-lg border border-slate-300 text-slate-600 text-sm flex items-center gap-1 hover:bg-slate-50">
            <Filter size={15} /> Filtros
          </button>
        </div>

        {/* Estado vazio (sem backend ainda) */}
        <div className="text-center py-12 text-slate-400">
          <Lock size={38} className="mx-auto mb-2 opacity-40" />
          <p className="text-sm">O banco de imóveis será liberado com a assinatura Premium.</p>
          <p className="text-[12px] mt-1">Aqui aparecerão amostras verificadas, com fonte, prontas para usar na sua avaliação.</p>
        </div>
      </div>

      {/* Sugestão para aumentar o grau */}
      <div className="rounded-xl border border-amber-200 bg-gradient-to-br from-amber-50 to-white p-4">
        <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 mb-2">
          <Sparkles size={16} className="text-amber-600" /> Como o banco aumenta o grau da sua avaliação
        </h3>
        <ul className="text-sm text-slate-600 space-y-1.5">
          <li className="flex gap-2"><CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" /> Você cadastra <b>alguns</b> comparáveis com fonte; o sistema completa com imóveis do banco na mesma região.</li>
          <li className="flex gap-2"><CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" /> Mais amostras válidas → atende o item de <b>quantidade de dados</b> da norma (grau III exige 6·(k+1)).</li>
          <li className="flex gap-2"><CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" /> O sistema sugere: <i>"adicione 4 imóveis próximos para passar de grau II para III"</i>.</li>
          <li className="flex gap-2"><MapPin size={16} className="text-blue-600 shrink-0 mt-0.5" /> Todas as amostras têm <b>fonte verificável</b> — o laudo fica mais defensável.</li>
        </ul>
      </div>
    </div>
  )
}

function Campo({ label, placeholder }: { label: string; placeholder: string }) {
  return (
    <div>
      <label className="block text-[11px] text-slate-500 mb-0.5">{label}</label>
      <input placeholder={placeholder} className="w-full px-2.5 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:border-emerald-500" />
    </div>
  )
}
