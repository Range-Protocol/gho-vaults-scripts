import json
import time

data_file = open("data.json")
data = json.load(data_file)
chain_data = data["chain_data"]
apy_file = open("../uni-analytics/data/RangeAPY.json")
apy_data = json.load(apy_file)

def calculate_vault_tvl_and_fee(vault_data, fee_data):
    initial_token0 = vault_data["initial_token0"]
    initial_token1 = vault_data["initial_token1"]
    token0_price = vault_data["token0_price"]
    token1_price = vault_data["token1_price"]
    fee0 = fee_data[vault_data["vault"]]["fee0"]
    fee1 = fee_data[vault_data["vault"]]["fee1"]
    decimal0 = fee_data[vault_data["vault"]]["decimal0"]
    decimal1 = fee_data[vault_data["vault"]]["decimal1"]

    return (
        (initial_token0 * token0_price) + (initial_token1 * token1_price),
        ((fee0 / 10 ** decimal0) * token0_price) + ((fee1 / 10 ** decimal1) * token1_price)
    )

while 1:
    tvl = 0
    fee = 0
    vault_count = 0
    for data in chain_data:
        if len(data["vaults"]) > 0:
            fee_file = open("../uni-analytics/data/fees-{}.json".format(data["name"]))
            fee_data = json.load(fee_file)
            for vault in data["vaults"]:
                for vault_data in apy_data["data"]:
                    if vault_data["vault"] == vault and vault_data["chain_id"] == data["chain_id"]:
                        (_tvl, _fee) = calculate_vault_tvl_and_fee(vault_data, fee_data)
                        tvl += _tvl
                        fee += _fee
                        vault_count += 1

    records = {
        "total_value_locked": tvl,
        "total_fee_earned": fee,
        "vault_count": vault_count
    }         
    json_object = json.dumps(records, indent=4)
    with open("../uni-analytics/data/tvl-and-fee.json", "w") as outfile:
        outfile.write(json_object)
    time.sleep(600)
