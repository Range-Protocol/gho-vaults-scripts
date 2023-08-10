import json
import time
import asyncio

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

file = open("data.json")
data = json.load(file)
chain_data = data["chain_data"]

async def process_vault(subgraph_link, vault):
    transport = AIOHTTPTransport(url=subgraph_link)
    client = Client(transport=transport, fetch_schema_from_transport=True)

    query = gql(
        """
            query Query {{
                vault(id: "{vault}") {{
                    lastUserIndex
                }}
            }}
        """.format(vault=vault)
    )

    result = await client.execute_async(query)
    lastUserIndex = int(result["vault"]["lastUserIndex"])
    if lastUserIndex == 0:
        return
    
    from_user_index = 1
    to_user_index = 1000
    if to_user_index > lastUserIndex:
        to_user_index = lastUserIndex

    token = 0
    tasks = []
    while 1:
        tasks.append(
            make_query(
                vault,
                from_user_index,
                to_user_index,
                client
            )
        )

        if to_user_index == lastUserIndex:
            break

        from_user_index = to_user_index + 1
        to_user_index = to_user_index + 1000
        if to_user_index > lastUserIndex:
            to_user_index = lastUserIndex
    
    tasks_data = await asyncio.gather(*tasks)
    for task_data in tasks_data:
        token += task_data["token"]

    return {
        "token": token,
        "vault": vault
    }
            

async def make_query(
    vault, 
    from_user_index, 
    to_user_index, 
    client
):
    query = gql(
        """
            query Query {{
                userVaultBalances(
                    first: 1000,
                    orderBy: userIndex,
                    orderDirection: asc,
                    where: {{
                        vault: "{vault}"
                        userIndex_gte: {from_user_index}
                        userIndex_lte: {to_user_index}
                    }}
                ) {{
                    address
                    balance
                    token
                    userIndex
                    id
                    vault {{
                        id
                    }}
                }}
            }}
        """.format(
            vault=vault,
            from_user_index=from_user_index,
            to_user_index=to_user_index
        )
    )
    
    results = await client.execute_async(query)
    token = 0
    for vaultBalance in results["userVaultBalances"]:
        token += int(vaultBalance["token"])
    
    return {"token": token}

async def main():
    while 1:
        for data in chain_data:
            if len(data["vaults"]) > 0:
                print("AMM: {}".format(data["name"]))
                tasks = []
                for vault in data["vaults"]:
                    print("Vault: {}".format(vault))
                    tasks.append(process_vault(data["subgraph_link"], vault))
                
                records = {}
                tasks_data = await asyncio.gather(*tasks)
                for task_data in tasks_data:
                    if task_data != None:
                        records[task_data["vault"]] = { 
                            "token": task_data["token"]
                        }
                json_object = json.dumps(records, indent=4)
                with open("exposure-{}.json".format(data["name"]), "w") as outfile:
                    outfile.write(json_object)
        time.sleep(3600)

asyncio.run(main())