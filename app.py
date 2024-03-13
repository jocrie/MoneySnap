import locale
import json
from datetime import datetime
from flask import Flask, request, render_template, redirect, session, g, flash
from flask_session import Session
from bokeh.resources import CDN
from pymongo.errors import DuplicateKeyError
from helpers import login_required, plot_bokeh
from werkzeug.security import check_password_hash, generate_password_hash


from db import db_user_add, db_user_login, db_user_categories, db_expenses_add, db_expenses_exchange_get, db_expenses_adjust, db_exchange

app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['BOKEH_RESOURCES'] = CDN
Session(app)

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# General settings
supportedCurrencies = {"EUR":"Euro", "SEK":"Swedish Krona", "USD":"United States Dollar", "CRC":"Costa Rica Colones"}
expenseCategorySymbols = [
  "🍔", "🚗", "🏠", "🛍️", "⚕️", "📚", "💼", "💡", "🎉", "🚑", 
  "🏊‍♂️", "📱", "🚰", "👕", "✂️", "✈️", "🎁", "💳", "💰",
  "🍕", "🍣", "🍺", "🚀", "🎤", "🎮", "📷", "🌳", "🎭", "💤",
  "💡", "🏠", "🚗", "🏥", "🍽️", "🎬", "👕", "🛠️", "🧼", "🛡️",
  "🎁", "💰", "✈️", "🎓"
];  


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        
        # Ensure all required input provided
        if (len(username) == 0 or len(password) == 0 or password != confirmation):
            flash("Provide username and matching passwords!")
            return redirect("/register")

        password_hash = generate_password_hash(password)
        
        try:
            func_result = db_user_add(username, password_hash)
            # set user id to mongodb _id
            if func_result.acknowledged == True:
                session["user_id"] = func_result.inserted_id
                # Update exchange rates
                db_exchange(session["user_id"], supportedCurrencies, 'SEK')
                # Add standard categories
                db_user_categories(session["user_id"], "addStandard")
                
                return redirect("/list")
        except DuplicateKeyError:
            flash("Username already exists. Provide different username!")
            return redirect("/register")
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    # session.clear()

    username = request.form.get("username")
    password = request.form.get("password")

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not username or not password:
            flash("Provide username and password")
            return redirect("/login")

        # Query database for username and passwordhash
        db_result = db_user_login(username)

        # Ensure username exists and password is correct
        if db_result is None or not check_password_hash(db_result['pwd_hash'], password
        ):
            flash("Invalid username and/or password")
            return redirect("/login")

        # Remember which user has logged in
        session["user_id"] = db_result['_id']

        # Redirect user to home page"""
        return redirect("/list")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")

@app.route("/")
@login_required
def diagram():
    expenses = []
    categories = []
         
    # get expense data and exchange data from mongodb
    exp_exc_db = db_expenses_exchange_get(session["user_id"])
    if exp_exc_db is not None and "user_expenses" in exp_exc_db:
        expenses = exp_exc_db["user_expenses"]       
           
    if exp_exc_db is not None and 'user_exchange' in exp_exc_db:
        if all(key in exp_exc_db['user_exchange'] for key in ['base_currency', 'rates', 'api_last_update']):
            baseCurrency = exp_exc_db['user_exchange']['base_currency']
            currentRates = exp_exc_db['user_exchange']['rates'] 
                
    # Calculate transferred value add add to user_expenses info to expenses
    for expense in expenses:
        expense['transferredValue'] = round(expense["amount"] / currentRates[expense["org_currency"]],2)
    
    date = [expense.get('date') for expense in expenses]
    transferredValue = [expense.get('transferredValue') for expense in expenses]
    category = [expense.get('category') for expense in expenses]
    
    # If expense data exists -> generate bokeh plot
    if (len(date) > 0):
        components_output, data = plot_bokeh(date, transferredValue, category, baseCurrency)
        script, div = components_output
        if data is None:
            data['dates'] = []
            data['total'] = []
        else:
            data['total'] = [round(value, 0) for value in data['total']]
            
        # Create a new dictionary with the selected keys and remove from data dictionary
        summation = {key: data.pop(key) for key in ['dates', 'total'] if key in data}
        colors = data.pop('colors')
        
        data = {key: [round(value, 0) for value in values] for key, values in data.items()}
        
    
        return render_template(
            "index.html", script=script, div=div, summation=summation, category_exp=data, cat_colors=colors, baseCurrency=baseCurrency)
    else:
        flash("Register expenses first to be able to show diagram!")
        return redirect("/list")
    
@app.route("/import", methods=["GET", "POST"])
@login_required
def importpage():
    if request.method == "POST":
        table_data_str = request.form.get('tableData')
        
        if table_data_str == '[]':
            flash('Import expenses first')
            return redirect("/import")
        
        currencySelect = request.form.get('org_currency')
        
        # Convert the string to a list of lists
        table_data = json.loads(table_data_str)

        # Define an array to store the final expense_data
        expense_data = []

        # Iterate over the data_list to create expense_data dictionaries
        for row in table_data:
            # Assuming the structure of each row in data_list is [description, date, amount, currency, category]
            try:
                date = datetime.strptime(row[1], "%Y-%m-%d") if row[1] != "" else None
            except:
                flash(f'Conversion error, check format of {row[1]}. Date must be in format YYYY-MM-DD')
                return redirect("/import") 
            
            try:
                # If amount_str is already a float, keep it as is; otherwise, convert
                amount = float(row[2].replace(',', '.')) if isinstance(row[2], str) else row[2]
            except:
                flash(f'Input error, check format of amount {row[2]}')
                return redirect("/import")
                  
            if currencySelect == "fromTable":
                if row[3].upper() in supportedCurrencies.keys():
                    currency = row[3].upper()
                else:
                    flash(f'Input error, make sure currencies from import column are supported: {row[3]}. Use same abbreviation as on Exchanges page or select currency from dropdown to set for all imported expenses.')
                    return redirect("/import")
            else:
                currency = currencySelect
                
            category = row[4] if row[4] != "" else None
                
            expense_object = {
                "description": row[0],
                "date": date,
                "amount": amount,
                "org_currency": currency,
                "category": category,
                "timestamp": datetime.now()
            }

            # Add the expense_object to the expense_data list
            expense_data.append(expense_object)
        
        # add to database
        db_expenses_add(session["user_id"], expense_data)
        
        flash(f"Sucessfully imported {len(expense_data)} expenses")
        return redirect("/list")
    else:
        return render_template("import.html", currencies=supportedCurrencies)
    
