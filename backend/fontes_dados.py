"""
Fontes de dados de imóveis — busca automática por vias legítimas.

Arquitetura de conectores plugáveis. Nenhum conector faz scraping:
todos consomem arquivos/APIs que a própria fonte publica para download.

Conectores nesta versão:
- CaixaImoveis: CSV oficial de imóveis à venda da Caixa Econômica Federal
  (https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_<UF>.csv).
  Traz preço, VALOR DE AVALIAÇÃO, áreas e link do imóvel.

Para adicionar uma fonte nova, implemente `FonteImoveis` e registre em FONTES.
"""

import csv
import io
import logging
import re
import unicodedata
import urllib.request
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)

TIMEOUT = 30


def _normalizar(texto: str) -> str:
    """Minúsculas sem acento, para comparar cidade/bairro."""
    if not texto:
        return ""
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def _num_br(texto: Any) -> Optional[float]:
    """Converte moeda no formato BR: '105.481,84' -> 105481.84."""
    if texto is None:
        return None
    s = str(texto).strip()
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(re.sub(r"[^\d.\-]", "", s))
    except (ValueError, TypeError):
        return None


def _num_decimal(texto: Any) -> Optional[float]:
    """
    Converte números da DESCRIÇÃO da Caixa, que usam ponto como decimal:
    '60.27' -> 60.27 · '1.234.56' é tratado como 1234.56.
    """
    if texto is None:
        return None
    s = re.sub(r"[^\d.]", "", str(texto).strip())
    if not s:
        return None
    # se houver mais de um ponto, só o último é decimal
    partes = s.split(".")
    if len(partes) > 2:
        s = "".join(partes[:-1]) + "." + partes[-1]
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


class FonteImoveis(Protocol):
    """Contrato de um conector de fonte pública."""
    id: str
    nome: str
    descricao: str
    legal: str

    def buscar(self, uf: str, cidade: str, bairro: str = "", limite: int = 200) -> List[Dict[str, Any]]:
        ...


# ---------------------------------------------------------------------------
# Conector: Caixa Econômica Federal (CSV público oficial)
# ---------------------------------------------------------------------------

class CaixaImoveis:
    id = "caixa"
    nome = "Caixa Econômica Federal — imóveis à venda"
    descricao = ("Lista oficial de imóveis da Caixa (retomados/leilão), publicada em CSV "
                 "por UF. Traz preço, valor de avaliação, áreas e link do imóvel.")
    legal = "Arquivo público disponibilizado pela Caixa para download — sem scraping."

    URL = "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.csv"

    # cache simples em memória por UF (evita rebaixar o CSV a cada busca)
    _cache: Dict[str, List[Dict[str, str]]] = {}

    def _baixar(self, uf: str) -> List[Dict[str, str]]:
        uf = uf.strip().upper()
        if uf in self._cache:
            return self._cache[uf]

        url = self.URL.format(uf=uf)
        req = urllib.request.Request(url, headers={"User-Agent": "Avaliador/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            bruto = resp.read()

        texto = bruto.decode("latin-1", errors="replace")
        linhas = texto.split("\n")
        # a linha 3 (índice 2) é o cabeçalho real
        idx_header = next((i for i, l in enumerate(linhas) if "N" in l and "im" in l and ";UF;" in l), 2)
        conteudo = "\n".join(linhas[idx_header:])
        leitor = csv.DictReader(io.StringIO(conteudo), delimiter=";")
        registros = [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in leitor]
        self._cache[uf] = registros
        logger.info("Caixa: %d imóveis carregados para %s", len(registros), uf)
        return registros

    @staticmethod
    def _parse_descricao(desc: str) -> Dict[str, Optional[float]]:
        """Extrai áreas e programa da descrição textual da Caixa."""
        out: Dict[str, Optional[float]] = {
            "area_total": None, "area_privativa": None, "area_terreno": None,
            "quartos": None, "tipo": None,
        }
        if not desc:
            return out
        d = desc.lower()

        # A descrição usa ponto como separador decimal (ex.: "60.27 de área total")
        m = re.search(r"([\d.,]+)\s*de\s*[áa]rea\s*total", d)
        if m:
            out["area_total"] = _num_decimal(m.group(1))
        m = re.search(r"([\d.,]+)\s*de\s*[áa]rea\s*privativa", d)
        if m:
            out["area_privativa"] = _num_decimal(m.group(1))
        m = re.search(r"([\d.,]+)\s*de\s*[áa]rea\s*do\s*terreno", d)
        if m:
            out["area_terreno"] = _num_decimal(m.group(1))
        m = re.search(r"(\d+)\s*(?:qto|quarto|dormit)", d)
        if m:
            out["quartos"] = float(m.group(1))

        for t in ("casa", "apartamento", "terreno", "sobrado", "loja", "sala", "galpao", "galpão"):
            if d.startswith(t) or f"{t}," in d:
                out["tipo"] = "casa" if t == "sobrado" else ("comercial" if t in ("loja", "sala", "galpao", "galpão") else t)
                break
        return out

    def buscar(self, uf: str, cidade: str, bairro: str = "", limite: int = 200) -> List[Dict[str, Any]]:
        """
        Retorna imóveis da Caixa na cidade (e bairro, se informado),
        já no formato de candidato do Comparable Search Engine.
        """
        registros = self._baixar(uf)
        alvo_cidade = _normalizar(cidade)
        alvo_bairro = _normalizar(bairro)

        saida: List[Dict[str, Any]] = []
        for r in registros:
            if _normalizar(r.get("Cidade", "")) != alvo_cidade:
                continue
            b = r.get("Bairro", "")
            if alvo_bairro and alvo_bairro not in _normalizar(b):
                continue

            desc = r.get("Descrição") or r.get("Descri��o") or ""
            areas = self._parse_descricao(desc)
            preco = _num_br(r.get("Preço") or r.get("Pre�o"))
            avaliacao = _num_br(r.get("Valor de avaliação") or r.get("Valor de avalia��o"))

            area = areas["area_privativa"] or areas["area_total"]
            saida.append({
                "identificacao": f"{r.get('Endereço') or r.get('Endere�o') or 'Imóvel'} — {b}".strip(),
                "endereco": r.get("Endereço") or r.get("Endere�o"),
                "tipo": areas["tipo"],
                # usa o valor de AVALIAÇÃO como referência de mercado (não o preço de leilão)
                "preco": avaliacao or preco,
                "preco_leilao": preco,
                "valor_avaliacao": avaliacao,
                "area_construida": area,
                "area_terreno": areas["area_terreno"],
                "quartos": areas["quartos"],
                "bairro": b or None,
                "cidade": r.get("Cidade"),
                "fonte": r.get("Link de acesso") or None,
                "fonte_nome": self.nome,
                "modalidade": r.get("Modalidade de venda"),
                "observacao": ("Valor de avaliação oficial da Caixa. O preço de venda "
                               "costuma ter deságio e não representa valor de mercado."),
            })
            if len(saida) >= limite:
                break
        return saida


# ---------------------------------------------------------------------------
# Registro de fontes
# ---------------------------------------------------------------------------

FONTES: Dict[str, Any] = {
    CaixaImoveis.id: CaixaImoveis(),
}


def listar_fontes() -> List[Dict[str, str]]:
    """Fontes disponíveis e sua base legal."""
    return [
        {"id": f.id, "nome": f.nome, "descricao": f.descricao, "legal": f.legal}
        for f in FONTES.values()
    ]


def buscar_em_fontes(
    uf: str,
    cidade: str,
    bairro: str = "",
    fontes: Optional[List[str]] = None,
    limite: int = 200,
) -> Dict[str, Any]:
    """
    Executa a busca nas fontes selecionadas (todas, por padrão).

    Returns:
        {"candidatos": [...], "por_fonte": {...}, "erros": [...]}
    """
    ids = fontes or list(FONTES.keys())
    candidatos: List[Dict[str, Any]] = []
    por_fonte: Dict[str, int] = {}
    erros: List[Dict[str, str]] = []

    for fid in ids:
        fonte = FONTES.get(fid)
        if not fonte:
            erros.append({"fonte": fid, "erro": "Fonte desconhecida."})
            continue
        try:
            achados = fonte.buscar(uf=uf, cidade=cidade, bairro=bairro, limite=limite)
            candidatos.extend(achados)
            por_fonte[fid] = len(achados)
        except Exception as e:
            logger.warning("Fonte %s falhou: %s", fid, e)
            erros.append({"fonte": fid, "erro": str(e)})
            por_fonte[fid] = 0

    return {"candidatos": candidatos, "por_fonte": por_fonte, "erros": erros}
