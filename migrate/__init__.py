import os
import sys
import time
from web3.providers import HTTPProvider
from web3 import Web3
from eth_account import Account

from migrate.legacy_rep import LEGACY_REP_ADDRESS, LEGACY_REP_ABI
from migrate.rep import REP_ADDRESS, REP_ABI

w3 = Web3(HTTPProvider(os.environ.get('ETHEREUM_HTTP')))
legacyReputationToken = w3.eth.contract(address=LEGACY_REP_ADDRESS, abi=LEGACY_REP_ABI)
reputationToken = w3.eth.contract(address=REP_ADDRESS, abi=REP_ABI)

def migrate():
    private_key = os.environ.get('ETHEREUM_PRIVATE_KEY')

    if not private_key:
        print("No value found for required environment variable ETHEREUM_PRIVATE_KEY")
        sys.exit()

    account = Account.privateKeyToAccount(private_key)

    address = account.address

    nonce = w3.eth.getTransactionCount(address)

    v1_balance = legacyReputationToken.functions.balanceOf(address).call()

    if v1_balance == 0:
        print("Account %s has no V1 REP balance to migrate" % address)
        sys.exit()

    v1_display_balance = v1_balance / 10**18
    yes = input("\nThe Provided Account %s has a V1 REP balance of %f.\n\nEnter 'Y' to convert that balance into V2 REP.\n\n" % (address, v1_display_balance))

    if yes != "Y" and yes != "y":
        print("Did not migrate")
        sys.exit()

    approve(v1_balance, account, nonce)

    nonce = nonce + 1

    doMigration(account, nonce)

    print('Migration Complete')

def approve(balance, account, nonce):
    print("Approving New Rep Token for Legacy Rep Token")
    approval_function = legacyReputationToken.functions.approve(REP_ADDRESS, balance)
    sign_and_wait_for_transaction(approval_function, account, nonce, 100000, "Approval")

def doMigration(account, nonce):
    print("Migrating Rep")
    migration_function = reputationToken.functions.migrateFromLegacyReputationToken()
    sign_and_wait_for_transaction(migration_function, account, nonce, 200000, "Migration")

def sign_and_wait_for_transaction(contract_function, account, nonce, gas, name):
    transaction = contract_function.buildTransaction({
        'chainId': w3.eth.chainId,
        'gas': gas,
        'gasPrice': w3.eth.gasPrice,
        'nonce': nonce,
    })
    signed_transaction = account.signTransaction(transaction)
    tx_hash = w3.eth.sendRawTransaction(signed_transaction.rawTransaction)
    print("%s Transaction sent with Hash: %s" % (name, tx_hash.hex()))
    receipt = w3.eth.waitForTransactionReceipt(tx_hash, 240)
    if receipt.status == 0:
        raise Exception("%s Transaction Failed" % name)
    print("%s Succeeded" % name)