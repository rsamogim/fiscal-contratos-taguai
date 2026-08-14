import os

import requests

BASE_URL = os.environ.get(
    "TAGUAI_PORTAL_BASE_URL",
    "http://portal.taguai.sp.gov.br:5656/transparencia/VersaoJson/LicitacoesEContratos/",
)
ENTIDADE = os.environ.get("TAGUAI_PORTAL_EMPRESA", "1")
TIMEOUT_SEGUNDOS = 30


def buscar_contratos_do_ano(ano: int) -> list[dict]:
    """Busca todos os contratos de um ano no Portal da Transparência de Taguaí.

    O endpoint não pagina: retorna o ano inteiro em uma única chamada.
    """
    params = {
        "ConectarExercicio": ano,
        "Listagem": "Contratos",
        "Ano": ano,
        "Empresa": ENTIDADE,
        "MostraDadosConsolidado": "False",
        "ContratosApenasPublicados": "False",
    }
    resp = requests.get(BASE_URL, params=params, timeout=TIMEOUT_SEGUNDOS)
    resp.raise_for_status()
    dados = resp.json()
    return [normalizar_contrato(item) for item in dados]


def buscar_contratos_dos_anos(anos: list[int]) -> list[dict]:
    contratos = []
    for ano in anos:
        contratos.extend(buscar_contratos_do_ano(ano))
    return contratos


def normalizar_contrato(item: dict) -> dict:
    """Reduz o registro cru do portal (chaves em maiúsculas) para os campos usados no projeto."""
    codtce = item.get("CODTCE") or ""
    codigo = item.get("CODIGO") or ""
    ano = item.get("ANO") or ""
    # Nem todo contrato tem CODTCE preenchido (ex: contratos de rateio/consórcio que não
    # vão a registro no TCE-SP). Nesses casos usamos codigo+ano como chave alternativa em
    # vez de descartar o contrato do monitoramento.
    chave = codtce if codtce else f"SEMCODTCE-{codigo}-{ano}"
    return {
        "chave": chave,
        "codtce": codtce,
        "codigo": codigo,
        "ano": ano,
        "fornecedor": item.get("FORNECEDOR"),
        "documento_fornecedor": item.get("INSMF"),
        "objeto": item.get("OBJETO_COMPLETO") or item.get("OBJETO"),
        "valcon": item.get("VALCON"),
        "dtassi": item.get("DTASSI"),
        "vigeni": item.get("VIGENI"),
        "vigenf": item.get("VIGENF"),
        "vencimento_atual": item.get("VENCIMENTO_ATUAL"),
        "aditado": item.get("ADITADO"),
        "modalidade": item.get("MODALI"),
        "fundamento_legal": item.get("FUNDLEGAL"),
        "processo": item.get("PROCLIC"),
    }
