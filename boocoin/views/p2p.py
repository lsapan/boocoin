import logging
from base64 import b64decode

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from boocoin.mining import mine_block
from boocoin.models import Block, UnconfirmedTransaction
from boocoin.p2p import normalize_node, get_nodes, sync
from boocoin.serializers import (
    BlockSerializer, UnconfirmedTransactionSerializer,
    RemoteBlockTransactionSerializer
)
from boocoin.util.views import APIView
from boocoin.validation import validate_block

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


class TransmitBlockView(APIView):
    @transaction.atomic
    def post(self, request):
        block = request.data.get('block')
        node = normalize_node(request.data.get('node'))
        nodes = get_nodes()
        if node not in nodes:
            return Response(status=400)

        logger.debug(f'Processing block {block["id"]} from node {node}...')

        # Check if we have the previous block this block refers to
        try:
            Block.objects.get(id=block['previous_block'])
        except Block.DoesNotExist:
            logger.debug(
                f'We do not have block {block["previous_block"]}, syncing...'
            )
            sync(node)
            return Response()

        # Set up the block
        serializer = BlockSerializer(data=block)
        serializer.is_valid(raise_exception=True)
        _block = serializer.validated_data.copy()
        if block.get('extra_data'):
            _block['extra_data'] = b64decode(block['extra_data'])
        block_obj = Block(**_block)

        # Set up the transactions
        transactions = []
        for t in block['transactions']:
            assert t.pop('block') == block_obj.id
            t_serializer = RemoteBlockTransactionSerializer(data=t)
            t_serializer.is_valid(raise_exception=True)
            _t = t_serializer.validated_data.copy()
            if t.get('extra_data'):
                _t['extra_data'] = b64decode(t['extra_data'])
            transaction = Transaction(**_t)
            transactions.append(transaction)

        # Validate the block and transactions
        if validate_block(block_obj, transactions):
            block_obj.save(transactions)
            return Response()
        else:
            logger.debug(f'Rejecting block from {node}')
            return Response(status=400)


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
