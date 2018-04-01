from binascii import hexlify, unhexlify

from django.conf import settings
from ecdsa import SigningKey, VerifyingKey


def key_to_hex(key):
    return hexlify(key.to_string()).decode('utf-8')


def unhex(key):
    return unhexlify(key.encode('utf-8'))


def generate_keypair():
    """
    Returns a tuple with the generated private and public keys.
    """
    sk = SigningKey.generate()
    vk = sk.get_verifying_key()
    return (key_to_hex(sk), key_to_hex(vk))


def sign(content):
    sk = SigningKey.from_string(unhex(settings.MINER_PRIVATE_KEY))
    return hexlify(sk.sign(content.encode('utf-8'))).decode('utf-8')
