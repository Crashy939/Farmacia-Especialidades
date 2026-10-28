"""Consultas agregadas para el panel de inicio."""

from base_datos import bd
from servicios.ventas import ventas_servicio


def resumen_inicio(usuario_id=None, solo_propias=False):
    filtro_usuario = usuario_id if solo_propias else None
    ventas_hoy = ventas_servicio.resumen_hoy(filtro_usuario)
    clientes = bd.obtener_uno(
        "SELECT COUNT(*) AS total FROM clientes WHERE activo = 1"
    )
    productos = bd.obtener_uno(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN existencia <= stock_minimo THEN 1 ELSE 0 END) AS bajo_stock,
               SUM(CASE WHEN existencia = 0 THEN 1 ELSE 0 END) AS agotados
        FROM productos WHERE activo = 1
        """
    )
    bajo_stock = bd.obtener_todos(
        """
        SELECT codigo, nombre, existencia, stock_minimo
        FROM productos
        WHERE activo = 1 AND existencia <= stock_minimo
        ORDER BY existencia ASC, nombre
        LIMIT 8
        """
    )
    recientes = bd.obtener_todos(
        """
        SELECT v.folio, v.fecha, v.total, v.estado,
               CONCAT(c.nombre, ' ', c.apellido) AS cliente,
               u.nombre_completo AS usuario
        FROM ventas v
        INNER JOIN clientes c ON c.id = v.cliente_id
        INNER JOIN usuarios u ON u.id = v.usuario_id
        WHERE (%s IS NULL OR v.usuario_id = %s)
        ORDER BY v.fecha DESC, v.id DESC
        LIMIT 8
        """,
        (filtro_usuario, filtro_usuario),
    )
    puntos_hoy = bd.obtener_uno(
        """
        SELECT COALESCE(SUM(puntos), 0) AS total
        FROM movimientos_puntos
        WHERE tipo = 'GANADO' AND DATE(fecha) = CURDATE()
        """
    )
    return {
        "ventas_hoy": ventas_hoy,
        "clientes": clientes,
        "productos": productos,
        "bajo_stock": bajo_stock,
        "recientes": recientes,
        "puntos_hoy": puntos_hoy,
    }
