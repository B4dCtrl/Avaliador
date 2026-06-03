# Avaliador

Backend para avaliação imobiliária com regressão linear múltipla (OLS), conforme **NBR 14653-02**.

## Stack

- Python 3.11+
- FastAPI + Uvicorn
- statsmodels, numpy, scipy, pandas
- python-docx, reportlab, matplotlib
- Pydantic v2

## Estrutura

```
backend/
├── main.py              # FastAPI app e endpoints
├── calculadora.py       # OLS, transformações, estatísticas
├── validador.py         # Validações NBR 14653-02
├── exportador.py        # Geração Word e PDF
├── graficos.py          # Imagens PNG para laudos
├── models.py            # Pydantic schemas
├── requirements.txt
├── Dockerfile
├── .env.example
└── tests/
    ├── test_transformacoes.py
    ├── test_regressao.py
    └── test_endpoints.py
```

## Instalação e execução

```bash
cd backend

# Instalar dependências
pip install -r requirements.txt

# Rodar o servidor
python -m uvicorn main:app --reload
```

A API estará disponível em `http://localhost:8000`.

Documentação interativa (Swagger): `http://localhost:8000/docs`

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/health` | Health check |
| POST | `/api/calcular-regressao` | Executa regressão OLS com transformações |
| POST | `/api/exportar-word` | Gera laudo em DOCX |
| POST | `/api/exportar-pdf` | Gera laudo em PDF |

## Transformações disponíveis

| Nome | Fórmula |
|------|---------|
| `nenhuma` | y = x |
| `log` | y = ln(x) |
| `raiz_quadrada` | y = √x |
| `raiz_reciproca` | y = 1/√x |
| `reciproca` | y = 1/x |
| `reciproca_quadrada` | y = 1/x² |
| `quadrada` | y = x² |

## Testes

```bash
cd backend
python -m pytest tests/ -v
```

## Docker

```bash
docker build -t avaliador-backend .
docker run -p 8000:8000 avaliador-backend
```

## Exemplo de uso

```bash
curl -X POST http://localhost:8000/api/calcular-regressao \
  -H "Content-Type: application/json" \
  -d '{
    "dados": {
      "variavel_dependente": "preco",
      "valores_dependentes": [150000, 200000, 175000, 220000, 185000],
      "variaveis_independentes": {
        "area_total": {"valores": [100, 150, 120, 160, 130], "transformacao": "nenhuma"},
        "distancia_polo": {"valores": [500, 1000, 800, 1200, 900], "transformacao": "log"}
      }
    }
  }'
```
