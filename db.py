import sys
import os

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
from helpers import exchangerate_api

uri = os.environ.get("MONGODB_URI")

try:
# Create a new client and connect to the server
  client = MongoClient(uri, server_api=ServerApi('1'))
  client.admin.command('ping')
  print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    sys.exit(1)

# use a database named "myDatabase"
db = client.myDatabase

def db_expenses_add(user_id, expenses):
  expenses_collection = db["expenses"]
  
  # create unique id for every expense
  expense_ids = [str(ObjectId()) for _ in range(len(expenses))]
  
  # Add the generated _id to each expense document
  for i, expense in enumerate(expenses):
      expense['expense_id'] = expense_ids[i]
  
  expenses_collection.update_many(
          {'user_id': user_id},
          {'$push': {'user_expenses': {'$each': expenses}}},
          upsert=True
      )
    
def db_expenses_adjust(user_id, expense_ids, expense_data = None):
  expenses_collection = db["expenses"]
  if expense_data == None:
    # delete expense
    expenses_collection.update_many(
          {'user_id': user_id},
          {'$pull': {'user_expenses': {'expense_id': {'$in': expense_ids}}}})
  else:
    # loop through keys and replace all matching keys with the new data. this keeps the original expense_id.
    # update only if new value is given, meaning not en empty string
    update_data = {'user_expenses.$[elem].' + key: value for key, value in expense_data[0].items() if (value !='' and value is not None)}

    expenses_collection.update_many(
        {'user_id': user_id, 'user_expenses.expense_id': {'$in': expense_ids}},
        {'$set': update_data},
        array_filters=[{'elem.expense_id': {'$in': expense_ids}}]
    )
  
def db_expenses_exchange_get(user_id):
  # Get user expenses and exchange data
  expenses_collection = db["expenses"]
  return expenses_collection.find_one(
        {'user_id': user_id},{"user_expenses":1, "user_exchange":1, "_id":0}
    )
  
def db_exchange(user_id, supportedCurrencies, base_currency):
  # set standard values
  # data = None
  # time_last_updated = None
  # filtered_rates = {}
  
  # call API for current exchange rates
  api_results = exchangerate_api(base_currency, supportedCurrencies)
  
  if api_results is None:
    print("API could not get current rates")
    api_last_update = None
    # set values to 1 if api update fails
    filtered_rates = {currency: 1 for currency in supportedCurrencies.keys()}
  else:
    api_last_update, filtered_rates = api_results
       
  # save to mongodb
  expenses_collection = db["expenses"]
  expenses_collection.update_one(
            {'user_id': user_id},
            {'$set': {'user_exchange': {
              'base_currency': base_currency, 
              'api_last_update': api_last_update,
              'rates': filtered_rates}}},
            upsert=True
        )

def db_user_categories(user_id, toDo = None, category = None):
    user = db["users"]
    if toDo == "deleteAll":
      user.update_one({"_id": user_id}, {"$unset": {"categories": []}})
    elif toDo == "deleteOne":
      user.update_one({"_id": user_id}, {"$pull": {"categories": category}})
    elif toDo == "addOne":
      user.update_one({"_id":user_id}, {"$push": {"categories": category}})
    elif toDo == "addStandard":
      standardCategories = [
        "Groceries 🛒","Utilities 💡","Rent/Mortgage 🏠","Transportation 🚗","Healthcare 🏥","Dining Out 🍽️",
        "Entertainment 🎬","Clothing 👕","Home Maintenance 🛠️","Personal Care 🧼","Insurance 🛡️",
        "Education 🎓","Gifts/Donations 🎁","Savings/Investments 💰","Travel ✈️"]
      user.update_one({"_id":user_id}, {"$push": {"categories": {"$each": standardCategories}}})
    else:
      # Get current categories
      return user.find_one({"_id":user_id},{"categories":1, "_id":0})
      

def db_user_add(username, pwd_hash=None):
    user = db["users"]
    # Create index to make sure that usernames are unique. Only executed once
    # user.create_index([("username", 1)], unique=True)
    return user.insert_one({"username":username, "pwd_hash":pwd_hash})

def db_user_login(username):
    user = db["users"]
    return user.find_one({"username":username})