import simplejson as json
import sys

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.timezone import now

from boocoin.balances import apply_transaction_to_balances
from boocoin.models import Block, Transaction


class Command(BaseCommand):
    help = 'Generates a genesis block and writes it to a file.'

    def add_arguments(self, parser):
        parser.add_argument('miner_public_keys', nargs='+', type=str)

    def handle(self, *args, **options):
        miners = options['miner_public_keys']

        # Verify the user doesn't already have a genesis block
        if Block.objects.count() > 0:
            sys.stderr.write("You already have a genesis block!\n")
            sys.exit(1)

        # This block will be signed by the miner, so its key must be included
        if settings.MINER_PUBLIC_KEY not in miners:
            sys.stderr.write("Your public key must be included.\n")
            sys.exit(1)

        # Set up the first transaction
        transaction = Transaction.create_block_reward()
        transactions = [transaction]

        # Set up the genesis block
        block = Block(
            depth=0,
            miner=settings.MINER_PUBLIC_KEY,
            extra_data=json.dumps(miners).encode('utf-8'),
            time=now(),
        )
        block.set_merkle_root(transactions)
        block.set_balances(apply_transaction_to_balances(transaction, {}))
        block.set_hash()
        block.sign()
        block.save(transactions)

        # Store the genesis block information in a file
        call_command(
            'dumpdata',
            'boocoin.Block',
            'boocoin.Transaction',
            indent=4,
            output='genesis.json'
        )
        self.stdout.write('Genesis block saved to db and genesis.json\n')
