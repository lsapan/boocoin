from django.urls import path

from boocoin import views

urlpatterns = [
    # User APIs
    path('api/block_count/', views.BlockCountView.as_view()),
    path('api/block/<slug:id>/', views.BlockView.as_view()),
    path('api/transaction/<slug:id>/', views.TransactionView.as_view()),
    path('api/submit_transaction/', views.SubmitTransactionView.as_view()),

    # "Peer-to-peer" APIs
    path('p2p/transmit_transaction/', views.TransmitTransactionView.as_view()),
]
