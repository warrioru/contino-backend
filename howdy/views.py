from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from .forms import PatchForm

# Create your views here.
class HomePageView(TemplateView):
    def get(self, request, **kwargs):
        return render(request, 'index.html', context=None)

    def post(self, request, **kwargs):
        patch = request.FILES['patch'].read()
        print(patch)
        name = request.POST['name']
        return render(request, 'index.html', {'name': name, 'patch': patch})

# Add this view
class AboutPageView(TemplateView):
    template_name = "about.html"