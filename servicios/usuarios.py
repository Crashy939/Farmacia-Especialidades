"""CRUD de usuarios y roles (exclusivo del administrador)."""

from base_datos import bd
from autenticacion import hashear_clave, validar_clave_nueva
from servicios import auditoria
from utilidades import ErrorValidacion, limpiar_texto, texto_requerido


class UsuariosServicio:
    def listar(self, texto="", incluir_inactivos=False):
        filtro = f"%{limpiar_texto(texto).lower()}%"
        condicion_activo = "" if incluir_inactivos else "AND u.activo = 1"
        return bd.obtener_todos(
            f"""
            SELECT u.id, u.nombre_completo, u.usuario, u.activo, u.ultimo_acceso,
                   u.creado_en, r.nombre AS rol
            FROM usuarios u
            INNER JOIN roles r ON r.id = u.rol_id
            WHERE (LOWER(u.nombre_completo) LIKE %s OR LOWER(u.usuario) LIKE %s
                   OR LOWER(r.nombre) LIKE %s)
            {condicion_activo}
            ORDER BY u.activo DESC, u.nombre_completo
            """,
            (filtro, filtro, filtro),
        )

    def roles(self):
        return bd.obtener_todos("SELECT id, nombre FROM roles ORDER BY id")

    def obtener(self, usuario_id):
        return bd.obtener_uno(
            """
            SELECT u.id, u.nombre_completo, u.usuario, u.activo, r.nombre AS rol,
                   r.id AS rol_id
            FROM usuarios u
            INNER JOIN roles r ON r.id = u.rol_id
            WHERE u.id = %s
            """,
            (usuario_id,),
        )

    def _rol_id(self, cursor, nombre_rol):
        cursor.execute("SELECT id FROM roles WHERE nombre = %s", (nombre_rol,))
        fila = cursor.fetchone()
        if not fila:
            raise ErrorValidacion("El rol seleccionado no existe.")
        return fila["id"]

    def _admin_activos(self, cursor, excluir_id=None):
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM usuarios u
            INNER JOIN roles r ON r.id = u.rol_id
            WHERE r.nombre = 'Administrador' AND u.activo = 1
              AND (%s IS NULL OR u.id <> %s)
            """,
            (excluir_id, excluir_id),
        )
        return cursor.fetchone()["total"]

    def crear(self, nombre_completo, usuario, clave, rol, ejecutor_id=None):
        nombre_completo = texto_requerido(nombre_completo, "nombre completo", 3, 120)
        usuario = texto_requerido(usuario, "usuario", 3, 50).lower()
        if " " in usuario:
            raise ErrorValidacion("El usuario no puede contener espacios.")
        validar_clave_nueva(clave)
        with bd.transaccion() as cursor:
            cursor.execute("SELECT id FROM usuarios WHERE LOWER(usuario) = %s", (usuario,))
            if cursor.fetchone():
                raise ErrorValidacion(f"El usuario '{usuario}' ya está registrado.")
            rol_id = self._rol_id(cursor, rol)
            cursor.execute(
                """
                INSERT INTO usuarios (nombre_completo, usuario, clave_hash, rol_id, activo)
                VALUES (%s, %s, %s, %s, 1)
                """,
                (nombre_completo, usuario, hashear_clave(clave), rol_id),
            )
            nuevo_id = cursor.lastrowid
            auditoria.registrar(
                cursor, ejecutor_id, "CREAR", "USUARIO", nuevo_id,
                f"Usuario {usuario} creado con rol {rol}.",
            )
        return nuevo_id

    def actualizar(self, usuario_id, nombre_completo, usuario, rol, activo,
                   clave=None, ejecutor_id=None):
        nombre_completo = texto_requerido(nombre_completo, "nombre completo", 3, 120)
        usuario = texto_requerido(usuario, "usuario", 3, 50).lower()
        if " " in usuario:
            raise ErrorValidacion("El usuario no puede contener espacios.")
        if clave:
            validar_clave_nueva(clave)
        with bd.transaccion() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.usuario, u.activo, r.nombre AS rol
                FROM usuarios u INNER JOIN roles r ON r.id = u.rol_id
                WHERE u.id = %s FOR UPDATE
                """,
                (usuario_id,),
            )
            actual = cursor.fetchone()
            if not actual:
                raise ErrorValidacion("El usuario ya no existe.")
            cursor.execute(
                "SELECT id FROM usuarios WHERE LOWER(usuario) = %s AND id <> %s",
                (usuario, usuario_id),
            )
            if cursor.fetchone():
                raise ErrorValidacion(f"El usuario '{usuario}' ya pertenece a otra cuenta.")
            rol_id = self._rol_id(cursor, rol)
            if actual["rol"] == "Administrador" and (rol != "Administrador" or not activo):
                if self._admin_activos(cursor, excluir_id=usuario_id) == 0:
                    raise ErrorValidacion("Debe existir al menos un administrador activo.")
            if clave:
                cursor.execute(
                    """
                    UPDATE usuarios
                    SET nombre_completo = %s, usuario = %s, rol_id = %s, activo = %s,
                        clave_hash = %s
                    WHERE id = %s
                    """,
                    (nombre_completo, usuario, rol_id, 1 if activo else 0,
                     hashear_clave(clave), usuario_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE usuarios
                    SET nombre_completo = %s, usuario = %s, rol_id = %s, activo = %s
                    WHERE id = %s
                    """,
                    (nombre_completo, usuario, rol_id, 1 if activo else 0, usuario_id),
                )
            auditoria.registrar(
                cursor, ejecutor_id, "MODIFICAR", "USUARIO", usuario_id,
                f"Usuario {usuario} actualizado. Activo={bool(activo)}.",
            )

    def cambiar_estado(self, usuario_id, activo, ejecutor_id=None, ejecutor_actual_id=None):
        if usuario_id == ejecutor_actual_id and not activo:
            raise ErrorValidacion("No puede cancelar la sesión con la que está trabajando.")
        with bd.transaccion() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.usuario, r.nombre AS rol
                FROM usuarios u INNER JOIN roles r ON r.id = u.rol_id
                WHERE u.id = %s FOR UPDATE
                """,
                (usuario_id,),
            )
            usuario = cursor.fetchone()
            if not usuario:
                raise ErrorValidacion("El usuario ya no existe.")
            if usuario["rol"] == "Administrador" and not activo:
                if self._admin_activos(cursor, excluir_id=usuario_id) == 0:
                    raise ErrorValidacion("Debe existir al menos un administrador activo.")
            cursor.execute(
                "UPDATE usuarios SET activo = %s WHERE id = %s",
                (1 if activo else 0, usuario_id),
            )
            auditoria.registrar(
                cursor, ejecutor_id, "ACTIVAR" if activo else "CANCELAR", "USUARIO",
                usuario_id, f"Usuario {usuario['usuario']} {'reactivado' if activo else 'cancelado'}.",
            )


usuarios_servicio = UsuariosServicio()
