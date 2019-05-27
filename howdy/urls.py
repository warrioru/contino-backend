# howdy/urls.py
from django.urls import path
from howdy import views


urlpatterns = [
    path('', views.HomePageView.as_view()),
    path('about/', views.AboutPageView.as_view()),
    path('commitCheck/', views.CommitCheckPageView.as_view()),
    path('getDiff/', views.GetDiffPageView.as_view()),
    path('getGraph/', views.GetGraphPageView.as_view()),
]
