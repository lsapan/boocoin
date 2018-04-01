from binascii import hexlify

from ecdsa import SigningKey, VerifyingKey


def key_to_hex(key):
    return hexlify(key.to_string()).decode('utf-8')


def generate_keypair():
    """
    Returns a tuple with the generated private and public keys.
    """
    sk = SigningKey.generate()
    vk = sk.get_verifying_key()
    return (key_to_hex(sk), key_to_hex(vk))
