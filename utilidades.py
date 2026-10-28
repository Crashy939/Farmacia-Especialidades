"""Funciones auxiliares compartidas por servicios e interfaces."""

import re
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

CENTAVOS = Decimal("0.01")


class ErrorValidacion(Exception):
    """Error de negocio que la interfaz muestra al usuario."""


class ErrorPermiso(Exception):
    """El usuario no cuenta con permisos para la operación."""


def a_decimal(valor, campo="valor"):
    """Convierte un valor a Decimal de 2 decimales con validación."""
    try:
        if isinstance(valor, str):
            valor = valor.strip().replace("$", "").replace(",", "")
        numero = Decimal(str(valor))
    except Exception as exc:
        raise ErrorValidacion(f"El {campo} debe ser un número válido.") from exc
    if numero.is_nan() or numero.is_infinite():
        raise ErrorValidacion(f"El {campo} debe ser un número válido.")
    return numero.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def a_entero(valor, campo="cantidad", minimo=0):
    try:
        numero = int(str(valor).strip())
    except Exception as exc:
        raise ErrorValidacion(f"El {campo} debe ser un número entero.") from exc
    if numero < minimo:
        raise ErrorValidacion(f"El {campo} no puede ser menor que {minimo}.")
    return numero


def dinero(valor) -> str:
    try:
        numero = Decimal(str(valor or 0)).quantize(CENTAVOS)
    except Exception:
        numero = Decimal("0.00")
    return f"${numero:,.2f}"


def porcentaje(valor) -> str:
    return f"{Decimal(str(valor)) * 100:.0f}%"


def fecha_legible(valor, con_hora=True) -> str:
    if not valor:
        return "—"
    if isinstance(valor, str):
        for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                valor = datetime.strptime(valor, formato)
                break
            except ValueError:
                continue
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M" if con_hora else "%d/%m/%Y")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


def hoy_texto() -> str:
    return datetime.now().strftime("%d/%m/%Y")


_DIAS_SEMANA = ("lunes", "martes", "miércoles", "jueves", "viernes",
                "sábado", "domingo")
_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def fecha_larga(valor=None) -> str:
    """Fecha en español, por ejemplo: 'Jueves, 22 de octubre de 2026'."""
    valor = valor or datetime.now()
    return (f"{_DIAS_SEMANA[valor.weekday()].capitalize()}, {valor.day} de "
            f"{_MESES[valor.month - 1]} de {valor.year}")


def limpiar_texto(valor) -> str:
    return " ".join(str(valor or "").strip().split())


def texto_requerido(valor, campo, minimo=1, maximo=250) -> str:
    texto = limpiar_texto(valor)
    if len(texto) < minimo:
        raise ErrorValidacion(f"El campo {campo} es obligatorio." if minimo <= 1 else
                              f"El campo {campo} debe tener al menos {minimo} caracteres.")
    if len(texto) > maximo:
        raise ErrorValidacion(f"El campo {campo} no puede superar {maximo} caracteres.")
    return texto


def email_valido(valor):
    if not valor:
        return True
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]{2,}", str(valor).strip()))


def telefono_valido(valor):
    if not valor:
        return True
    return bool(re.fullmatch(r"[0-9+\-\s().]{7,20}", str(valor).strip()))


def normalizar_busqueda(texto) -> str:
    return f"%{limpiar_texto(texto).lower()}%"


def descripcion_puntos(puntos: int) -> str:
    puntos = int(puntos or 0)
    return f"{puntos} punto" if puntos == 1 else f"{puntos} puntos"
