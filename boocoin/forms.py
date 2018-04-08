import logging
from base64 import b64decode

from django.utils.timezone import now
from rest_framework import serializers

from boocoin.mining import mine_block
from boocoin.models import Block, UnconfirmedTransaction
from boocoin.p2p import broadcast_transaction
from boocoin.serializers import (
    TransactionSerializer, UnconfirmedTransactionSerializer
)
from boocoin.signing import (
    SigningKey, VerifyingKey, key_to_hex, unhex, sign, verify
)
from boocoin.validation import validate_transaction

logger = logging.getLogger(__name__)


class TransactionForm(UnconfirmedTransactionSerializer):
    def validate_from_account(self, key):
        try:
            VerifyingKey.from_string(unhex(key))
        except Exception:
            raise serializers.ValidationError('Invalid public key.')
        return key

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

    def validate(self, data):
        # Check for extra data
        extra_data = self.context['request'].data.get('extra_data')
        if not data.get('extra_data') and extra_data:
            data['extra_data'] = b64decode(extra_data)

        # Build the transaction
        tx = UnconfirmedTransaction(**data)

        # Verify the hash
        tx.hash = tx.calculate_hash()
        if tx.hash != data['hash']:
            raise serializers.ValidationError('Invalid hash')

        # Verify the signature
        if not verify(tx.hash, tx.from_account, tx.signature):
            raise serializers.ValidationError('Bad signature')

        data['transaction'] = tx

        # Validate the transaction
        active_block = Block.get_active_block()
        if not validate_transaction(
            active_block.get_balances(),
            tx,
            prev_block=active_block,
        ):
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
