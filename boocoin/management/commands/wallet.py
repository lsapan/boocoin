import json
import os
import sys
from decimal import Decimal

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from boocoin.models import UnconfirmedTransaction
from boocoin.p2p import normalize_node
from boocoin.serializers import UnconfirmedTransactionSerializer
from boocoin.signing import (
    generate_keypair, hex_to_sk, hex_to_pk, key_to_hex, sign
)

wallet_path = os.path.join(settings.BASE_DIR, 'wallet.txt')


class Command(BaseCommand):
    help = 'Allows you to access your wallet and send transactions.'

    def handle(self, *args, **options):
        self.main_menu()

    def main_menu(self):
        while True:
            action = input('Welcome to your wallet. Your options are:\n1) Add a new key\n2) List keys\n3) Send coins (or data)\n4) Quit\nEnter your selection: ')
            if action == '4':
                break
            elif action == '1':
                self.prompt_new_key()
            elif action == '2':
                self.list_keys()
            elif action == '3':
                self.send_coins()

            self.stdout.write('\n')

    def prompt_new_key(self):
        key = input('Please enter your private key, or leave blank to generate: ')
        if not key:
            key = generate_keypair()[0]
        else:
            # Validate that the passed key is valid
            try:
                sk = hex_to_sk(key)
            except Exception:
                self.stderr.write('That is not a valid private key.\n')
                return
        self._add_key(key)
        self.stdout.write('Your key has been added.')

    def list_keys(self):
        self.stdout.write('\nYour public keys are:\n')
        for idx, key in enumerate(self._get_keys()):
            sk = hex_to_sk(key)
            vk = sk.get_verifying_key()
            vk_hex = key_to_hex(vk)
            self.stdout.write(f'{idx}: {vk_hex}\n')

    def send_coins(self):
        # Get the from_account
        self.list_keys()
        from_idx = int(input('Enter the index of the private key to send coins from: '))
        from_account = self._get_key(from_idx)

        # Get the to_account
        to_account = input('Enter the public key to send coins to: ')
        try:
            vk = hex_to_pk(to_account)
        except Exception:
            self.stderr.write('That is not a valid public key.\n')
            return

        # Get the number of coins
        coins = Decimal(input('Enter the number of coins to send: '))
        coins = Decimal('{0:.8f}'.format(Decimal(coins)))

        # Get the extra_data
        extra_data_path = input('Enter the file to include as extra binary data (or leave blank to skip): ')
        if extra_data_path:
            try:
                with open(extra_data_path, 'rb') as f:
                    extra_data = f.read()
            except FileNotFoundError:
                self.stderr.write('File not found.\n')
                return
        else:
            extra_data = None

        # Build the transaction
        private_key = hex_to_sk(from_account)
        from_account = key_to_hex(private_key.get_verifying_key())
        transaction = UnconfirmedTransaction(
            from_account=from_account,
            to_account=to_account,
            coins=coins,
            time=now(),
            extra_data=extra_data,
        )
        transaction.hash = transaction.calculate_hash()
        transaction.signature = sign(transaction.hash, sk=private_key)

        # Serialize the transaction
        tx = UnconfirmedTransactionSerializer(transaction).data
        self.stdout.write(f'Transaction created and signed:\n{json.dumps(tx)}')

        # Send to a miner
        miner_host = input('Enter the host url for a miner to send it (or leave blank to skip): ')
        if miner_host:
            response = requests.post(
                f'{normalize_node(miner_host)}/api/submit_transaction/',
                json=tx
            )

            code = response.status_code
            if code == 200:
                self.stdout.write('Transaction submitted!\n')
            elif code >= 400 and code < 500:
                self.stderr.write('Failed to submit transaction:\n')
                self.stderr.write(json.dumps(response.json()))
            else:
                self.stderr.write(f'Error, server returned code: {code}')

    def _add_key(self, key):
        with open(wallet_path, 'a') as f:
            f.write(f'{key}\n')

    def _get_keys(self):
        try:
            with open(wallet_path, 'r') as f:
                return [k.strip() for k in f.readlines()]
        except FileNotFoundError:
            self.stderr.write('You do not have any keys stored.')
            sys.exit(1)

    def _get_key(self, idx):
        try:
            return self._get_keys()[idx]
        except IndexError:
            self.stderr.write('Key does not exist.')
            sys.exit(1)
