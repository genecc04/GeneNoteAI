from django import forms
from .models import AppSettings, Note, ChatSession

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

class NoteSettingsForm(forms.ModelForm):
    generation_model = forms.ChoiceField(required=False, label="Model")

    class Meta:
        model = Note
        fields = ["generation_model", "quiz_question_count", "flashcard_count"]
        labels = {
            "quiz_question_count": "Questions per quiz",
            "flashcard_count": "Flashcards per set",
        }
        help_texts = {
            "quiz_question_count": "Leave blank to use the default.",
            "flashcard_count": "Leave blank to use the default.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cfg = AppSettings.load()
        self.fields["generation_model"].choices = (
            [("", f"Use default ({cfg.generation_model})")] + MODEL_CHOICES
        )
        self.fields["quiz_question_count"].widget.attrs["placeholder"] = f"{cfg.quiz_question_count} (default)"
        self.fields["flashcard_count"].widget.attrs["placeholder"] = f"{cfg.flashcard_count} (default)"

class ChatSettingsForm(forms.ModelForm):
    chat_model = forms.ChoiceField(required=False, label="Model")

    class Meta:
        model = ChatSession
        fields = ["chat_model", "chat_history_limit"]
        labels = {
            "chat_history_limit": "Past messages sent with each chat message",
        }
        help_texts = {
            "chat_history_limit": "Leave blank to use the default. Lower uses fewer tokens, but the AI forgets older messages.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cfg = AppSettings.load()
        self.fields["chat_model"].choices = (
            [("", f"Use default ({cfg.chat_model})")] + MODEL_CHOICES
        )
        self.fields["chat_history_limit"].widget.attrs["placeholder"] = f"{cfg.chat_history_limit} (default)"