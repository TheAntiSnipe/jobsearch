# This is another one of those design pattern practices. 
# More rudimentary, it's just a simple CRUD operation on
# csv that's highly optimized by personal preference.

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from tabulate import tabulate
import sqlite3
from sqlite3 import Error

# A singleton class for an SQLite connection. Returns a Connection
# object when create_connection is called. The same object is returned
# on subsequent create_connection calls.
class Sqlite3Connector:
    def __new__(cls):
        if not hasattr(cls,'instance'):
            cls.instance = super(Sqlite3Connector,cls).__new__(cls)
        return cls.instance
    
    def create_connection():
        connection = None
        try:
            connection = sqlite3.connect("applications.sqlite")
        except Error as e:
            print(f"The error '{e}' occurred!")
        return connection


# A bunch of one-off command line arg functions.
class AdminTools:

    # A one-time initialization when the user passes the new arg.
    # Fails if the CSV file is already present.
    def initialize_document(self):
        columns = ['Company','Status','Quantity','Date']
        dataframe = pd.DataFrame(columns=columns)
        if 'applications.csv' in os.listdir():
            print("Initialization failed, applications.csv is currently already initialized.")
        else:
            dataframe.to_csv('applications.csv',index=False)
    
    # A cleanup in case the user feels like there's way too many rows
    # and calls the clean arg.
    # By design decisions, we've made it so only applications on the same
    # day to the same company get aggregated, because otherwise, it leads
    # to a dishonest job count. If the user wants to flatten, they can do so here.
    def aggregate(self):
        dataframe = pd.read_csv('applications.csv')
        print("Condensing",dataframe.shape[0],"rows of input data.")
        dataframe = dataframe.groupby(['Company','Status'],as_index=False).agg({'Quantity':np.sum,'Date':np.max})
        dataframe = dataframe.sort_values(by='Date')
        print("Condensation complete! Data condensed to",dataframe.shape[0],"rows!")
        dataframe.to_csv("applications.csv",index=False)
    
    # Always called after aggregate. This is the function that makes an SQLite database
    # from the CSV file. Note that the CSV file is necessary in order to make a DB.
    # Fails if a database is already present.
    def transpile(self):
        dataframe = pd.read_csv('applications.csv')
        connection = Sqlite3Connector.create_connection()
        try:
            dataframe.to_sql("Jobs",connection,if_exists='fail',index = False)
            print("Write successful! Database created: applications.sqlite.")
            test_sql_write = pd.read_sql_query("SELECT * FROM Jobs",connection)
            print("Testing write by printing a small sample of data:")
            print(tabulate(test_sql_write.head(),headers='keys',tablefmt="psql",showindex=False))
        except ValueError:
            print("Write unsuccessful, a SQLite3 database file already exists in this directory. Delete to proceed.")
        connection.close()

    # Called if you want to revert from an SQLite database.
    def untranspile(self):
        connection = Sqlite3Connector.create_connection()
        dataframe = pd.read_sql_query("SELECT * FROM Jobs",connection)
        print("Extracted data! Sample:")
        print(dataframe.head)
        for i in dataframe.index:
            dataframe.loc[i,'Date'] = pd.to_datetime(dataframe.loc[i,'Date'],format="%Y-%m-%d %H:%M:%S")
        dataframe.to_csv("applications.csv",index=False)
        print("Write successful!")
    # When the user uses the help arg or enters an arg that's not in the list
    # of args, print this out.
    def help(self):
        print("Commands list:\n1. new -> In case you're just starting the program for the first time.\n2. clean -> In case you're trying to aggregate an existing document.\n3. tosql -> In case you want to convert the csv file to an SQLite3 DB.\n4. tocsv -> In case you want to convert the SQLite3 DB to a csv file.\n5. csv -> In case your input file is applications.csv.\n6. sql -> In case your input file is applications.sqlite.")
    
    # Tell the user their arg was invalid and show them what the valid args are.
    def default(self):
        print("Invalid command!\nList of valid commands:")
        self.help()


