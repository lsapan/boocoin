import logging

from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from boocoin.balances import apply_transactions_to_balances
from boocoin.models import Block, Transaction, UnconfirmedTransaction, SyncLock
from boocoin.validation import prune_invalid_transactions, validate_block

logger = logging.getLogger(__name__)


def is_time_to_mine():
    active_block = Block.get_active_block()
    minutes_passed = (now() - active_block.time).total_seconds() / 60
    if UnconfirmedTransaction.objects.count() >= 10 or minutes_passed > 10:
        return True
    return False


def mine_block():
    logger.debug('Checking for sync locks...')
    if SyncLock.objects.count():
        logger.debug("Looks like we're syncing, canceling mine_block call.")
        return

    logger.debug('Mining new block...')
    with transaction.atomic():
        # Get the active block
        active_block = Block.get_active_block()
        logger.debug(f'{active_block.id} is the active block.')

        # Collect the unconfirmed transactions
        unconfirmed = UnconfirmedTransaction.objects.all()
        logger.debug(f'{len(unconfirmed)} unconfirmed transactions found.')

        # Prune invalid transactions
        transactions = prune_invalid_transactions(active_block, unconfirmed)
        logger.debug(f'{len(transactions)} transactions after pruning.')

        # Convert the unconfirmed transactions and add the block reward
        transactions = [u.to_transaction() for u in transactions]
        transactions.insert(0, Transaction.create_block_reward())

        # Set up the block
        block = Block(
            previous_block=active_block,
            depth=active_block.depth + 1,
            miner=settings.MINER_PUBLIC_KEY,
            extra_data=settings.BLOCK_EXTRA_DATA,
            time=now(),
        )
        block.set_merkle_root(transactions)
        block.set_balances(apply_transactions_to_balances(
            transactions,
            active_block.get_balances(),
        ))
        block.set_hash()
        block.sign()

        # Validate the block and transactions
        if validate_block(block, transactions):
            # Save the block
            block.save(transactions)
            UnconfirmedTransaction.objects.all().delete()
            logger.info(f'Block {block.id} successfully mined.')
        else:
            logger.info('Failed to mine block - validation error!')
