import json
import time
import asyncio

from web3 import Web3
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

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

async def process_vault(chain, subgraph_link, blocks_in_hour, vault):
    w3 = Web3(Web3.HTTPProvider(rpc_urls[chain]))
    transport = AIOHTTPTransport(url=subgraph_link)
    client = Client(transport=transport, fetch_schema_from_transport=True)

    query = gql(
        """
      query Query {{
        vault(id: "{vault}") {{
            firstMintAtBlock
        }}
      }}
      """.format(vault=vault.lower())
    )
    results = await client.execute_async(query)
    first_mint_at_block = int(results["vault"]["firstMintAtBlock"])

    current_block = w3.eth.block_number
    blocks_in_six_hours = blocks_in_hour * 6
    block_to_query = first_mint_at_block
    
    tasks = []
    while block_to_query < current_block:
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
        current_block
    )
    current_supply = int(current_supply, 16)
    if current_block != block_to_query:
        sum_total_supply += current_supply
        blocks_queried += 1
    
    supply_twap = 0
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
                records = {}
                for vault in data["vaults"]:
                    print("Vault: {vault}".format(vault=vault))                    
                    records[vault] = await process_vault(
                        data["chain"],
                        data["subgraph_link"],
                        data["blocks_in_hour"],
                        vault,
                    )
                
                json_object = json.dumps(records, indent=4)
                with open("../uni-analytics/data/supply-twap-ratio-genesis-{}.json".format(data["name"]), "w") as outfile:
                    outfile.write(json_object)
        time.sleep(3600)

asyncio.run(main())
    