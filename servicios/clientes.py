"""CRUD de clientes, búsqueda para el punto de venta y gestión de puntos."""

import uuid

from base_datos import bd
from servicios import auditoria
from utilidades import (ErrorValidacion, email_valido, limpiar_texto, telefono_valido,
                        texto_requerido)


class ClientesServicio:
    def listar(self, texto="", incluir_inactivos=False):
        filtro = f"%{limpiar_texto(texto).lower()}%"
        condicion = "" if incluir_inactivos else "AND c.activo = 1"
        return bd.obtener_todos(
            f"""
            SELECT c.id, c.codigo, c.nombre, c.apellido, c.telefono, c.email,
                   c.direccion, c.puntos, c.puntos_historicos, c.activo, c.creado_en
            FROM clientes c
            WHERE (LOWER(c.codigo) LIKE %s OR LOWER(c.nombre) LIKE %s
                   OR LOWER(c.apellido) LIKE %s OR LOWER(CONCAT(c.nombre, ' ', c.apellido)) LIKE %s
                   OR c.telefono LIKE %s OR LOWER(COALESCE(c.email, '')) LIKE %s)
            {condicion}
            ORDER BY c.activo DESC, c.nombre, c.apellido
            """,
            (filtro, filtro, filtro, filtro, filtro, filtro),
        )

    def buscar_activos(self, texto="", limite=30):
        filtro = f"%{limpiar_texto(texto).lower()}%"
        return bd.obtener_todos(
            """
            SELECT c.id, c.codigo, c.nombre, c.apellido, c.telefono, c.email,
                   c.puntos, c.activo
            FROM clientes c
            WHERE c.activo = 1
              AND (LOWER(c.codigo) LIKE %s OR LOWER(c.nombre) LIKE %s
                   OR LOWER(c.apellido) LIKE %s
                   OR LOWER(CONCAT(c.nombre, ' ', c.apellido)) LIKE %s
                   OR c.telefono LIKE %s)
            ORDER BY c.nombre, c.apellido
            LIMIT %s
            """,
            (filtro, filtro, filtro, filtro, filtro, limite),
        )

    def obtener(self, cliente_id):
        return bd.obtener_uno(
            """
            SELECT id, codigo, nombre, apellido, telefono, email, direccion,
                   puntos, puntos_historicos, activo, creado_en, actualizado_en
            FROM clientes WHERE id = %s
            """,
            (cliente_id,),
        )

    def _validar(self, nombre, apellido, telefono, email):
        nombre = texto_requerido(nombre, "nombre", 2, 80)
        apellido = texto_requerido(apellido, "apellido", 2, 80)
        telefono = limpiar_texto(telefono)
        email = limpiar_texto(email)
        if telefono and not telefono_valido(telefono):
            raise ErrorValidacion("El teléfono no tiene un formato válido.")
        if email and not email_valido(email):
            raise ErrorValidacion("El correo electrónico no tiene un formato válido.")
        return nombre, apellido, telefono, email

    def crear(self, nombre, apellido, telefono="", email="", direccion="", ejecutor_id=None):
        nombre, apellido, telefono, email = self._validar(nombre, apellido, telefono, email)
        direccion = limpiar_texto(direccion)[:200]
        with bd.transaccion() as cursor:
            temporal = f"TMP-{uuid.uuid4().hex[:12]}"
            cursor.execute(
                """
                INSERT INTO clientes (codigo, nombre, apellido, telefono, email, direccion,
                                      puntos, puntos_historicos, activo)
                VALUES (%s, %s, %s, %s, %s, %s, 0, 0, 1)
                """,
                (temporal, nombre, apellido, telefono or None, email or None,
                 direccion or None),
            )
            cliente_id = cursor.lastrowid
            codigo = f"CLI-{cliente_id:04d}"
            cursor.execute(
                "UPDATE clientes SET codigo = %s WHERE id = %s", (codigo, cliente_id)
            )
            auditoria.registrar(
                cursor, ejecutor_id, "CREAR", "CLIENTE", cliente_id,
                f"Cliente {codigo} - {nombre} {apellido}.",
            )
        return cliente_id

    def actualizar(self, cliente_id, nombre, apellido, telefono="", email="",
                   direccion="", ejecutor_id=None):
        nombre, apellido, telefono, email = self._validar(nombre, apellido, telefono, email)
        direccion = limpiar_texto(direccion)[:200]
        with bd.transaccion() as cursor:
            cursor.execute("SELECT id, codigo FROM clientes WHERE id = %s FOR UPDATE",
                           (cliente_id,))
            cliente = cursor.fetchone()
            if not cliente:
                raise ErrorValidacion("El cliente ya no existe.")
            cursor.execute(
                """
                UPDATE clientes
                SET nombre = %s, apellido = %s, telefono = %s, email = %s, direccion = %s
                WHERE id = %s
                """,
                (nombre, apellido, telefono or None, email or None,
                 direccion or None, cliente_id),
            )
            auditoria.registrar(
                cursor, ejecutor_id, "MODIFICAR", "CLIENTE", cliente_id,
                f"Cliente {cliente['codigo']} actualizado.",
            )

    def cambiar_estado(self, cliente_id, activo, ejecutor_id=None):
        with bd.transaccion() as cursor:
            cursor.execute(
                "SELECT id, codigo, activo FROM clientes WHERE id = %s FOR UPDATE",
                (cliente_id,),
            )
            cliente = cursor.fetchone()
            if not cliente:
                raise ErrorValidacion("El cliente ya no existe.")
            cursor.execute("UPDATE clientes SET activo = %s WHERE id = %s",
                           (1 if activo else 0, cliente_id))
            auditoria.registrar(
                cursor, ejecutor_id, "ACTIVAR" if activo else "CANCELAR", "CLIENTE",
                cliente_id,
                f"Cliente {cliente['codigo']} {'reactivado' if activo else 'cancelado'}.",
            )

    def historial_puntos(self, cliente_id, limite=100):
        return bd.obtener_todos(
            """
            SELECT m.id, m.tipo, m.puntos, m.descripcion, m.fecha, v.folio
            FROM movimientos_puntos m
            LEFT JOIN ventas v ON v.id = m.venta_id
            WHERE m.cliente_id = %s
            ORDER BY m.fecha DESC, m.id DESC
            LIMIT %s
            """,
            (cliente_id, limite),
        )


clientes_servicio = ClientesServicio()
