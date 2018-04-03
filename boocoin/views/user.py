from django.shortcuts import get_object_or_404, get_list_or_404
from rest_framework.response import Response

from boocoin import forms
from boocoin.models import Block, Transaction
from boocoin.serializers import BlockSerializer, TransactionSerializer
from boocoin.util.forms import FormView
from boocoin.util.views import APIView


class BlockCountView(APIView):
    """
    Returns the number of blocks in the longest chain.
    """

    def get(self, request):
        return Response(Block.get_active_block().depth + 1)


class BlockView(APIView):
    """
    Returns the complete data (including transactions) for a block.
    """

    def get(self, request, id):
        block = get_object_or_404(Block, id=id)
        return Response(BlockSerializer(block).data)


class TransactionView(APIView):
    """
    Returns the complete data for a given transaction.
    """

    def get(self, request, hash):
        transaction = get_list_or_404(Transaction, hash=hash)
        if len(transaction) == 1:
            return Response(TransactionSerializer(transaction[0]).data)
        else:
            return Response(TransactionSerializer(transaction).data, many=True)


class SubmitTransactionView(FormView):
    """
    Accepts a transaction from a sender (wallet) and submits it to the
    unconfirmed transaction pool.
    """

    serializer_class = forms.TransactionForm
