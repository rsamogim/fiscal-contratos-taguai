import os
from datetime import datetime, timezone

import database
import taguai_client
import telegram_notifier

ANOS_RETROATIVOS = int(os.environ.get("ANOS_RETROATIVOS", "2"))


def main():
    database.init_db()

    ano_atual = datetime.now().year
    anos = list(range(ano_atual - ANOS_RETROATIVOS, ano_atual + 1))
    contratos_brutos = taguai_client.buscar_contratos_dos_anos(anos)
    now_iso = datetime.now(timezone.utc).isoformat()

    # O parâmetro "Ano" do portal não filtra estritamente por ano de assinatura (contratos
    # com vigência plurianual aparecem em várias consultas de Ano), então deduplicamos por
    # chave antes de processar.
    contratos_por_chave = {}
    for contrato in contratos_brutos:
        contratos_por_chave[contrato["chave"]] = contrato

    novos = 0
    atualizados = 0

    with database.get_connection() as conn:
        primeira_execucao = database.is_empty(conn)

        for contrato in contratos_por_chave.values():
            existing = database.get_contrato(conn, contrato["chave"])

            if existing is None:
                database.upsert_contrato(conn, contrato, now_iso)
                conn.commit()
                if not primeira_execucao:
                    telegram_notifier.enviar_mensagem(
                        telegram_notifier.montar_mensagem_novo_contrato(contrato)
                    )
                    novos += 1
            else:
                mudancas = database.campos_alterados(existing, contrato)
                if mudancas:
                    database.upsert_contrato(conn, contrato, now_iso)
                    conn.commit()
                    if not primeira_execucao:
                        telegram_notifier.enviar_mensagem(
                            telegram_notifier.montar_mensagem_contrato_atualizado(contrato, mudancas)
                        )
                        atualizados += 1

    print(
        f"Execução concluída. Anos verificados: {anos}. "
        f"Baseline (sem alertas): {primeira_execucao}. "
        f"Contratos lidos: {len(contratos_brutos)} (únicos: {len(contratos_por_chave)}). "
        f"Novos: {novos}. Atualizados: {atualizados}."
    )


if __name__ == "__main__":
    main()
