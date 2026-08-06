"""
Ponte entre o Avaliador e um agente de IA externo (CrewAI ou similar).

Princípio: o agente pode SUGERIR imóveis e escrever texto. Ele nunca decide
número que vai para o laudo. Todo retorno passa por um filtro que:

1. Extrai o JSON (mesmo vindo embrulhado em markdown/texto).
2. Descarta imóveis sem dado verificável (preço, área ou fonte).
3. Recalcula preço/m² a partir de preço e área — nunca aceita o valor do LLM.
4. Rejeita valores implausíveis (área, preço, R$/m² fora de faixa).
5. Deixa o motor determinístico refazer grau NBR, métricas e curadoria.
6. Detecta contradições declaradas pelo agente (ex.: grau III com 0 amostras).

Resultado: se o agente alucinar, o dado inventado é barrado aqui; se ele
acertar, a informação entra já normalizada.
"""

import json
import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Faixas de plausibilidade (Brasil, valores de mercado)
LIMITES_PLAUSIBILIDADE = {
    "area_m2": (10.0, 100_000.0),
    "preco": (5_000.0, 500_000_000.0),
    "preco_m2": (100.0, 100_000.0),
}

CAMPOS_NUMERICOS_PROIBIDOS = (
    # o agente não pode ditar estes: são calculados pelo motor
    "grau_fundamentacao", "grau_precisao", "n_elementos", "metricas_amostra",
    "confiabilidade_busca", "amplitude", "cv", "media_preco_m2", "mediana_preco_m2",
)


