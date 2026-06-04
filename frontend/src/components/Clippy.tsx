import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, X } from 'lucide-react'

interface Msg { autor: 'voce' | 'assistente'; texto: string }

// Base de conhecimento simples (offline). Casamento por palavras-chave.
const BASE: { chaves: string[]; resposta: string }[] = [
  { chaves: ['csv', 'importar', 'planilha', 'arquivo'], resposta: 'Para importar dados: no Passo 1, clique em "CSV" (substitui tudo) ou "CSV +" (acrescenta). O arquivo precisa ter cabeçalho na 1ª linha (ex.: valor, area, frente).' },
  { chaves: ['exemplo', 'teste', 'testar'], resposta: 'Clique no botão "Exemplo" no Passo 1 para carregar 15 amostras prontas e testar o sistema na hora.' },
  { chaves: ['r2', 'r²', 'r quadrado', 'determinação', 'determinacao'], resposta: 'O R² mede o quanto o modelo explica a variação dos preços (0 a 1). Acima de 0,80 é o recomendado pela NBR 14653-02. Quanto mais perto de 1, melhor.' },
  { chaves: ['transformação', 'transformacao', 'log', 'raiz', 'nenhuma'], resposta: 'Transformações ajustam a relação entre variáveis (ex.: ln(x), 1/x). O Avaliador testa várias combinações automaticamente e escolhe a de melhor ajuste — você não precisa decidir.' },
  { chaves: ['outlier', 'atípic', 'atipic', 'desabilitar', 'desabilita'], resposta: 'No Passo 4, "Desabilitar atípicas" analisa resíduos, distância de Cook e a distância ao imóvel-alvo, e desmarca as amostras fora do padrão. Depois é só calcular de novo.' },
  { chaves: ['fundamentação', 'fundamentacao', 'grau', 'precisão', 'precisao'], resposta: 'O grau de fundamentação (I, II ou III) mede a robustez do laudo conforme a NBR 14653-02 — combina nº de amostras, significância e amplitude. III é o melhor.' },
  { chaves: ['confiança', 'confianca', 'nível', 'nivel'], resposta: 'O nível de confiança padrão é 80% (exigido pela NBR para o grau de fundamentação). Você pode mudar para 90% ou 95% em "Opções avançadas" no Passo 3.' },
  { chaves: ['avaliar', 'imóvel', 'imovel', 'terreno', 'estimar', 'valor'], resposta: 'No Passo 2, preencha as características do imóvel a avaliar (área, frente, etc.). Ao calcular no Passo 3, o valor estimado aparece no Passo 4 com intervalo e campo de arbítrio.' },
  { chaves: ['laudo', 'word', 'pdf', 'exportar', 'imprimir', 'baixar'], resposta: 'No Passo 4, preencha endereço/avaliador/CREA e clique em "Baixar Word" ou "Baixar PDF". O laudo sai conforme a NBR 14653-02.' },
  { chaves: ['variável', 'variavel', 'coluna', 'valor y', 'x'], resposta: 'Cada coluna tem um papel: "Valor (Y)" é o preço a explicar, "Variável (X)" são as características (área, frente...), e "Ignorar" deixa de fora. Defina no cabeçalho da planilha.' },
  { chaves: ['salvar', 'abrir', 'projeto'], resposta: 'Use "Salvar" para guardar no navegador, ou "Salvar como" para baixar um arquivo .json do projeto. "Abrir" carrega um projeto salvo. Tudo é salvo automaticamente também.' },
  { chaves: ['durbin', 'watson', 'resíduo', 'residuo', 'autocorrelação', 'autocorrelacao'], resposta: 'Durbin-Watson detecta autocorrelação dos resíduos (ideal entre 1,5 e 2,5). Você vê o valor no painel de resultados, Passo 4.' },
]

const SAUDACOES = [
  'Oi! Sou o assistente do Avaliador. Posso ajudar?',
  'Precisa de ajuda com a avaliação? É só perguntar!',
  'Dica: comece carregando dados no Passo 1 (botão Exemplo).',
]

function responder(pergunta: string): string {
  const p = pergunta.toLowerCase()
  let melhor: { resposta: string; score: number } | null = null
  for (const item of BASE) {
    const score = item.chaves.reduce((s, c) => (p.includes(c) ? s + 1 : s), 0)
    if (score > 0 && (!melhor || score > melhor.score)) melhor = { resposta: item.resposta, score }
  }
  if (melhor) return melhor.resposta
  return 'Não tenho certeza sobre isso 🤔. Posso ajudar com: importar CSV, transformações, R², outliers, graus de fundamentação, avaliar o imóvel e gerar o laudo. Tente reformular!'
}

interface Props { aberto: boolean; setAberto: (v: boolean) => void; dica?: string }