@app.route("/list", methods=["GET", "POST"])
@login_required
def list():
    if request.method == "POST":
        action_and_id = request.form.get("action")
        if "|" in action_and_id:
            action, expense_id = action_and_id.split('|')
            # Case if several expenses should be updated/deleted
            expense_id = expense_id.split(',')
        else:
            # Handle the case where there is no '|' character
            action = action_and_id
            expense_id = None
        
        description = request.form.get("description")
        if description is not None:
            description = description.replace("  ", " ").strip().capitalize() 
        date_str = request.form.get("date")
        date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else None
        amount_str = request.form.get("amount")
        amount = float(amount_str) if amount_str else None
        org_currency= request.form.get("org_currency")
        category = request.form.get("category")
        expense_data = [
            {"description": description,
            "date": date,
            "amount": amount,
            "org_currency": org_currency,
            "category": category,                
            "timestamp": datetime.now()}]
        if action == "addOneManually":
            db_expenses_add(session["user_id"], expense_data)
        elif action == "modify":
            db_expenses_adjust(session["user_id"], expense_id, expense_data)
        elif action == "remove":
            db_expenses_adjust(session["user_id"], expense_id)
        
        return redirect("/list") 
    else:
        # Set empty list incase no categories or expenses registered yet
        user_expenses = []
        user_categories = []
         
        # Get exchange info and user expenses from database
        expenses_db = db_expenses_exchange_get(session["user_id"])
        
        if expenses_db is not None and "user_expenses" in expenses_db:
            user_expenses = expenses_db["user_expenses"]
            
        # dbResult = db_expenses_exchange(session["user_id"])
        if expenses_db is not None and 'user_exchange' in expenses_db:
            if all(key in expenses_db['user_exchange'] for key in ['base_currency', 'rates', 'api_last_update']):
                baseCurrency = expenses_db['user_exchange']['base_currency']
                currentRates = expenses_db['user_exchange']['rates']
                # lastUpdate = expenses_db['user_exchange']['api_last_update']
            else:
                flash('Error when trying to display list. Double check that currencies are updated on the exchange page.')
                return redirect("/exchange")
        
        # Get user categories from database    
        categories_db = db_user_categories(session["user_id"])
        if categories_db is not None and  "categories" in categories_db:
            user_categories = categories_db["categories"]
            
        # Calculate transferred value add add to user_expenses info to expenses
        for expense in user_expenses:
            expense['transferredValue'] = round(expense["amount"] / currentRates[expense["org_currency"]],2)

        return render_template(
            "list.html", expenses=user_expenses, categories=user_categories, currencies=supportedCurrencies, baseCurrency=baseCurrency)

@app.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
        if request.method == "POST":
            action = request.form.get("action")

            if action == "addOne":
                category = request.form.get("category")
                symbol = request.form.get("symbol")
                combined = category.replace("  ", " ").strip().capitalize() + " " + symbol
                db_user_categories(session["user_id"], "addOne", combined)
            elif action == "addStandard":
                db_user_categories(session["user_id"], "addStandard")
            elif action == "deleteAll":
                db_user_categories(session["user_id"], "deleteAll")
            else:
                db_user_categories(session["user_id"], "deleteOne", action)
            return redirect("/categories") 
        else:
            results = db_user_categories(session["user_id"])

            if "categories" not in results:
                results = []
            else:
                results=results['categories']
            return render_template("categories.html", results=results, expenseCategorySymbols=expenseCategorySymbols)
            
@app.route("/exchange", methods=["GET", "POST"])
@login_required
def exchange():
    if request.method == "POST":
        action = request.form.get("action")
        # Retrieve exchange rates from API and save to database
        if action == "setBaseCurrency":
            baseCurrency = request.form.get("base_currency")
            db_exchange(session["user_id"], supportedCurrencies, baseCurrency)
        return redirect("/exchange") 
    else:
        # Get exchange info from database
        db_exchange_results = db_expenses_exchange_get(session["user_id"])
        if (db_exchange_results is not None and 'user_exchange' in db_exchange_results):
            if all(key in db_exchange_results['user_exchange'] for key in ['base_currency', 'rates', 'api_last_update']):
                baseCurrency = db_exchange_results['user_exchange']['base_currency']
                currentRates = db_exchange_results['user_exchange']['rates']
                lastUpdate = db_exchange_results['user_exchange']['api_last_update']
        else:
            return ('Unknown error. Try to update exchange rates') 
        return render_template("exchange.html", currencies=supportedCurrencies, baseCurrency=baseCurrency, rates=currentRates, lastUpdate=lastUpdate)
        
if __name__ == "__main__":
    app.run(debug=True)