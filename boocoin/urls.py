from django.urls import path

from boocoin import views

urlpatterns = [
    path('api/block_count/', views.BlockCountView.as_view()),
    path('api/block/<slug:id>/', views.BlockView.as_view()),
    path('api/transaction/<slug:id>/', views.TransactionView.as_view()),
    path('api/submit_transaction/', views.SubmitTransactionView.as_view()),
]
