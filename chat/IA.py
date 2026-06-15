from langchain_ollama import OllamaLLM
import sqlite3
import re
from pathlib import Path


VERSION = "0.2.3"
DB_PATH = "./db/biblioteca.sqlite"
MODEL_SQL = "prem-research/prem-1b-sql-fp16:latest"
EXEMPLOS_GERAIS_PATH = "./exemplos.txt"
COMANDOS_BLOQUEADOS = {
    "insert", "update", "delete", "drop", "alter", "truncate",
    "create", "replace", "attach", "detach", "pragma", "reindex",
    "vacuum"
}


def limpar_sql(texto: str) -> str:
    texto = texto.strip()
    texto = re.sub(r"^```sql\s*", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"^```", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"```", "", texto, flags=re.IGNORECASE)
    texto = texto.strip()
    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
    texto = "\n".join(linhas)
    match = re.search(r"(?is)\b(SELECT|WITH)\b[\s\S]*", texto)
    if match:
        texto = match.group(0).strip()
    if ";" in texto:
        texto = texto.split(";")[0].strip() + ";"
    else:
        texto = texto.rstrip() + ";"
    return texto


def sql_valido(sql: str) -> tuple[bool, str]:
    sql_limpo = sql.strip().lower()
    if not sql_limpo.startswith(("select", "with")):
        return False, "O SQL não começa com SELECT ou WITH."
    palavras = set(re.findall(r"\b[a-z_]+\b", sql_limpo))
    perigosos = palavras.intersection(COMANDOS_BLOQUEADOS)
    if perigosos:
        return False, f"Comando perigoso detectado: {', '.join(sorted(perigosos))}."
    if ";" in sql_limpo[:-1]:
        return False, "Mais de um comando SQL detectado."
    return True, "OK"


def obter_schema(cursor) -> str:
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL;")
    return "\n\n".join(row[0] for row in cursor.fetchall())


def obter_mapa_colunas(cursor) -> str:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tabelas = [row[0] for row in cursor.fetchall()]

    partes = []
    for tabela in tabelas:
        cursor.execute(f"PRAGMA table_info({tabela});")
        colunas = [row[1] for row in cursor.fetchall()]
        partes.append(f"{tabela}: {', '.join(colunas)}")

    return "\n".join(partes)


def carregar_arquivo_texto(caminho: str) -> str:
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            return arquivo.read().strip()
    except FileNotFoundError:
        return ""


def obter_exemplos_bd_path(db_path: str) -> str:
    return str(Path(db_path).with_suffix(".txt"))


def montar_exemplos_prompt(exemplos_bd: str, exemplos_gerais: str) -> str:
    partes = []

    if exemplos_bd:
        partes.append("Examples specific to this database:\n" + exemplos_bd)

    if exemplos_gerais:
        partes.append("General examples:\n" + exemplos_gerais)

    return "\n\n".join(partes)


def gerar_sql(llm_sql, schema: str, mapa_colunas: str, pergunta: str, exemplos: str = "") -> str:
    prompt = f"""
You are an expert SQLite query generator.

Your task is to convert a natural language question into exactly one valid SQLite read-only query.

Rules:
- Output only SQL.
- Do not explain anything.
- Do not use markdown.
- Start directly with SELECT or WITH.
- Generate exactly one query.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, PRAGMA or any write command.
- Use only tables and columns that exist in the schema.
- Never invent table names or column names.
- Prefer the simplest correct query.
- Return only the columns necessary to answer the question.
- If the question asks for count, quantity, total, average, minimum, maximum, least, most, highest or lowest, use explicit aggregates when appropriate.
- If the question asks for the most or least frequent item, prefer returning both the item and COUNT(*) AS quantidade.
- If a JOIN is necessary, use it only when the schema supports it clearly.
- If the question is ambiguous, choose the safest interpretation based only on the schema.
- Never use generic column names like id, user_id, author_id, category_id or book_id unless they exist exactly in the schema.
- In this database, prefer exact names such as id_usuario, id_autor, id_categoria, id_livro and id_emprestimo when present.
- Primary keys in this database are named with prefixes like id_usuario, id_livro, id_autor, id_categoria and id_emprestimo.
- Never replace an existing schema column with a generic alias like id.
- Before writing SQL, match every referenced column to the column map.

Examples:
{exemplos}

Schema:
{schema}

Column map:
{mapa_colunas}

Question:
{pergunta}

SQL:
"""
    return llm_sql.invoke(prompt).strip()


