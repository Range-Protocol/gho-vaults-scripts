import json
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

aave_base_market_currency_multiplier = 10 ** 8


def create_function_selector(function_signature):
    return Web3.keccak(text=function_signature).hex()[0:10]


def call(w3, to, data, block=0):
    return w3.eth.call({
        "gas": 10_000_000,
        "to": to,
        "data": data,
    }, block_identifier="latest" if block == 0 else block).hex()


gho_minted_hash = Web3.keccak(text="GHOMinted(uint256)").hex()
gho_burned_hash = Web3.keccak(text="GHOBurned(uint256)").hex()
get_aave_position_data_selector = create_function_selector("getAavePositionData()")
is_token0_gho_selector = create_function_selector("isToken0GHO()")
token0_selector = create_function_selector("token0()")
token1_selector = create_function_selector("token1()")
decimals_selector = create_function_selector("decimals()")


def process_vault(name, chain, vault, last_block, w3):
    # fetch all the events for the vault since last fetched block
    gho_minted_events = requests.get(explorer_url.format(
        explorer_name=chain_to_explorer_name[chain],
        from_block=last_block,
        vault=vault,
        topic=gho_minted_hash,
        api_key=chain_to_explorer_api_key[chain]
    )).json()["result"]

    gho_burned_events = requests.get(explorer_url.format(
        explorer_name=chain_to_explorer_name[chain],
        from_block=last_block,
        vault=vault,
        topic=gho_burned_hash,
        api_key=chain_to_explorer_api_key[chain]
    )).json()["result"]
    events = sorted(gho_minted_events + gho_burned_events,
                    key=lambda x: (x["blockNumber"], x["logIndex"]))
    amount_minted = 0
    for event in events:
        if event["topics"][0] == gho_minted_hash:
            amount_minted = amount_minted + int(event["data"][0:66], 16)
        else:
            amount_minted = amount_minted - int(event["data"][0:66], 16)

    decimal0 = toInt(
        call(w3, w3.toChecksumAddress(call(w3, vault, token0_selector)[26:66]), decimals_selector)[58:66])
    decimal1 = toInt(
        call(w3, w3.toChecksumAddress(call(w3, vault, token1_selector)[26:66]), decimals_selector)[58:66])

    is_token0_gho = bool(call(w3, vault, is_token0_gho_selector))
    if is_token0_gho:
        amount_decimal = decimal0
    else:
        amount_decimal = decimal1

    current_debt_amount = int(call(w3, vault, get_aave_position_data_selector)[66:130],
                              16) * 10 ** amount_decimal / aave_base_market_currency_multiplier

    return (current_debt_amount - amount_minted) / 10 ** amount_decimal


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
                    w3
                )
            json_object = json.dumps(records, indent=4)
            with open("../uni-analytics/data/aave-borrow-fees-{}.json".format(data["name"]), "w") as outfile:
                outfile.write(json_object)

    time.sleep(1800)
