from decimal import Decimal


class InsufficientFunds(ValueError):
    pass


def apply_transaction_to_balances(transaction, balances):
    """
    Accepts a dictionary of balances and applies a transaction to it.
    Returns the new dictionary of balances.

    Raises:
        InsufficientFunds: If the account does not have enough coins.
    """
    # Prevent modifying the passed balances object
    balances = balances.copy()

    # Ensure the user has the coins that they're transferring
    if transaction.from_account:
        from_balance = balances.get(transaction.from_account, Decimal(0))
        if from_balance < transaction.coins:
            raise InsufficientFunds(f'{from_balance} < {transaction.coins}')

        # Remove the coins from the sender
        balances[transaction.from_account] = from_balance - transaction.coins

    # Add the coins to the destination account
    existing_balance = balances.get(transaction.to_account, Decimal(0))
    balances[transaction.to_account] = existing_balance + transaction.coins

    # Return the new balances
    return balances


def apply_transactions_to_balances(transactions, balances):
    """
    Accepts a dictionary of balances and plays a list of transactions over it.
    Returns the new dictionary of balances.

    Raises:
        InsufficientFunds: If one of the accounts does not have enough coins.
    """
    for transaction in transactions:
        balances = apply_transaction_to_balances(transaction, balances)
    return balances
