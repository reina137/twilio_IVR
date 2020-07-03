from django.urls import path

from . import views

urlpatterns = [
    path('answer', views.choose_theater, name='choose-theater'),
    path('choose-movie', views.choose_movie, name='choose-movie'),
    path('list-showtimes', views.list_showtimes, name='list-showtimes'),
    path('record-message', views.record_message, name='record-message'),
    path('save-to-dropbox', views.save_to_dropbox, name='save-to-dropbox'),
]