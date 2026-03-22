-- =============================================================
-- Zion Delivery Cliente – Script de criação das tabelas
-- Database: zion
-- =============================================================

USE zion;

-- Pedidos de delivery
CREATE TABLE IF NOT EXISTS tb_pedido_delivery (
    NUMERO_PEDIDO      INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    NOME_CLIENTE       VARCHAR(100) NOT NULL,
    CPF_CLIENTE        VARCHAR(20)  DEFAULT '',
    TELEFONE_CLIENTE   VARCHAR(20)  DEFAULT '',
    RUA                VARCHAR(200) NOT NULL,
    NUMERO             VARCHAR(20)  NOT NULL,
    COMPLEMENTO        VARCHAR(100) DEFAULT '',
    CEP                VARCHAR(10)  NOT NULL,
    BAIRRO             VARCHAR(100) NOT NULL,
    CIDADE             VARCHAR(100) NOT NULL,
    UF                 CHAR(2)      NOT NULL,
    OBS_ENTREGADOR     VARCHAR(255) DEFAULT '',
    OBS_PEDIDO         VARCHAR(255) DEFAULT '',
    TAXA_ENTREGA       DECIMAL(10,2) DEFAULT 0.00,
    TOTAL_PRODUTOS     DECIMAL(10,2) NOT NULL,
    TOTAL_PEDIDO       DECIMAL(10,2) NOT NULL,
    FORMA_PAGAMENTO    VARCHAR(20)  NOT NULL,   -- CARTAO | DINHEIRO | PIX
    TROCO_PARA         DECIMAL(10,2) DEFAULT 0.00,
    STATUS_PEDIDO      TINYINT      NOT NULL DEFAULT 0,
    -- 0=Aguardando, 1=Aceito, 2=Em preparo, 3=Saiu, 4=Entregue, 99=Cancelado
    ORIGEM             VARCHAR(50)  DEFAULT 'Delivery próprio',
    DATA_HORA          DATETIME     NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Itens dos pedidos de delivery
CREATE TABLE IF NOT EXISTS tb_item_pedido_delivery (
    ID_ITEM            INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    NUMERO_PEDIDO      INT          NOT NULL,
    ID_PRODUTO         INT          NOT NULL,
    DESCRICAO_PRODUTO  VARCHAR(200) NOT NULL,
    ID_GRADE           INT          DEFAULT NULL,
    QTDE               INT          NOT NULL DEFAULT 1,
    PRECO_UNITARIO     DECIMAL(10,2) NOT NULL,
    TOTAL_ITEM         DECIMAL(10,2) NOT NULL,
    OBS_ITEM           VARCHAR(255) DEFAULT '',
    FOREIGN KEY (NUMERO_PEDIDO) REFERENCES tb_pedido_delivery(NUMERO_PEDIDO)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_pedido_delivery_status
    ON tb_pedido_delivery (STATUS_PEDIDO, DATA_HORA);

CREATE INDEX idx_item_pedido_delivery_numero
    ON tb_item_pedido_delivery (NUMERO_PEDIDO);
