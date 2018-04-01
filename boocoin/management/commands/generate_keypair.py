from django.core.management.base import BaseCommand

from boocoin.signing import generate_keypair


class Command(BaseCommand):
    help = 'Generates a private and public keypair suitable for use.'

    def handle(self, *args, **options):
        sk, pk = generate_keypair()
        self.stdout.write(f"""Your keypair has been generated.
Your secret key is: {sk}
Your public key is: {pk}""")
