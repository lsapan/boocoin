import os

import jinja2
from django.conf import settings
from django.core.management.base import BaseCommand

from boocoin.signing import generate_keypair

all_miners = set(['miner1', 'miner2', 'miner3'])


class Command(BaseCommand):
    help = 'Generates keypairs and settings files for test nodes.'

    def handle(self, *args, **options):
        # Load the local_settings template
        loader = jinja2.FileSystemLoader(settings.BASE_DIR)
        template = jinja2.Environment(loader=loader)\
            .get_template('local_settings.template.py')

        # Create the keys and settings files
        for i in range(1, 4):
            sk, vk = generate_keypair()
            self.stdout.write(vk)
            fname = f'local_settings{i}.py'
            miners = list(all_miners - set([f'miner{i}']))
            with open(os.path.join(settings.BASE_DIR, fname), 'w') as f:
                f.write(template.render(
                    nodes="'" + "', '".join(miners) + "'",
                    miner_ip=f'miner{i}',
                    sk=sk,
                    vk=vk,
                ))
