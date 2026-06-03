"""Pydantic schemas para o projeto Avaliador."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums / Literais
# ---------------------------------------------------------------------------

TRANSFORMACOES_VALIDAS = [
    "nenhuma",
    "raiz_reciproca",
    "log",
    "raiz_quadrada",
    "reciproca",
    "reciproca_quadrada",
    "quadrada",
]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class VariavelIndependente(BaseModel):
    valores: List[float]
    transformacao: str = "nenhuma"

    @field_validator("transformacao")
    @classmethod
    def transformacao_valida(cls, v: str) -> str:
        if v not in TRANSFORMACOES_VALIDAS:
            raise ValueError(
                f"Transformação '{v}' inválida. Use: {TRANSFORMACOES_VALIDAS}"
            )
        return v


class DadosRegressao(BaseModel):
    variavel_dependente: str
    valores_dependentes: List[float] = Field(..., min_length=4)
    variaveis_independentes: Dict[str, VariavelIndependente]

    @field_validator("variaveis_independentes")
    @classmethod
    def ao_menos_uma_variavel(cls, v: dict) -> dict:
        if not v:
            raise ValueError("É necessário ao menos uma variável independente.")
        return v


class DadosRegressaoRequest(BaseModel):
    dados: DadosRegressao


class ImovelInfo(BaseModel):
    endereco: str
    area_terreno: Optional[float] = None
    area_construida: Optional[float] = None
    data_avaliacao: str
    finalidade: Optional[str] = None


class AvaliadorInfo(BaseModel):
    nome: str
    crea: str
    empresa: Optional[str] = None


class ExportarRequest(BaseModel):
    resultado_regressao: Dict[str, Any]
    imovel: ImovelInfo
    avaliador: AvaliadorInfo


# Bestfit / auto-ranking

class BestfitRequest(BaseModel):
    """Modo dataset: cliente envia linha-por-linha + variáveis a usar."""
    dados: List[Dict[str, Any]]
    variavel_dependente: str
    variaveis_independentes: List[str]
    transformacoes_testar: List[str] = ["nenhuma", "log", "raiz_quadrada", "raiz_reciproca"]
    excluir_indices: List[int] = []
    nivel_confianca: float = Field(default=0.80, ge=0.50, le=0.99)
    top_n: int = 20


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class CoeficienteResponse(BaseModel):
    variavel: str
    transformacao: str
    coeficiente: float
    elasticidade: float
    t_calculado: float
    p_valor: float
    significancia_percent: float
    erro_padrao: float
    intervalo_confianca_95: List[float]


class RegressaoStats(BaseModel):
    r_squared: float
    r_ajustado: float
    f_calculado: float
    p_valor_f: float
    durbin_watson: float
    desvio_padrao: float
    observacoes: int
    variaveis: int


class OutliersInfo(BaseModel):
    detectados: int
    percentual: float
    indices: List[int]
    residuos_standardizados: List[float]


class ValidacaoNBR(BaseModel):
    ok: bool
    avisos: List[str]
    erros: List[str]


class GraficosResponse(BaseModel):
    residuos_vs_predito: Dict[str, List[float]]
    qq_plot: Dict[str, List[float]]
    scatter_por_variavel: Dict[str, Any]


class RegressaoResponse(BaseModel):
    status: str
    regressao: RegressaoStats
    coeficientes: List[CoeficienteResponse]
    intercepto: float
    correlacao_matrix: Dict[str, Any]
    outliers: OutliersInfo
    validacao_nbr: ValidacaoNBR
    graficos: GraficosResponse


class ExportarResponse(BaseModel):
    status: str
    arquivo: str
    tamanho_kb: float
    url_download: str
