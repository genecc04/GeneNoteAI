from .models import Note

def sidebar_notes(request):
    return {'sidebar_notes': Note.objects.all().order_by('-created_at')}