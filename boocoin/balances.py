from decimal import Decimal


class InsufficientFunds(ValueError):
    pass


def apply_transaction_to_balances(transaction, balances):
    # Ensure the user has the coins that they're transferring
    if transaction.from_account:
        from_balance = balances[transaction.from_account]
        if from_balance < transaction.coins:
            raise InsufficientFunds(f'{from_balance} < {transaction.coins}')

        # Remove the coins from the sender
        balances[transaction.from_account] -= transaction.coins

    # Add the coins to the destination account
    existing_balance = balances.get(transaction.to_account, Decimal(0))
    balances[transaction.to_account] = existing_balance + transaction.coins

    # Return the new balances
    return balances


def apply_transactions_to_balances(transactions, balances):
    for transaction in transactions:
        balances = apply_transaction_to_balances(transaction, balances)
    return balances
