from django.db import models


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
    extra_data = models.BinaryField(null=True)
    time = models.DateTimeField()
    signature = models.CharField(max_length=96)


class Transaction(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    block = models.ForeignKey(
        Block,
        related_name='transactions',
        on_delete=models.CASCADE
    )
    from_account = models.CharField(
        max_length=96,
        db_index=True,
        null=True
    )
    to_account = models.CharField(max_length=96, db_index=True)
    coins = models.DecimalField(max_digits=20, decimal_places=8)
    extra_data = models.BinaryField(null=True)
    time = models.DateTimeField()
    signature = models.CharField(max_length=96)
