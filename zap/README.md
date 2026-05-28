# Bot de WhatsApp da Loja (MVP)

Este modulo responde automaticamente novos contatos no WhatsApp Web da loja,
incentivando o cliente a acessar o link do delivery.

## Mensagem padrao

O bot envia uma mensagem simples com boas-vindas e link do cardapio.
A mensagem pode ser alterada por variavel de ambiente.

## Como executar (Windows / PowerShell)

1. Ative seu ambiente virtual.
2. Instale as dependencias:

```powershell
pip install -r zap/requirements.txt
```

3. (Opcional) Configure variaveis de ambiente:

```powershell
$env:ZAP_DELIVERY_LINK = "https://lojabeervt.ziondelivery.app.br/"
$env:ZAP_POLL_SECONDS = "6"
$env:ZAP_MIN_SECONDS_BETWEEN_REPLIES = "21600"
```

4. Execute:

```powershell
python -m zap.main
```

5. No primeiro uso, escaneie o QR Code no WhatsApp Web.

## Observacoes importantes

- Este MVP usa automacao de interface (Selenium + WhatsApp Web), portanto
  seletores podem mudar com atualizacoes do WhatsApp.
- Para evitar spam, o bot aplica uma janela de bloqueio por conversa
  (`ZAP_MIN_SECONDS_BETWEEN_REPLIES`).
- Recomenda-se rodar em maquina dedicada para evitar interferencia de uso manual.
