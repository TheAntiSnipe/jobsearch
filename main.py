# This is another one of those design pattern practices. 
# More rudimentary, it's just a simple CRUD operation on
# csv that's highly optimized by personal preference.

import pandas as pd
import sys
from datetime import datetime

# A one-time initialization when the user passes the --new arg
def initialize_document():
    columns = ['Company','Status','Quantity','Date']
    dataframe = pd.DataFrame(columns=columns)
    dataframe.to_csv('applications.csv',index=False)

# The operator class
class Database:
    # Need to enforce a singleton on the database,
    # since the dataframe it holds must be consistent across
    # the subsystem classes.
    def __new__(cls):
        if not hasattr(cls,'instance'):
            cls.instance = super(Database,cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.dataframe = pd.read_csv('applications.csv')

    def commit(self):
        self.dataframe.to_csv('applications.csv',index=False)
    
    
    def append_entry(self,name,quantity):
        date = datetime.now().strftime('%d/%m/%Y')
        columns = ['Company','Status','Quantity','Date']
        input_row = pd.DataFrame([[name,'Applied',int(quantity),date]],columns = columns)
        self.dataframe = pd.concat([self.dataframe,input_row])
        self.commit()

    def update_entry(self,name,status):
        self.dataframe.loc[self.dataframe['Company']==name,'Status'] = status
        self.commit()
    
    def search(self,name):
        found_data = self.dataframe[self.dataframe['Company'] == name]
        print("This is what came up:")
        print(found_data)
    
    def jobcount_check(self):
        date = datetime.now().strftime('%d/%m/%Y')
        found_data = self.dataframe[self.dataframe['Date'] == date]
        print("Verbose applications today",found_data)
        print("Applications today = ",found_data['Quantity'].sum())
        print("So far, you have a total of",self.dataframe['Quantity'].sum(),"applications!")

# The create subsystem, handles entries
class Create:
    def __init__(self):
        self.database = Database()

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
            except ValueError:
                # If the user enters only the name, we
                # select the quantity for them.
                [name,quantity] = [input_data,1]
            self.database.append_entry(name,quantity)

# The update subsystem, handles updations
class Update:
    def __init__(self):
        self.database = Database()
    
    def update(self):
        print('Enter company name followed by status update')
        [name,status] = input().split(',')
        self.database.update_entry(name,status)

# The select subsystem, handles search and count queries
class Select:
    def __init__(self):
        self.database = Database()
    
    def select(self):
        print('Enter company name')
        name = input()
        self.database.search(name)
    
    def count(self):
        self.database.jobcount_check()

# The overlying facade, abstracts each subsystem and the DB
# from view.
class Facade:
    def __init__(self):
        self._create_subsystem = Create()
        self._update_subsystem = Update()
        self._select_subsystem = Select()
    
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
            # character, we say that this was probably an entry op.
            # So we rapid-fire a special entry to the DB.
            if len(choice) > 1:
                self._create_subsystem.entry(choice,1)
            else:
                sys.exit()

# The main routine, runs every time main.py is executed.
if(__name__ == '__main__'):
    if(len(sys.argv) > 1 and sys.argv[1] == 'new'):
        initialize_document()
    facade_object = Facade()
    while True:
        facade_object.operation()
