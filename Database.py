

import sqlite3
import random
import string

def randomword(length):
    return ''.join(random.choice(string.ascii_letters) for i in range(length))

class Database:

    def __init__(self, database):
        self.database = sqlite3.connect(database)


    def read_accounts(self):
        c = self.database.cursor()
        c.execute("SELECT owner, number, password FROM account")
        return c.fetchall()


    def read_roster(self, owner):
        c = self.database.cursor()
        c.execute( "SELECT number FROM roster WHERE owner = ?", (owner,) )
        return c.fetchall()

    def save_path(self, path, frm, msgid):
        rid = randomword(10)
        c = self.database.cursor()
        c.execute( "INSERT INTO files (path, frm, read, password) VALUES (?, ?, ?, ?)"
                 , (path, frm, msgid, rid)
                 )
        return (c.lastrowid, rid)

    def add_contact(self, owner, contact):
        c = self.database.cursor()
        c.execute( "INSERT INTO roster (owner, number) VALUES (?, ?)"
                 , (owner, contact)
                 )


    def lookup_path(self, id1, id2):
        c = self.database.cursor()
        c.execute( "SELECT path, reciever, frm, read FROM files WHERE rowid = ? AND password = ?"
                 , (id1, id2)
                 )
        return c.fetchone()

    def set_file_read(self, id1, id2):
        c = self.database.cursor()
        c.execute( "UPDATE files SET read = 0 WHERE rowid = ? AND password = ?"
                 , (id1, id2)
                 )

def get_database(path):
    if not hasattr(get_database, '__instances'):
        setattr(get_database, '__instances', dict())

    inst = getattr(get_database, '__instances')

    if path in inst:
        return inst[path]
    else:
        db = Database(path)
        inst[path] = db
        return db
