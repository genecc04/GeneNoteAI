from types import SimpleNamespace
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

QUIZ_COUNT_RANGE = [MinValueValidator(1), MaxValueValidator(20)]
FLASHCARD_COUNT_RANGE = [MinValueValidator(1), MaxValueValidator(30)]
HISTORY_LIMIT_RANGE = [MinValueValidator(2), MaxValueValidator(100)]

md = (
    MarkdownIt("commonmark", {"breaks": True, "html": False})
    .enable(["table", "strikethrough"])
    .use(dollarmath_plugin, allow_space=False)
)

def pick(override, default):
    """Use the override if it is set (not None or empty), otherwise the global default."""
    return default if override in (None, "") else override

class Note(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='notes/', blank=True, null=True)
    summary = models.TextField(blank=True)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Per-note overrides. Empty means "use the global default".
    generation_model = models.CharField(max_length=100, blank=True, default="")
    quiz_question_count = models.PositiveSmallIntegerField(null=True, blank=True, validators=QUIZ_COUNT_RANGE)
    flashcard_count = models.PositiveSmallIntegerField(null=True, blank=True, validators=FLASHCARD_COUNT_RANGE)

    def effective(self):
        cfg = AppSettings.load()
        return SimpleNamespace(
            generation_model=pick(self.generation_model, cfg.generation_model),
            quiz_question_count=pick(self.quiz_question_count, cfg.quiz_question_count),
            flashcard_count=pick(self.flashcard_count, cfg.flashcard_count),
        )

    @property
    def content_html(self):
        return md.render(self.content)

    def __str__(self):
        return self.title

class Quiz(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    choice_a = models.CharField(max_length=255)
    choice_b = models.CharField(max_length=255)
    choice_c = models.CharField(max_length=255)
    choice_d = models.CharField(max_length=255)
    correct_choice = models.CharField(max_length=1)

    def __str__(self):
        return self.text[:50]

class Flashcard(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='flashcards')
    front = models.TextField()
    back = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class ChatSession(models.Model):
    title = models.CharField(max_length=255, blank=True)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Per-chat overrides. Empty means "use the global default".
    chat_model = models.CharField(max_length=100, blank=True, default="")
    chat_history_limit = models.PositiveSmallIntegerField(null=True, blank=True, validators=HISTORY_LIMIT_RANGE)

    def effective(self):
        cfg = AppSettings.load()
        return SimpleNamespace(
            chat_model=pick(self.chat_model, cfg.chat_model),
            chat_history_limit=pick(self.chat_history_limit, cfg.chat_history_limit),
        )

    def __str__(self):
        return self.title or f"Chat {self.id}"

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def content_html(self):
        return md.render(self.content)

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"

class AppSettings(models.Model):
    quiz_question_count = models.PositiveSmallIntegerField(default=5, validators=QUIZ_COUNT_RANGE)
    flashcard_count = models.PositiveSmallIntegerField(default=8, validators=FLASHCARD_COUNT_RANGE)
    generation_model = models.CharField(max_length=100, default="gemini-3.5-flash-lite")
    chat_model = models.CharField(max_length=100, default="gemini-3.5-flash-lite")
    chat_history_limit = models.PositiveSmallIntegerField(default=20, validators=HISTORY_LIMIT_RANGE)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj