# Zion Delivery Cliente

App de delivery para adega de bebidas. Clientes realizam pedidos pelo celular/navegador.

## Estrutura do Projeto

```
Zion_Delivery_Cliente/
├── app.py                    # Frontend (Flet) – ponto de entrada
├── run_backend.py            # Backend (FastAPI) – ponto de entrada
├── requirements_frontend.txt
├── requirements_backend.txt
├── backend/
│   ├── main.py               # Rotas FastAPI
│   ├── cfg/config.py         # Configurações (DB, API)
│   ├── base/
│   │   ├── database.py       # Pool de conexões MySQL
│   │   ├── qBase.py          # Utilitários de query
│   │   └── authentication.py # JWT (PyJWT + Werkzeug)
│   ├── models/               # Dataclasses (Token, Produto, Pedido…)
│   ├── views/                # Handlers de negócio (produto, endereco, pedido)
│   └── migrations/
│       └── create_tables.sql # DDL das tabelas de delivery
└── frontend/
    ├── cfg/config.py         # Config frontend (URL API, cores, caches)
    ├── base/
    │   ├── server.py         # ZionAPI – cliente HTTP (requests)
    │   └── cache.py          # CacheManager – JSON local
    ├── models/               # Dataclasses frontend
    ├── style/zControls.py    # Componentes visuais reutilizáveis
    ├── utils/currency_formatter.py
    ├── data/                 # Cache JSON local (produtos, famílias, grades)
    ├── img/                  # Imagens / logo
    └── views/
        ├── endereco.py       # Tela 1 – Endereço de entrega
        ├── cardapio.py       # Tela 2 – Catálogo de produtos
        ├── cliente.py        # Tela 3 – Dados do cliente + CPF
        ├── pagamento.py      # Tela 4 – Forma de pagamento
        └── confirmacao.py    # Tela 5 – Revisão e envio do pedido
```

## Fluxo de telas

1. **Splash** – Download automático do cardápio da API  
2. **Endereço** – UF → Cidade → Pesquisa de rua (debounce) ou busca por CEP  
3. **Cardápio** – Filtro por família / texto, adicionar/remover itens na sacola  
4. **Cliente** – Nome, telefone, CPF no cupom  
5. **Pagamento** – Cartão / Dinheiro / Pix (com troco opcional)  
6. **Confirmação** – Resumo completo + envio para API + polling de status do pedido  

## Cores

| Elemento | Hex |
|---|---|
| Fundo principal | `#a7b1b6` |
| Fonte / destaque | `#874531` |

## Banco de dados (MySQL – `zion`)

Configurado em `backend/cfg/config.py`:
- host: `localhost:3306`
- user: `root`
- password: `56Runna01`

Tabelas consumidas pela API:
- `tb_produto` · `tb_familia_produto` · `tb_grade_produto`
- `enderecos` (UF, cidade, logradouro, bairro, CEP)

Tabelas criadas para delivery (`backend/migrations/create_tables.sql`):
- `tb_pedido_delivery`
- `tb_item_pedido_delivery`

## Como executar

### Backend (Linux/servidor ou local)
```bash
pip install -r requirements_backend.txt
python run_backend.py
# API disponível em http://localhost:8000
# Documentação: http://localhost:8000/docs
```

### Frontend (web / android via Flet)
```bash
pip install -r requirements_frontend.txt
python app.py
# Abre em http://localhost:8080
```

### Build Android (Flet)
```bash
flet build apk --project "Zion Delivery"
```

## Estratégia de cache de produtos

Ao iniciar, o app tenta:
1. Carregar `frontend/data/produtos.json` (cache local)  
2. Baixar da API `/produtos`, `/familias`, `/grades` e salvar localmente  

Pesquisas de produto são feitas **localmente** (sem rede), pela classe `CacheManager`.

## Estratégia de busca de endereços

A tabela `enderecos` é grande — a pesquisa é feita **sempre via API** com filtro obrigatório por UF + Cidade antes de qualquer busca por texto/CEP, e retorna no máximo 50 resultados por consulta.
