from rest_framework import status, views
from rest_framework.response import Response

from boocoin.models import Block


class APIView(views.APIView):
    """
    Prevents DRF from trying to access the (nonexistent) user.
    """
    def perform_authentication(self, request):
        pass


class BlockCountView(APIView):
    def get(self, request):
        return Response(Block.get_active_block().depth + 1)
