import logging

from django.utils.timezone import now
from rest_framework import serializers

from boocoin.mining import mine_block
from boocoin.models import Block, UnconfirmedTransaction
from boocoin.p2p import broadcast_transaction
from boocoin.serializers import TransactionSerializer
from boocoin.signing import SigningKey, VerifyingKey, key_to_hex, unhex, sign
from boocoin.validation import validate_transaction

logger = logging.getLogger(__name__)


class TransactionForm(serializers.Serializer):
    private_key = serializers.CharField(max_length=48)
    to_account = serializers.CharField(max_length=96)
    coins = serializers.DecimalField(max_digits=20, decimal_places=8)
    extra_data = serializers.FileField(required=False)

    def validate_private_key(self, key):
        try:
            return SigningKey.from_string(unhex(key))
        except Exception:
            raise serializers.ValidationError('Invalid private key.')

    def validate_to_account(self, key):
        try:
            VerifyingKey.from_string(unhex(key))
        except Exception:
            raise serializers.ValidationError('Invalid public key.')
        return key

    def validate_coins(self, coins):
        if coins <= 0:
            raise serializers.ValidationError('Must be a positive number.')
        return coins

    def validate_extra_data(self, data):
        return data.read()

    def validate(self, data):
        # Build the transaction
        from_account = key_to_hex(data['private_key'].get_verifying_key())
        transaction = UnconfirmedTransaction(
            from_account=from_account,
            to_account=data['to_account'],
            coins=data['coins'],
            time=now(),
            extra_data=data.get('extra_data'),
        )
        transaction.hash = transaction.calculate_hash()
        transaction.signature = sign(transaction.hash, sk=data['private_key'])
        data['transaction'] = transaction

        # Validate the transaction
        active_block = Block.get_active_block()
        if not validate_transaction(active_block.get_balances(), transaction):
            raise serializers.ValidationError('Transaction was not accepted.')

        return data

    def save(self):
        self.transaction = self.validated_data['transaction']
        self.transaction.save()

        # Mine a block if we have at least 10 transaction waiting
        if UnconfirmedTransaction.objects.count() >= 10:
            logger.info('At least 10 transactions waiting, mining new block.')
            mine_block()
        else:
            # Notify other nodes about the transaction
            broadcast_transaction(self.transaction)

    def to_representation(self, instance):
        self.transaction.block = None
        return TransactionSerializer(self.transaction).data
