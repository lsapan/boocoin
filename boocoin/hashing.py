from binascii import hexlify
import hashlib

from merkletools import MerkleTools


def create_hash(content):
    hasher = hashlib.sha3_256()
    hasher.update(content.encode('utf-8'))
    return hexlify(hasher.digest()).decode('utf-8')


def calculate_merkle_root(hashes):
    mt = MerkleTools(hash_type='sha3_256')

    for h in hashes:
        mt.add_leaf(h)

    mt.make_tree()
    return mt.get_merkle_root()
