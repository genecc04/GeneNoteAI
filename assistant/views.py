import os
import time
import json
import markdown
from django.shortcuts import render, get_object_or_404, redirect
from dotenv import load_dotenv
from google import genai
from google.genai import types
from .models import ChatSession, ChatMessage, Note, Quiz, Question, Flashcard

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def home_view(request):
    latest_note = Note.objects.order_by('-created_at').first()
    if latest_note:
        return redirect('note_detail', note_id=latest_note.id)

    sessions = ChatSession.objects.all().order_by('-created_at')
    return render(request, "notes/home.html", {"sessions": sessions})

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
                contents=f"Summarize the following study notes concisely. Use a flat bulleted list only — no nested sub-bullets — and use **bold** only for key terms.\n\n{content}"
            )
            note.summary = response.text
            note.save()

        elif note.file:
            gemini_file = client.files.upload(file=note.file.path)

            while gemini_file.state.name == "PROCESSING":
                time.sleep(1)
                gemini_file = client.files.get(name=gemini_file.name)

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=["Summarize the key points from this document concisely. Use a flat bulleted list only — no nested sub-bullets — and use **bold** only for key terms.", gemini_file]
            )
            note.summary = response.text
            note.save()

        return redirect("note_detail", note_id=note.id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "notes/partials/note_form_content.html")

    return render(request, "notes/note_form.html")

def note_detail_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    summary_html = markdown.markdown(note.summary, extensions=['extra', 'nl2br']) if note.summary else ""
    context = {"note": note, "summary_html": summary_html, "active_note_id": note.id}

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "notes/partials/note_detail_content.html", context)

    return render(request, "notes/note_detail.html", context)

def generate_quiz_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    source_text = note.content if note.content else note.summary

    prompt = f"""
    Create a 5-question multiple choice quiz based on these notes.
    Respond ONLY with valid JSON, no other text, in this exact format:
    [
    {{"question": "...", "choice_a": "...", "choice_b": "...", "choice_c": "...", "choice_d": "...", "correct_choice": "a"}}
    ]

    Notes:
    {source_text}
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
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == "POST":
        score = 0
        results = []

        for question in questions:
            selected = request.POST.get(f"question_{question.id}")
            is_correct = selected == question.correct_choice
            if is_correct:
                score += 1
            results.append({
                "question": question,
                "selected": selected,
                "is_correct": is_correct
            })

        context = {"quiz": quiz, "results": results, "score": score, "total": len(questions), "active_note_id": quiz.note.id}

        if is_ajax:
            return render(request, "notes/partials/quiz_results_content.html", context)
        return render(request, "notes/quiz_results.html", context)

    context = {"quiz": quiz, "questions": questions, "active_note_id": quiz.note.id}

    if is_ajax:
        return render(request, "notes/partials/quiz_detail_content.html", context)
    return render(request, "notes/quiz_detail.html", context)

def generate_flashcards_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    source_text = note.content if note.content else note.summary

    prompt = f"""
    Create 8 flashcards based on these notes.
    Respond ONLY with valid JSON, no other text, in this exact format:
    [
    {{"front": "...", "back": "..."}}
    ]

    Notes:
    {source_text}
    """

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    clean_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
    cards_data = json.loads(clean_text)

    for card in cards_data:
        Flashcard.objects.create(
            note=note,
            front=card["front"],
            back=card["back"]
        )

    return redirect("flashcards_detail", note_id=note.id)

def flashcards_detail_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    flashcards = note.flashcards.all()
    context = {"note": note, "flashcards": flashcards, "active_note_id": note.id}

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "notes/partials/flashcards_detail_content.html", context)

    return render(request, "notes/flashcards_detail.html", context)

def toggle_favorite_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    note.is_favorite = not note.is_favorite
    note.save()

    notes = Note.objects.all().order_by('-is_favorite', '-created_at')
    return render(request, "notes/partials/sidebar_notes.html", {"sidebar_notes": notes})

def delete_note_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    note.delete()

    notes = Note.objects.all().order_by('-is_favorite', '-created_at')
    return render(request, "notes/partials/sidebar_notes.html", {"sidebar_notes": notes})

def note_edit_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)

    if request.method == "POST":
        note.title = request.POST.get("title")
        note.content = request.POST.get("content", "")
        note.save()

        summary_html = markdown.markdown(note.summary, extensions=['extra', 'nl2br']) if note.summary else ""
        context = {"note": note, "summary_html": summary_html, "active_note_id": note.id}
        return render(request, "notes/partials/note_detail_content.html", context)

    context = {"note": note, "active_note_id": note.id}
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "notes/partials/note_edit_content.html", context)

    return render(request, "notes/note_edit.html", context)

def regenerate_summary_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    source_text = note.content if note.content else note.summary

    if note.content:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=f"Summarize the following study notes concisely. Use a flat bulleted list only — no nested sub-bullets — and use **bold** only for key terms.\n\n{source_text}"
        )
        note.summary = response.text
        note.save()

    elif note.file:
        gemini_file = client.files.upload(file=note.file.path)

        while gemini_file.state.name == "PROCESSING":
            time.sleep(1)
            gemini_file = client.files.get(name=gemini_file.name)

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=["Summarize the key points from this document concisely. Use a flat bulleted list only — no nested sub-bullets — and use **bold** only for key terms.", gemini_file]
        )
        note.summary = response.text
        note.save()

    summary_html = markdown.markdown(note.summary, extensions=['extra', 'nl2br']) if note.summary else ""
    context = {"note": note, "summary_html": summary_html, "active_note_id": note.id}
    return render(request, "notes/partials/note_detail_content.html", context)