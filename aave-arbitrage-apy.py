# import json
# from datetime import datetime
# from web3 import Web3
# import requests
# import time
#
# data_file = open("data.json")
# data = json.load(data_file)
# chain_data = data["chain_data"]
# rpc_urls = data["rpc_urls"]
#
# explorer_url = "https://api.{explorer_name}/api?module=logs&action=getLogs&fromBlock={from_block}&toBlock=latest&address={vault}&topic0={topic}&apikey={api_key}"
# chain_to_explorer_name = {
#     "ethereum": "etherscan.com",
#     "arbitrum": "arbiscan.io",
#     "bsc": "bscscan.com",
#     "polygon": "polygonscan.com"
# }
# chain_to_explorer_api_key = {
#     "ethereum": "DNRBUQ9BW2YU2777ZAF4767QS2B6AHQIGS",
#     "arbitrum": "XPQH853TTPK4PJSD5ZVNIUQ7AUJJMQQRZF",
#     "bsc": "XDSTRY7M9CDMZFEHGUDEQYAKI4DJJDBDZ9",
#     "polygon": "UQU8PVWE6YEVS8BNPQCYWPFAYC6VCYV75J"
# }
#
# timestamp_now = datetime.now().timestamp().__floor__()
# seconds_seven_days = 604800
# hours_in_seven_days = 168
# aave_base_market_currency_multiplier = 10 ** 8
#
#
# def create_function_selector(function_signature):
#     return Web3.keccak(text=function_signature).hex()[0:10]
#
#
# def call(w3, to, data, block=0):
#     return w3.eth.call({
#         "gas": 10_000_000,
#         "to": to,
#         "data": data,
#     }, block_identifier="latest" if block == 0 else block).hex()
#
# pool_rebalanced_hash = Web3.keccak(text="PoolRebalanced()").hex()
# get_balance_in_collateral_token_selector = create_function_selector("getBalanceInCollateralToken()")
# get_current_fees_selector = create_function_selector("getCurrentFees()")
# token0_selector = create_function_selector("token0()")
# token1_selector = create_function_selector("token1()")
# decimals_selector = create_function_selector("decimals()")
#
#
# def process_vault(name, chain, vault, deploy_block, blocks_in_hour, w3):
#     latest_block = w3.eth.block_number
#     block_at_last_week = latest_block - (blocks_in_hour * (hours_in_seven_days * 2))
#     if deploy_block > block_at_last_week:
#         block_at_last_week = deploy_block
#
#     # fetch events from last seven days or first block if deployment block is less than 7 days old
#     pool_rebalanced_events = requests.get(explorer_url.format(
#         explorer_name=chain_to_explorer_name[chain],
#         from_block=block_at_last_week,
#         vault=vault,
#         topic=pool_rebalanced_hash,
#         api_key=chain_to_explorer_api_key[chain]
#     )).json()["result"]
#
#     blocks = set()
#     for event in pool_rebalanced_events:
#         blocks.add(toInt(event["blockNumber"]))
#
#     decimal0 = toInt(
#         call(w3, w3.to_checksum_address(call(w3, vault, token0_selector)[26:66]), decimals_selector)[58:66])
#     decimal1 = toInt(
#         call(w3, w3.to_checksum_address(call(w3, vault, token1_selector)[26:66]), decimals_selector)[58:66])
#
#     apy = 0
#     for block in blocks:
#         prev_fee_data = call(w3, vault, get_current_fees_selector, block - 1)
#         prev_fee = (toInt(prev_fee_data[0: 66]) * 10 ** decimal1 / 10 ** decimal0) + toInt(prev_fee_data[66: 130])
#         prev_balance = toInt(call(w3, vault, get_balance_in_collateral_token_selector, block - 1))
#         prev_amount = prev_balance - prev_fee
#
#         current_fee_data = call(w3, vault, get_current_fees_selector, block)
#         current_fee = (toInt(current_fee_data[0: 66]) * 10 ** decimal1 / 10 ** decimal0) + toInt(current_fee_data[66: 130])
#         current_balance = toInt(call(w3, vault, get_balance_in_collateral_token_selector, block))
#         current_amount = current_balance - current_fee
#
#         diff = current_amount - prev_amount
#         apy += diff / current_balance
#
#     return apy * 52
#
#
# def toInt(value):
#     return int(value, 16)
#
#
# while 1:
#     for data in chain_data:
#         if len(data["vaults"]) > 0:
#             print("AMM: {name}".format(name=data["name"]))
#             w3 = Web3(Web3.HTTPProvider(rpc_urls[data["chain"]]))
#             records = {}
#             for idx, vault in enumerate(data["vaults"]):
#                 print("Vault: {vault}".format(vault=vault))
#                 records[vault] = process_vault(
#                     data["name"],
#                     data["chain"],
#                     vault,
#                     data["deploy_blocks"][idx],
#                     data["blocks_in_hour"],
#                     w3
#                 )
#             json_object = json.dumps(records, indent=4)
#             with open("../uni-analytics/data/aave-arbitrage-apy-{}.json".format(data["name"]), "w") as outfile:
#                 outfile.write(json_object)
#     time.sleep(1800)
