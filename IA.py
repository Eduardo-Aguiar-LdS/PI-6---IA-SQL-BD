from langchain_ollama import OllamaLLM
import sqlite3

# Conecta ao banco
conn = sqlite3.connect("./db/biblioteca.sqlite")
cursor = conn.cursor()

# Pega o schema
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
schema = "\n".join([row[0] for row in cursor.fetchall() if row[0]])

# Inicializa os dois modelos
# llm_sql = OllamaLLM(model="prem-research/prem-1b-sql-fp16:latest") # Faz o SQL
llm_sql = OllamaLLM(model="llama3.2")
llm_texto = OllamaLLM(model="llama3.2") # Explica o SQL em português
llm_resultado = OllamaLLM(model="llama3.2") # Explica o resultado

pergunta = "Qual o escritor com mais livros na bilbioteca?"

# 1. GERA O SQL (com o Prem)
prompt_sql = f"""Given the following SQLite database schema:
{schema}

Generate only the SQL query to answer this question (no explanation) do not limit the result:
{pergunta}"""

sql = llm_sql.invoke(prompt_sql).strip()

# 2. EXECUTA NO BANCO
try:
    cursor.execute(sql)
    resultado = cursor.fetchall()
except Exception as e:
    resultado = f"Erro: {e}"

# 3. EXPLICA O SQL GERADO (com o Llama 3.2)
prompt_explicacao = f"""Você é um analista de banco de dados.
Explique de forma curta e simples, em português, o que o comando SQL abaixo faz.

Comando SQL:
{sql}

Responda apenas com a explicação, sem enrolação."""

explicacao = llm_texto.invoke(prompt_explicacao).strip()

# 4. Explica o resultado da query
prompt_resultado = f"""
    Explique de forma objetiva, clara e simples, em português a resposta gerada pela execução, bom base no schema do banco: {schema}

    resposta: {resultado}
"""

resultado_explicado = llm_texto.invoke(prompt_resultado).strip()

# 4. MOSTRA TUDO
print("=" * 50)
print("SQL GERADO:")
print(sql)
print("-" * 50)
print("RESULTADO DO BANCO:")
print(resultado)
print("-" * 50)
print("O QUE ESTA QUERY FAZ:")
print(explicacao)
print("=" * 50)
print("EXPLICAÇÃO DO RESULTADO:")
print(resultado_explicado)
print("=" * 50)

conn.close()