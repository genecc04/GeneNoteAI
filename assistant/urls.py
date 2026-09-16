from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('chat/', views.chat_view, name='chat_new'),
    path('chat/<int:session_id>/', views.chat_view, name='chat_session'),
    path('notes/new/', views.note_create_view, name='note_create'),
    path('notes/<int:note_id>/', views.note_detail_view, name='note_detail'),
    path('notes/<int:note_id>/generate-quiz/', views.generate_quiz_view, name='generate_quiz'),
    path('quiz/<int:quiz_id>/', views.quiz_detail_view, name='quiz_detail'),
]