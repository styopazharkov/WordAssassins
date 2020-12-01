
####################################
#### SQLITE DATABASE SETUP FILE ####
####################################

## imports ##
import sqlite3

#SQLite database setup:
con = sqlite3.connect("database.db")
print("Database opened successfully")

### Players table for storing information about each player ###
## Format: int id, str key, str name, list<str> games, str pfpPath ## 
con.execute("create table Players ( \
    id INTEGER PRIMARY KEY AUTOINCREMENT, \
    key TEXT NOT NULL, \
    name TEXT NOT NULL, \
    games TEXT NOT NULL, \
    pfpPath TEXT)") 
print("Players table created successfully")  

### Games table for storing information about each game ###
## Format: int id, str code, str name, str host, bool started, list<str> players, ##
## set<str> alive, map<str, (str, str)> targets, str winner ##
con.execute("create table Games ( \
    id INTEGER PRIMARY KEY AUTOINCREMENT, \
    code TEXT NOT NULL, \
    name TEXT NOT NULL,\
    host TEXT NOT NULL, \
    started BOOLEAN NOT NULL CHECK (started IN (0,1)), \
    players TEXT NOT NULL, \
    alive TEXT NOT NULL, \
    targets TEXT NOT NULL, \
    winner TEXT)") 
print("Games table created successfully")  

con.close()  