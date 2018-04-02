#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Pulling the latest version of boocoin..."
docker pull lsapan/boocoin

echo "Generating key pairs and settings files..."
MINERKEYS=$(docker run -v "$PWD:/home/docker/code" lsapan/boocoin ./manage.py create_test_settings)

echo "Creating database..."
docker run -v "$PWD:/home/docker/code" -e DB_NAME=db.sqlite3 lsapan/boocoin ./manage.py migrate

echo "Creating genesis block..."
docker run -v "$PWD:/home/docker/code" -e DB_NAME=db.sqlite3 -e DJANGO_SETTINGS_MODULE=local_settings1 lsapan/boocoin ./manage.py generate_genesis_block $MINERKEYS

echo "Creating test databases..."
cp db.sqlite3 db1.sqlite3
cp db.sqlite3 db2.sqlite3
cp db.sqlite3 db3.sqlite3

echo "Cleaning up..."
rm db.sqlite3

echo "Starting miners..."
docker-compose up
