import os
import time
import json
import markdown
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from .models import ChatSession, ChatMessage, Note, Quiz, Question, Flashcard, AppSettings
from .forms import AppSettingsForm, NoteSettingsForm, ChatSettingsForm

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def home_view(request):
    latest_note = Note.objects.order_by('-created_at').first()
    if latest_note:
        return redirect('note_detail', note_id=latest_note.id)

    latest_chat = ChatSession.objects.order_by('-created_at').first()
    if latest_chat:
        return redirect('chat_session', session_id=latest_chat.id)

    return render(request, "notes/home.html")

def generate_with_retry(model, contents, max_retries=3, delay=2):
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(model=model, contents=contents)
        except genai_errors.ServerError:
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                raise

def chat_view(request, session_id=None):
    if session_id is None:
        session = ChatSession.objects.create(title="New Chat")
        return redirect("chat_session", session_id=session.id)

    session = get_object_or_404(ChatSession, id=session_id)

    if request.method == "POST":
        user_text = request.POST.get("message", "").strip()
        if not user_text:
            return JsonResponse({"error": "Message is empty."}, status=400)

        opts = session.effective()

        recent = list(session.messages.order_by("-created_at")[:opts.chat_history_limit])
        recent.reverse()
        if recent and recent[0].role == "model":
            recent = recent[1:]

        history = [
            types.Content(role=msg.role, parts=[types.Part(text=msg.content)])
            for msg in recent
        ]

        try:
            chat = client.chats.create(model=opts.chat_model, history=history)
            response = chat.send_message(user_text)
        except genai_errors.APIError:
            return JsonResponse(
                {"error": "Gemini couldn't respond right now. Please try again."},
                status=502
            )

        ChatMessage.objects.create(session=session, role="user", content=user_text)
        reply = ChatMessage.objects.create(
            session=session, role="model",
            content=response.text or "(No response was generated.)"
        )

        if session.title == "New Chat":
            first_prompt = " ".join(user_text.split())
            session.title = first_prompt[:40] + ("…" if len(first_prompt) > 40 else "")
            session.save()

        return JsonResponse({"reply_html": reply.content_html, "title": session.title})

    messages = session.messages.order_by("created_at")
    return render(request, "notes/chat.html", { "session": session, "messages": messages, "active_tab": "chats", "active_chat_id": session.id })

