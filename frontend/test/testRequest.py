import base64
import requests

imgBase64 = ""
urlDelivery = "https://ziondelivery.app.br/"

byte1 = None

with open('C:/Projetos/Zion_PDV_Nativo/frontend/img/Bohemia350ml.jpg', 'rb') as fi:
    byte1 = fi.read()

imgBase64 = base64.b64encode(byte1).decode("utf-8")

dados = {
    "DESCRICAO_PRODUTO": "BOHEMIA 350ML PACK DE 24 UNIDADES",
    "PRECO_DELIVERY": 88.50,
    "PRODUTO_ATIVO": 1,
    "FOTO_PRODUTO": imgBase64
}

result = requests.patch(
    url=f"{urlDelivery}produtos/5736",
    json=dados
)

print(result.status_code, result.text)

# dados = {
#     "CODIGO_PRODUTO": "P1426",
#     "CODIGO_PRODUTO_PDV": "65874442355",
#     "DESCRICAO_PRODUTO": "Cachaça Pinhalzinho",
#     "PRECO_BALCAO": 18.50,
#     "PRECO_DELIVERY": 18.50,
#     "ID_TRIBUTO": 1,
#     "ID_FAMILIA": 1
# }

# urlDelivery = "https://ziondelivery.app.br/"
# #urlDelivery = "http://127.0.0.1:8000/"

# result = requests.post(
#     url=f"{urlDelivery}produtos",
#     json=dados
# )

# print(result.status_code, result.text)

# dados = {
#     "PRODUTO_ATIVO": 0
# }

# urlDelivery = "https://ziondelivery.app.br/"
# #urlDelivery = "http://127.0.0.1:8000/"

# result = requests.patch(
#     url=f"{urlDelivery}produtos/{6989}/ativo",
#     json=dados
# )

# print(result.status_code, result.text)

# urlDelivery = "https://ziondelivery.app.br/"

# result = requests.get(
#     url=f"{urlDelivery}pedidos/pendentes",
#     json={}
# )

# print(result.status_code, result.text)

# urlDelivery = "https://ziondelivery.app.br/"

# result = requests.get(
#     url=f"{urlDelivery}produtos",
#     json={}
# )

# print(result.status_code, result.text)
