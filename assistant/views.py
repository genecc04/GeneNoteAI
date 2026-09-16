import os
from django.shortcuts import render, get_object_or_404, redirect
from dotenv import load_dotenv
from google import genai
from google.genai import types
from .models import ChatSession, ChatMessage, Note

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

def note_create_view(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content", "")
        uploaded_file = request.FILES.get("file")

        note = Note.objects.create(
            title=title,
            content=content,
            file=uploaded_file
        )

        if content:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=f"Summarize the following study notes concisely:\n\n{content}"
            )
            note.summary = response.text
            note.save()

        return redirect("note_detail", note_id=note.id)

    return render(request, "notes/note_form.html")

def note_detail_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    return render(request, "notes/note_detail.html", {"note": note})