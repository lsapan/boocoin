from django.urls import path

from boocoin import views

urlpatterns = [
    path('api/block_count/', views.BlockCountView.as_view()),
]
