import { useState } from 'react'
import { Info } from 'lucide-react'

export interface Explicacao {
  oque: string
  impacto: string
  importancia: string
}

/** Ícone (i) que ao passar o mouse mostra o que é o indicador e seu impacto. */
export default function InfoHint({ titulo, exp }: { titulo: string; exp: Explicacao }) {
  const [aberto, setAberto] = useState(false)
  return (
    <span className="relative inline-flex align-middle"
      onMouseEnter={() => setAberto(true)}
      onMouseLeave={() => setAberto(false)}>
      <Info size={12} className="text-slate-400 hover:text-blue-600 cursor-help" />
      {aberto && (
        <span className="absolute z-30 left-1/2 -translate-x-1/2 bottom-full mb-1.5 w-64 p-2.5 rounded-lg
                         bg-slate-900 text-white text-[11px] leading-snug shadow-xl text-left normal-case font-normal">
          <span className="block font-semibold text-blue-200 mb-1">{titulo}</span>
          <span className="block mb-1"><b className="text-slate-300">O que é:</b> {exp.oque}</span>
          <span className="block mb-1"><b className="text-slate-300">Impacto:</b> {exp.impacto}</span>
          <span className="block"><b className="text-slate-300">Por que importa:</b> {exp.importancia}</span>
          <span className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0
                           border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-slate-900" />
        </span>
      )}
    </span>
  )
}

/** Dicionário central de explicações dos indicadores. */
export const EXPLICACOES: Record<string, Explicacao> = {
  r2: {
    oque: 'Coeficiente de determinação: quanto da variação dos preços o modelo consegue explicar (0 a 1).',
    impacto: 'Quanto mais perto de 1, mais o modelo acompanha os dados reais.',
    importancia: 'A NBR 14653 recomenda modelos com bom poder explicativo; abaixo de 0,80 acende alerta.',
  },
  r2_ajustado: {
    oque: 'R² ajustado pelo número de variáveis — penaliza variáveis que não ajudam.',
    impacto: 'Se cair ao adicionar uma variável, aquela variável provavelmente é inútil.',
    importancia: 'É o R² mais honesto para comparar modelos com quantidades diferentes de variáveis.',
  },
  f: {
    oque: 'Teste F: verifica se o modelo como um todo é estatisticamente significativo.',
    impacto: 'p-valor baixo (< 5%) indica que o conjunto de variáveis realmente explica o preço.',
    importancia: 'É um dos itens do grau de fundamentação (III exige p ≤ 1%, II ≤ 2%, I ≤ 5%).',
  },
  aic_bic: {
    oque: 'Critérios de informação (AIC/BIC): medem o equilíbrio entre ajuste e simplicidade.',
    impacto: 'Menor é melhor — usados para ranquear e escolher o melhor modelo.',
    importancia: 'Ajudam a evitar modelos complexos demais que "decoram" os dados.',
  },
  durbin_watson: {
    oque: 'Durbin-Watson: detecta autocorrelação (dependência) entre os resíduos.',
    impacto: 'Valor ideal entre 1,5 e 2,5. Fora disso, o modelo pode estar mal especificado.',
    importancia: 'Autocorrelação viola as premissas da regressão e enfraquece o laudo.',
  },
  shapiro: {
    oque: 'Shapiro-Wilk: testa se os resíduos seguem distribuição normal.',
    impacto: 'p-valor alto (> 5%) é bom: indica resíduos normais, como a regressão pressupõe.',
    importancia: 'Normalidade dos resíduos valida os intervalos de confiança e a estimativa.',
  },
  jarque_bera: {
    oque: 'Jarque-Bera: outro teste de normalidade dos resíduos (assimetria e curtose).',
    impacto: 'p-valor alto (> 5%) confirma que os resíduos são normais.',
    importancia: 'Reforça a confiabilidade dos intervalos e do valor estimado.',
  },
  breusch_pagan: {
    oque: 'Breusch-Pagan: testa homocedasticidade (variância constante dos resíduos).',
    impacto: 'p-valor alto (> 5%) é bom: a dispersão dos erros é uniforme.',
    importancia: 'Heterocedasticidade distorce os erros-padrão e a significância das variáveis.',
  },
  outliers_cooks: {
    oque: 'Distância de Cook: mede o quanto cada amostra influencia o modelo.',
    impacto: 'Amostras muito influentes podem estar puxando o resultado indevidamente.',
    importancia: 'Identificar e revisar outliers deixa a avaliação mais robusta e defensável.',
  },
  amplitude: {
    oque: 'Amplitude do intervalo de confiança de 80% em torno do valor central.',
    impacto: 'Quanto menor, mais preciso o resultado.',
    importancia: 'Define o grau de precisão (III ≤ 30%, II ≤ 40%, I ≤ 50%).',
  },
  grau_precisao: {
    oque: 'Grau de precisão (NBR 14653): classifica a exatidão do resultado pela amplitude.',
    impacto: 'III é o melhor; abaixo de I o resultado é considerado impreciso.',
    importancia: 'Consta obrigatoriamente no laudo e indica a qualidade da estimativa.',
  },
  grau_fundamentacao: {
    oque: 'Grau de fundamentação (NBR 14653): mede o rigor técnico do trabalho.',
    impacto: 'Combina quantidade de dados, significância das variáveis e do modelo (F).',
    importancia: 'É exigido no laudo; graus mais altos dão mais credibilidade e valor jurídico.',
  },
  campo_arbitrio: {
    oque: 'Campo de arbítrio: faixa de ±15% em torno do valor estimado (NBR 14653-1).',
    impacto: 'Dentro dela o avaliador pode ajustar o valor final com justificativa técnica.',
    importancia: 'Dá flexibilidade ao avaliador sem sair do que a norma considera aceitável.',
  },
  micronumerosidade: {
    oque: 'Micronumerosidade: quantidade mínima de dados para cada característica.',
    impacto: 'Poucos dados em um nível tornam aquele efeito pouco confiável.',
    importancia: 'A norma exige mínimos (n≤30: 3; ≤100: 10%; >100: 10) para o modelo ser válido.',
  },
  poder_predicao: {
    oque: 'Poder de predição: compara valores observados com os estimados pelo modelo.',
    impacto: 'Quanto mais pontos próximos da reta de 45°, melhor a previsão.',
    importancia: 'Mostra na prática o quanto o modelo acerta — evidência forte para o laudo.',
  },
}
