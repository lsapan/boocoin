"""
This file is a starting point for your local configuration file.

Start by duplicating this file and naming it local_settings.py.
Then, simply fill in the configuration appropriately for your setup.

You can generate keypairs by running scripts/generate_keypair.sh.
"""

from boocoin.settings import *


# Network Nodes
# Don't include the IP of the active node, just the additional nodes.

NODES = [
    # '10.20.30.40',
    # '10.20.30.41:9811',
    # '10.20.30.42:9812',
]


# Miner Configuration
# Your miner and wallet keys can be the same, but they don't have to be.
# The wallet public key will receive the 100 coin block reward.

MINER_PUBLIC_KEY = ''

MINER_PRIVATE_KEY = ''

WALLET_PUBLIC_KEY = ''


# Extra Block Data
# This data will be included with every blocked mined by this miner.

BLOCK_EXTRA_DATA = b''
