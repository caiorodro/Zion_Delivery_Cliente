-- Otimizacoes para a query get_all_produtos
-- Execute em ambiente de homologacao antes de producao.

USE zion;

-- 1) Produto: acelera o filtro de ativos/preco e ordenacao por descricao.
-- Ajuste para PRECO_BALCAO apenas se sua instancia nao usar PRECO_DELIVERY.
ALTER TABLE tb_produto
    ADD INDEX idx_produto_ativo_preco_desc (PRODUTO_ATIVO, PRECO_DELIVERY, DESCRICAO_PRODUTO, ID_PRODUTO);

-- 2) Pedido delivery: colunas normalizadas para permitir indexacao do CPF/telefone sem REPLACE.
ALTER TABLE tb_pedido_delivery
    ADD COLUMN TELEFONE_CLIENTE_DIGITOS VARCHAR(20)
        GENERATED ALWAYS AS (
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(COALESCE(TELEFONE_CLIENTE, ''), '(', ''), ')', ''), '-', ''), ' ', ''), '+', '')
        ) STORED,
    ADD COLUMN CPF_CLIENTE_DIGITOS VARCHAR(20)
        GENERATED ALWAYS AS (
            REPLACE(REPLACE(REPLACE(REPLACE(COALESCE(CPF_CLIENTE, ''), '.', ''), '-', ''), ' ', ''), '/', '')
        ) STORED;

-- 3) Pedido delivery: indexa busca do ultimo pedido por cliente.
ALTER TABLE tb_pedido_delivery
    ADD INDEX idx_pedido_tel_status_data (TELEFONE_CLIENTE_DIGITOS, STATUS_PEDIDO, DATA_HORA, NUMERO_PEDIDO),
    ADD INDEX idx_pedido_cpf_status_data (CPF_CLIENTE_DIGITOS, STATUS_PEDIDO, DATA_HORA, NUMERO_PEDIDO),
    ADD INDEX idx_pedido_data_status_numero (DATA_HORA, STATUS_PEDIDO, NUMERO_PEDIDO);

-- 4) Itens: acelera agrupamento por produto dentro do pedido e historico 15d.
ALTER TABLE tb_item_pedido_delivery
    ADD INDEX idx_item_pedido_produto_item (NUMERO_PEDIDO, ID_PRODUTO, ID_ITEM),
    ADD INDEX idx_item_produto_pedido (ID_PRODUTO, NUMERO_PEDIDO);

-- 5) Opcional: caso o ambiente use tb_pedido/tb_item_pedido (schema legado),
-- replique os mesmos indices nas tabelas equivalentes.
