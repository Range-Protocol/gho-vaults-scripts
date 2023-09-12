import json
from datetime import datetime
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from web3 import Web3
from web3.middleware import geth_poa_middleware

data_file = open("data.json")
data = json.load(data_file)
chain_data = data["chain_data"]
rpc_urls = data["rpc_urls"]

def create_function_selector(function_signature):
    return Web3.keccak(text=function_signature).hex()[0:10]

def call(w3, to, data, block_number):
  return w3.eth.call({
        "gas": 10_000_000,
        "to": to,
        "data": data,
  }, block_identifier=block_number).hex()

# create selectors for all the used function signatures.
current_fee_selector = create_function_selector("getCurrentFees()")
underlying_balance_selector = create_function_selector("getBalanceInCollateralToken()")
pool_selector = create_function_selector("pool()")
slot0_selector = create_function_selector("slot0()")
token0_selector = create_function_selector("token0()")
token1_selector = create_function_selector("token1()")
decimals_selector = create_function_selector("decimals()")

timestamp_now = datetime.now().timestamp().__floor__()
seconds_seven_days = 604800
hours_in_seven_days = 168

async def process_vault(name, chain, subgraph_link, supply_twap_ratio, blocks_in_hour, vault, last_block):
    w3 = Web3(Web3.HTTPProvider(rpc_urls[chain]))
    if chain == "bsc" or chain == "polygon":
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    
    transport = AIOHTTPTransport(url=subgraph_link)
    client = Client(transport=transport, fetch_schema_from_transport=False)
    block_at_last_week = w3.eth.block_number - (blocks_in_hour * hours_in_seven_days)
    timestamp_last_week = w3.eth.get_block(block_at_last_week).timestamp
    timestamp_last_block = w3.eth.get_block(last_block).timestamp

    fee0 = 0
    fee1 = 0
    weekFee0 = 0
    weekFee1 = 0
    last_timestamp_fetched = 0
    while True:
        query = gql(
            """
        query Query {{
            feeEarneds(
            first: 1000,
            orderBy: timestamp,
            orderDirection: asc, 
            where: {{
                timestamp_gt: {last_timestamp_fetched}
                timestamp_lte: {timestamp_last_block}
                vault: "{vault}"
            }}
            ) {{
                amount0
                amount1
                timestamp
                vault {{ id }}
            }}
        }}
        """.format(
                last_timestamp_fetched=last_timestamp_fetched, 
                timestamp_last_block=timestamp_last_block, 
                vault=vault.lower()
            )
        )
        results = await client.execute_async(query)
        for result in results["feeEarneds"]:
            fee0 += int(result["amount0"])
            fee1 += int(result["amount1"])
            if int(result["timestamp"]) > timestamp_last_week:
                weekFee0 += int(result["amount0"])
                weekFee1 += int(result["amount1"])
        
        if len(results["feeEarneds"]) < 1000:
            break

        last_timestamp_fetched = results["feeEarneds"][len(results["feeEarneds"]) - 1]["timestamp"]

    # get unclaimed fee.
    uncalimedFee = call(w3, vault, current_fee_selector, last_block)
    uncalimedFee0 = int(uncalimedFee[0:66], 16)
    uncalimedFee1 = int("0x" + uncalimedFee[66:130], 16)
    fee0 += uncalimedFee0
    fee1 += uncalimedFee1

    # get unclaimed fee from last week
    unclaimedFeeWeekAgo = call(w3, vault, current_fee_selector, block_at_last_week)
    if unclaimedFeeWeekAgo == "0x":
        unclaimedFeeWeekAgo0 = 0
        unclaimedFeeWeekAgo1 = 0
    else:
        unclaimedFeeWeekAgo0 = int(unclaimedFeeWeekAgo[0:66], 16)
        unclaimedFeeWeekAgo1 = int("0x" + unclaimedFeeWeekAgo[66:130], 16)
        
    weekFee0 += uncalimedFee0 - unclaimedFeeWeekAgo0
    weekFee1 += uncalimedFee1 - unclaimedFeeWeekAgo1 

    # get current vault balance in token0 and token1.
    balance = int(call(w3, vault, underlying_balance_selector, last_block)[0:66], 16) * supply_twap_ratio

    # get pool address from vault
    pool = call(w3, vault, pool_selector, last_block)
    pool = w3.to_checksum_address("0x" + pool[26:66])

    # get token0 address
    token0 = call(w3, vault, token0_selector, last_block)
    token0 = w3.to_checksum_address(token0[26:66])

    # get token0 decimals
    decimal0 = call(w3, token0, decimals_selector, last_block)
    decimal0 = int("0x" + decimal0[58:66], 16)

    # get token1 address
    token1 = call(w3, vault, token1_selector, last_block)
    token1 = w3.to_checksum_address(token1[26:66])

    # get token1 decimals
    decimal1 = call(w3, token1, decimals_selector, last_block)
    decimal1 = int("0x" + decimal1[58:66], 16)

    # get current tick from pool
    tick = call(w3, pool, slot0_selector, last_block)
    
    tick = int(tick[124:130], 16)
    if tick > 0x800000: # if tick value is negative
       tick -= 0x1000000

    if balance == 0:
        return
    
    return {
        "fee0": fee0,
        "fee1": fee1, 
        "decimal0": decimal0,
        "decimal1": decimal1,
        # calculate 7 days extrapolated fee apy
        "apy": round(((((weekFee1 * 10 ** decimal0) / 10 ** decimal1) + weekFee0) * 52 * 100
            ) / ((balance * 10 ** decimal0) / 10 ** decimal1), 6)
    }

async def calculate_7dapy():
    print("Running 7dapy...")
    for data in chain_data:
        if len(data["vaults"]) > 0:
            print("AMM: {name}".format(name=data["name"]))
            supply_twap_ratio_file = open("../uni-analytics/data/supply-twap-ratio-{}.json".format(data["name"]));
            supply_twap_ratio_data = json.load(supply_twap_ratio_file)

            last_block_file = open("last_block.json");
            last_block_data = json.load(last_block_file)
            records = {}
            for vault in data["vaults"]:
                print("Vault: {vault}".format(vault=vault))
                records[vault] = await process_vault(
                    data["name"],
                    data["chain"],
                    data["subgraph_link"],
                    supply_twap_ratio_data[vault],
                    data["blocks_in_hour"],
                    vault,
                    last_block_data[data["chain"]]
                )
            json_object = json.dumps(records, indent=4)
            with open("../uni-analytics/data/fees-{}.json".format(data["name"]), "w") as outfile:
                outfile.write(json_object)