export default function Clippy({ aberto, setAberto, dica }: Props) {
  const [msgs, setMsgs] = useState<Msg[]>([{ autor: 'assistente', texto: SAUDACOES[0] }])
  const [texto, setTexto] = useState('')
  const fimRef = useRef<HTMLDivElement>(null)
  const [piscar, setPiscar] = useState(false)

  // pisca os olhos periodicamente
  useEffect(() => {
    const t = setInterval(() => { setPiscar(true); setTimeout(() => setPiscar(false), 160) }, 3200)
    return () => clearInterval(t)
  }, [])

  useEffect(() => { fimRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, aberto])

  // dica contextual quando muda de passo
  useEffect(() => {
    if (dica) setMsgs((m) => [...m, { autor: 'assistente', texto: dica }])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dica])

  const enviar = () => {
    const q = texto.trim(); if (!q) return
    setMsgs((m) => [...m, { autor: 'voce', texto: q }])
    setTexto('')
    setTimeout(() => setMsgs((m) => [...m, { autor: 'assistente', texto: responder(q) }]), 350)
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-2">
      <AnimatePresence>
        {aberto && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className="w-[300px] sm:w-[340px] bg-[#fffef2] border-2 border-[#0a4fd6] rounded-lg shadow-2xl overflow-hidden"
          >
            <div className="flex items-center justify-between px-3 py-1.5 bg-gradient-to-b from-[#0a6cff] to-[#0a4fd6] text-white text-[12px] font-semibold">
              Assistente do Avaliador
              <button onClick={() => setAberto(false)} className="hover:bg-white/20 rounded p-0.5"><X size={14} /></button>
            </div>
            <div className="h-[260px] overflow-auto p-2 space-y-2 bg-[#fffdf0]">
              {msgs.map((m, i) => (
                <div key={i} className={`flex ${m.autor === 'voce' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] px-2.5 py-1.5 rounded-lg text-[12px] ${m.autor === 'voce' ? 'bg-[#0a4fd6] text-white' : 'bg-[#fff7c2] text-[#333] border border-[#e6d98a]'}`}>
                    {m.texto}
                  </div>
                </div>
              ))}
              <div ref={fimRef} />
            </div>
            <div className="flex items-center gap-1 p-2 border-t border-[#e6d98a] bg-[#fffef2]">
              <input
                value={texto} onChange={(e) => setTexto(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && enviar()}
                placeholder="Pergunte algo…"
                className="flex-1 px-2 py-1.5 text-[12px] border border-[#bbb] rounded focus:outline-none focus:border-[#0a4fd6]"
              />
              <button onClick={enviar} className="p-1.5 bg-[#0a4fd6] text-white rounded hover:bg-[#0a3fb0]"><Send size={14} /></button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Personagem (clipe animado) */}
      <motion.button
        onClick={() => setAberto(!aberto)}
        title="Assistente"
        animate={{ y: [0, -6, 0], rotate: [0, -3, 3, 0] }}
        transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
        className="w-16 h-20 relative drop-shadow-lg"
      >
        <svg viewBox="0 0 64 80" className="w-full h-full">
          {/* corpo do clipe */}
          <path d="M22 24 C22 12, 42 12, 42 24 L42 58 C42 70, 24 70, 24 58 L24 30 C24 24, 34 24, 34 30 L34 54"
            fill="none" stroke="#9aa7c4" strokeWidth="6" strokeLinecap="round" />
          <path d="M22 24 C22 12, 42 12, 42 24 L42 58 C42 70, 24 70, 24 58 L24 30 C24 24, 34 24, 34 30 L34 54"
            fill="none" stroke="#cdd6e8" strokeWidth="2.5" strokeLinecap="round" />
          {/* olhos */}
          <g>
            <ellipse cx="27" cy="30" rx="6" ry={piscar ? 0.8 : 6} fill="white" stroke="#333" strokeWidth="1.2" />
            <ellipse cx="40" cy="30" rx="6" ry={piscar ? 0.8 : 6} fill="white" stroke="#333" strokeWidth="1.2" />
            {!piscar && <>
              <circle cx="28" cy="31" r="2.4" fill="#222" />
              <circle cx="41" cy="31" r="2.4" fill="#222" />
            </>}
            {/* sobrancelhas */}
            <path d="M22 22 L31 24" stroke="#333" strokeWidth="1.4" strokeLinecap="round" />
            <path d="M36 24 L45 22" stroke="#333" strokeWidth="1.4" strokeLinecap="round" />
          </g>
        </svg>
        {!aberto && (
          <motion.span
            initial={{ scale: 0 }} animate={{ scale: 1 }}
            className="absolute -top-1 -left-1 bg-[#d24] text-white text-[10px] w-4 h-4 rounded-full flex items-center justify-center">?</motion.span>
        )}
      </motion.button>
    </div>
  )
}
