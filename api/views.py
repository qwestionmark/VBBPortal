from datetime import datetime, timedelta
import random

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.db.models import Q
from django.shortcuts import render
from rest_auth.registration.views import SocialLoginView
from rest_framework.decorators import api_view
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import status

from api import aux_fns
from api.models import *
from api.serializers import *
from api.google_apis import *

@api_view(["POST"])
def first_time_signup(request):
    """
    When a user signs up, create a mentor profile. If they are new mentors, create a vbb email and send a
    welcome email.
    """
    fname = request.data.get("first_name").title()
    lname = request.data.get("last_name").title()
    pemail = request.data.get("personal_email").lower()
    gapi = google_apis()

    #TODO test this functionality more thoroughly
    if request.data["vbb_email"] is not None and request.data["vbb_email"] != '':
        #check to see if the serializer works
        serializer = MentorProfileSerializer(data=request.data)
        if not (serializer.is_valid()):
            return Response({
                'success': 'false',
                'message': (str(serializer.errors)),
            })#FIXME use proper protocol and add a status
        request.data["vbb_email"] = request.data["vbb_email"].lower()
        mps = MentorProfile.objects.filter(vbb_email=request.data["vbb_email"])
        if mps is not None and len(mps) > 0 :
            return Response({
                "success": "false", 
                "message": "Sorry, this VBB email has already been used to create a mentor profile."}#,
                # status=status.HTTP_400_BAD_REQUEST #FIXME include status
            )
        welcome_mail = os.path.join("api", "emails", "templates", "welcomeLetterExisting.html")
        gapi.email_send(
            pemail,  # personal email form form
            "Welcome to the New VBB Portal!",#FIXME change back to welcome to the VBB family when we start registering new mentors
            welcome_mail,
            {
            '__first_name': fname,                 # first name from form
            '__new_email': request.data["vbb_email"],  
            }
            ,[request.data["vbb_email"]]
        )
    else:
        #check to see if the serializer works
        request.data["vbb_email"]="mentor@villagebookbuilders.org"
        serializer = MentorProfileSerializer(data=request.data)
        if not (serializer.is_valid()):
            return Response({
                'success': 'false',
                'message': (str(serializer.errors)),
            })#FIXME use proper protocol and add a status
        request.data["vbb_email"], pwd = gapi.account_create(fname.lower(), lname.lower(), pemail)
        welcome_mail = os.path.join("api", "emails", "templates", "welcomeLetter.html")
        gapi.email_send(
            pemail,  # personal email form form
            "Welcome to the New VBB Portal!",#FIXME change back to welcome to the VBB family when we start registering new mentors
            welcome_mail,
            {
            '__first_name': fname,                 # first name from form
            '__new_email': request.data["vbb_email"],   # email generated by shwetha's code
            '__password': pwd                        # password generated by shwetha's code
            }
            ,[request.data["vbb_email"]]
        )
    gapi.group_subscribe("mentor.announcements@villagebookbuilders.org", pemail)
    gapi.group_subscribe("mentor.announcements@villagebookbuilders.org", request.data["vbb_email"])
    gapi.group_subscribe("mentor.collaboration@villagebookbuilders.org", request.data["vbb_email"])
    serializer = MentorProfileSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': 'true',
            'serializer': serializer.data}, status=status.HTTP_201_CREATED
        )
    return Response({
        'success': 'false',
        'message': (str(serializer.errors)),
    })#FIXME use proper protocol and add a status

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

@api_view(["GET"])
def check_signin(request):
    """
    When a user logs in, check if they have a mentor profile before allowing them to proceed
    """
    if ("villagementors.org" not in request.user.email and "villagebookbuilders.org" not in request.user.email):
        return Response({
            "success": "false",
            "message": "Sorry, you need to use a villagementors.org Gsuite account to log in to this website. If you do not have a village mentors account, please sign up for one using the register link above.",
        })
    mps = MentorProfile.objects.filter(vbb_email=request.user.email)
    if mps is None or len(mps) < 1:
        return Response({
            "success": "false",
            "message": "Sorry, there is no signin data associated with this account. Please sign up to be a mentor using the register link above or contact our mentor advisors at mentor@villagebookbuilders.org for assistance.",
        })
    if len(mps) > 1:
        return Response({
            "success": "false",
            "message": "Sorry, there appears to be multiple mentors associated with this account. Please contact our mentor advisors at mentor@villagebookbuilders.org for assistance.",
        })
    if mps[0].user is None:
        mps[0].user = request.user
        mps[0].save()
    return Response({
        "success": "true", 
        "message": ("Welcome, " + request.user.username + "!")
    })