def extrair_json(texto: str) -> Optional[Any]:
    """
    Extrai JSON de uma resposta de LLM, tolerando ```json ... ``` e texto ao redor.
    """
    if not texto:
        return None
    if isinstance(texto, (dict, list)):
        return texto

    s = str(texto).strip()

    # bloco markdown
    m = re.search(r"```(?:json)?\s*(.+?)```", s, re.DOTALL)
    if m:
        s = m.group(1).strip()

    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # primeiro objeto/array balanceado
    for abre, fecha in (("{", "}"), ("[", "]")):
        ini = s.find(abre)
        if ini == -1:
            continue
        nivel = 0
        for i in range(ini, len(s)):
            if s[i] == abre:
                nivel += 1
            elif s[i] == fecha:
                nivel -= 1
                if nivel == 0:
                    try:
                        return json.loads(s[ini:i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def _num(x: Any) -> Optional[float]:
    if x is None or x == "":
        return None
    if isinstance(x, (int, float)):
        return float(x) if math.isfinite(float(x)) else None
    s = re.sub(r"[^\d,.\-]", "", str(x))
    if not s:
        return None
    # formato BR: 1.234.567,89
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        v = float(s)
        return v if math.isfinite(v) else None
    except ValueError:
        return None


def _plausivel(valor: Optional[float], faixa: Tuple[float, float]) -> bool:
    return valor is not None and faixa[0] <= valor <= faixa[1]


def filtrar_imoveis(brutos: List[Dict[str, Any]], exigir_fonte: bool = True) -> Dict[str, Any]:
    """
    Aplica o filtro anti-alucinação sobre a lista de imóveis sugerida pelo agente.

    Returns:
        {"aceitos": [...], "rejeitados": [{"motivo", "imovel"}], "resumo": {...}}
    """
    aceitos: List[Dict[str, Any]] = []
    rejeitados: List[Dict[str, Any]] = []

    for i, b in enumerate(brutos or []):
        if not isinstance(b, dict):
            rejeitados.append({"motivo": "registro não é objeto", "imovel": str(b)[:80]})
            continue

        ident = (b.get("endereco") or b.get("identificacao")
                 or b.get("id") or b.get("id_temp") or f"item {i + 1}")

        preco = _num(b.get("preco") or b.get("preco_total") or b.get("valor"))
        area = _num(b.get("area_construida") or b.get("area_m2") or b.get("area"))
        area_terreno = _num(b.get("area_terreno"))
        fonte = (b.get("url") or b.get("fonte") or b.get("link") or "").strip() or None

        # 1. dado verificável
        if exigir_fonte and not fonte:
            rejeitados.append({"motivo": "sem fonte/URL para verificação", "imovel": ident})
            continue
        if fonte and not re.match(r"^https?://", fonte):
            rejeitados.append({"motivo": f"fonte não é URL válida: {fonte[:40]}", "imovel": ident})
            continue

        # 2. plausibilidade
        if not _plausivel(preco, LIMITES_PLAUSIBILIDADE["preco"]):
            rejeitados.append({"motivo": f"preço ausente ou implausível ({preco})", "imovel": ident})
            continue
        area_efetiva = area or area_terreno
        if not _plausivel(area_efetiva, LIMITES_PLAUSIBILIDADE["area_m2"]):
            rejeitados.append({"motivo": f"área ausente ou implausível ({area_efetiva})", "imovel": ident})
            continue

        # 3. preço/m² SEMPRE recalculado — ignora o que o agente escreveu
        preco_m2 = preco / area_efetiva
        if not _plausivel(preco_m2, LIMITES_PLAUSIBILIDADE["preco_m2"]):
            rejeitados.append({
                "motivo": f"preço/m² implausível (R$ {preco_m2:,.0f}/m²)".replace(",", "."),
                "imovel": ident,
            })
            continue

        declarado = _num(b.get("preco_m2"))
        divergencia = None
        if declarado and abs(declarado - preco_m2) / preco_m2 > 0.02:
            divergencia = (f"agente informou R$ {declarado:.2f}/m²; "
                           f"recalculado R$ {preco_m2:.2f}/m²")

        aceitos.append({
            "identificacao": ident,
            "endereco": b.get("endereco") or ident,
            "tipo": b.get("tipo") or b.get("tipo_imovel"),
            "preco": round(preco, 2),
            "area_construida": area,
            "area_terreno": area_terreno,
            "preco_m2": round(preco_m2, 2),
            "quartos": _num(b.get("quartos") or b.get("dormitorios")),
            "banheiros": _num(b.get("banheiros")),
            "vagas": _num(b.get("vagas")),
            "padrao_construtivo": b.get("padrao_construtivo") or b.get("padrao"),
            "bairro": b.get("bairro"),
            "cidade": b.get("cidade"),
            "distancia_km": _num(b.get("distancia_km")),
            "fonte": fonte,
            "fonte_nome": b.get("portal") or b.get("portal_origem") or b.get("fonte_nome"),
            "data_anuncio": b.get("data_coleta") or b.get("data_anuncio"),
            "divergencia_corrigida": divergencia,
        })

    corrigidos = sum(1 for a in aceitos if a["divergencia_corrigida"])
    return {
        "aceitos": aceitos,
        "rejeitados": rejeitados,
        "resumo": {
            "recebidos": len(brutos or []),
            "aceitos": len(aceitos),
            "rejeitados": len(rejeitados),
            "precos_m2_corrigidos": corrigidos,
        },
    }


def detectar_contradicoes(payload: Dict[str, Any]) -> List[str]:
    """
    Aponta afirmações do agente que contradizem os próprios dados.

    Caso clássico: declarar grau de fundamentação III com zero elementos.
    """
    problemas: List[str] = []
    if not isinstance(payload, dict):
        return problemas

    amostra = payload.get("amostra_final") if isinstance(payload.get("amostra_final"), dict) else payload
    elementos = amostra.get("elementos")
    n_declarado = amostra.get("n_elementos")
    grau = str(amostra.get("grau_fundamentacao") or "").strip().upper()

    n_real = len(elementos) if isinstance(elementos, list) else None

    if n_real is not None and n_declarado is not None:
        try:
            if int(n_declarado) != n_real:
                problemas.append(
                    f"n_elementos declarado ({n_declarado}) difere da lista enviada ({n_real})."
                )
        except (TypeError, ValueError):
            problemas.append(f"n_elementos não numérico: {n_declarado!r}.")

    if grau in ("I", "II", "III"):
        efetivo = n_real if n_real is not None else _num(n_declarado)
        if efetivo is not None and efetivo < 5:
            problemas.append(
                f"Agente declarou grau {grau} com apenas {int(efetivo)} elemento(s). "
                "Grau será recalculado pelo motor."
            )

    metricas = amostra.get("metricas_amostra")
    if isinstance(metricas, dict) and n_real == 0:
        if any(v not in (None, "", "null") for v in metricas.values()):
            problemas.append("Métricas preenchidas com amostra vazia.")

    return problemas


def processar_retorno_agente(
    retorno: Any,
    exigir_fonte: bool = True,
) -> Dict[str, Any]:
    """
    Ponto de entrada: recebe o que o agente devolveu (texto, markdown ou dict)
    e devolve candidatos limpos + diagnóstico do filtro.

    Os campos numéricos de laudo são removidos: quem calcula é o motor.
    """
    dados = extrair_json(retorno)
    if dados is None:
        return {
            "status": "erro",
            "erro": "Não foi possível extrair JSON da resposta do agente.",
            "candidatos": [],
            "rejeitados": [],
            "contradicoes": [],
        }

    contradicoes = detectar_contradicoes(dados)

    # localiza a lista de imóveis, aceitando os vários nomes que o agente pode usar
    brutos: List[Dict[str, Any]] = []
    if isinstance(dados, list):
        brutos = dados
    else:
        base = dados.get("amostra_final") if isinstance(dados.get("amostra_final"), dict) else dados
        for chave in ("elementos", "imoveis_normalizados", "imoveis_brutos",
                      "imoveis_comparaveis", "amostras", "candidatos", "imoveis"):
            valor = base.get(chave) if isinstance(base, dict) else None
            if isinstance(valor, list) and valor:
                brutos = valor
                break

    filtro = filtrar_imoveis(brutos, exigir_fonte=exigir_fonte)

    # campos que o agente não pode ditar
    ignorados = [c for c in CAMPOS_NUMERICOS_PROIBIDOS
                 if isinstance(dados, dict) and (c in dados or
                    (isinstance(dados.get("amostra_final"), dict) and c in dados["amostra_final"]))]

    texto = None
    if isinstance(dados, dict):
        texto = dados.get("relatorio") or dados.get("relatorio_tecnico")

    return {
        "status": "sucesso",
        "candidatos": filtro["aceitos"],
        "rejeitados": filtro["rejeitados"],
        "resumo_filtro": filtro["resumo"],
        "contradicoes": contradicoes,
        "campos_ignorados": ignorados,
        "texto_agente": texto,
        "observacao": (
            "Números do laudo (grau, métricas, confiabilidade) são calculados pelo "
            "motor do Avaliador. Valores enviados pelo agente foram ignorados."
        ),
    }
