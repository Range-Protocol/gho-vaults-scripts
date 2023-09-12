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
get_aave_position_data_selector = create_function_selector("getAavePositionData()")
underlying_balance_selector = create_function_selector("getBalanceInCollateralToken()")
token0_selector = create_function_selector("token0()")
token1_selector = create_function_selector("token1()")
decimals_selector = create_function_selector("decimals()")

def supply_apy(name, chain, vault, deploy_block, blocks_in_hour, w3):
    block_at_last_week = w3.eth.block_number - (blocks_in_hour * hours_in_seven_days)
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

    events = sorted(collateral_supplied_events + collateral_withdrawn_events,
                    key=lambda x: (x["blockNumber"], x["logIndex"]))

    decimals = toInt(
        call(w3, w3.to_checksum_address(call(w3, vault, token1_selector)[26:66]), decimals_selector)[58:66])
    collateral_amount_last_week = toInt(call(w3, vault, get_aave_position_data_selector, block_at_last_week)[
                                        0:66]) * 10 ** decimals / aave_base_market_currency_multiplier

    collateral_amount_delta = collateral_amount_last_week
    for event in events:
        if event["topics"][0] == collateral_supplied_hash:
            collateral_amount_delta = collateral_amount_delta + toInt(event["data"][66:130])
        else:
            collateral_amount_delta = collateral_amount_delta - toInt(event["data"][66:130])

    current_amount = toInt(call(w3, vault, get_aave_position_data_selector)[
                           0:66]) * 10 ** decimals / aave_base_market_currency_multiplier

    return current_amount - collateral_amount_delta

def borrow_apy(name, chain, vault, deploy_block, blocks_in_hour, w3):
    block_at_last_week = w3.eth.block_number - (blocks_in_hour * hours_in_seven_days)
    if deploy_block > block_at_last_week:
        block_at_last_week = deploy_block

    # fetch all the events for the vault since last fetched block
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

    events = sorted(gho_minted_events + gho_burned_events,
                    key=lambda x: (x["blockNumber"], x["logIndex"]))

    decimal0 = toInt(
        call(w3, w3.to_checksum_address(call(w3, vault, token0_selector)[26:66]), decimals_selector)[58:66])

    decimal1 = toInt(
        call(w3, w3.to_checksum_address(call(w3, vault, token1_selector)[26:66]), decimals_selector)[58:66])

    amount = toInt(call(w3, vault, get_aave_position_data_selector, block_at_last_week)[
                   66:130]) * 10 ** decimal0 / aave_base_market_currency_multiplier
    for event in events:
        if event["topics"][0] == gho_minted_hash:
            amount = amount + toInt(event["data"][0:66])
        else:
            amount = amount - toInt(event["data"][0:66])

    current_amount = int(call(w3, vault, get_aave_position_data_selector)[66:130],
                         16) * 10 ** decimal0 / aave_base_market_currency_multiplier
    diff = current_amount - amount
    return diff * 10 ** decimal1 / 10 ** decimal0

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
                supply_delta_amount = supply_apy(
                    data["name"],
                    data["chain"],
                    vault,
                    data["deploy_blocks"][idx],
                    data["blocks_in_hour"],
                    w3
                )
                borrow_delta_amount = borrow_apy(
                    data["name"],
                    data["chain"],
                    vault,
                    data["deploy_blocks"][idx],
                    data["blocks_in_hour"],
                    w3
                )
                underlying_balance = toInt(
                    call(w3, vault, underlying_balance_selector)[0:66])
                records[vault] = (supply_delta_amount - borrow_delta_amount) / underlying_balance * 52 * 100
            json_object = json.dumps(records, indent=4)
            with open("../uni-analytics/data/aave-supply-apy-{}.json".format(data["name"]), "w") as outfile:
                outfile.write(json_object)

    time.sleep(1800)
