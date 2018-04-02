"""
This template is used by provision_test_nodes.sh.
Use local_settings.example.py if you're configuring by hand.
"""

from boocoin.settings import *


LOGGING['loggers']['boocoin']['level'] = 'DEBUG'


# Network Nodes
# Don't include the IP of the active node, just the additional nodes.

NODES = [{{ nodes }}]


# Miner Configuration
# Your miner and wallet keys can be the same, but they don't have to be.
# The wallet public key will receive the 100 coin block reward.

MINER_IP = '{{ miner_ip }}'

MINER_PUBLIC_KEY = '{{ vk }}'

MINER_PRIVATE_KEY = '{{ sk }}'

WALLET_PUBLIC_KEY = '{{ vk }}'


# Extra Block Data
# This data will be included with every blocked mined by this miner.

BLOCK_EXTRA_DATA = b''
