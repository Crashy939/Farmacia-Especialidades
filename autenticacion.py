"""Autenticación, sesión y matriz de permisos por rol."""

from dataclasses import dataclass, field

import bcrypt

from base_datos import bd
from utilidades import ErrorValidacion, limpiar_texto


class ErrorAutenticacion(Exception):
    pass


@dataclass
class Sesion:
    id: int
    nombre_completo: str
    usuario: str
    rol: str
    permisos: dict = field(default_factory=dict)

    def puede(self, modulo: str, accion: str) -> bool:
        return accion in self.permisos.get(modulo, set())

    def es_admin(self) -> bool:
        return self.rol == "Administrador"

    def es_gerente(self) -> bool:
        return self.rol == "Gerente"

    def es_cajero(self) -> bool:
        return self.rol == "Cajero"

    def puede_autorizar(self) -> bool:
        return self.rol in ("Administrador", "Gerente")


CRUD = {"crear", "buscar", "modificar", "cancelar"}

PERMISOS_POR_ROL = {
    "Administrador": {
        "inicio": {"ver"},
        "usuarios": set(CRUD),
        "almacen": set(CRUD),
        "compras": set(CRUD),
        "clientes": set(CRUD),
        "ventas": set(CRUD),
        "reportes": {"ver"},
    },
    "Gerente": {
        "inicio": {"ver"},
        "clientes": set(CRUD),
        "ventas": set(CRUD),
        "reportes": {"ver"},
    },
    "Cajero": {
        "inicio": {"ver"},
        # Requisito 7: el cajero busca o registra al cliente desde el punto de venta.
        "clientes": {"crear", "buscar"},
        # Requisito 5: modificar/cancelar requiere autorización del gerente.
        "ventas": {"crear", "buscar", "modificar", "cancelar"},
    },
}


def hashear_clave(clave: str) -> str:
    return bcrypt.hashpw(clave.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verificar_clave(clave: str, clave_hash: str) -> bool:
    try:
        return bcrypt.checkpw(clave.encode("utf-8"), clave_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _validar_credenciales(usuario, clave):
    usuario = limpiar_texto(usuario)
    if not usuario or not clave:
        raise ErrorAutenticacion("Ingrese su usuario y contraseña.")
    return usuario


def iniciar_sesion(usuario: str, clave: str) -> Sesion:
    usuario = _validar_credenciales(usuario, clave)
    registro = bd.obtener_uno(
        """
        SELECT u.id, u.nombre_completo, u.usuario, u.clave_hash, u.activo, r.nombre AS rol
        FROM usuarios u
        INNER JOIN roles r ON r.id = u.rol_id
        WHERE LOWER(u.usuario) = LOWER(%s)
        """,
        (usuario,),
    )
    if not registro or not verificar_clave(clave, registro["clave_hash"]):
        raise ErrorAutenticacion("Usuario o contraseña incorrectos.")
    if not registro["activo"]:
        raise ErrorAutenticacion("Este usuario está cancelado. Contacte al administrador.")

    bd.ejecutar("UPDATE usuarios SET ultimo_acceso = NOW() WHERE id = %s", (registro["id"],))
    rol = registro["rol"]
    return Sesion(
        id=registro["id"],
        nombre_completo=registro["nombre_completo"],
        usuario=registro["usuario"],
        rol=rol,
        permisos=PERMISOS_POR_ROL.get(rol, {}),
    )


def autorizar_supervisor(usuario: str, clave: str) -> Sesion:
    """Valida las credenciales de un gerente o administrador para autorizar acciones."""
    sesion = iniciar_sesion(usuario, clave)
    if not sesion.puede_autorizar():
        raise ErrorAutenticacion(
            "Las credenciales ingresadas no pertenecen a un gerente ni a un administrador."
        )
    return sesion


def validar_clave_nueva(clave: str) -> None:
    from configuracion import LONGITUD_MINIMA_CLAVE

    if not clave or len(clave) < LONGITUD_MINIMA_CLAVE:
        raise ErrorValidacion(
            f"La contraseña debe tener al menos {LONGITUD_MINIMA_CLAVE} caracteres."
        )
    if not any(c.isalpha() for c in clave) or not any(c.isdigit() for c in clave):
        raise ErrorValidacion("La contraseña debe combinar letras y números.")
