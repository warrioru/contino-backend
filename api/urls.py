from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
from .views import CreateView
from .views import DetailsView

urlpatterns = {
    path('bucketlists/', CreateView.as_view(), name="create"),
    path('bucketlists/<pk>/',
        DetailsView.as_view(), name="details"),
}

urlpatterns = format_suffix_patterns(urlpatterns)