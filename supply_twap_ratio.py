import json
import time
import asyncio

from web3 import Web3
from seven_day_apy import calculate_7dapy

file = open("data.json")
data = json.load(file)
chain_data = data["chain_data"]
rpc_urls = data["rpc_urls"]

def create_function_selector(function_signature):
    return Web3.keccak(text=function_signature).hex()[0:10]

async def call(w3, to, data, block):
    return w3.eth.call({
        "gas": 10_000_000,
        "to": to,
        "data": data,
    }, block_identifier=block).hex()

total_supply_selector = create_function_selector("totalSupply()")
six_hour_intervals_in_a_week = 28

async def process_vault(w3, blocks_in_hour, vault, last_block):
    blocks_in_six_hours = blocks_in_hour * 6
    block_to_query = last_block - (six_hour_intervals_in_a_week * blocks_in_six_hours)

    tasks = []
    while block_to_query <= last_block:
        tasks.append(call(
            w3,
            vault,
            total_supply_selector,
            block_to_query
        ))
        block_to_query += blocks_in_six_hours

    sum_total_supply = 0
    blocks_queried = 0
    tasks_data = await asyncio.gather(*tasks)
    for task_data in tasks_data:
        if task_data != "0x":
            amount = int(task_data, 16)
            if amount != 0:
                sum_total_supply = sum_total_supply + amount
                blocks_queried += 1

    current_supply = await call(
        w3,
        vault,
        total_supply_selector,
        last_block
    )
    current_supply = int(current_supply, 16)
    if blocks_queried != 0:
        supply_twap = sum_total_supply / blocks_queried
    else:
        supply_twap = current_supply

    return float(supply_twap / current_supply)

async def main():
    while 1:
        for data in chain_data:
            if len(data["vaults"]) > 0:
                print("AMM: {name}".format(name=data["name"]))
                w3 = Web3(Web3.HTTPProvider(rpc_urls[data["chain"]]))
                current_block = w3.eth.block_number
                last_block_file_data = None
                with open("last_block.json", "r") as last_block_file:
                    last_block_file_data = json.load(last_block_file)
                    last_block_file.close()
                
                with open("last_block.json", "w") as last_block_file:
                    last_block_file_data[data["chain"]] = current_block
                    last_block_file.write(json.dumps(last_block_file_data, indent=4))
                    last_block_file.close()

                records = {}
                for vault in data["vaults"]:
                    print("Vault: {vault}".format(vault=vault))
                    records[vault] = await process_vault(
                        w3,
                        data["blocks_in_hour"],
                        vault,
                        current_block
                    )

                json_object = json.dumps(records, indent=4)
                with open("../uni-analytics/data/supply-twap-ratio-{}.json".format(data["name"]), "w") as outfile:
                    outfile.write(json_object)

        await calculate_7dapy()         
        time.sleep(3600)

asyncio.run(main())
