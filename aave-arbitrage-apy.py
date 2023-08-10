import json
from datetime import datetime
from web3 import Web3
import requests
import time

data_file = open("data.json")
data = json.load(data_file)
chain_data = data["chain_data"]
rpc_urls = data["rpc_urls"]

explorer_url = "https://api.{explorer_name}/api?module=logs&action=getLogs&fromBlock={from_block}&toBlock=latest&address={vault}&topic0={topic}&apikey={api_key}"
chain_to_explorer_name = {
    "ethereum": "etherscan.com",
    "arbitrum": "arbiscan.io",
    "bsc": "bscscan.com",
    "polygon": "polygonscan.com"
}
chain_to_explorer_api_key = {
    "ethereum": "DNRBUQ9BW2YU2777ZAF4767QS2B6AHQIGS",
    "arbitrum": "XPQH853TTPK4PJSD5ZVNIUQ7AUJJMQQRZF",
    "bsc": "XDSTRY7M9CDMZFEHGUDEQYAKI4DJJDBDZ9",
    "polygon": "UQU8PVWE6YEVS8BNPQCYWPFAYC6VCYV75J"
}

timestamp_now = datetime.now().timestamp().__floor__()
seconds_seven_days = 604800
hours_in_seven_days = 168
aave_base_market_currency_multiplier = 10 ** 8


def create_function_selector(function_signature):
    return Web3.keccak(text=function_signature).hex()[0:10]


def call(w3, to, data, block=0):
    return w3.eth.call({
        "gas": 10_000_000,
        "to": to,
        "data": data,
    }, block_identifier="latest" if block == 0 else block).hex()


collateral_supplied_hash = Web3.keccak(text="CollateralSupplied(address,uint256)").hex()
collateral_withdrawn_hash = Web3.keccak(text="CollateralWithdrawn(address,uint256)").hex()
gho_minted_hash = Web3.keccak(text="GHOMinted(uint256)").hex()
gho_burned_hash = Web3.keccak(text="GHOBurned(uint256)").hex()
get_underlying_balance_selector = create_function_selector("getUnderlyingBalance()")
get_current_fees_selector = create_function_selector("getCurrentFees()")
is_token0_gho_selector = create_function_selector("isToken0GHO()")
token0_selector = create_function_selector("token0()")
token1_selector = create_function_selector("token1()")
decimals_selector = create_function_selector("decimals()")


def process_vault(name, chain, vault, deploy_block, blocks_in_hour, w3):
    latest_block = w3.eth.block_number
    block_at_last_week = latest_block - (blocks_in_hour * (hours_in_seven_days * 2))
    if deploy_block > block_at_last_week:
        block_at_last_week = deploy_block

    # fetch all the events for the vault since last fetched block
    collateral_supplied_events = requests.get(explorer_url.format(
        explorer_name=chain_to_explorer_name[chain],
        from_block=block_at_last_week,
        vault=vault,
        topic=collateral_supplied_hash,
        api_key=chain_to_explorer_api_key[chain]
    )).json()["result"]

    collateral_withdrawn_events = requests.get(explorer_url.format(
        explorer_name=chain_to_explorer_name[chain],
        from_block=block_at_last_week,
        vault=vault,
        topic=collateral_withdrawn_hash,
        api_key=chain_to_explorer_api_key[chain]
    )).json()["result"]

    gho_minted_events = requests.get(explorer_url.format(
        explorer_name=chain_to_explorer_name[chain],
        from_block=block_at_last_week,
        vault=vault,
        topic=gho_minted_hash,
        api_key=chain_to_explorer_api_key[chain]
    )).json()["result"]

    gho_burned_events = requests.get(explorer_url.format(
        explorer_name=chain_to_explorer_name[chain],
        from_block=block_at_last_week,
        vault=vault,
        topic=gho_burned_hash,
        api_key=chain_to_explorer_api_key[chain]
    )).json()["result"]

    events = sorted(collateral_supplied_events + collateral_withdrawn_events + gho_minted_events + gho_burned_events,
                    key=lambda x: (x["blockNumber"], x["logIndex"]))

    blocks = set()
    for event in events:
        blocks.add(toInt(event["blockNumber"]))

    decimal0 = toInt(
        call(w3, w3.to_checksum_address(call(w3, vault, token0_selector)[26:66]), decimals_selector)[58:66])
    decimal1 = toInt(
        call(w3, w3.to_checksum_address(call(w3, vault, token1_selector)[26:66]), decimals_selector)[58:66])

    is_token0_gho = bool(call(w3, vault, is_token0_gho_selector))
    amount = 0
    for block in blocks:
        prev_fee_data = call(w3, vault, get_current_fees_selector, block - 1)
        if is_token0_gho:
            prev_fee0 = toInt(prev_fee_data[0: 66]) * 10 ** decimal1 / 10 ** decimal0
            prev_fee1 = toInt(prev_fee_data[66: 130])
        else:
            prev_fee0 = toInt(prev_fee_data[0: 66])
            prev_fee1 = toInt(prev_fee_data[66: 130]) * 10 ** decimal0 / 10 ** decimal1
        prev_fee = prev_fee0 + prev_fee1
        prev_balance = toInt(call(w3, vault, get_underlying_balance_selector, block - 1))
        prev_total_amount = prev_fee + prev_balance

        current_fee_data = call(w3, vault, get_current_fees_selector, block)
        if is_token0_gho:
            current_fee0 = toInt(current_fee_data[0: 66]) * 10 ** decimal1 / 10 ** decimal0
            current_fee1 = toInt(current_fee_data[66: 130])
        else:
            current_fee0 = toInt(current_fee_data[0: 66]) * 10 ** decimal0 / 10 ** decimal1
            current_fee1 = toInt(current_fee_data[66: 130])
        current_fee = current_fee0 + current_fee1
        current_balance = toInt(call(w3, vault, get_underlying_balance_selector, block))
        current_total_amount = current_fee + current_balance

        diff = current_total_amount - prev_total_amount
        amount = diff / 10 ** decimal1 if is_token0_gho else decimal0

    return amount * 52 * 100


def toInt(value):
    return int(value, 16)


while 1:
    for data in chain_data:
        if len(data["vaults"]) > 0:
            print("AMM: {name}".format(name=data["name"]))
            w3 = Web3(Web3.HTTPProvider(rpc_urls[data["chain"]]))
            records = {}
            for idx, vault in enumerate(data["vaults"]):
                print("Vault: {vault}".format(vault=vault))
                records[vault] = process_vault(
                    data["name"],
                    data["chain"],
                    vault,
                    data["deploy_blocks"][idx],
                    data["blocks_in_hour"],
                    w3
                )
            json_object = json.dumps(records, indent=4)
            with open("../uni-analytics/data/aave-arbitrage-apy-{}.json".format(data["name"]), "w") as outfile:
                outfile.write(json_object)
    time.sleep(1800)
