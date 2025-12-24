# auth/login.py
import bcrypt
import pyodbc
from config.db import get_connection

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def authenticate_user(email: str, password: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id_usuario, nombre, password, id_rol 
        FROM usuarios 
        WHERE email = ? AND activo = 1
    """, (email,))
    row = cursor.fetchone()
    conn.close()

    if row:
        # pyodbc devuelve una tupla o Row, accedemos por índice
        user_id, nombre, password_hash, rol_id = row[0], row[1], row[2], row[3]
        if verify_password(password, password_hash):
            return {
                "id": user_id,
                "nombre": nombre,
                "rol_id": rol_id
            }
    return None