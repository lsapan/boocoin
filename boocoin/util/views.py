from rest_framework import views


class APIView(views.APIView):
    """
    Prevents DRF from trying to access the (nonexistent) user.
    """
    def perform_authentication(self, request):
        pass
