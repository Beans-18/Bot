import os

import interactions
import requests
import urllib.parse
import json
import random
import asyncio
import sqlite3
import aiohttp
import roblox
from roblox import UserNotFound
system_url = [REDACTED]

from discord_webhook import AsyncDiscordWebhook
import dotenv

dotenv.load_dotenv()



client = roblox.Client()

usage_logs = 1
purchase_logs = 971841032427819021
token = os.getenv("DISCORD_TOKEN")
api_key = os.getenv("SHOPPY_API_KEY")
hub_id = os.getenv("VENDR_HUB_ID")
vendr_api_key = os.getenv("VENDR_API_KEY")
shoppy_name = "Havoc_Studios"
customer_role_id = int(os.getenv("CUSTOMER_ROLE_ID"))

keys = []

bot = interactions.Client(token=token)
database = sqlite3.connect(os.getcwd() + r"/havocdatabase.db")


@bot.command(name="removeblacklist", default_member_permissions=interactions.Permissions.ADMINISTRATOR,
             description="Removes a blacklist from somebody", options=[interactions.Option(name="roblox_username",
                                                                                           description="The username of the person to remove the blacklist from",
                                                                                           type=interactions.OptionType.STRING,
                                                                                           required=True)])
async def delete_blacklist(ctx, roblox_username):
    user = await client.get_user_by_username(roblox_username)
    roblox_id = user.id
    if not check_blacklist(roblox_id):
        await ctx.send("This user is not blacklisted.")
    database.execute("DELETE FROM Blacklists WHERE UserID=?;", (str(roblox_id),))
    database.commit()


def check_blacklist(roblox_id):
    cursor = database.execute("SELECT * FROM Blacklists WHERE UserID=?;", (str(roblox_id),))
    if len(cursor.fetchall()) == 0:
        return False
    else:
        return True

async def check_transaction(transaction_id, product_name):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://shoppy.gg/api/v1/orders/{transaction_id}", headers={"Authorization": api_key}) as request:
            content = await request.json()
            async with session.get(f"https://shoppy.gg/api/v1/products/{content['product_id']}", headers={"Authorization": api_key}) as product:
                info = await product.json()
                print(info)
                if not info["seller"] == shoppy_name:
                    return False
            print(content)
            if "product" in content.keys():
                product = content["product"]
                if product["title"] == product_name:
                    return True
                else:
                    return False
            else:
                return False




@bot.command(name="checkblacklist", default_member_permissions=interactions.Permissions.ADMINISTRATOR,
             description="Checks if a user is blacklisted", options=[
        interactions.Option(name="roblox_username", description="The username of the user to check the blacklist for.",
                            type=interactions.OptionType.STRING, required=True)])
async def check(ctx, roblox_username):
    try:
        user = await client.get_user_by_username(roblox_username)
        roblox_id = user.id
    except UserNotFound:
        await ctx.send("User does not exist.")
        return
    if check_blacklist(roblox_id):
        await ctx.send("This user is blacklisted.")
    else:
        await ctx.send("This user is not blacklisted.")


@bot.command(name="blacklist", default_member_permissions=interactions.Permissions.ADMINISTRATOR,
             description="Blacklists a user from using our products", options=[
        interactions.Option(name="roblox_username", description="The username of the person to blacklist",
                            type=interactions.OptionType.STRING, required=True)])
async def create_blacklist(ctx, roblox_username):
    try:
        user = await client.get_user_by_username(roblox_username)
        roblox_id = user.id
    except UserNotFound:
        await ctx.send("User does not exist.")
        return

    if check_blacklist(roblox_id):
        await ctx.send("User already blacklisted.")
        return
    database.execute("INSERT INTO Blacklists (UserID) VALUES (?);", (str(roblox_id),))
    database.commit()
    await ctx.send(f"Successfully blacklisted user {roblox_username}.")


@bot.command(name="initialize", description="Initializes the database",
             default_member_permissions=interactions.Permissions.ADMINISTRATOR)
async def init(ctx):
    try:
        database.execute("CREATE TABLE Blacklists ("
                         "UserID VARCHAR(12))")
    except sqlite3.Error:
        pass

    try:
        database.execute("CREATE TABLE Products ("
                         "ShoppyName VARCHAR(255),"
                         "VendrName VARCHAR(255),"
                         "RoleID VARCHAR(25))")
    except sqlite3.Error as e:
        print(e)

    try:
        database.execute("CREATE TABLE Redeemed("
                         "TransactionID VARCHAR(50))")
    except sqlite3.Error:
        pass

@bot.command(name="setproduct", default_member_permissions=interactions.Permissions.ADMINISTRATOR, description="Sets a product.", options=[
    interactions.Option(name="shoppy_name", description="The shoppy name", type=interactions.OptionType.STRING, required=True),
    interactions.Option(name="vendr_name", description="The Vendr name", type=interactions.OptionType.STRING, required=True),
    interactions.Option(name="role", description="The role to connect it to", type=interactions.OptionType.ROLE, required=False)
])
async def add_product(ctx, shoppy_name, vendr_name, role=None):
    role_id = None
    if role:
        role_id = int(role.id)

    if len((database.execute("SELECT * FROM Products WHERE ShoppyName=?", (shoppy_name,)).fetchall())) == 0:
        database.execute("INSERT INTO Products (ShoppyName, VendrName, RoleID) VALUES (?, ?, ?)", (shoppy_name, vendr_name, role_id))
        database.commit()
        await ctx.send("Successfully added product.")
    else:
        database.execute("UPDATE Products SET ShoppyName=?, VendrName=?, RoleID=? WHERE ShoppyName=?", (shoppy_name, vendr_name, role_id, shoppy_name))
        database.commit()
        await ctx.send("Successfully updated product.")

