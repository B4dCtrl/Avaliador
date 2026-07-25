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
    # Arbítrio do avaliador: usar este modelo (ranking) em vez do melhor por AIC.
    # Dicionário {variavel: transformacao} igual ao campo "transformacoes" do ranking.
    transformacoes_escolhidas: Optional[Dict[str, str]] = None


class AvaliarImovelRequest(BaseModel):
    """Predição pontual: estima o valor de um imóvel-alvo."""
    dados: List[Dict[str, Any]]
    variavel_dependente: str
    variaveis_independentes: List[str]
    # transformação por variável (inclui a dependente). Ex.: {"preco": "log", "area": "nenhuma"}
    transformacoes: Dict[str, str]
    # valores do imóvel a avaliar. Ex.: {"area": 130, "distancia": 800}
    imovel_alvo: Dict[str, float]
    excluir_indices: List[int] = []
    nivel_confianca: float = Field(default=0.80, ge=0.50, le=0.99)


# ---------------------------------------------------------------------------
# Comparáveis (comps) — busca por similaridade. Isolado do motor de avaliação.
# ---------------------------------------------------------------------------

class PerfilTerritorial(BaseModel):
    """Indicadores socioeconômicos/urbanos de uma região (bases públicas)."""
    idh: Optional[float] = None
    renda_per_capita: Optional[float] = None
    densidade_populacional: Optional[float] = None
    escolaridade_media_anos: Optional[float] = None
    indice_seguranca: Optional[float] = None      # 0–10 (maior = mais seguro)
    infraestrutura: Optional[float] = None        # 0–10
    distancia_centro_km: Optional[float] = None


class PerfilImovel(BaseModel):
    """Perfil técnico do imóvel de referência."""
    tipo_imovel: Optional[str] = None
    finalidade: Optional[str] = None
    zoneamento: Optional[str] = None
    area_terreno: Optional[float] = None
    area_construida: Optional[float] = None
    idade: Optional[float] = None
    padrao_construtivo: Optional[str] = None
    conservacao: Optional[str] = None
    dormitorios: Optional[float] = None
    banheiros: Optional[float] = None
    vagas: Optional[float] = None
    endereco: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None


class CandidatoComparavel(PerfilImovel):
    """Imóvel candidato encontrado, com dados de anúncio e região."""
    identificacao: Optional[str] = None
    fonte: Optional[str] = None            # link de verificação
    preco: Optional[float] = None
    data_anuncio: Optional[str] = None
    distancia_km: Optional[float] = None
    perfil_territorial: Optional[PerfilTerritorial] = None


class ComparaveisRequest(BaseModel):
    alvo: PerfilImovel
    candidatos: List[CandidatoComparavel]
    perfil_territorial_alvo: Optional[PerfilTerritorial] = None
    minimo_similaridade: float = Field(default=0.0, ge=0.0, le=100.0)


class ViabilidadeRequest(BaseModel):
    """Análise de viabilidade de investimento imobiliário."""
    valor_mercado: float = Field(..., gt=0)
    preco_compra: float = Field(..., gt=0)
    custos_aquisicao: float = 0.0
    custos_reforma: float = 0.0
    aluguel_mensal: Optional[float] = None
    despesas_mensais: float = 0.0
    valorizacao_anual_pct: float = 0.0
    horizonte_anos: float = Field(default=5.0, gt=0, le=50)
    custo_venda_pct: float = 6.0


class AnalisarAmostrasRequest(BaseModel):
    """Detecta outliers/amostras atípicas considerando o imóvel-alvo."""
    dados: List[Dict[str, Any]]
    variavel_dependente: str
    variaveis_independentes: List[str]
    transformacoes: Dict[str, str]
    imovel_alvo: Optional[Dict[str, float]] = None
    limiar_residuo: float = 2.0


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