# The operator class, singleton.
class Database:
    # Need to enforce a singleton on the database,
    # since the dataframe it holds must be consistent across
    # the subsystem classes.
    def __new__(cls,type):
        if not hasattr(cls,'instance'):
            cls.instance = super(Database,cls).__new__(cls)
        return cls.instance

    # Initializes the dataframe from the CSV file or the SQLite database.
    # In case of an SQLite database, connects to it using SqliteConnector.create_connection().
    # Also handles date formatting so that date comparisons occur the right way.
    def __init__(self,type):
        self.connection = None
        self.jobcount_today = None
        self.total_jobcount = None
        self.new_entries = pd.DataFrame(columns = ['Company','Status','Quantity','Date'])
        self.type = type
        self.date = pd.to_datetime(datetime.now().strftime('%Y-%m-%d'),format="%Y-%m-%d")
        if self.is_csv(type):
            self.dataframe = pd.read_csv('applications.csv')
            for i in self.dataframe.index:
                self.dataframe.loc[i,'Date'] = pd.to_datetime(self.dataframe.loc[i,'Date'],format="%Y-%m-%d %H:%M:%S")
        else:
            self.connection = Sqlite3Connector.create_connection()
            self.dataframe = pd.read_sql_query("SELECT * FROM Jobs",self.connection)
            for i in self.dataframe.index:
                self.dataframe.loc[i,'Date'] = pd.to_datetime(self.dataframe.loc[i,'Date'],format="%Y-%m-%d %H:%M:%S")
        todays_data = self.dataframe[self.dataframe['Date'] == self.date]
        self.jobcount_today = todays_data['Quantity'].sum()
        self.total_jobcount = self.dataframe['Quantity'].sum() - self.jobcount_today
    # This checks whether the user passed the 
    # csv arg or the sql arg. Important to ensure
    # dual functionality.
    def is_csv(self,type):
        if type == 'csv':
            return True
        else:
            return False

    # Regularly commits entries to the data file, whether it's SQLite or CSV.
    # In case of CSV, the "replace" flag means a simple append operation, otherwise
    # it means we changed status or something (which cannot be done on a single-row
    # basis since CSV is simply a flat file).
    # In case of SQLite, everything is a query operation, and we never need
    # to dump the entire dataframe into the SQLite file.
    def commit(self,replace = False,status_replace = False,value=None,company = None,status = None,choice='s'):
        if self.is_csv(self.type):
            if replace:
                # Standard entry
                self.new_entries.to_csv('applications.csv',mode =  'a',index=False,header=False)
            else:
                # Updating quantity/status
                self.dataframe.to_csv('applications.csv',index=False)
        else:
            # Updating quantity
            if replace:
                query = "UPDATE Jobs SET Quantity = Quantity + "+str(value)+" WHERE Company = \'"+company+"\' AND Date = \'"+str(self.date)+"\'"
                self.connection.cursor().execute(query)
            else:
                # Updating status
                if status_replace:
                    if choice == 's':
                        query = "UPDATE Jobs SET Status = \'"+status+"\' WHERE Company = \'"+company+"\'"
                        self.connection.cursor().execute(query)
                    else:
                        query = "UPDATE Jobs SET Company = \'"+status+"\' WHERE Company = \'"+company+"\'"
                        self.connection.cursor().execute(query)
                else:
                    # Standard entry
                    self.new_entries.to_sql("Jobs",self.connection,if_exists='append',index = False)
            self.connection.commit()
        # In any case, empty the "new entries" section
        self.new_entries = pd.DataFrame(columns = ['Company','Status','Quantity','Date'])

    # Appends new entries to the database.
    def append_entry(self,name,quantity):
        columns = ['Company','Status','Quantity','Date']
        found_data = self.dataframe[self.dataframe['Company'] == name]

        # We only want to aggregate applications done today, everything else
        # is a new entry. If the user wants aggregations done on all data,
        # they can call clean. This is to ensure an honest count of applications.
        # found_data['Date'] = pd.to_datetime(found_data['Date'],format="%d/%m/%Y")
        if found_data['Quantity'].sum() == 0 or found_data['Date'].max() != self.date:
            input_row = pd.DataFrame([[name,'Applied',int(quantity),self.date]],columns = columns)
            self.dataframe = pd.concat([self.dataframe,input_row])
            self.new_entries = pd.concat([self.new_entries,input_row])
            self.commit()
        else:
            self.dataframe.loc[self.dataframe['Company']==name,'Quantity'] += int(quantity)
            if self.is_csv(self.type):
                self.commit()
            else:
                self.commit(replace=True,value=quantity,company=name)
        self.jobcount_today += quantity

    # Status update
    def update_entry(self,name,status,choice):
        if choice == 's':
            self.dataframe.loc[self.dataframe['Company']==name,'Status'] = status
        elif choice == 'c':
            self.dataframe.loc[self.dataframe['Company']==name,'Company'] = status
        self.commit(status_replace=True,company=name,status=status,choice=choice)
    
    # Searching for a company
    def search(self,name):
        found_data = self.dataframe[self.dataframe['Company'] == name]
        print("This is what came up:")
        print(tabulate(found_data,headers='keys',tablefmt="psql",showindex=False))
    
    # How many jobs today, and how many so far?
    def jobcount_check(self):
        found_data = self.dataframe[self.dataframe['Date'] == self.date]
        if self.jobcount_today != 0:
            print(tabulate(found_data,headers='keys',tablefmt="psql",showindex=False))
        print("Applications today = ",self.jobcount_today)
        print("So far, you have a total of",self.jobcount_today+self.total_jobcount,"applications!")


