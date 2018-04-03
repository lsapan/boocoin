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
    """
    A block in the blockchain.

    Blocks contains transactions among other data, and can only be mined by the
    miners who are defined in the genesis block. Blocks are mined when there
    are 10 unconfirmed transactions, or every 10 minutes, whichever comes
    first.

    Only one chain of blocks are considered active at one time. The chain made
    up of the most blocks is treated as the active chain, with the final
    block's hash used as a tiebreaker if necessary.

    Attributes:
        id (str): The SHA3-256 hash of everything in the block, with the
            exception of the signature.
        previous_block (str): The hash of the block that preceded this block
            in the chain.
        depth (int): The distance of the block from the beginning of the chain.
            This is used to quickly find the longest chain. Note that the depth
            of the genesis block is 0.
        miner (str): The public key of the miner that mined this block.
        balances (str): A JSON string containing a dictionary of account
            balances. Use get_balances() to properly parse balances as
            decimals.
        merkle_root (str): The merkle root hash of all the balances included in
            this block.
        extra_data (bytes): Arbitrary data that can be included with the block
            by the miner. In the case of the genesis block, this is a JSON
            string containing an array of public keys that are authorized to
            mine new blocks.
        time (datetime): The time that the block was mined. Note that while
            there are some sanity checks, it is not difficult for a miner to
            lie about when the block was created.
        signature (str): A signature of the block's id from the miner.
    """

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
        """
        Returns the genesis block, which will always be the only block with a
        depth of 0.
        """
        return cls.objects.get(depth=0)

    @classmethod
    def get_active_block(cls):
        """
        Returns the latest block in the longest chain. If two blocks have the
        same depth, the block whose hash comes first alphabetically will be
        chosen.
        """
        return cls.objects.order_by('-depth', 'id')[:1][0]

    def get_balances(self):
        """
        Returns a dictionary of decimal balances, keyed by public key.
        """
        balances = json.loads(self.balances, object_pairs_hook=OrderedDict)
        for a, b in balances.items():
            balances[a] = Decimal(b)
        return balances

    def set_balances(self, balances):
        """
        Updates the block's balances.
        """
        self.balances = json.dumps(balances)

    def calculate_hash(self):
        """
        Serializes all of the block's data and returns the hash of the block.
        """
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
        """
        Calculates and stores the hash of the block.
        """
        self.id = self.calculate_hash()

    def set_merkle_root(self, transactions):
        """
        Calculates and stores the merkle root for the passed transactions on
        the block.
        """
        self.merkle_root = calculate_merkle_root(t.hash for t in transactions)

    def sign(self):
        """
        Signs the block with the private key of the current miner.
        """
        self.signature = sign(self.id)

    def save(self, transactions):
        """
        Saves the block along with its transactions.
        """
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
    """
    Mixin for calculating transaction hashes. Allows the Transaction and
    UnconfirmedTransaction models to share this logic.
    """

    def calculate_hash(self):
        """
        Serializes all of the transactions's data and returns the hash.
        """
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
    """
    A transaction represents the exchange of coins from one account (wallet) to
    another. Transactions can also store arbitrary data, and are therefore
    quite versatile.

    While a from_account is usually required, each block contains a special
    transaction which awards 100 coins to the miner (or their wallet) that
    mined the block. That transaction does not have a from_account, and has a
    fixed string for a signature.

    Transaction hashes are not unique because the same transaction may be
    pulled into sibling blocks by different miners. With that said,
    transaction hashes may not be duplicated within the same chain.

    Attributes:
        hash (str): The SHA3-256 hash of everything in the transaction, with
            the exception of the signature and the block hash. The block hash
            is not factored in because it is not known at the time of
            calculation.
        block (boocoin.models.Block): The block that the transaction was
            included in.
        from_account (str): The public key of the wallet that sent coins.
        to_account (str): The public key of the wallet that received coins.
        coins (Decimal): The number of coins that were sent.
        extra_data (bytes): Arbitrary data that can be included with the
            transaction by the sender.
        time (datetime): The time that the transaction was created. Note that
            while there are some sanity checks, it is not difficult for a miner
            to lie about when the transaction was created.
        signature (str): A signature of the transaction's hash by the sender.
    """

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
        """
        Calculates and stores the hash of the transaction.
        """
        self.hash = self.calculate_hash()

    @classmethod
    def create_block_reward(cls):
        """
        Creates and returns a generic block reward transaction, awarding 100
        coins to the configured wallet.
        """
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
    """
    Unconfirmed transactions are simply transactions that haven't been included
    in a block yet. Blocks are only created every 10 minutes, or when there are
    at least 10 unconfirmed transactions.

    For more information about fields, see the docstring for regular
    transactions.
    """
    hash = models.CharField(max_length=64, primary_key=True)
    from_account = models.CharField(max_length=96, db_index=True)
    to_account = models.CharField(max_length=96, db_index=True)
    coins = models.DecimalField(max_digits=20, decimal_places=8)
    extra_data = models.BinaryField(null=True)
    time = models.DateTimeField()
    signature = models.CharField(max_length=96)

    def to_transaction(self):
        """
        Maps the unconfirmed transaction's data and returns a Transaction.
        """
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
    """
    A row is added to this table whenever we are actively syncing with another
    miner/node. The mining process checks this table before creating any new
    blocks, preventing us from mining blocks when we aren't fully up to date
    with the rest of the network.
    """
    node = models.CharField(max_length=255)
