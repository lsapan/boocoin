<div align="center">
    <img src="https://user-images.githubusercontent.com/3203257/38212099-92c0602e-368a-11e8-9049-d03deb294749.PNG" width="256" height="256">
</div>

# Boocoin
A toy HTTP-based Proof of Authority cryptocurrency written in Python with Django and Django REST Framework.

Welcome to the blockchain, Django!


## Why?
Let's just get this out here now, this is obviously not meant to be a robust cryptocurrency. It was just a fun experiment to try out. Use [something real](https://github.com/ethereum/pyethereum) if you're looking for a blockchain to fork.


## Getting Started
Ready to run your own blockchain on Django? You'll find it's incredibly simple, just make sure you have Docker [installed first](https://docs.docker.com/install/).

From the project root, run:

```
./scripts/provision_test_nodes.sh
```

That's it! In a few moments you'll have a blockchain network running with 3 miners. Here's what that command did for you:
1) Create three key pairs (one for each miner)
2) Create a genesis block with the public keys of the miners in it. Only these miners will be authorized to mine new blocks. (In case you missed it, this is Proof of Authority, not Proof of Work.)
3) Set up each miner's database and configuration settings.
4) Start up the 3 miners.

You can press `Ctrl + C` when you're ready to stop the miners. If you want to run them again in the future, simply run:

```
docker-compose up
```

Running `provision_test_nodes.sh` again will wipe out your existing blockchain, so keep that in mind.


## Interacting with the Blockchain
So you have some miners, awesome. While you could idly watch them mine blocks every 10 minutes, that _could_ get boring. Good news my friend, there are APIs you can use! We are using Django after all.

### How to make API calls
Fire up your favorite HTTP client (I recommend [Paw](https://paw.cloud) if you're on a Mac), and point it to `http://localhost:9811`. This assumes that you provisioned your miners with the script above of course.

You can change the port to determine which miner you talk to:

    9811: miner 1
    9812: miner 2
    9813: miner 3


### Query the block count

```
GET /api/block_count/
```
This will give you the number of blocks in the longest chain. Keep in mind there may be more blocks in the database, but they're not important right now.


### Get all of a single block's data

```
GET /api/block/{block_hash}/
```

This will give you all of the block's data, along with all of the data of the transactions that belong to it.


### Get a single transaction's data

```
GET /api/transaction/{transaction_hash}/
```

This will give you all of the transaction's data.


### Submit a transaction to the blockchain

```
POST /api/submit_transaction/
```

This will create a transaction and send it off to the pool of unconfirmed transactions. (I've heard it's sunny there!)

This API expects you to send some extra data along in either JSON or Form URL-Encoded format:

- `private_key` - the private key of the wallet to send coins from
- `to_account` - the public key of the wallet to send coins to
- `coins` - the number of coins to send

If you're sending data in form format, you can also send a fourth `extra_data` parameter which can contain arbitrary binary data.

### Peer-to-peer APIs
There are other API endpoints that are used by the miners to communicate with eachother and send blocks/transactions around. I won't write about them here, but just know they exist if you really want them.
