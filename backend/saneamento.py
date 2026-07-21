"""
Saneamento e validação robusta de datasets antes da regressão.

Garante que o motor nunca receba dados inválidos: converte para numérico,
detecta texto/faltantes/colunas constantes e devolve mensagens claras
(em PT-BR) em vez de deixar estourar um erro 500.
"""

import math
from typing import Any, Dict, List, Tuple

import numpy as np


class DadosInvalidos(ValueError):
    """Erro de dados com mensagem amigável ao usuário."""


def _to_float(v: Any):
    """Tenta converter para float. Retorna None se vazio/inválido."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return None if (isinstance(v, float) and math.isnan(v)) else float(v)
    s = str(v).strip()
    if s == "":
        return None
    # aceita vírgula decimal (pt-BR)
    s = s.replace(".", "").replace(",", ".") if s.count(",") == 1 and s.count(".") > 1 else s.replace(",", ".")
    try:
        f = float(s)
        return None if math.isnan(f) or math.isinf(f) else f
    except (ValueError, TypeError):
        return "INVALIDO"


def sanear_dataset(
    dados: List[Dict[str, Any]],
    variavel_dependente: str,
    variaveis_independentes: List[str],
    min_por_variavel: int = 2,
) -> Tuple[List[Dict[str, float]], List[str]]:
    """
    Valida e limpa o dataset.

    Regras:
    - Todas as colunas necessárias devem existir.
    - Valores são convertidos para número (aceita vírgula decimal).
    - Linhas com valor faltante/texto nas colunas usadas são descartadas (com aviso).
    - Precisa sobrar nº mínimo de amostras: 3*(k+1)+1 não é exigido aqui,
      mas ao menos k+2 para o OLS rodar.
    - Nenhuma coluna independente pode ser constante (quebra a regressão).

    Returns:
        (dados_limpos, avisos)

    Raises:
        DadosInvalidos: com mensagem clara se algo impedir o cálculo.
    """
    if not dados:
        raise DadosInvalidos("Nenhuma amostra foi enviada.")

    colunas = [variavel_dependente, *variaveis_independentes]

    # 1. Colunas presentes
    faltando = [c for c in colunas if c not in dados[0]]
    if faltando:
        raise DadosInvalidos(f"Colunas ausentes nos dados: {', '.join(faltando)}.")

    if not variaveis_independentes:
        raise DadosInvalidos("Defina ao menos uma variável independente.")

    k = len(variaveis_independentes)
    minimo = k + 2

    # 2. Converter e filtrar linhas
    limpos: List[Dict[str, float]] = []
    descartadas = 0
    invalidos_por_coluna: Dict[str, int] = {c: 0 for c in colunas}

    for linha in dados:
        registro: Dict[str, float] = {}
        ok = True
        for c in colunas:
            val = _to_float(linha.get(c))
            if val is None or val == "INVALIDO":
                invalidos_por_coluna[c] += 1
                ok = False
            else:
                registro[c] = val
        if ok:
            limpos.append(registro)
        else:
            descartadas += 1

    avisos: List[str] = []
    if descartadas:
        cols_ruins = [c for c, n in invalidos_por_coluna.items() if n]
        avisos.append(
            f"{descartadas} amostra(s) descartada(s) por valor vazio ou não-numérico "
            f"(colunas: {', '.join(cols_ruins)})."
        )

    # 3. Amostras suficientes
    if len(limpos) < minimo:
        raise DadosInvalidos(
            f"Amostras válidas insuficientes: {len(limpos)} (mínimo {minimo} para "
            f"{k} variável(is)). Verifique valores vazios ou em formato de texto."
        )

    # 4. Colunas constantes (quebram o OLS)
    for c in variaveis_independentes:
        valores = np.array([r[c] for r in limpos], dtype=float)
        if np.all(valores == valores[0]):
            raise DadosInvalidos(
                f"A variável '{c}' tem o mesmo valor em todas as amostras — "
                "não é possível usá-la na regressão. Remova-a ou varie os dados."
            )

    dep_vals = np.array([r[variavel_dependente] for r in limpos], dtype=float)
    if np.all(dep_vals == dep_vals[0]):
        raise DadosInvalidos(
            f"A variável dependente '{variavel_dependente}' é constante — "
            "não há variação de preço para explicar."
        )

    return limpos, avisos


def num_seguro(x: Any, casas: int = 6, default=0.0):
    """Converte para float arredondado, trocando NaN/inf pelo default (JSON-safe)."""
    try:
        f = float(x)
        if math.isnan(f) or math.isinf(f):
            return default
        return round(f, casas)
    except (ValueError, TypeError):
        return default
