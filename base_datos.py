"""Acceso a MySQL/MariaDB mediante mysql-connector-python."""

from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error as ErrorMySQL

from configuracion import CONFIG_BD


class ErrorBaseDatos(Exception):
    pass


def _traducir_error(exc):
    texto = str(exc)
    if "Access denied" in texto:
        return ErrorBaseDatos(
            "No fue posible autenticarse en MySQL. Verifique el usuario y la contraseña "
            "configurados para LAMPP."
        )
    if "Unknown database" in texto:
        return ErrorBaseDatos(
            "La base de datos FARMACIA_ESPECIALIDADES no existe. Ejecute primero "
            "'python scripts/instalar_bd.py'."
        )
    if "Can't connect" in texto or "Connection refused" in texto or "2002" in texto:
        return ErrorBaseDatos(
            "No se pudo conectar con MySQL. Inicie el servicio con: "
            "sudo /opt/lampp/lampp startmysql"
        )
    return ErrorBaseDatos(f"Error de base de datos: {texto}")


class BaseDatos:
    """Pequeño repositorio de utilidades de conexión."""

    def conectar(self):
        try:
            return mysql.connector.connect(**CONFIG_BD)
        except ErrorMySQL as exc:
            raise _traducir_error(exc) from exc

    @contextmanager
    def conexion(self):
        conn = self.conectar()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaccion(self, dictionary=True):
        """Transacción atómica: hace commit o rollback automáticamente."""
        conn = self.conectar()
        cursor = conn.cursor(dictionary=dictionary)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def obtener_uno(self, consulta, params=()):
        conn = self.conectar()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(consulta, params)
            return cursor.fetchone()
        except ErrorMySQL as exc:
            raise _traducir_error(exc) from exc
        finally:
            cursor.close()
            conn.close()

    def obtener_todos(self, consulta, params=()):
        conn = self.conectar()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(consulta, params)
            return cursor.fetchall()
        except ErrorMySQL as exc:
            raise _traducir_error(exc) from exc
        finally:
            cursor.close()
            conn.close()

    def ejecutar(self, consulta, params=()):
        conn = self.conectar()
        cursor = conn.cursor()
        try:
            cursor.execute(consulta, params)
            conn.commit()
            return cursor.lastrowid
        except ErrorMySQL as exc:
            conn.rollback()
            raise _traducir_error(exc) from exc
        finally:
            cursor.close()
            conn.close()

    def probar_conexion(self):
        return self.obtener_uno("SELECT DATABASE() AS bd, VERSION() AS version")


bd = BaseDatos()
