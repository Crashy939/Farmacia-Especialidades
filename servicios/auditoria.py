"""Registro de auditoría dentro de una transacción existente."""


def registrar(cursor, usuario_id, accion, entidad, entidad_id=None, detalle=None):
    cursor.execute(
        """
        INSERT INTO auditoria (usuario_id, accion, entidad, entidad_id, detalle)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (usuario_id, accion, entidad, entidad_id, (detalle or "")[:500]),
    )
