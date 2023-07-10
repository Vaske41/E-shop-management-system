from web3 import Web3, HTTPProvider
import os


def read_file(path):
    with open(path, "r") as file:
        return file.read()


blockchainURL = os.environ['BlockchainURL']

web3 = Web3(HTTPProvider(f"http://{blockchainURL}:8545"))
bytecode = read_file('./order.bin')
abi = read_file('./order.abi')

orderContractInterface = web3.eth.contract(bytecode=bytecode, abi=abi)
owner = web3.eth.accounts[0]
