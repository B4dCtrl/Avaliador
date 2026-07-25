"""
Análise de viabilidade de investimento imobiliário.

Combina o valor de mercado (estimado pela avaliação) com os dados do negócio
para dizer se o investimento vale a pena — em dois cenários:

1. Renda (locação): rentabilidade mensal/anual, cap rate, payback.
2. Revenda (valorização): lucro, ROI e retorno anualizado.

Nenhuma recomendação é aconselhamento financeiro personalizado — são
indicadores objetivos calculados a partir dos números informados.
"""

import math
from typing import Any, Dict, List, Optional


def _num(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def analisar_viabilidade(
    valor_mercado: float,
    preco_compra: float,
    custos_aquisicao: float = 0.0,   # ITBI, escritura, corretagem
    custos_reforma: float = 0.0,
    aluguel_mensal: Optional[float] = None,
    despesas_mensais: float = 0.0,   # condomínio, IPTU, manutenção, vacância
    valorizacao_anual_pct: float = 0.0,
    horizonte_anos: float = 5.0,
    custo_venda_pct: float = 6.0,    # corretagem na revenda
) -> Dict[str, Any]:
    """
    Calcula indicadores de viabilidade.

    Returns:
        Dicionário com investimento total, cenário de renda, cenário de
        revenda, comparação com o valor de mercado e um veredito.
    """
    valor_mercado = _num(valor_mercado)
    preco_compra = _num(preco_compra)
    investimento_total = preco_compra + _num(custos_aquisicao) + _num(custos_reforma)

    # --- Comparação com o valor de mercado (ganho/desconto na compra) ---
    desconto_valor = valor_mercado - preco_compra
    desconto_pct = (desconto_valor / valor_mercado * 100) if valor_mercado else 0.0
    # patrimônio imediato = valor de mercado - investimento total
    ganho_patrimonial = valor_mercado - investimento_total
    ganho_patrimonial_pct = (ganho_patrimonial / investimento_total * 100) if investimento_total else 0.0

    # --- Cenário de RENDA (locação) ---
    renda = None
    if aluguel_mensal is not None and _num(aluguel_mensal) > 0 and investimento_total > 0:
        aluguel = _num(aluguel_mensal)
        liquido_mensal = aluguel - _num(despesas_mensais)
        yield_bruto_anual = (aluguel * 12) / investimento_total * 100
        yield_liquido_anual = (liquido_mensal * 12) / investimento_total * 100
        # cap rate usa o valor do imóvel (mercado) como base
        cap_rate = (liquido_mensal * 12) / valor_mercado * 100 if valor_mercado else 0.0
        payback_anos = (investimento_total / (liquido_mensal * 12)) if liquido_mensal > 0 else None
        renda = {
            "aluguel_mensal": round(aluguel, 2),
            "liquido_mensal": round(liquido_mensal, 2),
            "yield_bruto_anual_pct": round(yield_bruto_anual, 2),
            "yield_liquido_anual_pct": round(yield_liquido_anual, 2),
            "cap_rate_pct": round(cap_rate, 2),
            "payback_anos": round(payback_anos, 1) if payback_anos else None,
        }

    # --- Cenário de REVENDA (valorização) ---
    revenda = None
    if investimento_total > 0:
        vpct = _num(valorizacao_anual_pct) / 100
        anos = max(0.1, _num(horizonte_anos, 5.0))
        valor_futuro = valor_mercado * ((1 + vpct) ** anos)
        custo_venda = valor_futuro * _num(custo_venda_pct) / 100
        # soma dos aluguéis líquidos no período, se houver locação
        renda_acumulada = 0.0
        if renda:
            renda_acumulada = renda["liquido_mensal"] * 12 * anos
        lucro = (valor_futuro - custo_venda + renda_acumulada) - investimento_total
        roi_total_pct = (lucro / investimento_total * 100)
        # retorno anualizado (CAGR sobre patrimônio final/inicial)
        base_final = investimento_total + lucro
        cagr = ((base_final / investimento_total) ** (1 / anos) - 1) * 100 if investimento_total > 0 and base_final > 0 else 0.0
        revenda = {
            "horizonte_anos": round(anos, 1),
            "valor_futuro_estimado": round(valor_futuro, 2),
            "renda_acumulada": round(renda_acumulada, 2),
            "lucro_liquido": round(lucro, 2),
            "roi_total_pct": round(roi_total_pct, 2),
            "retorno_anualizado_pct": round(cagr, 2),
        }

    # --- Veredito objetivo ---
    pontos = 0
    sinais: List[str] = []
    if desconto_pct >= 5:
        pontos += 1
        sinais.append(f"Compra {desconto_pct:.1f}% abaixo do valor de mercado — bom ponto de entrada.")
    elif desconto_pct <= -5:
        pontos -= 1
        sinais.append(f"Compra {abs(desconto_pct):.1f}% acima do valor de mercado — pagando caro.")
    if renda:
        if renda["yield_liquido_anual_pct"] >= 6:
            pontos += 1
            sinais.append(f"Rentabilidade líquida de {renda['yield_liquido_anual_pct']:.1f}% a.a. — acima do aluguel típico.")
        elif renda["yield_liquido_anual_pct"] < 4:
            pontos -= 1
            sinais.append(f"Rentabilidade líquida de {renda['yield_liquido_anual_pct']:.1f}% a.a. — baixa para locação.")
    if revenda:
        if revenda["retorno_anualizado_pct"] >= 10:
            pontos += 1
            sinais.append(f"Retorno anualizado de {revenda['retorno_anualizado_pct']:.1f}% — atrativo.")
        elif revenda["retorno_anualizado_pct"] < 0:
            pontos -= 1
            sinais.append("Projeção de prejuízo no horizonte informado.")

    if pontos >= 2:
        veredito = "Favorável"
    elif pontos <= -1:
        veredito = "Desfavorável"
    else:
        veredito = "Neutro / analisar"

    return {
        "status": "sucesso",
        "investimento_total": round(investimento_total, 2),
        "valor_mercado": round(valor_mercado, 2),
        "comparacao_mercado": {
            "desconto_valor": round(desconto_valor, 2),
            "desconto_pct": round(desconto_pct, 2),
            "ganho_patrimonial": round(ganho_patrimonial, 2),
            "ganho_patrimonial_pct": round(ganho_patrimonial_pct, 2),
        },
        "renda": renda,
        "revenda": revenda,
        "veredito": veredito,
        "pontuacao": pontos,
        "sinais": sinais,
        "observacao": (
            "Indicadores calculados a partir dos números informados. "
            "Não constituem recomendação personalizada de investimento."
        ),
    }
