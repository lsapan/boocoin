import json
import logging

from django.utils.timezone import now

from boocoin.balances import apply_transaction_to_balances, InsufficientFunds
from boocoin.hashing import calculate_merkle_root
from boocoin.models import Block
from boocoin.signing import verify

logger = logging.getLogger(__name__)


def prune_invalid_transactions(previous_block, transactions):
    """
    Deletes any transactions that would not pass validation.
    Returns the transactions that passed.
    """
    logger.debug('Pruning invalid transactions...')
    approved_transactions = []

    # Start with the current balancess
    balances = previous_block.get_balances()

    for transaction in transactions:
        if not validate_transaction(balances, transaction, False):
            # Invalid transaction, delete it and move on
            logger.debug(f'Transaction {transaction.id} invalid, pruning...')
            transaction.delete()
            continue
        else:
            # Transaction passed, add it and update balances
            approved_transactions.append(transaction)
            balances = apply_transaction_to_balances(transaction, balances)

    return approved_transactions


def tinvalid(reason):
    logger.debug(f'Transaction is invalid: {reason}')
    return False


def binvalid(reason):
    logger.debug(f'Block is invalid: {reason}')
    return False


def validate_transaction(balances, transaction, first_in_block=False):
    logger.debug(f'Validating transaction {transaction.id}')

    # Verify the transaction hash
    if transaction.id != transaction.calculate_hash():
        return tinvalid('Hash is incorrect')

    # Ensure the transaction isn't in the future
    if transaction.time > now():
        return tinvalid('Time is in the future')

    # Check for a to_account
    if not transaction.to_account:
        return tinvalid('Missing to_account')

    if first_in_block:
        # This block should be a block reward
        if transaction.from_account:
            return tinvalid('Block reward should not have from_account')

        if transaction.coins != 100:
            return tinvalid('Block reward must be 100 coins')

        if transaction.signature != 'boocoin-block-reward':
            return tinvalid('Block reward signature is invalid')
    else:
        # We should have a from_account
        if not transaction.from_account:
            return tinvalid('Missing from_account')

        # It shouldn't match the to_account
        if transaction.from_account == transaction.to_account:
            return tinvalid('from_account should not equal to_account')

        # Verify the sender's signature
        valid_signature = verify(
            content=transaction.id,
            public_key=transaction.from_account,
            signature=transaction.signature,
        )
        if not valid_signature:
            return tinvalid('Bad signature')

    # Ensure coins is positive
    if transaction.coins <= 0:
        return tinvalid('Coins must be positive')

    # Check for sufficient funds
    try:
        balances = apply_transaction_to_balances(transaction, balances)
    except InsufficientFunds:
        return tinvalid('Insufficient funds')

    logger.debug('Transaction validated')
    return True


def validate_block(block, transactions):
    logger.debug(f'Validating block {block.id}')

    # Verify the block hash
    if block.id != block.calculate_hash():
        return binvalid('Hash is incorrect')

    # Get the previous block
    try:
        previous_block = Block.objects.get(id=block.previous_block_id)
    except Block.DoesNotExist:
        return binvalid('Previous block does not exist')

    # Verify the depth of the block
    if block.depth != previous_block.depth + 1:
        return binvalid('Depth is incorrect')

    # Ensure the block isn't in the future
    if block.time > now():
        return binvalid('Time is in the future')

    # Verify the block has 11 transactions (10 + 1) or it has been 10 minutes
    minutes_passed = (block.time - previous_block.time).total_seconds() / 60
    if len(transactions) < 11 and minutes_passed < 10:
        return binvalid('Transaction count and minutes passed are wrong')

    # A miner must be set
    if not block.miner:
        return binvalid('Missing miner')

    # The miner must be in the genesis block
    genesis_block = Block.get_genesis_block()
    miners = json.loads(genesis_block.extra_data.decode('utf-8'))
    if block.miner not in miners:
        return binvalid('Miner not in genesis block')

    # Verify the miner's signature
    valid_signature = verify(
        content=block.id,
        public_key=block.miner,
        signature=block.signature,
    )
    if not valid_signature:
        return binvalid('Bad signature')

    # Verify merkle root
    expected_merkle_root = calculate_merkle_root(t.id for t in transactions)
    if expected_merkle_root != block.merkle_root:
        return binvalid('Bad merkle root')

    # Verify balances
    balances = previous_block.get_balances()
    for idx, transaction in enumerate(transactions):
        if not validate_transaction(balances, transaction, idx == 0):
            return binvalid('Invalid transaction detected')

    # All checks passed, the block is valid
    logger.debug('Block validated')
    return True