def regenerar_sql_com_erro(llm_sql, schema: str, mapa_colunas: str, pergunta: str, sql_anterior: str, erro: str, exemplos: str = "") -> str:
    prompt = f"""
You are an expert SQLite query generator.

Your task is to correct an invalid SQLite query based on the real schema and the database error.

Rules:
- Output only SQL.
- Do not explain anything.
- Do not use markdown.
- Start directly with SELECT or WITH.
- Generate exactly one query.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, PRAGMA or any write command.
- Use only tables and columns that exist in the schema.
- Never invent table names or column names.
- Fix the query based on the reported database error.
- Prefer the simplest correct query.
- Never use generic column names like id, user_id, author_id, category_id or book_id unless they exist exactly in the schema.
- In this database, prefer exact names such as id_usuario, id_autor, id_categoria, id_livro and id_emprestimo when present.
- Primary keys in this database are named with prefixes like id_usuario, id_livro, id_autor, id_categoria and id_emprestimo.
- Never replace an existing schema column with a generic alias like id.
- Before writing SQL, match every referenced column to the column map.

Examples:
{exemplos}

Schema:
{schema}

Column map:
{mapa_colunas}

Question:
{pergunta}

Previous invalid SQL:
{sql_anterior}

Database error:
{erro}

Corrected SQL:
"""
    return llm_sql.invoke(prompt).strip()


def executar_sql_readonly(cursor, sql: str):
    cursor.execute("PRAGMA query_only = ON;")
    cursor.execute(sql)
    colunas = [desc[0] for desc in cursor.description] if cursor.description else []
    linhas = cursor.fetchall()
    return colunas, linhas


def montar_resposta_direta(colunas, linhas):
    if not linhas:
        return "Nenhum resultado encontrado."

    if len(linhas) == 1 and len(colunas) == 1:
        return f"Resposta: {linhas[0][0]}"

    if len(linhas) == 1:
        pares = [f"{col}: {valor}" for col, valor in zip(colunas, linhas[0])]
        return "Resposta: " + ", ".join(pares)

    resultados = []
    limite = min(len(linhas), 5)

    for i, linha in enumerate(linhas[:limite], start=1):
        pares = [f"{col}: {valor}" for col, valor in zip(colunas, linha)]
        resultados.append(f"{i}) " + ", ".join(pares))

    return "Resultados encontrados:\n" + "\n".join(resultados)


def loop_perguntas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    schema = obter_schema(cursor)
    mapa_colunas = obter_mapa_colunas(cursor)
    exemplos_bd_path = obter_exemplos_bd_path(DB_PATH)
    exemplos_bd = carregar_arquivo_texto(exemplos_bd_path)
    exemplos_gerais = carregar_arquivo_texto(EXEMPLOS_GERAIS_PATH)
    exemplos = montar_exemplos_prompt(exemplos_bd, exemplos_gerais)
    llm_sql = OllamaLLM(model=MODEL_SQL)

    print("=" * 70)
    print(f"IA SQL v{VERSION} pronta. Faça perguntas sobre o banco em linguagem natural.")
    print("Digite 'sair' para encerrar.")
    print("=" * 70)

    try:
        while True:
            pergunta = input("\nPergunta: ").strip()

            if not pergunta:
                print("Digite uma pergunta válida.")
                continue

            if pergunta.lower() in {"sair", "exit", "quit"}:
                print("Encerrando.")
                break

            try:
                sql_bruto = gerar_sql(llm_sql, schema, mapa_colunas, pergunta, exemplos)
                sql = limpar_sql(sql_bruto)
                valido, motivo = sql_valido(sql)

                if not valido:
                    print("\n" + "-" * 70)
                    print("SQL BLOQUEADO:")
                    print(sql)
                    print(f"Motivo: {motivo}")
                    print("-" * 70)
                    continue

                try:
                    colunas, linhas = executar_sql_readonly(cursor, sql)
                except Exception as e_exec:
                    erro_execucao = str(e_exec)

                    if "no such column" in erro_execucao.lower() or "no such table" in erro_execucao.lower():
                        sql_bruto = regenerar_sql_com_erro(
                            llm_sql,
                            schema,
                            mapa_colunas,
                            pergunta,
                            sql,
                            erro_execucao,
                            exemplos
                        )
                        sql = limpar_sql(sql_bruto)
                        valido, motivo = sql_valido(sql)

                        if not valido:
                            print("\n" + "-" * 70)
                            print("SQL REGERADO BLOQUEADO:")
                            print(sql)
                            print(f"Motivo: {motivo}")
                            print("-" * 70)
                            continue

                        colunas, linhas = executar_sql_readonly(cursor, sql)
                    else:
                        raise

                resposta = montar_resposta_direta(colunas, linhas)

                print("\n" + "-" * 70)
                print("SQL EXECUTADO:")
                print(sql)
                print("-" * 70)
                print("RESPOSTA:")
                print(resposta)
                print("-" * 70)

            except Exception as e:
                print("\nErro ao processar a pergunta:")
                print(str(e))

    finally:
        conn.close()


if __name__ == "__main__":
    loop_perguntas()