def rename_chat_view(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)

    if request.method == "POST":
        new_title = request.POST.get("title", "").strip()
        if new_title:
            session.title = new_title[:255]
            session.save()

    return JsonResponse({"title": session.title})

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
        opts = note.effective()

        try:
            if content:
                response = generate_with_retry(
                    model=opts.generation_model,
                    contents=f"Summarize the following study notes concisely.\n\n{content}"
                )
                note.summary = response.text
                note.save()

            elif note.file:
                gemini_file = client.files.upload(file=note.file.path)

                while gemini_file.state.name == "PROCESSING":
                    time.sleep(1)
                    gemini_file = client.files.get(name=gemini_file.name)

                response = generate_with_retry(
                    model=opts.generation_model,
                    contents=["Summarize the key points from this document concisely.", gemini_file]
                )
                note.summary = response.text
                note.save()
        except genai_errors.ServerError:
            note.summary = "Summary generation failed, Gemini may be experiencing high demand. You can try regenerating it from the note page."
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
    opts = note.effective()
    source_text = note.content if note.content else note.summary

    prompt = f"""
    Create a {opts.quiz_question_count}-question multiple choice quiz if possible based on these notes.
    Respond ONLY with valid JSON, no other text, in this exact format:
    [
    {{"question": "...", "choice_a": "...", "choice_b": "...", "choice_c": "...", "choice_d": "...", "correct_choice": "a"}}
    ]

    Notes:
    {source_text}
    """

    try:
        response = generate_with_retry(model=opts.generation_model, contents=prompt)
        clean_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        questions_data = json.loads(clean_text)
    except (genai_errors.ServerError, json.JSONDecodeError):
        return render(request, "notes/partials/error_content.html", {"note": note, "active_note_id": note.id})

    quiz = Quiz.objects.create(note=note, title=f"Quiz: {note.title}")

    for q in questions_data[:opts.quiz_question_count]:
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

            selected_text = getattr(question, f"choice_{selected}", None) if selected else None
            correct_text = getattr(question, f"choice_{question.correct_choice}")

            results.append({
                "question": question,
                "selected": selected,
                "selected_text": selected_text,
                "correct_text": correct_text,
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
    opts = note.effective()
    source_text = note.content if note.content else note.summary

    note.flashcards.all().delete()

    prompt = f"""
    Create {opts.flashcard_count} flashcards if possible based on these notes.
    Respond ONLY with valid JSON, no other text, in this exact format:
    [
    {{"front": "...", "back": "..."}}
    ]

    Notes:
    {source_text}
    """

    try:
        response = generate_with_retry(model=opts.generation_model, contents=prompt)
        clean_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        cards_data = json.loads(clean_text)
    except (genai_errors.ServerError, json.JSONDecodeError):
        return render(request, "notes/partials/error_content.html", {"note": note, "active_note_id": note.id})

    for card in cards_data[:opts.flashcard_count]:
        Flashcard.objects.create(
            note=note,
            front=card["front"],
            back=card["back"]
        )

    return redirect("flashcards_detail", note_id=note.id)

def flashcards_detail_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    flashcards = list(note.flashcards.all())
    pages = [flashcards[i:i + 4] for i in range(0, len(flashcards), 4)]
    context = {"note": note, "pages": pages, "active_note_id": note.id}

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

def toggle_chat_favorite_view(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    session.is_favorite = not session.is_favorite
    session.save()

    chats = ChatSession.objects.all().order_by('-is_favorite', '-created_at')
    return render(request, "notes/partials/sidebar_chats.html", {"sidebar_chats": chats})

def delete_chat_view(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    session.delete()

    chats = ChatSession.objects.all().order_by('-is_favorite', '-created_at')
    return render(request, "notes/partials/sidebar_chats.html", {"sidebar_chats": chats})

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
    opts = note.effective()
    source_text = note.content if note.content else note.summary

    try:
        if note.content:
            response = generate_with_retry(
                model=opts.generation_model,
                contents=f"Summarize the following study notes concisely.\n\n{source_text}"
            )
            note.summary = response.text
            note.save()

        elif note.file:
            gemini_file = client.files.upload(file=note.file.path)

            while gemini_file.state.name == "PROCESSING":
                time.sleep(1)
                gemini_file = client.files.get(name=gemini_file.name)

            response = generate_with_retry(
                model=opts.generation_model,
                contents=["Summarize the key points from this document concisely.", gemini_file]
            )
            note.summary = response.text
            note.save()
    except genai_errors.ServerError:
        pass

    summary_html = markdown.markdown(note.summary, extensions=['extra', 'nl2br']) if note.summary else ""
    context = {"note": note, "summary_html": summary_html, "active_note_id": note.id}
    return render(request, "notes/partials/note_detail_content.html", context)

def settings_view(request):
    cfg = AppSettings.load()
    saved = False
    status = 200

    if request.method == "POST":
        form = AppSettingsForm(request.POST, instance=cfg)
        if form.is_valid():
            form.save()
            saved = True
        else:
            status = 400
    else:
        form = AppSettingsForm(instance=cfg)

    context = {
        "form": form,
        "saved": saved,
        "note_fields": [form["generation_model"], form["quiz_question_count"], form["flashcard_count"]],
        "chat_fields": [form["chat_model"], form["chat_history_limit"]],
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "notes/partials/settings_content.html", context, status=status)
    return render(request, "notes/settings.html", context)

def note_settings_view(request, note_id):
    note = get_object_or_404(Note, id=note_id)

    if request.method == "POST":
        form = NoteSettingsForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            return JsonResponse({"ok": True})
        return render(request, "notes/partials/note_settings_content.html",
                      {"form": form, "note": note}, status=400)

    form = NoteSettingsForm(instance=note)
    return render(request, "notes/partials/note_settings_content.html", {"form": form, "note": note})

def chat_settings_view(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)

    if request.method == "POST":
        form = ChatSettingsForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            return JsonResponse({"ok": True})
        return render(request, "notes/partials/chat_settings_content.html",
                      {"form": form, "session": session}, status=400)

    form = ChatSettingsForm(instance=session)
    return render(request, "notes/partials/chat_settings_content.html", {"form": form, "session": session})