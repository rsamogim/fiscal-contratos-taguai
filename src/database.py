import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "contratos.db"

# Campos cuja mudança caracteriza aditivo/retificação. EMPENHADO e LIQUIDADO
# não entram aqui porque mudam a cada pagamento normal (execução orçamentária),
# não representam alteração contratual.
TRACKED_FIELDS = ["valcon", "vigenf", "vencimento_atual", "aditado"]


@contextmanager
def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contratos_notificados (
                chave TEXT PRIMARY KEY,
                codtce TEXT,
                codigo TEXT NOT NULL,
                ano TEXT NOT NULL,
                valcon TEXT,
                vigenf TEXT,
                vencimento_atual TEXT,
                aditado TEXT,
                data_primeiro_alerta TEXT NOT NULL,
                data_ultima_atualizacao TEXT NOT NULL
            )
            """
        )


def is_empty(conn) -> bool:
    row = conn.execute("SELECT COUNT(*) AS n FROM contratos_notificados").fetchone()
    return row["n"] == 0


def get_contrato(conn, chave: str):
    return conn.execute(
        "SELECT * FROM contratos_notificados WHERE chave = ?", (chave,)
    ).fetchone()


def upsert_contrato(conn, contrato: dict, now_iso: str):
    existing = get_contrato(conn, contrato["chave"])
    if existing is None:
        conn.execute(
            """
            INSERT INTO contratos_notificados
                (chave, codtce, codigo, ano, valcon, vigenf, vencimento_atual, aditado,
                 data_primeiro_alerta, data_ultima_atualizacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contrato["chave"],
                contrato["codtce"],
                contrato["codigo"],
                contrato["ano"],
                contrato["valcon"],
                contrato["vigenf"],
                contrato["vencimento_atual"],
                contrato["aditado"],
                now_iso,
                now_iso,
            ),
        )
    else:
        conn.execute(
            """
            UPDATE contratos_notificados
               SET codtce = ?, codigo = ?, ano = ?, valcon = ?, vigenf = ?,
                   vencimento_atual = ?, aditado = ?, data_ultima_atualizacao = ?
             WHERE chave = ?
            """,
            (
                contrato["codtce"],
                contrato["codigo"],
                contrato["ano"],
                contrato["valcon"],
                contrato["vigenf"],
                contrato["vencimento_atual"],
                contrato["aditado"],
                now_iso,
                contrato["chave"],
            ),
        )


def campos_alterados(existing_row, contrato: dict) -> list[tuple[str, str, str]]:
    """Retorna lista de (campo, valor_antigo, valor_novo) para os campos rastreados que mudaram."""
    mudancas = []
    for campo in TRACKED_FIELDS:
        antigo = existing_row[campo] or ""
        novo = contrato[campo] or ""
        if antigo != novo:
            mudancas.append((campo, antigo, novo))
    return mudancas