# The create subsystem, handles entries.
class Create:
    def __init__(self,type):
        self.database = Database(type)

    # The create query operates in either a GUI
    # fashion or a rapid-fire fashion depending on
    # what the user wants.
    def entry(self,name = None, quantity = None):
        if name and quantity != None:
            self.database.append_entry(name,quantity)
        else:
            print('Enter company name followed by a comma, followed by quantity.')
            input_data = input()
            try:
                [name,quantity] = input_data.split(',')
                quantity = int(quantity)
            except ValueError:
                # If the user enters only the name, we
                # select the quantity for them.
                [name,quantity] = [input_data,1]
            self.database.append_entry(name,quantity)


# The update subsystem, handles updations.
class Update:
    def __init__(self,type):
        self.database = Database(type)
    
    def update(self):
        choice = input("What do you want to update? Type s if status, c if company name.\n")
        [name,status] = input('Enter company name followed by a comma, then the status/name update.\n').split(',')
        self.database.update_entry(name,status,choice)


# The select subsystem, handles search and count queries.
class Select:
    def __init__(self,type):
        self.database = Database(type)
    
    def select(self):
        print('Enter company name')
        name = input()
        self.database.search(name)
    
    def count(self):
        self.database.jobcount_check()


# The overlying facade, abstracts each subsystem and the DB
# from view.
class Facade:
    def __init__(self,type):
        self._create_subsystem = Create(type)
        self._update_subsystem = Update(type)
        self._select_subsystem = Select(type)
    
    def operation(self):
        self._select_subsystem.count()
        print("Enter 'n' if new job, 'u' if update, 's' if search, anything else if exit.")
        choice = input()
        if choice == 'n':
            self._create_subsystem.entry()
        elif choice == 'u':
            self._update_subsystem.update()
        elif choice == 's':
            self._select_subsystem.select()
        else:
            # We kinda lie to the user. If they enter more than one
            # character, we assume that this was probably an entry op.
            # So we rapid-fire a special entry to the DB.
            if len(choice) > 1:
                self._create_subsystem.entry(choice,1)
            else:
                sys.exit()


# The facade for the arg panel. Abstracts AdminTools from view.
class AdminFacade:
    def __init__(self):
        self._admin_subsystem = AdminTools()
    
    def operation(self,arg):
        if arg == 'new':
            self._admin_subsystem.initialize_document()
        elif arg == 'clean':
            # Coalesces the CSV file, lowering size.
            self._admin_subsystem.aggregate()
        elif arg == 'help':
            self._admin_subsystem.help()
        elif arg == 'tosql':
            self._admin_subsystem.transpile()
        elif arg == 'tocsv':
            self._admin_subsystem.untranspile()
        else:
            self._admin_subsystem.default()


# The main routine, runs every time main.py is executed.
if(__name__ == '__main__'):
    if(len(sys.argv) > 1):
        if sys.argv[1] != 'csv' and sys.argv[1] != 'sql':
            facade_object = AdminFacade()
            facade_object.operation(sys.argv[1])
        else:
            facade_object = Facade(sys.argv[1])
            while True:
                facade_object.operation()
    else:
        AdminFacade().operation("invalid")
        