def get_product_value(value, **kwargs):
    arg1 = list(kwargs.keys())[0]
    arg2 = kwargs[arg1]
    print(f"SELECT {value} FROM Products WHERE {arg1}={arg2}", value, arg1, arg2)
    for i in kwargs.keys():
        if i not in ["VendrName", "ShoppyName", "Role"]:
            return

    if value not in ["VendrName", "ShoppyName", "Role"]:
        return
    cursor = database.execute(f"SELECT {value} FROM PRODUCTS WHERE {arg1} = ?;", (arg2,))
    return cursor.fetchone()


async def get_product_id(vendr_name):
    async with aiohttp.ClientSession() as session:
        url = f"https://api.onpointrblx.com/vendr/v2/hubs/getinfo?apitoken={vendr_api_key}"
        async with session.get(url) as response:
            content = await response.json()
            print(content)
            for i in content["Products"]:
                if i["Name"] == vendr_name[0]:
                    print("IT IS..")
                    return i["_id"]
            else:
                return False





@bot.command(name="redeemproduct", description="Redeems a product bought from Shoppy", options=[
    interactions.Option(name="shoppy_product_name", description="The product name on Shoppy", type=interactions.OptionType.STRING, required=True),
    interactions.Option(name="transaction_id", description="The transaction ID", type=interactions.OptionType.STRING, required=True)
])
async def redeem_token(ctx, shoppy_product_name, transaction_id):
    check = database.execute("SELECT TransactionID FROM Redeemed WHERE TransactionID=?", (transaction_id,))
    if check.fetchall():
        await ctx.send("This transaction ID has already been redeemed.")
        message = f"**License Redeem Detected**\nDiscord User: <@{ctx.author.id}>\nProduct: {shoppy_product_name}\nSuccess: False (Transaction ID already used)\nTransaction ID: {transaction_id}"
        redeem_webhook = AsyncDiscordWebhook(content=message, url=system_url)
        await redeem_webhook.execute()
        return



    vendr_name = get_product_value("VendrName", ShoppyName=shoppy_product_name)
    if not vendr_name:
        await ctx.send("This product does not exist! Please contact support for help.")
        return

    if await check_transaction(transaction_id, shoppy_product_name):
        success = None
        print(vendr_name)
        url = f"https://api.onpointrblx.com/vendr/v2/licences/grant/discord/{int(ctx.author.id)}/{await get_product_id(vendr_name)}?apitoken={vendr_api_key}"
        async with aiohttp.ClientSession() as session:
            database.execute("INSERT INTO Redeemed (TransactionID) VALUES (?)", (transaction_id,))
            database.commit()
            async with session.post(url) as response:
                    print(await response.json())
                    print("YAS")
                    if response.status == 404:
                        await ctx.send("User not found. Please make sure that you are linked with Vendr.")
                        success = "False (404)"
                        database.execute("DELETE FROM Redeemed WHERE TransactionID=?", (transaction_id,))
                        database.commit()
                    elif response.status == 401:
                        await ctx.send("Error encountered. You most likely already have this product.")
                        success = "False (401)"
                        database.execute("DELETE FROM Redeemed WHERE TransactionID=?", (transaction_id,))
                        database.commit()
                    elif response.status == 200:
                        try:
                            if role_id := get_product_value("RoleID", ShoppyName=shoppy_product_name)[0]:
                                await ctx.author.add_role(int(role_id), int(ctx.guild_id))
                        except KeyError:
                            pass

                        if customer_role_id != 0:
                            await ctx.author.add_role(customer_role_id, int(ctx.guild_id))
                        else:
                            role_id = "None"

                        await ctx.send("Successfully gave you the product.")
                        success = "True (200)"

                    message = f"**License Redeem Detected**\nDiscord User: <@{ctx.author.id}>\nProduct: {shoppy_product_name}\nSuccess: {success}\nTransaction ID: {transaction_id}"
                    redeem_webhook = AsyncDiscordWebhook(content=message, url=system_url)
                    await redeem_webhook.execute()
    else:
        database.execute("DELETE FROM Redeemed WHERE TransactionID=?", (transaction_id,))
        database.commit()
        await ctx.send("Invalid transaction ID.")
        message = f"**License Redeem Detected**\nDiscord User: <@{ctx.author.id}>\nProduct: {shoppy_product_name}\nSuccess: False (Invalid transaction ID)\nTransaction ID: {transaction_id}"
        redeem_webhook = AsyncDiscordWebhook(content=message, url=system_url)
        await redeem_webhook.execute()

@bot.command(name="getroles", description="Gives you your roles from your products", options=[interactions.Option(name="user", description="The user", type=interactions.OptionType.USER, required=False)])
async def get_roles(ctx, user=None):

    if not user:
        user = ctx.author

    async def give_roles(ctx: interactions.CommandContext, user, VendrName, roles_list, role_id):
        if not role_id:
            print("Does not contain a role ID.")
            return
        else:
            role_id = int(role_id)


        url = f"https://api.onpointrblx.com/vendr/v2/licences/getlicence/discord/{user.id}/2gJAtG0ipn/{VendrName}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as request:
                print("Request sent.")
                if request.status == 200:
                    print("Has product.")
                    guild = ctx.guild_id
                    await user.add_role(int(role_id), int(guild))
                    await user.add_role(908450336061128755, int(guild))
                    roles_list += [VendrName]

    tasks = []
    roles = []
    cursor = database.execute("SELECT * FROM Products")
    for i in cursor.fetchall():
        print(i)
        tasks += [give_roles(ctx, user, i[1], roles, i[2])]

    await asyncio.gather(*tasks)
    roles = "\n".join(roles)
    await ctx.send("**Successfully given roles**")





bot.start()
