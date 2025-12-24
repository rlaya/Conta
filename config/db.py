# config/db.py
import pyodbc

def get_connection():
    # Usa autenticación de Windows (trusted_connection=yes)
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=.\\SQLEXPRESS;"  # Cambia si tu servidor es remoto
        "DATABASE=Conta;"
        "Trusted_Connection=yes;"
    )
    return conn