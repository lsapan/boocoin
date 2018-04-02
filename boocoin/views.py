from django.shortcuts import get_object_or_404
from rest_framework import status, views
from rest_framework.response import Response

from boocoin.models import Block, Transaction
from boocoin.serializers import BlockSerializer, TransactionSerializer


class APIView(views.APIView):
    """
    Prevents DRF from trying to access the (nonexistent) user.
    """
    def perform_authentication(self, request):
        pass


class BlockCountView(APIView):
    def get(self, request):
        return Response(Block.get_active_block().depth + 1)


class BlockView(APIView):
    def get(self, request, id):
        block = get_object_or_404(Block, id=id)
        return Response(BlockSerializer(block).data)


class TransactionView(APIView):
    def get(self, request, id):
        transaction = get_object_or_404(Transaction, id=id)
        return Response(TransactionSerializer(transaction).data)
