import logging

from django.db import transaction
from rest_framework.response import Response

from boocoin.mining import mine_block
from boocoin.models import UnconfirmedTransaction
from boocoin.serializers import UnconfirmedTransactionSerializer
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
