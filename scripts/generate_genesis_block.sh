#!/bin/bash

docker-compose run miner ./manage.py generate_genesis_block $@
