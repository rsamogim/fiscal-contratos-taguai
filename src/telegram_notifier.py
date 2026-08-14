import os
from datetime import datetime

import requests

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
LIMITE_CARACTERES = 4096
PORTAL_CONTRATOS_URL = "http://portal.taguai.sp.gov.br:5656/transparencia/?AcessoIndividual=lnkContratos"

NOME_CAMPO = {
    "valcon": "Valor do contrato",
    "vigenf": "Vigência final",
    "vencimento_atual": "Vencimento atual",
    "aditado": "Valor aditivado",
}


def escapar_html(texto) -> str:
    if texto is None:
        return ""
    texto = str(texto)
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def formatar_valor(valor_str) -> str:
    if not valor_str:
        return "não informado"
    try:
        valor = float(str(valor_str).replace(",", "."))
    except ValueError:
        return escapar_html(valor_str)
    inteiro, decimal = f"{valor:,.2f}".split(".")
    inteiro = inteiro.replace(",", ".")
    return f"R$ {inteiro},{decimal}"


def formatar_data(data_str) -> str:
    if not data_str:
        return "não informada"
    for formato in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(data_str, formato).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return escapar_html(data_str)


def _truncar(texto: str) -> str:
    if len(texto) <= LIMITE_CARACTERES:
        return texto
    return texto[: LIMITE_CARACTERES - 1] + "…"


def montar_mensagem_novo_contrato(contrato: dict) -> str:
    linhas = [
        "🆕 <b>Novo Contrato — Prefeitura de Taguaí</b>",
        "",
        f"📋 Contrato: {escapar_html(contrato['codigo'])}",
        f"🏢 Fornecedor: {escapar_html(contrato['fornecedor'])} "
        f"(CNPJ/CPF: {escapar_html(contrato['documento_fornecedor'])})",
        f"📝 Objeto: {escapar_html(contrato['objeto'])}",
        f"💰 Valor: {formatar_valor(contrato['valcon'])}",
        f"📅 Assinatura: {formatar_data(contrato['dtassi'])}",
        f"⏳ Vigência: {formatar_data(contrato['vigeni'])} até {formatar_data(contrato['vigenf'])}",
        f"⚖️ Modalidade: {escapar_html(contrato['modalidade'])} ({escapar_html(contrato['fundamento_legal'])})",
        f"📂 Processo: {escapar_html(contrato['processo'])}",
        "",
        f"🔗 {PORTAL_CONTRATOS_URL}",
    ]
    return _truncar("\n".join(linhas))


def montar_mensagem_contrato_atualizado(contrato: dict, mudancas: list[tuple[str, str, str]]) -> str:
    linhas = [
        "📝 <b>Contrato Atualizado (Aditivo/Retificação) — Prefeitura de Taguaí</b>",
        "",
        f"📋 Contrato: {escapar_html(contrato['codigo'])}",
        f"🏢 Fornecedor: {escapar_html(contrato['fornecedor'])} "
        f"(CNPJ/CPF: {escapar_html(contrato['documento_fornecedor'])})",
        f"📝 Objeto: {escapar_html(contrato['objeto'])}",
        "",
        "🔄 <b>O que mudou:</b>",
    ]
    for campo, antigo, novo in mudancas:
        rotulo = NOME_CAMPO.get(campo, campo)
        if campo in ("valcon", "aditado"):
            antigo_fmt, novo_fmt = formatar_valor(antigo), formatar_valor(novo)
        elif campo in ("vigenf", "vencimento_atual"):
            antigo_fmt, novo_fmt = formatar_data(antigo), formatar_data(novo)
        else:
            antigo_fmt, novo_fmt = escapar_html(antigo), escapar_html(novo)
        linhas.append(f"• {rotulo}: {antigo_fmt} → {novo_fmt}")
    linhas += [
        "",
        f"💰 Valor atual do contrato: {formatar_valor(contrato['valcon'])}",
        f"⏳ Vigência atual: {formatar_data(contrato['vigeni'])} até {formatar_data(contrato['vigenf'])}",
        "",
        f"🔗 {PORTAL_CONTRATOS_URL}",
    ]
    return _truncar("\n".join(linhas))


def enviar_mensagem(texto: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    resp = requests.post(
        TELEGRAM_API_URL.format(token=token),
        json={"chat_id": chat_id, "text": texto, "parse_mode": "HTML"},
        timeout=30,
    )
    resp.raise_for_status()
