import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from boocoin.mining import mine_block
from boocoin.models import Block, UnconfirmedTransaction
from boocoin.serializers import BlockSerializer, UnconfirmedTransactionSerializer
from boocoin.util.views import APIView

logger = logging.getLogger(__name__)


class TransmitTransactionView(APIView):
    @transaction.atomic
    def post(self, request):
        transaction = UnconfirmedTransactionSerializer(data=request.data)
        transaction.is_valid(raise_exception=True)
        transaction.save()

        # Mine a block if we have at least 10 transaction waiting
        if UnconfirmedTransaction.objects.count() >= 10:
            logger.info('At least 10 transactions waiting, mining new block.')
            mine_block()

        return Response()


class BlockchainHistoryView(APIView):
    def get(self, request):
        before = request.GET.get('before')
        if before:
            from_block = get_object_or_404(Block, id=before)
        else:
            from_block = Block.get_active_block()

        ids = []
        for i in range(100):
            ids.append(from_block.id)
            if from_block.previous_block:
                from_block = from_block.previous_block
            else:
                break

        return Response(ids)


class BlocksView(APIView):
    def post(self, request):
        block_ids = request.data.get('blocks')
        blocks = Block.objects.filter(id__in=block_ids)
        return Response({b.id: BlockSerializer(b).data for b in blocks})
