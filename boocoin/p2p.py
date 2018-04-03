import logging
from base64 import b64decode

import requests
from django.db import transaction as db_transaction
from django.conf import settings

from boocoin.mining import mine_block, is_time_to_mine
from boocoin.models import Block, SyncLock, Transaction, UnconfirmedTransaction
from boocoin.serializers import (
    BlockSerializer, RemoteBlockTransactionSerializer,
    UnconfirmedTransactionSerializer
)
from boocoin.validation import validate_block

logger = logging.getLogger(__name__)


def normalize_node(node):
    """
    Returns an acceptable URL for the given node.
    """
    if ':' not in node:
        node = f'{node}:9811'
    return f'http://{node}'


def get_nodes():
    """
    Returns a list of all the configured nodes.
    """
    return [normalize_node(n) for n in settings.NODES]


def broadcast_transaction(transaction):
    """
    Broadcasts a transaction to all of the configured nodes.
    """
    data = UnconfirmedTransactionSerializer(transaction).data
    for node in get_nodes():
        try:
            requests.post(f'{node}/p2p/transmit_transaction/', data, timeout=5)
        except Exception as e:
            logger.warn(str(e))
            continue


def broadcast_block(block):
    """
    Broadcasts a block to all of the configured nodes.
    """
    data = {
        'block': BlockSerializer(block).data,
        'node': settings.MINER_IP,
    }
    for node in get_nodes():
        try:
            requests.post(f'{node}/p2p/transmit_block/', json=data, timeout=5)
        except Exception as e:
            logger.warn(str(e))
            continue


def sync_all():
    """
    Syncs this node with each configured node. Note that we only sync with one
    node at a time.
    """
    for node in get_nodes():
        sync(node)


def sync(node):
    """
    Wrapper function around _sync that creates a lock and releases it when
    we're finished. The lock prevents us from mining new blocks before we're
    fully up to date with the rest of the network.
    """
    lock = SyncLock.objects.create(node=node)

    try:
        logger.info(f'Starting sync with {node}...')
        _sync(node)
    except Exception as e:
        logger.warn(f'Failed to sync to node {node}!')
        logger.warn(str(e))
        success = False
    else:
        logger.info(f'Finished syncing with {node}.')
        success = True
    finally:
        lock.delete()

    # Kick off a mine process if all locks are gone and we're due
    if SyncLock.objects.count() == 0 and is_time_to_mine():
        logger.info("All syncs are completed and it's time to mine!")
        mine_block()


def _sync(node):
    # Try to find the most recent overlap, 100 hashes at a time
    before = None
    while True:
        logger.debug(f'Getting blockchain history (before {before})')
        blockchain_history = get_blockchain_history(node, before=before)

        # Check if we're fully synced (we have the node's active block)
        latest_block = blockchain_history[0]
        if before is None and Block.objects.filter(id=latest_block).exists():
            logger.debug('We are fully synced!')
            return

        # We aren't synced yet, check if we have any blocks mentioned
        logger.debug('Searching for common block...')
        for idx, block in enumerate(blockchain_history):
            if Block.objects.filter(id=block).exists():
                # We have this block, so let's add all the ones that come after
                # Note: They come after this block, but are listed before
                logger.debug(f'Found common block {block}')
                return _sync_blocks(node, reversed(blockchain_history[:idx]))

        # We need to go deeper
        logger.debug('No common blocks found, going deeper...')
        before = blockchain_history[-1]


def _sync_blocks(node, blocks):
    # Request full block information from the node
    blocks = list(blocks)
    logger.debug(f'Downloading block data for {len(blocks)} blocks...')
    block_data = get_blocks(node, blocks)

    # Process each block
    with db_transaction.atomic():
        logger.debug('Processing block data...')
        for block in blocks:
            logger.debug(f'Processing block {block}...')
            data = block_data[block]

            # Set up the block
            serializer = BlockSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            _block = serializer.validated_data.copy()
            if data.get('extra_data'):
                _block['extra_data'] = b64decode(data['extra_data'])
            block_obj = Block(**_block)

            # Set up the transactions
            transactions = []
            for t in data['transactions']:
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

                # Delete any matching unconfirmed transactions
                UnconfirmedTransaction.objects.filter(
                    hash__in=(t.hash for t in transactions)
                ).delete()
            else:
                raise ValueError('Block failed validation.')

    # Make sure there aren't any other blocks we need to sync
    logger.debug('Double checking we are synced...')
    return _sync(node)


def get_blockchain_history(node, before=None):
    """
    Gets a list of block hashes from the specified node.
    """
    endpoint = f'{node}/p2p/blockchain_history/'
    if before:
        endpoint += f'?before={before}'
    timeout = 10 if not before else 60
    return requests.get(endpoint, timeout=timeout).json()


def get_blocks(node, blocks):
    """
    Gets block data for the specified blocks from the target node.
    """
    return requests.post(f'{node}/p2p/blocks/', json={
        'blocks': blocks,
    }).json()
