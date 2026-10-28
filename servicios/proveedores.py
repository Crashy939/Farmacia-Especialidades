"""CRUD de proveedores utilizado por el módulo de compras."""

from base_datos import bd
from servicios import auditoria
from utilidades import (ErrorValidacion, email_valido, limpiar_texto, telefono_valido,
                        texto_requerido)


class ProveedoresServicio:
    def listar(self, texto="", incluir_inactivos=False):
        filtro = f"%{limpiar_texto(texto).lower()}%"
        condicion = "" if incluir_inactivos else "AND activo = 1"
        return bd.obtener_todos(
            f"""
            SELECT id, nombre, contacto, telefono, email, direccion, activo, creado_en
            FROM proveedores
            WHERE (LOWER(nombre) LIKE %s OR LOWER(COALESCE(contacto, '')) LIKE %s
                   OR LOWER(COALESCE(email, '')) LIKE %s)
            {condicion}
            ORDER BY activo DESC, nombre
            """,
            (filtro, filtro, filtro),
        )

    def obtener(self, proveedor_id):
        return bd.obtener_uno(
            "SELECT * FROM proveedores WHERE id = %s", (proveedor_id,)
        )

    def _validar(self, nombre, telefono, email):
        nombre = texto_requerido(nombre, "nombre", 2, 120)
        telefono = limpiar_texto(telefono)
        email = limpiar_texto(email)
        if telefono and not telefono_valido(telefono):
            raise ErrorValidacion("El teléfono del proveedor no es válido.")
        if email and not email_valido(email):
            raise ErrorValidacion("El correo del proveedor no es válido.")
        return nombre, telefono, email

    def crear(self, nombre, contacto="", telefono="", email="", direccion="",
              ejecutor_id=None):
        nombre, telefono, email = self._validar(nombre, telefono, email)
        with bd.transaccion() as cursor:
            cursor.execute("SELECT id FROM proveedores WHERE LOWER(nombre) = LOWER(%s)",
                           (nombre,))
            if cursor.fetchone():
                raise ErrorValidacion(f"El proveedor '{nombre}' ya existe.")
            cursor.execute(
                """
                INSERT INTO proveedores (nombre, contacto, telefono, email, direccion, activo)
                VALUES (%s, %s, %s, %s, %s, 1)
                """,
                (nombre, limpiar_texto(contacto)[:120], telefono or None,
                 email or None, limpiar_texto(direccion)[:200]),
            )
            proveedor_id = cursor.lastrowid
            auditoria.registrar(cursor, ejecutor_id, "CREAR", "PROVEEDOR", proveedor_id,
                                f"Proveedor {nombre}.")
        return proveedor_id

    def actualizar(self, proveedor_id, nombre, contacto="", telefono="", email="",
                   direccion="", ejecutor_id=None):
        nombre, telefono, email = self._validar(nombre, telefono, email)
        with bd.transaccion() as cursor:
            cursor.execute("SELECT id FROM proveedores WHERE id = %s FOR UPDATE",
                           (proveedor_id,))
            if not cursor.fetchone():
                raise ErrorValidacion("El proveedor ya no existe.")
            cursor.execute(
                "SELECT id FROM proveedores WHERE LOWER(nombre) = LOWER(%s) AND id <> %s",
                (nombre, proveedor_id),
            )
            if cursor.fetchone():
                raise ErrorValidacion(f"El proveedor '{nombre}' ya existe.")
            cursor.execute(
                """
                UPDATE proveedores
                SET nombre = %s, contacto = %s, telefono = %s, email = %s, direccion = %s
                WHERE id = %s
                """,
                (nombre, limpiar_texto(contacto)[:120], telefono or None,
                 email or None, limpiar_texto(direccion)[:200], proveedor_id),
            )
            auditoria.registrar(cursor, ejecutor_id, "MODIFICAR", "PROVEEDOR",
                                proveedor_id, f"Proveedor {nombre} actualizado.")

    def cambiar_estado(self, proveedor_id, activo, ejecutor_id=None):
        with bd.transaccion() as cursor:
            cursor.execute("SELECT nombre FROM proveedores WHERE id = %s FOR UPDATE",
                           (proveedor_id,))
            proveedor = cursor.fetchone()
            if not proveedor:
                raise ErrorValidacion("El proveedor ya no existe.")
            cursor.execute("UPDATE proveedores SET activo = %s WHERE id = %s",
                           (1 if activo else 0, proveedor_id))
            auditoria.registrar(
                cursor, ejecutor_id, "ACTIVAR" if activo else "CANCELAR", "PROVEEDOR",
                proveedor_id, f"Proveedor {proveedor['nombre']}.",
            )


proveedores_servicio = ProveedoresServicio()
