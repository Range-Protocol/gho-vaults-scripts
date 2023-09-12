import datetime as datetime
import os

import pandas as pd
import numpy as np
from web3 import Web3
import time
from abi import erc20_abi, v3pool_abi, pancake_pool_abi, algebra_pool_abi
from datetime import datetime
from web3.middleware import geth_poa_middleware


rpc_url = 'https://rpc.ankr.com/eth'
w3 = Web3(Web3.HTTPProvider(rpc_url))

w3_bsc = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))
w3_arbitrum = Web3(Web3.HTTPProvider('https://1rpc.io/arb'))
w3_polygon = Web3(Web3.HTTPProvider('https://polygon.llamarpc.com'))
w3_bsc.middleware_onion.inject(geth_poa_middleware, layer=0)
w3_arbitrum.middleware_onion.inject(geth_poa_middleware, layer=0)
w3_polygon.middleware_onion.inject(geth_poa_middleware, layer=0)

config = [
    {"vault_address": "0x9Ad8d0df2dA118DcE898b7F5BD9Ab749c593A5d9",
     "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
     "name": "USDC/ETH",
     "token0": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
     "token1": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
     "startBlock": 17284954,
     "chainId": 1,
     },
    {"vault_address": "0x8Ae8b0C4e804A87CA20BB14DBDbFEFf2f2f1BD44",
     "pool_address": "0x0e2c4bE9F3408E5b1FF631576D946Eb8C224b5ED",
     "name": "GRT/ETH",
     "token0": "0xc944E90C64B2c07662A292be6244BDf05Cda44a7",
     "token1": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
     "startBlock": 17284885,
     "chainId": 1,
     },
    {"vault_address": "0x965e7249CfBDa46120C88EFcCdE1D9bD02AD7e2F",
     "pool_address": "0x39c9E3128b8736e02A30B2B9b7E50FF522b935c5",
     "name": "FXS/ETH",
     "token0": "0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0",
     "token1": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
     "startBlock": 17284954,
     "chainId": 1,
     },
    {"vault_address": "0x350D81A7733Ee6b001966e0844A0ebb096FAbF0f",
     "pool_address": "0xD1D5A4c0eA98971894772Dcd6D2f1dc71083C44E",
     "name": "LQTY/ETH",
     "token0": "0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D",
     "token1": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
     "startBlock": 17285024,
     "chainId": 1,
     },
    {"vault_address": "0x91e0FBD44472511f815680382f5E781C3B8285B4",
     "pool_address": "0x13dC0a39dc00F394E030B97b0B569dedBe634c0d",
     "name": "ANKR/ETH",
     "token0": "0x8290333ceF9e6D528dD5618Fb97a76f268f3EDD4",
     "token1": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
     "startBlock": 17285111,
     "chainId": 1,
     },
    {"vault_address": "0xc1fD7257645a3A93989Bab15ba32EA315C8f3117",
     "pool_address": "0x8dD34EEA39d0d90edFE5f8Cc8005c99B905dF139",
     "name": "GAL/ETH",
     "token0": "0x5fAa989Af96Af85384b8a938c2EdE4A7378D9875 ",
     "token1": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
     "startBlock": 17291029,
     "chainId": 1,
     },
    {"vault_address": "0x3d0D622513191E8CF2ED5A340A9180bbfA2Ca95D",
     "pool_address": "0xD340B57AAcDD10F96FC1CF10e15921936F41E29c",
     "name": "wstETH/ETH",
     "token0": "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0 ",
     "token1": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
     "startBlock": 17286148,
     "chainId": 1,
     },
    {"vault_address": "0xd40A5C0642721c0A6C6db381ccd868aa646AE10a",
     "pool_address": "0x3416cF6C708Da44DB2624D63ea0AAef7113527C6",
     "name": "USDC/USDT",
     "token0": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 ",
     "token1": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
     "startBlock": 17286033,
     "chainId": 1,
     },
    {"vault_address": "0x7deA5e8d6269a02220608d07Ae5feaE7de856868",
     "pool_address": "0x133B3D95bAD5405d14d53473671200e9342896BF",
     "name": "CAKE/BNB",
     "token0": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82 ",
     "token1": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
     "startBlock": 28168935,
     "chainId": 56,
     },
    {"vault_address": "0x48E76CC26f53DF0Ebb98C050d83c650bFC6de46d",
     "pool_address": "0x92c63d0e701CAAe670C9415d91C474F686298f00",
     "name": "ARB/ETH",
     "token0": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1 ",
     "token1": "0x912CE59144191C1204E64559FE8253a0e49E6548",
     "startBlock": 91205568,
     "chainId": 42161,
     },
    {"vault_address": "0xB99F1Ce0f1C95422913FAF5b1ea980BbC580c14a",
     "pool_address": "0x479e1B71A702a595e19b6d5932CD5c863ab57ee0",
     "name": "MATIC/ETH",
     "token0": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270 ",
     "token1": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
     "startBlock": 42851536,
     "chainId": 137,
     },
    {"vault_address": "0x06Bb3234927Fd175dFB77225DC434A2BfaB42977",
     "pool_address": "0xE936f0073549AD8b1fA53583600d629Ba9375161",
     "name": "RNDR/ETH",
     "token0": "0x6De037ef9aD2725EB40118Bb1702EBb27e4Aeb24 ",
     "token1": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
     "startBlock": 17351685,
     "chainId": 1,
     },
    {"vault_address": "0x252B35419180f0f1a1B287C637f475fBaF62B053",
     "pool_address": "0x465E56cD21ad47d4d4790F17de5E0458F20C3719",
     "name": "GALA/ETH",
     "token0": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 ",
     "token1": "0xd1d2Eb1B1e90B638588728b4130137D262C87cae",
     "startBlock": 17351685,
     "chainId": 1,
     },
    {"vault_address": "0x74e3D57025Bb1fB972eE336C93dF87c179250F5E",
     "pool_address": "0xAc4b3DacB91461209Ae9d41EC517c2B9Cb1B7DAF",
     "name": "APE/ETH",
     "token0": "0x4d224452801ACEd8B2F0aebE155379bb5D594381 ",
     "token1": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
     "startBlock": 17351685,
     "chainId": 1,
     },
    {"vault_address": "0x52fC153d440c669c1Fc8779A0508795832a51167",
     "pool_address": "0xa3f558aebAecAf0e11cA4b2199cC5Ed341edfd74",
     "name": "LDO/ETH",
     "token0": "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32 ",
     "token1": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
     "startBlock": 17351685,
     "chainId": 1,
     },
    {"vault_address": "0x3c0ACF2AC603837eFA8B247A54b42b71e706ef71",
     "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
     "name": "USDC/ETH",
     "token0": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
     "token1": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
     "startBlock": 17426827,
     "chainId": 1,
     },
    {"vault_address": "0x04f7a8FD669B6e84c3A642f6f48B1200A4B1E1E2",
     "pool_address": "0x55CAaBB0d2b704FD0eF8192A7E35D8837e678207",
     "name": "USDC/ETH",
     "token0": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
     "token1": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
     "startBlock": 43628241,
     "chainId": 137,
     },
    {"vault_address": "0xB99F1Ce0f1C95422913FAF5b1ea980BbC580c14a",
     "pool_address": "0x36696169C63e42cd08ce11f5deeBbCeBae652050",
     "name": "USDT/BNB",
     "token0": "0x55d398326f99059fF775485246999027B3197955",
     "token1": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
     "startBlock": 28888489,
     "chainId": 56,
     },
]

