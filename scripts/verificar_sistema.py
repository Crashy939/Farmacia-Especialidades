#!/usr/bin/env python3
"""Verificación rápida de dependencias, conexión y datos de la farmacia.

Uso:
    python scripts/verificar_sistema.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def revisar_dependencias():
    faltantes = []
    for modulo, paquete in (
        ("customtkinter", "customtkinter"),
        ("mysql.connector", "mysql-connector-python"),
        ("bcrypt", "bcrypt"),
        ("PIL", "pillow"),
    ):
        try:
            __import__(modulo)
        except ImportError:
            faltantes.append(paquete)
    if faltantes:
        print("✖ Faltan dependencias:", ", ".join(faltantes))
        print("  Instálelas con: pip install -r requirements.txt")
        return False
    print("✔ Dependencias de Python instaladas.")
    return True


def revisar_bd():
    import mysql.connector

    from configuracion import CONFIG_BD, NOMBRE_BD
    from servicios.reportes import resumen_inicio

    config = dict(CONFIG_BD)
    config.pop("database", None)
    config.pop("autocommit", None)
    try:
        conexion = mysql.connector.connect(**config)
    except Exception as exc:
        print("✖ No se pudo conectar con MySQL/MariaDB.")
        print(f"  Detalle: {exc}")
        print("  Inicie LAMPP con: sudo /opt/lampp/lampp startmysql")
        return False

    try:
        cursor = conexion.cursor()
        cursor.execute(f"USE `{NOMBRE_BD}`")
        esperadas = {
            "roles", "usuarios", "categorias", "proveedores", "productos",
            "clientes", "movimientos_puntos", "compras", "compra_detalle",
            "ventas", "venta_detalle", "auditoria",
        }
        cursor.execute("SHOW TABLES")
        existentes = {fila[0] for fila in cursor.fetchall()}
        faltantes = esperadas - existentes
        if faltantes:
            print("✖ Faltan tablas:", ", ".join(sorted(faltantes)))
            print("  Ejecute: python scripts/instalar_bd.py")
            return False
        print(f"✔ Base de datos {NOMBRE_BD} disponible ({len(existentes)} tablas).")

        for tabla in ("usuarios", "productos", "clientes", "ventas", "compras"):
            cursor.execute(f"SELECT COUNT(*) FROM `{tabla}`")
            print(f"  · {tabla:18s}: {cursor.fetchone()[0]}")

        cursor.execute("SELECT usuario, activo FROM usuarios ORDER BY id")
        print("\n  Usuarios:")
        for usuario, activo in cursor.fetchall():
            print(f"    - {usuario:10s} {'activo' if activo else 'cancelado'}")

        datos = resumen_inicio(1)
        print("\n  Panel de inicio:")
        print(f"    Ventas de hoy : {datos['ventas_hoy']['cantidad']}")
        print(f"    Clientes      : {datos['clientes']['total']}")
        print(f"    Productos     : {datos['productos']['total']}")
        print(f"    Stock bajo    : {datos['productos']['bajo_stock']}")
        print("\n✔ Verificación completada. Ejecute: python principal.py")
        return True
    except Exception as exc:
        print(f"✖ Error al verificar la base de datos: {exc}")
        return False
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conexion.close()


def main():
    print("Farmacia Especialidades · verificación del sistema\n")
    if not revisar_dependencias():
        return 1
    return 0 if revisar_bd() else 1


if __name__ == "__main__":
    raise SystemExit(main())
