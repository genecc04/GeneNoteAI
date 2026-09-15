import os
from django.shortcuts import render, get_object_or_404
from dotenv import load_dotenv
from google import genai
from google.genai import types
from .models import ChatSession, ChatMessage

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def chat_view(request, session_id=None):
    if session_id:
        session = get_object_or_404(ChatSession, id=session_id)
    else:
        session = ChatSession.objects.create(title="New Chat")

    if request.method == "POST":
        user_text = request.POST.get("message")

        ChatMessage.objects.create(session=session, role="user", content=user_text)

        past_messages = session.messages.order_by("created_at")
        history = [
            types.Content(role=msg.role, parts=[types.Part(text=msg.content)])
            for msg in past_messages
        ]

        chat = client.chats.create(model="gemini-3.6-flash", history=history[:-1])
        response = chat.send_message(user_text)

        ChatMessage.objects.create(session=session, role="model", content=response.text)

    messages = session.messages.order_by("created_at")
    return render(request, "notes/chat.html", {"session": session, "messages": messages})