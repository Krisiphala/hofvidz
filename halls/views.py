from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth.forms import UserCreationForm
from .models import Hall, Video
from django.contrib.auth import authenticate, login
from .forms import VideoForm, SearchForm
from django.forms import formset_factory
from django.http import Http404, JsonResponse
from django.forms.utils import ErrorList
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
import urllib
import requests


YOUTUBE_API_KEY = "AIzaSyBwI0wjswAdjpj26UfBVOGXn6Nx0S2RKlE"

# Create your views here.
def home(request):
    recent_halls = Hall.objects.all().order_by("-id")[:3]
    popular_halls = [Hall.objects.get(pk=2), Hall.objects.get(pk=6), Hall.objects.get(pk=4)]
    return render(request, "halls/home.html", {"recent_halls": recent_halls, "popular_halls": popular_halls}) 

@login_required
def dashboard(request):
    halls = Hall.objects.filter(user = request.user)
    return render(request, "halls/dashboard.html", {"halls": halls})

@login_required
def add_video(request, pk):
    #VideoFormSet = formset_factory(VideoForm, extra=5)
    form = VideoForm()
    search_form = SearchForm()
    hall = Hall.objects.get(pk=pk)

    if not hall.user == request.user:
        raise Http404

    if request.method == "POST":
        form = VideoForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data["url"]
            parsed_url = urllib.parse.urlparse(url)
            video_id = urllib.parse.parse_qs(parsed_url.query).get("v")
            if video_id:
                youtube_id = video_id[0]
                response = requests.get(f"https://youtube.googleapis.com/youtube/v3/videos?part=snippet&id={ youtube_id }&key={ YOUTUBE_API_KEY }")
                json = response.json()
                title = json["items"][0]["snippet"]["title"]
                video = Video(url=url, title=title, youtube_id=youtube_id, hall=hall)
                video.save()
                return redirect("detail_hall", pk)
            else:
                errors = form._errors.setdefault("url", ErrorList())
                errors.append("Needs to be a YouTube URL")

    return render(request, "halls/add_video.html", {"form": form, "search_form": search_form, "hall": hall})

@login_required
def video_search(request):
    search_form = SearchForm(request.GET)
    if search_form.is_valid():
        encoded_search_term = urllib.parse.quote(search_form.cleaned_data["search_term"])
        response = requests.get(f"https://youtube.googleapis.com/youtube/v3/search?part=snippet&maxResults=6&q={encoded_search_term}&key={YOUTUBE_API_KEY}")
        return JsonResponse(response.json())
    return JsonResponse({"error":"Not able to validate form"})

class DeleteVideo(LoginRequiredMixin, generic.DeleteView):
    model = Video
    template_name = "halls/delete_video.html"
    success_url = reverse_lazy("dashboard")

    def get_object(self):
        video = super(DeleteVideo, self).get_object()
        if not video.hall.user == self.request.user:
            raise Http404
        return video

class SignUp(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy("dashboard")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        view = super(SignUp, self).form_valid(form)
        username, password = form.cleaned_data.get("username"), form.cleaned_data.get("password1")
        user = authenticate(username=username, password=password)
        login(self.request, user)
        return view

class CreateHall(LoginRequiredMixin, generic.CreateView):
    model = Hall
    fields = ["title"]
    template_name = "halls/create_hall.html"
    success_url = reverse_lazy("dashboard") # it will search for this url if provided
                                       # but can be overwritten by using redirect

    def form_valid(self, form):
        form.instance.user = self.request.user
        super(CreateHall, self).form_valid(form) # will validate the form and redirect to success_url
        return redirect("dashboard")

class DetailHall(generic.DetailView):
    model = Hall
    template_name = "halls/detail_hall.html"

class UpdateHall(LoginRequiredMixin, generic.UpdateView):
    model = Hall
    template_name = "halls/update_hall.html"
    fields = ["title"]
    success_url = reverse_lazy("dashboard")

    def get_object(self):
        hall = super(UpdateHall, self).get_object()
        if not hall.user == self.request.user:
            raise Http404
        return hall

class DeleteHall(LoginRequiredMixin, generic.DeleteView):
    model = Hall
    template_name = "halls/delete_hall.html"
    success_url = reverse_lazy("dashboard")

    def get_object(self):
        hall = super(DeleteHall, self).get_object()
        if not hall.user == self.request.user:
            raise Http404
        return hall

