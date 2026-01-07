# from pymongo.mongo_client import MongoClient
# from pymongo.server_api import ServerApi
# uri = "mongodb+srv://siddthecoder:CALFA4AC5DA#MONGODB@base.rnyakdb.mongodb.net/?appName=base"
# # Create a new client and connect to the server
# client = MongoClient(uri, server_api=ServerApi('1'))
# # Send a ping to confirm a successful connection
# try:
#     client.admin.command('ping')
#     print("Pinged your deployment. You successfully connected to MongoDB!")
# except Exception as e:
#     print(e)

from app.db.mongo import connect_to_mongo, close_mongo_connection
import asyncio
uri = "mongodb+srv://siddthecoder:CALFA4AC5DA#MONGODB@base.rnyakdb.mongodb.net/?appName=base"

asyncio.run(connect_to_mongo())