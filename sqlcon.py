import sqlite3

try: 
    mi_conexion=sqlite3.connect("database/bdgps")
    cursor=mi_conexion.cursor()
    cursor.execute("CREATE TABLE persona (nombre(VARCHAR(50), edad INTEGER)")
except Exception as ex: 
    print(ex)