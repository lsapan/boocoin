import logging

import requests
from django.conf import settings

from boocoin.serializers import UnconfirmedTransactionSerializer

logger = logging.getLogger(__name__)


def get_nodes():
    nodes = []
    for node in settings.NODES:
        if ':' not in node:
            node = f'{node}:9811'

        nodes.append(f'http://{node}')
    return nodes


def broadcast_transaction(transaction):
    data = UnconfirmedTransactionSerializer(transaction).data
    for node in get_nodes():
        try:
            requests.post(f'{node}/p2p/transmit_transaction/', data)
        except Exception as e:
            logger.warn(str(e))
            continue
