from django.shortcuts import render
import os

# Twilio authorization
from django.conf import settings
from django.http import HttpRequest
from django.core.exceptions import SuspiciousOperation
from twilio.request_validator import RequestValidator
request_validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)

def validate_django_request(request: HttpRequest):
   try:
       signature = request.META['HTTP_X_TWILIO_SIGNATURE']
   except KeyError:
       is_valid_twilio_request = False
   else:
       is_valid_twilio_request = request_validator.validate(
           signature = signature,
           uri = request.get_raw_uri(),
           params = request.POST,
       )
   if not is_valid_twilio_request:
       # Invalid request from Twilio
       raise SuspiciousOperation()

# movies/views.py
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.voice_response import Record, VoiceResponse, Say

from .models import Theater, Movie, Show


#Greeting and selection menu
@csrf_exempt
def answer(request: HttpRequest) -> HttpResponse:
    validate_django_request(request)
def choose_theater(request: HttpRequest) -> HttpResponse:
   vr = VoiceResponse()
   vr.say('映画館情報メニューにようこそ!', voice='woman', language='ja-JP')

   with vr.gather(
       action=reverse('choose-movie'),
       finish_on_key='#',
       timeout=20,
   ) as gather:
       gather.say('映画館を選択して、シャープを押してください！', voice='woman', language='ja-JP')
       theaters = (
           Theater.objects
           .filter(digits__isnull=False)
           .order_by('digits')
       )
       for theater in theaters:
           gather.say(f' {theater.name} は、 {theater.digits}、メッセージを送る場合は、3を押してください', voice='woman', language='ja-JP')

   vr.say('選択していません', voice='woman', language='ja-JP')
   vr.redirect('')

   return HttpResponse(str(vr), content_type='text/xml')


#Select movie menu
@csrf_exempt
def answer(request: HttpRequest) -> HttpResponse:
    validate_django_request(request)
def choose_movie(request: HttpRequest) -> HttpResponse:
   vr = VoiceResponse()

   digits = request.POST.get('Digits')
   try:
       theater = Theater.objects.get(digits=digits)

   except Theater.DoesNotExist:
       vr.say('登録されている映画館から選択してください', voice='woman', language='ja-JP')
       vr.redirect(reverse('choose-theater'))

   else:
       with vr.gather(
           action=f'{reverse("list-showtimes")}?theater={theater.id}',
           finish_on_key='#',
           timeout=20,
       ) as gather:
           gather.say('映画を選択して、シャープを押してください', voice='woman', language='ja-JP')
           movies = (
               Movie.objects
               .filter(digits__isnull=False)
               .order_by('digits')
           )
           for movie in movies:
               gather.say(f' {movie.title} は、 {movie.digits}', voice='woman', language='ja-JP')

       vr.say('選択していません', voice='woman', language='ja-JP')
       vr.redirect(reverse('choose-theater'))

   return HttpResponse(str(vr), content_type='text/xml')


#List movie broadcast times menu
import datetime
from django.utils import timezone

@csrf_exempt
def answer(request: HttpRequest) -> HttpResponse:
    validate_django_request(request)
def list_showtimes(request: HttpRequest) -> HttpResponse:
   vr = VoiceResponse()

   digits = request.POST.get('Digits')
   theater = Theater.objects.get(id=request.GET['theater'])

   try:
       movie = Movie.objects.get(id=digits)

   except Movie.DoesNotExist:
       vr.say('登録されている映画から選択してください', voice='woman', language='ja-JP')
       vr.redirect(f'{reverse("choose-movie")}?theater={theater.id}')

   else:
       # User selected movie and theater, search shows in the next 12 hours:
       from_time = timezone.now()
       until_time = from_time + datetime.timedelta(hours=12)
       shows = list(
           Show.objects.filter(
               theater=theater,
               movie=movie,
               starts_at__range=(from_time, until_time),
           ).order_by('starts_at')
       )
       if len(shows) == 0:
           vr.say('すみません。こちらの映画はしばらく見れません。', voice='woman', language='ja-JP')
       else:
           showtimes = ', '.join(show.starts_at.time().strftime('%I:%M%p') for show in shows)
           vr.say(f' {movie.title} は、 {showtimes} に、 {theater.name} で見れます。', voice='woman', language='ja-JP')

       vr.say('ご利用ありがとうございました！', voice='woman', language='ja-JP')
       vr.hangup()

   return HttpResponse(str(vr), content_type='text/xml')


#Record message 
@csrf_exempt
def answer(request: HttpRequest) -> HttpResponse:
    validate_django_request(request)
def record_message(request: HttpRequest) -> HttpResponse:
   vr = VoiceResponse()
   digits = request.POST.get('Digits')

   vr.say('こちらはメッセージを送るメニューです。終わったら、シャープマークを押してください。メッセージどうぞ：', voice='woman', language='ja-JP')
   vr.record(timeout=10, max_length=50, finish_on_key='#', action=reverse('save-to-dropbox'), method='POST', transcribe=True)
   vr.say('メッセージがありません。')

#Save message to dropbox
import dropbox

@csrf_exempt
def answer(request: HttpRequest) -> HttpResponse:
    validate_django_request(request)
def save_to_dropbox(request: HttpRequest) -> HttpResponse:
    rec_name = request.POST.get('RecordingSid')+'.wav'
    rec_url = request.POST.get('RecordingUrl')
    dbx = dropbox.Dropbox('DROPBOX_ACCESS_TOKEN')
    dbx.files_upload(rec_name,rec_url, mute=True, client_modified=timezone.now())
