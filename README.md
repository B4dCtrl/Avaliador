# Avaliador

Plataforma completa de avaliação imobiliária por inferência estatística (regressão linear múltipla — OLS) com conformidade **NBR 14653-02**.

## Recursos

### Backend (FastAPI)
- **5 endpoints**: `/health`, `/api/calcular-regressao`, `/api/bestfit`, `/api/exportar-word`, `/api/exportar-pdf`
- **7 transformações** de variáveis (`nenhuma`, `log`, `raiz_quadrada`, `raiz_reciproca`, `reciproca`, `reciproca_quadrada`, `quadrada`) + aliases compatíveis com `appraiseR`
- **Auto-ranking** (`/api/bestfit`): testa cartesianamente as transformações em todas as variáveis (dep + indep) e ordena por AIC
- **Diagnósticos avançados**: Shapiro-Wilk, Jarque-Bera, Breusch-Pagan, Cook's Distance, Durbin-Watson
- **NBR completa**: amplitude do IC, grau de precisão (I/II/III), campo de arbítrio, grau de fundamentação
- **Export**: Word (.docx) e PDF com tabelas formatadas e gráficos
- **36 testes pytest** verdes

### Frontend (React + Vite + TypeScript + Tailwind + Plotly)
- Upload de CSV (Papaparse)
- Configuração de variáveis e transformações a testar
- Visualização do melhor modelo, ranking, diagnósticos
- Gráficos interativos: resíduos × ajustados, Q-Q plot, barras de resíduo
- Dark mode
- Export Word/PDF integrado

## Stack
- Python 3.11+ (testado em 3.13), FastAPI, statsmodels, numpy, pandas, scipy, python-docx, reportlab, matplotlib
- Node 20+, React 18, Vite 6, TypeScript 5, TailwindCSS 3, Plotly.js, Papaparse

## Estrutura
```
Avaliador/
├── backend/
│   ├── main.py              FastAPI app
│   ├── calculadora.py       OLS, transformações, elasticidade
│   ├── bestfit.py           auto-ranking por AIC
│   ├── diagnosticos.py      Shapiro/JB/BP/Cook's
│   ├── nbr_grau.py          grau de precisão e fundamentação
│   ├── validador.py         checklist NBR 14653-02
│   ├── exportador.py        DOCX e PDF
│   ├── graficos.py          PNG para os laudos
│   ├── models.py            Pydantic
│   └── tests/               36 testes
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api.ts
│   │   └── components/      ConfigPanel, ResultsPanel, Charts
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Como rodar (dev local)

### Backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload
# API em http://localhost:8000
# Swagger em http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# UI em http://localhost:5173 (proxy /api → 8000)
```

## Como rodar (Docker)
```bash
docker compose up --build
# UI em http://localhost (80)
# API em http://localhost:8000
```

## Testes
```bash
cd backend
python -m pytest tests/ -v
```

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET  | `/health` | Health check |
| POST | `/api/calcular-regressao` | OLS com transformações escolhidas pelo usuário |
| POST | `/api/bestfit` | Auto-ranking de modelos por AIC + diagnóstico completo |
| POST | `/api/exportar-word` | Gera laudo DOCX |
| POST | `/api/exportar-pdf`  | Gera laudo PDF |

## Status

- Repositório público: [B4dCtrl/Avaliador](https://github.com/B4dCtrl/Avaliador)
- 36/36 testes passando
- Backend testado em produção local com R²=0.989 em dataset real
- Frontend buildando sem erros (45 módulos)
