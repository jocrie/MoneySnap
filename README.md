# MoneySnap
## Video Demo:  https://youtu.be/RsCYeRrf0lM
## Deployed: https://moneysnap.onrender.com
## General Description:
The Expense Tracker App is a web application built with Flask, a Python web framework. This application helps users keep track of their expenses, manage categories, and visualize their spending habits through interactive diagrams.

## Features of the app
### Registration/login
User Registration: Allows users to register with a unique username and password.
User Authentication: Implements a secure login system using password hashing.
The userdata is saved to a MongoDB database.

### Expense List
Users can manually add, modify, and remove their expenses. The expenses can be filtered and sorttd with the implemented DataTable function. The user has the possibility to either delete or modify expenses one by one or to delete or modify several ones at the same time. Duplicates are marked in the list. The expenses in the list are synchrnised with a collection in MongoDB.

### Categories
Provides functionality to manage expense categories. Standard categories can be added or other categories can be added with or without emoji symbols. The categories are then linked to the expense list so that the user has the possibility to add expenses and categorize them.

### Exchange Rates
Retrieves and displays exchange rates for different currencies from an API.

### Diagram
Generates an interactive diagram (created with Bokeh) to visualize expense data. The expenses are grouped by month and category and  are shown in a stacked bar diagrm. The user can also view the expenses in a table view. The table view visualizes the categories with the same color coding as the bokeh diagram so that the user can easily find the appropriate categories in the tables

### Import
The user can import expenses from excel files. The column mapping function allows great flexibility in the supported layout of the imported excel file and the user maps the columns from the excel file to the appropriate keys before importing. The expenses that are imported are shown in a preview table so the user has the possiblity to go through them before adding the expenses to the expense list. There is an option to import only parts of the file by providing the number of the last row that should be imported.

## Technologies Used
Python: The primary programming language for the backend logic.
Flask: A web framework for building the application.
Javascript functions and functionality to provide some features of the app like chaning button states or importing the excel file.

MongoDB: A NoSQL database called MongoDB is used to store user data, expenses, and categories.

Bokeh: A Python interactive visualization library for creating charts.

HTML/CSS: Frontend design and structure.