weth = w3.eth.contract(address=w3.to_checksum_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                       abi=erc20_abi)

# non-standard decimal coins
usdc = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
usdt = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
gala = "0xd1d2Eb1B1e90B638588728b4130137D262C87cae"
usdc_polygon = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

def get_price(vault, block):
    if vault['chainId'] == 1:
        v3_pool = w3.eth.contract(address=w3.to_checksum_address(vault['pool_address']),
                                  abi=v3pool_abi)
        slot0 = v3_pool.functions.slot0().call(block_identifier=block)
        if vault['token0'] == usdc and vault['token1'] != usdt:
            token_price = 1 / (1.0001 ** slot0[1] * 10 ** -12)
        elif vault['token1'] == gala:
            token_price = 1 / (1.0001 ** slot0[1] * 10 ** 10)
        else:
            token_price = 1 / (1.0001 ** slot0[1])
    elif vault['chainId'] == 56:
        v3_pool = w3_bsc.eth.contract(address=w3_bsc.to_checksum_address(vault['pool_address']),
                                  abi=pancake_pool_abi)
        slot0 = v3_pool.functions.slot0().call(block_identifier=block)
        token_price = 1 / (1.0001 ** slot0[1])
    elif vault['chainId'] == 42161:
        v3_pool = w3_arbitrum.eth.contract(address=w3_arbitrum.to_checksum_address(vault['pool_address']),
                                  abi=v3pool_abi)
        slot0 = v3_pool.functions.slot0().call(block_identifier=block)
        token_price = 1 / (1.0001 ** slot0[1])
    elif vault['chainId'] == 137:
        v3_pool = w3_polygon.eth.contract(address=w3_polygon.to_checksum_address(vault['pool_address']),
                                  abi=algebra_pool_abi)
        slot0 = v3_pool.functions.globalState().call(block_identifier=block)
        if vault['token0'] == usdc_polygon:
            token_price = 1 / (1.0001 ** slot0[1] * 10 ** -12)
        else:
            token_price = 1 / (1.0001 ** slot0[1])
    print(token_price)
    return token_price


while 1:
    for vault in config:
        chainId = vault['chainId']
        if chainId == 1:
            incr = 500
            w3Cli = w3
        elif chainId == 56:
            incr = 2000
            w3Cli = w3_bsc
        elif chainId == 42161:
            incr = 20000
            w3Cli = w3_arbitrum
        elif chainId == 137:
            incr = 2000
            w3Cli = w3_polygon
        fileName = '../uni-analytics/data/prices/' + str(chainId) + '-' + w3.to_checksum_address(vault["vault_address"]) + '.csv'
        exists = os.path.exists(fileName)
        if not exists:
            file = open(fileName, 'a')
            file.write('Block,price,timestamp\n')
            file.close()
        df = pd.read_csv(fileName)
        if df.empty:
            block = vault["startBlock"]
            df.to_csv(fileName, index=False)
        else:
            block = int(df.iloc[-1].Block) + incr
        while block < w3Cli.eth.block_number:
            try:
                price = get_price(vault, int(block))
                ts = datetime.fromtimestamp(w3Cli.eth.get_block(block).timestamp)
                data = [block, price, ts]
                df.loc[len(df)] = data
                block += incr
                df.to_csv(fileName, index=False)
            except Exception as e:
                print(e)
    time.sleep(600)
