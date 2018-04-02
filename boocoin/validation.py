import json

from django.utils.timezone import now

from boocoin.balances import apply_transaction_to_balances, InsufficientFunds
from boocoin.hashing import calculate_merkle_root
from boocoin.models import Block
from boocoin.signing import verify


def prune_invalid_transactions(previous_block, transactions):
    """
    Deletes any transactions that would not pass validation.
    Returns the transactions that passed.
    """
    approved_transactions = []

    # Start with the current balancess
    balances = previous_block.get_balances()

    for idx, transaction in enumerate(transactions):
        if not validate_transaction(balances, transaction, idx == 0):
            # Invalid transaction, delete it and move on
            transaction.delete()
            continue
        else:
            # Transaction passed, add it and update balances
            approved_transactions.append(transaction)
            balances = apply_transaction_to_balances(transaction, balances)

    return approved_transactions


def validate_transaction(balances, transaction, first_in_block=False):
    # Verify the transaction hash
    if transaction.id != transaction.calculate_hash():
        return False

    # Ensure the transaction isn't in the future
    if transaction.time > now():
        return False

    # Check for a to_account
    if not transaction.to_account:
        return False

    if first_in_block:
        # This block should be a block reward
        if transaction.from_account:
            return False

        if transaction.coins != 100:
            return False

        if transaction.signature != 'boocoin-block-reward':
            return False
    else:
        # We should have a from_account
        if not transaction.from_account:
            return False

        # Verify the sender's signature
        valid_signature = verify(
            content=transaction.id,
            public_key=transaction.from_account,
            signature=transaction.signature,
        )
        if not valid_signature:
            return False

    # Ensure coins is positive
    if transaction.coins <= 0:
        return False

    # Check for sufficient funds
    try:
        balances = apply_transaction_to_balances(transaction, balances)
    except InsufficientFunds:
        return False

    return True


def validate_block(block, transactions):
    # Verify the block hash
    if block.id != block.calculate_hash():
        return False

    # Get the previous block
    try:
        previous_block = Block.objects.get(id=block.previous_block_id)
    except Block.DoesNotExist:
        return False

    # Verify the depth of the block
    if block.depth != previous_block.depth + 1:
        return False

    # Ensure the block isn't in the future
    if block.time > now():
        return False

    # Verify the block has 11 transactions (10 + 1) or it has been 10 minutes
    minutes_passed = (block.time - previous_block.time).total_seconds() / 60
    if len(transactions) < 11 and minutes_passed < 10:
        return False

    # A miner must be set
    if not block.miner:
        return False

    # The miner must be in the genesis block
    genesis_block = Block.get_genesis_block()
    miners = json.loads(genesis_block.extra_data.decode('utf-8'))
    if block.miner not in miners:
        return False

    # Verify the miner's signature
    valid_signature = verify(
        content=block.id,
        public_key=block.miner,
        signature=block.signature,
    )
    if not valid_signature:
        return False

    # Verify merkle root
    expected_merkle_root = calculate_merkle_root(t.id for t in transactions)
    if expected_merkle_root != block.merkle_root:
        return False

    # Verify balances
    balances = previous_block.get_balances()
    for idx, transaction in enumerate(transactions):
        if not validate_transaction(balances, transaction, idx == 0):
            return False

    # All checks passed, the block is valid
    return True
