from langchain_ollama import OllamaLLM
import sqlite3
import re

VERSION = "0.2.1"
DB_PATH = "./db/biblioteca.sqlite"
MODEL_SQL = "prem-research/prem-1b-sql-fp16:latest"
MODEL_TEXT = "llama3.2"
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
    return "\n".join(row[0] for row in cursor.fetchall())


def gerar_sql(llm_sql, schema: str, pergunta: str) -> str:
    prompt = f"""
You are a SQLite SQL generator.
Return exactly one valid SQLite query.

Rules:
- Output only SQL.
- Do not explain anything.
- Do not use markdown.
- Start directly with SELECT or WITH.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, PRAGMA or any write command. 
- Use only tables and columns that exist in the schema.
- Return a read-only query.
- When aggregating, alias the column as 'total' (e.g. COUNT(*) AS total, AVG(...) AS total).

Schema:
{schema}

Question:
{pergunta}
"""
    return llm_sql.invoke(prompt).strip()


def executar_sql_readonly(cursor, sql: str):
    cursor.execute("PRAGMA query_only = ON;")
    cursor.execute(sql)
    colunas = [desc[0] for desc in cursor.description] if cursor.description else []
    linhas = cursor.fetchall()
    return colunas, linhas


def explicar_sql_curto(sql: str) -> str:
    sql_lower = sql.lower()
    if "count(" in sql_lower and "group by" in sql_lower and "order by" in sql_lower and "asc" in sql_lower:
        return "Essa consulta agrupa os registros, conta quantos existem em cada grupo e retorna o grupo com a menor quantidade."
    if "count(" in sql_lower and "group by" in sql_lower and "order by" in sql_lower and "desc" in sql_lower:
        return "Essa consulta agrupa os registros, conta quantos existem em cada grupo e retorna o grupo com a maior quantidade."
    if "count(" in sql_lower and "group by" in sql_lower:
        return "Essa consulta agrupa os registros e conta quantos existem em cada grupo."
    if "avg(" in sql_lower:
        return "Essa consulta calcula uma média com base nos dados do banco."
    if "sum(" in sql_lower:
        return "Essa consulta soma valores do banco e retorna o total calculado."
    if sql_lower.startswith("select"):
        return "Essa consulta lê dados do banco e retorna o resultado que melhor responde à pergunta feita."
    return "Consulta SQL de leitura executada no banco."


def montar_resposta_direta(pergunta: str, colunas, linhas):
    if not linhas:
        return "Nenhum resultado encontrado."

    # 1 linha, 1 coluna → valor único direto
    if len(linhas) == 1 and len(linhas[0]) == 1:
        valor = linhas[0][0]
        return f"Resultado: {valor}"

    # 1 linha, 2 colunas → item + quantidade (padrão de COUNT/GROUP BY)
    if len(linhas) == 1 and len(linhas[0]) == 2:
        valor, quantidade = linhas[0]
        col_nome = colunas[1].lower() if len(colunas) >= 2 else "quantidade"
        return f"Resultado principal: **{valor}** — {col_nome}: {quantidade}"

    # Poucas linhas → deixa pro LLM explicar melhor
    return None


def explicar_resultado_llm(llm_texto, pergunta: str, colunas, linhas) -> str:
    prompt = f"""
Responda em português, de forma objetiva e fiel, com base apenas no resultado abaixo.
Não invente informação.
Não contradiga o resultado.
Se houver informação suficiente, responda diretamente.
Se não houver, diga claramente que não há informação suficiente.

Pergunta:
{pergunta}

Colunas:
{colunas}

Linhas:
{linhas}

Responda em no máximo 3 linhas.
"""
    return llm_texto.invoke(prompt).strip()


def perguntar_novamente() -> bool:
    while True:
        resposta = input("Deseja tentar gerar o SQL novamente? (s/n): ").strip().lower()
        if resposta in {"s", "sim"}:
            return True
        if resposta in {"n", "nao", "não"}:
            return False
        print("Resposta inválida. Digite 's' para sim ou 'n' para não.")


def loop_perguntas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    schema = obter_schema(cursor)
    llm_sql = OllamaLLM(model=MODEL_SQL)
    llm_texto = OllamaLLM(model=MODEL_TEXT)

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

            while True:
                try:
                    sql_bruto = gerar_sql(llm_sql, schema, pergunta)
                    sql = limpar_sql(sql_bruto)
                    valido, motivo = sql_valido(sql)

                    if not valido:
                        print("\n" + "-" * 70)
                        print("SQL BLOQUEADO:")
                        print(sql)
                        print(f"Motivo: {motivo}")
                        print("-" * 70)
                        if perguntar_novamente():
                            continue
                        break

                    colunas, linhas = executar_sql_readonly(cursor, sql)
                    explicacao = explicar_sql_curto(sql)
                    resposta_final = montar_resposta_direta(pergunta, colunas, linhas)
                    if resposta_final is None:
                        resposta_final = explicar_resultado_llm(llm_texto, pergunta, colunas, linhas)

                    print("\n" + "-" * 70)
                    print("SQL EXECUTADO:")
                    print(sql)

                    # Para voltar a mostrar o SQL bruto do modelo, descomente as 3 linhas abaixo:
                    # print("-" * 70)
                    # print("SQL BRUTO DO MODELO:")
                    # print(sql_bruto)

                    print("-" * 70)
                    print("COLUNAS:")
                    print(colunas)
                    print("-" * 70)
                    print("RESULTADO:")
                    print(linhas)
                    print("-" * 70)
                    print("O QUE ESTA QUERY FAZ:")
                    print(explicacao)
                    print("-" * 70)
                    print("RESPOSTA FINAL:")
                    print(resposta_final)
                    print("-" * 70)
                    break
                except Exception as e:
                    print("Erro ao processar a pergunta:")
                    print(str(e))
                    if perguntar_novamente():
                        continue
                    break
    finally:
        conn.close()


if __name__ == "__main__":
    loop_perguntas()