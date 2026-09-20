from django import forms
from .models import AppSettings

MODEL_CHOICES = [
    ("gemini-3.5-flash-lite", "gemini-3.5-flash-lite"),
]

class AppSettingsForm(forms.ModelForm):
    generation_model = forms.ChoiceField(
        choices=MODEL_CHOICES, label="Model for summaries, quizzes and flashcards")
    chat_model = forms.ChoiceField(choices=MODEL_CHOICES, label="Chat model")

    class Meta:
        model = AppSettings
        fields = ["generation_model", "quiz_question_count", "flashcard_count",
                  "chat_model", "chat_history_limit"]
        labels = {
            "quiz_question_count": "Questions per quiz",
            "flashcard_count": "Flashcards per set",
            "chat_history_limit": "Past messages sent with each chat message",
        }
        help_texts = {
            "chat_history_limit": "Lower uses fewer tokens, but the AI forgets older messages.",
        }