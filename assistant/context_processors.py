from .models import Note, ChatSession  

def sidebar_notes(request):
    return {
        'sidebar_notes': Note.objects.all().order_by('-is_favorite', '-created_at'), 
        'sidebar_chats': ChatSession.objects.all().order_by('-is_favorite', '-created_at')
        }