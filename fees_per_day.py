import json
import time
import requests
import os

from web3 import Web3
from web3.middleware import geth_poa_middleware

file = open("data.json")
data = json.load(file)
chain_data = data["chain_data"]
rpc_urls = data["rpc_urls"]

# endpoint to get the closest block to the provided expected timestamp.
llama_endpoint = "https://coins.llama.fi/block/{chain}/{timestamp}"
explorer_url = "https://api.{explorer_name}/api?module=logs&action=getLogs&fromBlock={from_block}&toBlock=latest&address={vault}&topic0={topic}&apikey={api_key}"
chain_to_explorer_name = {
    "ethereum": "etherscan.com",
    "arbitrum": "arbiscan.io",
    "bsc": "bscscan.com",
    "polygon": "polygonscan.com"
}
chain_to_explorer_api_key = {
    "ethereum": "",
    "arbitrum": "",
    "bsc": "",
    "polygon": ""
}


def create_function_selector(function_signature):
    return Web3.keccak(text=function_signature).hex()[0:10]


def call(w3, to, data, block=0):
    return w3.eth.call({
        "gas": 10_000_000,
        "to": to,
        "data": data,
    }, block_identifier="latest" if block == 0 else block).hex()


fee_earned_signature_hash = Web3.keccak(text="FeesEarned(uint256,uint256)").hex()
get_current_fee_selector = create_function_selector("getCurrentFees()")


def process_vault(chain, w3, vault, from_block, data):
    # fetch all the events for the vault since last fetched block
    fee_earned_events = requests.get(explorer_url.format(
        explorer_name=chain_to_explorer_name[chain],
        from_block=from_block,
        vault=vault,
        topic=fee_earned_signature_hash,
        api_key=chain_to_explorer_api_key[chain]
    )).json()

    fee_dividing_timestamps = []
    for entry in fee_earned_events["result"]:
        fee_dividing_timestamps.append(int(entry["timeStamp"], 16))

    from_block_timestamp = w3.eth.get_block(from_block).timestamp
    latest_block_number = w3.eth.block_number
    latest_block_timestamp = w3.eth.get_block("latest").timestamp

    # compute the starting day based on the provided last fetched block's timestamp.
    day_id = (from_block_timestamp / 86400).__floor__()
    day_timestamp = day_id * 86400

    # compute the next day's timestamp by adding 24 hours (86400 seconds) to current day's starting timestamp.
    next_day_timestamp = day_timestamp + 86400

    # get the closest block from "llama" to the timestamp where current day starts.
    day_block_data = requests.get(llama_endpoint.format(chain=chain, timestamp=day_timestamp)).json()
    day_block_timestamp = day_block_data["timestamp"]
    day_block_number = day_block_data["height"]
    try:
        # get the closest block from "llama" to the timestamp where the next day starts.
        # We do the exception handling since "llama" request throws if the provided expected timestamp
        # falls ahead of the current timestamp from latest block.
        next_day_block_data = requests.get(llama_endpoint.format(chain=chain, timestamp=next_day_timestamp)).json()
        next_day_block_number = next_day_block_data["height"]
        next_day_block_timestamp = next_day_block_data["timestamp"]
    except:
        # if the expected next day timestamp falls ahead of the timestamp from latest block then we utilise the
        # timestamp and block number from latest block as next day's timestamp and block, respectively.
        next_day_block_number = latest_block_number
        next_day_block_timestamp = latest_block_timestamp

    while True:
        fee0 = 0
        fee1 = 0
        prev_fee0 = 0
        prev_fee1 = 0

        # fetch unclaimed fee from the vault contract at the start of the current
        # day (fee at the time when previous day ended).
        prev_fee_data = call(w3, vault, get_current_fee_selector, day_block_number)
        if prev_fee_data != "0x":
            prev_fee0 = int(prev_fee_data[:66], 16)
            prev_fee1 = int("0x" + prev_fee_data[66:130], 16)

        for idx, fee_dividing_timestamp in enumerate(fee_dividing_timestamps):
            # sum all the fee events that fall in the current day's time period.
            if next_day_block_timestamp > fee_dividing_timestamp >= day_block_timestamp:
                # the fee event falls in the current day's time period.
                fee_data = fee_earned_events["result"][idx]["data"]
                fee0 += int(fee_data[:66], 16)
                fee1 += int("0x" + fee_data[66:130], 16)

        # fetch current unclaimed fee from the vault contract
        fee_data = call(w3, vault, get_current_fee_selector, next_day_block_number)
        fee0 += int(fee_data[:66], 16) - prev_fee0
        fee1 += int(fee_data[66:130], 16) - prev_fee1

        # if the day already exists in the data, then delete the entry from data dictionary as
        # we re-fetch all the fees for current day.
        if str(day_id) in data.keys():
            del data[str(day_id)]

        # set the fee for current day.
        data[day_id] = {"fee0": fee0, "fee1": fee1}

        # if the next day falls ahead of the current latest timestamp from the blockchain, we already had set
        # the next day's timestamp to latest block's timestamp in the succeeding "if" block and "continue" to break the
        # "while" loop in this iteration after fetching the current day's data to the point it has elapsed
        # and break the loop.
        if next_day_block_timestamp == latest_block_timestamp:
            break

        # if there is additional days remaining then calculate id and the starting timestamp for
        # the next day.
        day_id = (next_day_block_timestamp / 86400).__floor__()
        day_timestamp = day_id * 86400

        # set block number and timestamp for the current day as what was previously the next day.
        day_block_number = next_day_block_number
        day_block_timestamp = next_day_block_timestamp

        # set the next day 24 hours ahead.
        next_day_timestamp = day_timestamp + 86400

        if next_day_timestamp > latest_block_timestamp:
            # if the next day falls ahead of the current latest timestamp from the blockchain, we set the next day
            # starting block as the latest block to break the "while" loop in the next iteration after fetching
            # the fees for partially elapsed current day.
            next_day_block_timestamp = latest_block_timestamp
            next_day_block_number = latest_block_number
            continue

        # get the closest block from "llama" to the timestamp where next day starts.
        next_day_block_data = requests.get(llama_endpoint.format(chain=chain, timestamp=next_day_timestamp)).json()
        next_day_block_number = next_day_block_data["height"]
        next_day_block_timestamp = next_day_block_data["timestamp"]

    return {"data": data, "last_processed_block": latest_block_number}

