#!/usr/bin/env python3
"""Instalador de la base de datos FARMACIA_ESPECIALIDADES en LAMPP/MySQL.

Uso:
    python scripts/instalar_bd.py
    python scripts/instalar_bd.py --reiniciar        (elimina y recrea la BD)
    python scripts/instalar_bd.py --reiniciar --si   (sin confirmación)
"""

import argparse
import os
import sys
from pathlib import Path

import mysql.connector
from mysql.connector import Error as ErrorMySQL

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from configuracion import CONFIG_BD, NOMBRE_BD  # noqa: E402


def ejecutar_archivo(cursor, ruta):
    contenido = ruta.read_text(encoding="utf-8")
    lineas = []
    for linea in contenido.splitlines():
        if linea.strip().startswith("--"):
            continue
        lineas.append(linea)
    sentencias = [s.strip() for s in "\n".join(lineas).split(";") if s.strip()]
    for sentencia in sentencias:
        cursor.execute(sentencia)
    return len(sentencias)


def main():
    parser = argparse.ArgumentParser(description="Instala la base de datos de la farmacia.")
    parser.add_argument("--reiniciar", action="store_true",
                        help="Elimina la base de datos existente y la crea de nuevo.")
    parser.add_argument("--si", action="store_true", help="No pedir confirmación.")
    args = parser.parse_args()

    config = dict(CONFIG_BD)
    config.pop("database", None)
    config.pop("autocommit", None)

    if args.reiniciar and not args.si:
        respuesta = input(
            f"⚠ Se eliminará la base de datos {NOMBRE_BD} y todos sus datos. "
            "¿Continuar? (s/N): "
        ).strip().lower()
        if respuesta not in ("s", "si", "sí"):
            print("Instalación cancelada.")
            return 0

    try:
        conexion = mysql.connector.connect(**config)
    except ErrorMySQL as exc:
        print("✖ No se pudo conectar con MySQL/MariaDB.")
        print(f"  Detalle: {exc}")
        print("\n  Inicie LAMPP con:")
        print("    sudo /opt/lampp/lampp startmysql")
        print("  Verifique usuario/contraseña en configuracion.py o con variables de entorno.")
        return 1

    cursor = conexion.cursor()
    try:
        if args.reiniciar:
            cursor.execute(f"DROP DATABASE IF EXISTS `{NOMBRE_BD}`")
            conexion.commit()
            print(f"• Base de datos {NOMBRE_BD} eliminada.")

        n_esquema = ejecutar_archivo(cursor, RAIZ / "sql" / "esquema.sql")
        conexion.commit()
        print(f"• Esquema creado/verificado ({n_esquema} sentencias).")

        cursor.execute(f"USE `{NOMBRE_BD}`")
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        usuarios_existentes = cursor.fetchone()[0]
        if usuarios_existentes == 0:
            n_datos = ejecutar_archivo(cursor, RAIZ / "sql" / "datos_iniciales.sql")
            conexion.commit()
            print(f"• Datos iniciales cargados ({n_datos} sentencias).")
        else:
            print("• Los datos iniciales ya existen; no se sobrescribieron.")

        cursor.execute("SELECT COUNT(*) FROM usuarios")
        usuarios = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM productos")
        productos = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM clientes")
        clientes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM ventas")
        ventas = cursor.fetchone()[0]

        print("\n✔ Instalación completada.")
        print(f"  Base de datos: {NOMBRE_BD}")
        print(f"  Usuarios: {usuarios} | Productos: {productos} | "
              f"Clientes: {clientes} | Ventas: {ventas}")
        print("\n  Credenciales de demostración:")
        print("    Administrador : admin   / Admin123!")
        print("    Gerente       : gerente / Gerente123!")
        print("    Cajero        : cajero  / Cajero123!")
        print("\n  Ejecute la aplicación con:  python principal.py")
        return 0
    except ErrorMySQL as exc:
        conexion.rollback()
        print(f"✖ Error durante la instalación: {exc}")
        return 1
    finally:
        cursor.close()
        conexion.close()


if __name__ == "__main__":
    raise SystemExit(main())
