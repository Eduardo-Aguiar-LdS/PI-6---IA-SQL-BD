import json, random
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import ChatSession, Message

AI_RESPONSES = [
    "Analisando sua solicitação... Com base nos dados fornecidos, posso identificar padrões relevantes. Gostaria que eu aprofundasse algum aspecto específico?",
    "Ótima pergunta. Para responder com precisão, vou cruzar as métricas disponíveis. Aqui está um resumo preliminar dos pontos críticos encontrados.",
    "Processando os dados. A correlação entre as variáveis indica uma tendência consistente. Recomendo focar nos segmentos com maior variância.",
    "Entendido. Com esse contexto adicional, a análise fica mais precisa. Os dados apontam para oportunidades claras de otimização.",
    "Baseado nos padrões históricos, posso projetar três cenários possíveis. Qual deles você gostaria de explorar com mais profundidade?",
]

USER = {'name': 'Eduardo Aguiar', 'initials': 'EA', 'role': 'Estagiário', 'email': 'eduardo@email.com'}

def index(request):
    sessions = ChatSession.objects.filter(is_highlighted=False)
    highlighted = ChatSession.objects.filter(is_highlighted=True)
    active_session = sessions.first()
    messages = active_session.messages.all() if active_session else []
    return render(request, 'chat/index.html', {
        'sessions': sessions, 'highlighted': highlighted,
        'active_session': active_session, 'messages': messages, 'user': USER,
    })

def session_detail(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    sessions = ChatSession.objects.filter(is_highlighted=False)
    highlighted = ChatSession.objects.filter(is_highlighted=True)
    return render(request, 'chat/index.html', {
        'sessions': sessions, 'highlighted': highlighted,
        'active_session': session, 'messages': session.messages.all(), 'user': USER,
    })

@csrf_exempt
@require_http_methods(["POST"])
def send_message(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    data = json.loads(request.body)
    user_text = data.get('message', '').strip()
    if not user_text:
        return JsonResponse({'error': 'Empty'}, status=400)
    Message.objects.create(session=session, role='user', content=user_text)
    ai_text = random.choice(AI_RESPONSES)
    ai_msg = Message.objects.create(session=session, role='ai', content=ai_text)
    session.save()
    return JsonResponse({'ai_message': ai_text, 'timestamp': ai_msg.created_at.strftime('%H:%M')})

@csrf_exempt
@require_http_methods(["POST"])
def new_session(request):
    data = json.loads(request.body)
    title = data.get('title', 'Novo chat')
    session = ChatSession.objects.create(title=title)
    Message.objects.create(session=session, role='ai',
        content=f'Olá, {USER["name"]}! Estou pronto para ajudar. Como posso auxiliar você hoje?')
    return JsonResponse({'session_id': session.id, 'title': session.title})

@csrf_exempt
@require_http_methods(["POST"])
def toggle_highlight(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    session.is_highlighted = not session.is_highlighted
    session.save()
    return JsonResponse({'is_highlighted': session.is_highlighted})

@csrf_exempt
@require_http_methods(["POST"])
def delete_session(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    session.delete()
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(["POST"])
def rename_session(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    data = json.loads(request.body)
    title = data.get('title', '').strip()
    if title:
        session.title = title
        session.save()
    return JsonResponse({'title': session.title})

def settings_page(request):
    sessions = ChatSession.objects.filter(is_highlighted=False)
    highlighted = ChatSession.objects.filter(is_highlighted=True)
    active_session = sessions.first()
    return render(request, 'chat/settings.html', {
        'user': USER,
        'active_session': active_session,
    })


@csrf_exempt
@require_http_methods(["POST"])
def save_settings(request):
    data = json.loads(request.body)
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
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