def create_recursive_dir(dir_path):
  if not os.path.exists(dir_path):
    os.makedirs(dir_path)

while 1:
    for data in chain_data:
        if len(data["vaults"]) > 0:
            print("AMM: {name}".format(name=data["name"]))
            w3 = Web3(Web3.HTTPProvider(rpc_urls[data["chain"]]))
            if data["chain"] == "bsc" or data["chain"] == "polygon":
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)

            for idx, vault in enumerate(data["vaults"]):
                print("Vault: {vault}".format(vault=vault))
                from_block = 0
                record_data = {}
                try:
                    # create the dir recursively if it does not exist.
                    create_recursive_dir("../uni-analytics/data/fees-per-day/{chain}/{name}/".format(chain=data["chain"], name=data["name"]))
                    # if the vault fee file exists then start from today
                    fees_per_day_file = open("../uni-analytics/data/fees-per-day/{chain}/{name}/{vault}.json"
                                             .format(chain=data["chain"], name=data["name"], vault=vault))
                    fees_per_day_data = json.load(fees_per_day_file)
                    record_data = fees_per_day_data["data"]
                    from_block = fees_per_day_data["last_processed_block"] + 1
                except:
                    # vault does not exist, start from the block when vault was deployed
                    from_block = data["deploy_blocks"][idx]

                # process fee fetching for the vault
                record = process_vault(data["chain"], w3, vault, from_block, record_data)
                json_object = json.dumps(record, indent=4)
                with open("../uni-analytics/data/fees-per-day/{chain}/{name}/{vault}.json"
                                  .format(chain=data["chain"], name=data["name"], vault=vault), "w") as outfile:
                    outfile.write(json_object)
    time.sleep(3600)
