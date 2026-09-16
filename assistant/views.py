import os
import json
from django.shortcuts import render, get_object_or_404, redirect
from dotenv import load_dotenv
from google import genai
from google.genai import types
from .models import ChatSession, ChatMessage, Note
from .models import Note, Quiz, Question

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

def generate_quiz_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)

    prompt = f"""
Create a 5-question multiple choice quiz based on these notes.
Respond ONLY with valid JSON, no other text, in this exact format:
[
  {{"question": "...", "choice_a": "...", "choice_b": "...", "choice_c": "...", "choice_d": "...", "correct_choice": "a"}}
]

Notes:
{note.content}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    clean_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
    questions_data = json.loads(clean_text)

    quiz = Quiz.objects.create(note=note, title=f"Quiz: {note.title}")

    for q in questions_data:
        Question.objects.create(
            quiz=quiz,
            text=q["question"],
            choice_a=q["choice_a"],
            choice_b=q["choice_b"],
            choice_c=q["choice_c"],
            choice_d=q["choice_d"],
            correct_choice=q["correct_choice"]
        )

    return redirect("quiz_detail", quiz_id=quiz.id)

def quiz_detail_view(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()
    return render(request, "notes/quiz_detail.html", {"quiz": quiz, "questions": questions})