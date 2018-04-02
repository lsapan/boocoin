from rest_framework import serializers

from boocoin.models import Block, Transaction, UnconfirmedTransaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = (
            'id', 'block', 'from_account', 'to_account', 'coins', 'extra_data',
            'time', 'signature'
        )


class UnconfirmedTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnconfirmedTransaction
        fields = (
            'id', 'from_account', 'to_account', 'coins', 'extra_data', 'time',
            'signature'
        )


class BlockSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True)

    def get_balances(self, instance):
        return instance.get_balances()

    class Meta:
        model = Block
        fields = (
            'id', 'previous_block', 'depth', 'miner', 'balances',
            'merkle_root', 'extra_data', 'time', 'signature', 'transactions'
        )