@api_view(["POST"])
def generate_sessionslots(request):
    """
    Generates session slots from opentime to closetime on days from startday to endday
    example - to generate hour long slots from monday to friday in library 3 from 5 to 11 am: (library opens at 5 closes at 11)
    URL example:  api/generate/?library=3&startday=1&endday=5&opentime=300&closetime=660&increment=60
    """
    # OLD URL example:  api/generate/?computer=3&language=1&startday=0&endday=4&opentime=5&closetime=6
    # computer_params = request.query_params.get("computer")
    library = request.query_params.get("library")
    language = request.query_params.get("language")
    startday = int(request.query_params.get("startday"))
    endday = int(request.query_params.get("endday"))
    opentime = int(request.query_params.get("opentime"))
    closetime = int(request.query_params.get("closetime"))
    increment = int(request.query_params.get("increment"))

    daymsms = [i*24*60 for i in range(startday-1, endday)]
    msms = [(j + daymsm) for daymsm in daymsms for j in range(opentime, closetime, increment) ]
    computers = MenteeComputer.objects.filter(library=library).order_by("-computer_number")
    for msm in msms[::-1]:
        for computer in computers:
            if language is None:
                lang = computer.language
            else:
                lang = Language.objects.get(pk=language)
            apt = SessionSlot()
            apt.mentee_computer = computer
            apt.language = lang
            apt.msm = msm
            apt.save()
    
    return Response({"success": "true"})

class LibraryListView(ListAPIView):
    queryset = Library.objects.all()
    serializer_class = LibrarySerializer
    permission_classes = (AllowAny,)

class LanguageListView(ListAPIView):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    permission_classes = (AllowAny,)

class AvailableSessionSlotList(ListAPIView):
    """
    Returns a list of available sessionslot times based on a mentor's preference (queries specific fields by primary key).
    URL example:  api/available/?library=1&language=1&min=1&max=24
    """

    queryset = SessionSlot.objects.all()
    permission_classes = (AllowAny,)

    def get(self, request):
        appts = SessionSlot.objects.all()
        library_params = self.request.query_params.get("library")
        language_params = self.request.query_params.get("language")
        min_msm_params = int(self.request.query_params.get("min_msm"))
        max_msm_params = int(self.request.query_params.get("max_msm"))

        # library and mentor filtering
        if library_params is None or library_params == "0":
            appts = (
                appts.filter(mentor=None, language=language_params)
                .values("msm")
                .distinct()
            )
        else:
            appts = (
                appts.filter(
                    mentor=None,
                    mentee_computer__library=library_params,
                    language=language_params,
                )
                .values("msm")
                .distinct()
            )

        # msm filtering
        if min_msm_params < 0:
            appts = appts.filter(
                Q(msm__lt=max_msm_params) | Q(msm__gte=10080 + min_msm_params)
            )
        elif max_msm_params >= 10080:
            appts = appts.filter(
                Q(msm__lt=max_msm_params - 10080) | Q(msm__gte=min_msm_params)
            )
        else:
            appts = appts.filter(msm__gte=min_msm_params, msm__lt=max_msm_params)

        return Response(appts.order_by("msm"))

