import simplejson as json
from binascii import hexlify
from collections import OrderedDict
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction as db_transaction
from django.utils.timezone import now

from boocoin.hashing import create_hash, calculate_merkle_root
from boocoin.signing import sign
from boocoin.util.db import query_value


class Block(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    previous_block = models.ForeignKey(
        'self',
        null=True,
        related_name='children',
        on_delete=models.CASCADE
    )
    depth = models.IntegerField()
    miner = models.CharField(max_length=96)
    balances = models.TextField()
    merkle_root = models.CharField(max_length=64)
    extra_data = models.BinaryField(null=True)
    time = models.DateTimeField()
    signature = models.CharField(max_length=96)

    @classmethod
    def get_genesis_block(cls):
        return cls.objects.get(depth=0)

    @classmethod
    def get_active_block(cls):
        """
        Returns the latest block in the longest chain.
        """
        return cls.objects.order_by('-depth', 'id')[:1][0]

    def get_balances(self):
        balances = json.loads(self.balances, object_pairs_hook=OrderedDict)
        for a, b in balances.items():
            balances[a] = Decimal(b)
        return balances

    def set_balances(self, balances):
        self.balances = json.dumps(balances)

    def calculate_hash(self):
        extra_data = None
        if self.extra_data:
            extra_data = hexlify(self.extra_data).decode('utf-8')

        data = json.dumps(OrderedDict([
            ('previous_block', self.previous_block_id),
            ('depth', self.depth),
            ('miner', self.miner),
            ('balances', self.balances),
            ('merkle_root', self.merkle_root),
            ('extra_data', extra_data),
            ('time', self.time),
        ]), default=str)
        return create_hash(data)

    def set_hash(self):
        self.id = self.calculate_hash()

    def set_merkle_root(self, transactions):
        self.merkle_root = calculate_merkle_root(t.hash for t in transactions)

    def sign(self):
        self.signature = sign(self.id)

    def save(self, transactions):
        with db_transaction.atomic():
            super().save()
            for t in transactions:
                t.block = self
                t.save()

    def has_transaction_in_chain(self, tx_hash):
        """
        Returns whether or not the provided transaction exists anywhere
        upstream in the chain (including this block).
        """
        return bool(query_value("""
            WITH RECURSIVE
            txsearch(block_id, parent_id, has_tx) AS (
                SELECT b.id, b.previous_block_id, t.hash
                    FROM boocoin_block b
                    LEFT JOIN boocoin_transaction t
                        ON t.block_id = b.id AND t.hash = %s
                    WHERE b.id = %s
                UNION ALL
                SELECT b.id, b.previous_block_id, t.hash
                    FROM boocoin_block b
                    INNER JOIN txsearch p ON p.parent_id = b.id
                    LEFT JOIN boocoin_transaction t
                        ON t.block_id = b.id AND t.hash = %s
                    WHERE b.id IS NOT NULL
                    LIMIT 100
            )
            SELECT CASE WHEN COUNT(*) THEN 1 ELSE 0 END AS tx_found
            FROM txsearch
            WHERE has_tx IS NOT NULL;
        """, tx_hash, self.id, tx_hash))


class TransactionHashMixin:
    def calculate_hash(self):
        extra_data = None
        if self.extra_data:
            extra_data = hexlify(self.extra_data).decode('utf-8')

        data = json.dumps(OrderedDict([
            ('from_account', self.from_account),
            ('to_account', self.to_account),
            ('coins', self.coins),
            ('extra_data', extra_data),
            ('time', self.time),
        ]), default=str)
        return create_hash(data)


class Transaction(TransactionHashMixin, models.Model):
    hash = models.CharField(max_length=64)
    block = models.ForeignKey(
        Block,
        related_name='transactions',
        on_delete=models.CASCADE
    )
    from_account = models.CharField(max_length=96, db_index=True, null=True)
    to_account = models.CharField(max_length=96, db_index=True)
    coins = models.DecimalField(max_digits=20, decimal_places=8)
    extra_data = models.BinaryField(null=True)
    time = models.DateTimeField()
    signature = models.CharField(max_length=96)

    class Meta:
        unique_together = (('hash', 'block'),)
        ordering = ['id']

    def set_hash(self):
        self.hash = self.calculate_hash()

    @classmethod
    def create_block_reward(cls):
        reward = cls(
            from_account=None,
            to_account=settings.WALLET_PUBLIC_KEY,
            coins=Decimal('100.00000000'),
            time=now(),
            signature='boocoin-block-reward',
        )
        reward.set_hash()
        return reward


class UnconfirmedTransaction(TransactionHashMixin, models.Model):
    hash = models.CharField(max_length=64, primary_key=True)
    from_account = models.CharField(max_length=96, db_index=True)
    to_account = models.CharField(max_length=96, db_index=True)
    coins = models.DecimalField(max_digits=20, decimal_places=8)
    extra_data = models.BinaryField(null=True)
    time = models.DateTimeField()
    signature = models.CharField(max_length=96)

    def to_transaction(self):
        return Transaction(
            hash=self.hash,
            from_account=self.from_account,
            to_account=self.to_account,
            coins=self.coins,
            extra_data=self.extra_data,
            time=self.time,
            signature=self.signature,
        )


class SyncLock(models.Model):
    node = models.CharField(max_length=255)
