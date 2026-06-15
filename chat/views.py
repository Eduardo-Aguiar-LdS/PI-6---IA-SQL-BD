import json
import datetime
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import ChatSession, Message

from pathlib import Path
import sqlite3
from langchain_ollama import OllamaLLM
from .IA import (
    limpar_sql, sql_valido, obter_schema, obter_mapa_colunas,
    carregar_arquivo_texto, obter_exemplos_bd_path,
    montar_exemplos_prompt, gerar_sql, regenerar_sql_com_erro,
    executar_sql_readonly, montar_resposta_direta
)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = str(BASE_DIR / "db" / "biblioteca.sqlite")
EXEMPLOS_GERAIS_PATH = str(BASE_DIR / "exemplos.txt")
MODEL_SQL = "prem-research/prem-1b-sql-fp16:latest"

def _get_ia_recursos():
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    schema          = obter_schema(cursor)
    mapa_colunas    = obter_mapa_colunas(cursor)
    exemplos_bd     = carregar_arquivo_texto(obter_exemplos_bd_path(DB_PATH))
    exemplos_gerais = carregar_arquivo_texto(EXEMPLOS_GERAIS_PATH)
    exemplos        = montar_exemplos_prompt(exemplos_bd, exemplos_gerais)
    llm_sql         = OllamaLLM(model=MODEL_SQL)
    return conn, cursor, schema, mapa_colunas, exemplos, llm_sql

def _consultar_ia(pergunta: str) -> str:
    conn, cursor, schema, mapa_colunas, exemplos, llm_sql = _get_ia_recursos()
    try:
        sql_bruto = gerar_sql(llm_sql, schema, mapa_colunas, pergunta, exemplos)
        sql = limpar_sql(sql_bruto)
        valido, motivo = sql_valido(sql)
        if not valido:
            return f"Não foi possível gerar uma consulta válida: {motivo}"
        try:
            colunas, linhas = executar_sql_readonly(cursor, sql)
        except Exception as e_exec:
            erro = str(e_exec)
            if "no such column" in erro.lower() or "no such table" in erro.lower():
                sql_bruto = regenerar_sql_com_erro(
                    llm_sql, schema, mapa_colunas, pergunta, sql, erro, exemplos
                )
                sql = limpar_sql(sql_bruto)
                valido, motivo = sql_valido(sql)
                if not valido:
                    return f"Não foi possível corrigir a consulta: {motivo}"
                colunas, linhas = executar_sql_readonly(cursor, sql)
            else:
                return f"Erro ao executar a consulta: {erro}"
        return montar_resposta_direta(colunas, linhas)
    finally:
        conn.close()

USER = {'name': 'Eduardo Aguiar', 'initials': 'EA', 'role': 'Estagiário', 'email': 'eduardo@email.com'}

def index(request):
    return render(request, 'chat/index.html', {'user': USER})

def settings_page(request):
    return render(request, 'chat/settings.html', {'user': USER})

@csrf_exempt
@require_http_methods(["POST"])
def perguntar(request):
    data = json.loads(request.body)
    user_text = data.get('message', '').strip()
    if not user_text:
        return JsonResponse({'error': 'Empty'}, status=400)
    try:
        ai_text = _consultar_ia(user_text)
    except Exception as e:
        ai_text = f"Erro interno: {str(e)}"
    now = datetime.datetime.now()
    return JsonResponse({'ai_message': ai_text, 'timestamp': now.strftime('%H:%M')})

@csrf_exempt
@require_http_methods(["POST"])
def save_settings(request):
    data     = json.loads(request.body)
    name     = data.get('name', '').strip()
    email    = data.get('email', '').strip()
    password = data.get('password')
    if name:
        USER['name'] = name
        parts = name.split()
        USER['initials'] = (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else parts[0][:2].upper()
    if email:
        USER['email'] = email
    if password:
        USER['password'] = password
    return JsonResponse({'ok': True, 'initials': USER['initials']})

@csrf_exempt
@require_http_methods(["POST"])
def delete_account(request):
    USER.update({'name': 'Usuário', 'initials': 'US', 'email': '', 'role': 'Estagiário'})
    return JsonResponse({'ok': True})