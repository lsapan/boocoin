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


# Miner Public Keys

MINER_PUBLIC_KEYS = [
    # 'abcdef...',
    # 'a1b2c3...',
]


# Miner Configuration
# Your miner and wallet private key can be the same, but they don't have to be.
# The wallet private key will receive the 100 coin block reward.

MINER_PRIVATE_KEY = ''

WALLET_PRIVATE_KEY = ''