@api_view(["POST"])
def book_sessionslot(request):
    """
    Gets an sessionslot list at a given time based on preferences then randomly picks one sessionslot and populates it with the mentor's name (queries specific fields by primary key).
    URL example:  api/book/?library=1&language=1&msm=1
    """
    appts = SessionSlot.objects.all()
    library_params = request.query_params.get("library")
    language_params = request.query_params.get("language")
    msm_params = request.query_params.get("msm")

    if library_params is None or library_params == "0":
        appts = appts.filter(mentor=None, language=language_params, msm=msm_params,)
    else:
        appts = appts.filter(
            mentor=None,
            mentee_computer__library=library_params,
            language=language_params,
            msm=msm_params,
        )
    # Check if there are no sessionslots that match the request.
    if not appts:
        return Response(
            {
                "success": "false",
                "message": "No available sessionslots exist with those specifications.",
            }
        )
    myappt = random.choice(appts)
    #print("apt", myappt) #debuggin statementing
    myappt.mentor = request.user
    # FIXME CHANGE START DATE CALCULATION BACK TO THE CODE BELOW ONCE PHASE 1 CURRENT MENTORING TEST IS THROUGH
    # myappt.start_date = datetime.today() + timedelta(
    #     days=(aux_fns.diff_today_dsm(myappt.msm) + 7)
    # )
    myappt.start_date = datetime.today() + timedelta(
        days=(aux_fns.diff_today_dsm(myappt.msm))
    )
    myappt.end_date = myappt.start_date + timedelta(weeks=17)
    gapi = google_apis()
    start_time = aux_fns.date_combine_time(str(myappt.start_date), int(myappt.msm))
    end_date = aux_fns.date_combine_time(str(myappt.end_date), int(myappt.msm))
    event_id, hangouts_link = gapi.calendar_event(
        myappt.mentor.first_name,
        myappt.mentee_computer.computer_email,
        myappt.mentor.mp.vbb_email,
        myappt.mentor.mp.personal_email,
        myappt.mentee_computer.library.program_director_email,
        start_time,
        end_date,
        myappt.mentee_computer.library.calendar_id,
        myappt.mentee_computer.room_id
    )
    myappt.event_id = event_id
    myappt.hangouts_link = hangouts_link
    myappt.save()
    library_time = aux_fns.display_day(
        myappt.mentee_computer.library.time_zone,
        myappt.msm,
        myappt.end_date)
    newMentorNotice_mail = os.path.join("api","emails","templates", "newMentorNotice.html")
    sessionConfirm_mail = os.path.join("api","emails","templates", "sessionConfirm.html")
    gapi.email_send(
        myappt.mentee_computer.library.program_director_email,
        "New Mentoring Session Booked for "+ library_time,
        newMentorNotice_mail,
        {
            '__directorname': myappt.mentee_computer.library.program_director_name,
            '__sessionslot': library_time,
            '__mentorname': myappt.mentor.first_name +" "+ myappt.mentor.last_name,
            '__mentoremail': myappt.mentor.email,
            '__occupation': myappt.mentor.mp.occupation,
            '__languages': myappt.mentor.mp.languages,
            '__computer': str(myappt.mentee_computer)
        } 
    )
    gapi.email_send(
        myappt.mentor.mp.vbb_email,
        "New Mentoring Session Booked for "+ myappt.display(),
        sessionConfirm_mail,
        {
            '__mentorname' : myappt.mentor.first_name,
            '__sessionslot': myappt.display(),
            '__programname': myappt.mentee_computer.library.name,
            '__programdirector': myappt.mentee_computer.library.program_director_name,
            '__hangout': myappt.hangouts_link,
            '__vbbemail': myappt.mentor.email,
            '__pdemail': myappt.mentee_computer.library.program_director_email,
        },
        [myappt.mentor.mp.personal_email]
    )
    training_mail = os.path.join("api", "emails", "templates", "training.html")
    gapi.email_send(
        myappt.mentor.mp.vbb_email,
        "VBB Mentor Training",
        training_mail,
        {
            '__mentorname': myappt.mentor.first_name,
            "__whatsapp_group": myappt.mentee_computer.library.whatsapp_group
        },
        cc=[myappt.mentor.mp.personal_email]
    )
    gapi.group_subscribe(myappt.mentee_computer.library.announcements_group, myappt.mentor.mp.personal_email)
    gapi.group_subscribe(myappt.mentee_computer.library.announcements_group, myappt.mentor.mp.vbb_email)
    gapi.group_subscribe(myappt.mentee_computer.library.collaboration_group, myappt.mentor.mp.vbb_email)
    # FIXME - Add try/except/finally blocks for error checking (not logged in, sessionslot got taken before they refreshed)
    return Response(
        {"success": "true", "user": str(myappt.mentor), "sessionslot": str(myappt),}
    )

class MySessionSlotListView(ListAPIView):
    """
    Returns a list of the mentor's booked sessionslots.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = MySessionSlotListSerializer

    def get_queryset(self):
        return self.request.user.sessionslots.all()
