from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from .models import Note, ChatSession, AppSettings


class HomeViewTests(TestCase):
    def test_empty_state(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome")

    def test_redirects_to_latest_note(self):
        note = Note.objects.create(title="Test note", content="Some content")
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, reverse('note_detail', args=[note.id]))


class NoteViewTests(TestCase):
    @patch('assistant.views.client')
    def test_create_note_with_content(self, mock_client):
        # Fake Gemini's reply so no real API call happens
        mock_client.models.generate_content.return_value = MagicMock(text="- A fake summary")

        response = self.client.post(reverse('note_create'), {
            "title": "Physics notes",
            "content": "Forces and motion.",
        })
        note = Note.objects.get(title="Physics notes")
        self.assertRedirects(response, reverse('note_detail', args=[note.id]))
        self.assertEqual(note.summary, "- A fake summary")

    def test_note_detail_renders(self):
        note = Note.objects.create(title="Test", content="Some **bold** content")
        response = self.client.get(reverse('note_detail', args=[note.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<strong>bold</strong>")


class QuizViewTests(TestCase):
    @patch('assistant.views.client')
    def test_generate_quiz(self, mock_client):
        note = Note.objects.create(title="Test", content="Some content", summary="A summary")
        fake_json = '[{"question": "Q1?", "choice_a": "A", "choice_b": "B", "choice_c": "C", "choice_d": "D", "correct_choice": "a"}]'
        mock_client.models.generate_content.return_value = MagicMock(text=fake_json)

        response = self.client.get(reverse('generate_quiz', args=[note.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(note.quizzes.first().questions.count(), 1)


class ChatViewTests(TestCase):
    def test_new_chat_redirects(self):
        response = self.client.get(reverse('chat_new'))
        self.assertEqual(response.status_code, 302)

    @patch('assistant.views.client')
    def test_send_message(self, mock_client):
        session = ChatSession.objects.create(title="New Chat")
        mock_chat = MagicMock()
        mock_chat.send_message.return_value = MagicMock(text="Hello back")
        mock_client.chats.create.return_value = mock_chat

        response = self.client.post(reverse('chat_session', args=[session.id]),
                                     {"message": "Hi"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply_html"].strip(), "<p>Hello back</p>")
        self.assertEqual(session.messages.count(), 2)


class SettingsViewTests(TestCase):
    def test_settings_page_loads(self):
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 200)

    def test_settings_rejects_invalid_value(self):
        cfg = AppSettings.load()
        response = self.client.post(
            reverse('settings'),
            {
                "generation_model": cfg.generation_model,
                "quiz_question_count": 0,
                "flashcard_count": cfg.flashcard_count,
                "chat_model": cfg.chat_model,
                "chat_history_limit": cfg.chat_history_limit,
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 400)