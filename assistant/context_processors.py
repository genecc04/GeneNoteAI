from .models import Note

def sidebar_notes(request):
    return {'sidebar_notes': Note.objects.all().order_by('-is_favorite', '-created_at')}