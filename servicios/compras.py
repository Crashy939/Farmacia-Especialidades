"""Compras de mercancía a proveedores y actualización de inventario."""

import uuid
from decimal import Decimal

from base_datos import bd
from servicios import auditoria
from utilidades import (ErrorValidacion, a_decimal, a_entero, limpiar_texto,
                        texto_requerido)


def _normalizar_entradas(items):
    if not items:
        raise ErrorValidacion("Agregue al menos un producto a la compra.")
    agrupados = {}
    for item in items:
        producto_id = int(item.get("producto_id") or 0)
        cantidad = a_entero(item.get("cantidad"), "cantidad", 1)
        costo = a_decimal(item.get("costo_unitario"), "costo unitario")
        if costo < 0:
            raise ErrorValidacion("El costo unitario no puede ser negativo.")
        if producto_id <= 0:
            raise ErrorValidacion("Seleccione un producto válido.")
        if producto_id in agrupados:
            agrupados[producto_id]["cantidad"] += cantidad
        else:
            agrupados[producto_id] = {
                "producto_id": producto_id,
                "cantidad": cantidad,
                "costo_unitario": costo,
            }
    return list(agrupados.values())


class ComprasServicio:
    def _folio(self, cursor, compra_id):
        folio = f"COM-{compra_id:06d}"
        cursor.execute("UPDATE compras SET folio = %s WHERE id = %s", (folio, compra_id))
        return folio

    def _productos_bloqueados(self, cursor, items):
        preparados = []
        for item in items:
            cursor.execute(
                """
                SELECT id, codigo, nombre, precio_compra, existencia, activo
                FROM productos WHERE id = %s FOR UPDATE
                """,
                (item["producto_id"],),
            )
            producto = cursor.fetchone()
            if not producto:
                raise ErrorValidacion("Uno de los productos seleccionados ya no existe.")
            if not producto["activo"]:
                raise ErrorValidacion(
                    f"El producto '{producto['codigo']} - {producto['nombre']}' está cancelado."
                )
            item = dict(item)
            item.update(producto)
            item["subtotal"] = (item["costo_unitario"] * item["cantidad"]).quantize(
                Decimal("0.01")
            )
            preparados.append(item)
        return preparados

    def listar(self, texto="", estado="TODAS", incluir_detalle=False):
        filtro = f"%{limpiar_texto(texto).lower()}%"
        condiciones = [
            "(LOWER(c.folio) LIKE %s OR LOWER(pr.nombre) LIKE %s "
            "OR LOWER(u.nombre_completo) LIKE %s)"
        ]
        params = [filtro, filtro, filtro]
        if estado in ("COMPLETADA", "CANCELADA"):
            condiciones.append("c.estado = %s")
            params.append(estado)
        where = " AND ".join(condiciones)
        return bd.obtener_todos(
            f"""
            SELECT c.id, c.folio, c.fecha, c.subtotal, c.total, c.estado,
                   c.observaciones, pr.nombre AS proveedor, u.nombre_completo AS usuario,
                   COUNT(cd.id) AS partidas,
                   COALESCE(SUM(cd.cantidad), 0) AS unidades
            FROM compras c
            INNER JOIN proveedores pr ON pr.id = c.proveedor_id
            INNER JOIN usuarios u ON u.id = c.usuario_id
            LEFT JOIN compra_detalle cd ON cd.compra_id = c.id
            WHERE {where}
            GROUP BY c.id
            ORDER BY c.fecha DESC, c.id DESC
            LIMIT 400
            """,
            tuple(params),
        )

    def obtener(self, compra_id):
        return bd.obtener_uno(
            """
            SELECT c.*, pr.nombre AS proveedor, u.nombre_completo AS usuario,
                   uc.nombre_completo AS cancelada_por_nombre
            FROM compras c
            INNER JOIN proveedores pr ON pr.id = c.proveedor_id
            INNER JOIN usuarios u ON u.id = c.usuario_id
            LEFT JOIN usuarios uc ON uc.id = c.cancelada_por
            WHERE c.id = %s
            """,
            (compra_id,),
        )

    def detalle(self, compra_id):
        return bd.obtener_todos(
            """
            SELECT cd.id, cd.producto_id, cd.cantidad, cd.costo_unitario, cd.subtotal,
                   p.codigo, p.nombre
            FROM compra_detalle cd
            INNER JOIN productos p ON p.id = cd.producto_id
            WHERE cd.compra_id = %s
            ORDER BY cd.id
            """,
            (compra_id,),
        )

    def crear(self, proveedor_id, items, observaciones="", usuario_id=None):
        entradas = _normalizar_entradas(items)
        with bd.transaccion() as cursor:
            cursor.execute("SELECT id, nombre, activo FROM proveedores WHERE id = %s",
                           (proveedor_id,))
            proveedor = cursor.fetchone()
            if not proveedor or not proveedor["activo"]:
                raise ErrorValidacion("Seleccione un proveedor activo.")
            preparados = self._productos_bloqueados(cursor, entradas)
            total = sum((item["subtotal"] for item in preparados), Decimal("0.00"))
            cursor.execute(
                """
                INSERT INTO compras (folio, proveedor_id, usuario_id, subtotal, total,
                                     estado, observaciones)
                VALUES (%s, %s, %s, %s, %s, 'COMPLETADA', %s)
                """,
                (f"TMP-{uuid.uuid4().hex[:12]}", proveedor_id, usuario_id,
                 total, total, limpiar_texto(observaciones)[:300]),
            )
            compra_id = cursor.lastrowid
            folio = self._folio(cursor, compra_id)
            for item in preparados:
                cursor.execute(
                    """
                    INSERT INTO compra_detalle
                        (compra_id, producto_id, cantidad, costo_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (compra_id, item["producto_id"], item["cantidad"],
                     item["costo_unitario"], item["subtotal"]),
                )
                cursor.execute(
                    "UPDATE productos SET existencia = existencia + %s WHERE id = %s",
                    (item["cantidad"], item["producto_id"]),
                )
            auditoria.registrar(
                cursor, usuario_id, "CREAR", "COMPRA", compra_id,
                f"Compra {folio} a {proveedor['nombre']} por {total}.",
            )
        return {"id": compra_id, "folio": folio, "total": total}

    def modificar(self, compra_id, proveedor_id, items, observaciones="",
                  usuario_id=None):
        entradas = _normalizar_entradas(items)
        with bd.transaccion() as cursor:
            cursor.execute(
                "SELECT id, folio, estado FROM compras WHERE id = %s FOR UPDATE",
                (compra_id,),
            )
            compra = cursor.fetchone()
            if not compra:
                raise ErrorValidacion("La compra ya no existe.")
            if compra["estado"] == "CANCELADA":
                raise ErrorValidacion("No se puede modificar una compra cancelada.")
            cursor.execute("SELECT id, nombre, activo FROM proveedores WHERE id = %s",
                           (proveedor_id,))
            proveedor = cursor.fetchone()
            if not proveedor or not proveedor["activo"]:
                raise ErrorValidacion("Seleccione un proveedor activo.")

            cursor.execute(
                """
                SELECT cd.producto_id, cd.cantidad, p.codigo, p.nombre, p.existencia
                FROM compra_detalle cd
                INNER JOIN productos p ON p.id = cd.producto_id
                WHERE cd.compra_id = %s
                FOR UPDATE
                """,
                (compra_id,),
            )
            anteriores = cursor.fetchall()
            for item in anteriores:
                if item["existencia"] < item["cantidad"]:
                    raise ErrorValidacion(
                        f"No se puede modificar: parte de '{item['codigo']} - {item['nombre']}' "
                        f"ya fue vendida (existencia actual {item['existencia']}, "
                        f"comprada {item['cantidad']})."
                    )
            for item in anteriores:
                cursor.execute(
                    "UPDATE productos SET existencia = existencia - %s WHERE id = %s",
                    (item["cantidad"], item["producto_id"]),
                )

            preparados = self._productos_bloqueados(cursor, entradas)
            total = sum((item["subtotal"] for item in preparados), Decimal("0.00"))
            cursor.execute(
                """
                UPDATE compras
                SET proveedor_id = %s, subtotal = %s, total = %s, observaciones = %s
                WHERE id = %s
                """,
                (proveedor_id, total, total, limpiar_texto(observaciones)[:300], compra_id),
            )
            cursor.execute("DELETE FROM compra_detalle WHERE compra_id = %s", (compra_id,))
            for item in preparados:
                cursor.execute(
                    """
                    INSERT INTO compra_detalle
                        (compra_id, producto_id, cantidad, costo_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (compra_id, item["producto_id"], item["cantidad"],
                     item["costo_unitario"], item["subtotal"]),
                )
                cursor.execute(
                    "UPDATE productos SET existencia = existencia + %s WHERE id = %s",
                    (item["cantidad"], item["producto_id"]),
                )
            auditoria.registrar(
                cursor, usuario_id, "MODIFICAR", "COMPRA", compra_id,
                f"Compra {compra['folio']} modificada. Nuevo total {total}.",
            )
        return {"id": compra_id, "folio": compra["folio"], "total": total}

    def cancelar(self, compra_id, motivo, usuario_id=None):
        motivo = texto_requerido(motivo, "motivo de cancelación", 5, 300)
        with bd.transaccion() as cursor:
            cursor.execute(
                "SELECT id, folio, estado FROM compras WHERE id = %s FOR UPDATE",
                (compra_id,),
            )
            compra = cursor.fetchone()
            if not compra:
                raise ErrorValidacion("La compra ya no existe.")
            if compra["estado"] == "CANCELADA":
                raise ErrorValidacion("La compra ya está cancelada.")
            cursor.execute(
                """
                SELECT cd.producto_id, cd.cantidad, p.codigo, p.nombre, p.existencia
                FROM compra_detalle cd
                INNER JOIN productos p ON p.id = cd.producto_id
                WHERE cd.compra_id = %s
                FOR UPDATE
                """,
                (compra_id,),
            )
            partidas = cursor.fetchall()
            for item in partidas:
                if item["existencia"] < item["cantidad"]:
                    raise ErrorValidacion(
                        f"No se puede cancelar: parte de '{item['codigo']} - {item['nombre']}' "
                        f"ya fue vendida (existencia actual {item['existencia']}, "
                        f"comprada {item['cantidad']})."
                    )
            for item in partidas:
                cursor.execute(
                    "UPDATE productos SET existencia = existencia - %s WHERE id = %s",
                    (item["cantidad"], item["producto_id"]),
                )
            cursor.execute(
                """
                UPDATE compras
                SET estado = 'CANCELADA', cancelada_en = NOW(), cancelada_por = %s,
                    motivo_cancelacion = %s
                WHERE id = %s
                """,
                (usuario_id, motivo, compra_id),
            )
            auditoria.registrar(
                cursor, usuario_id, "CANCELAR", "COMPRA", compra_id,
                f"Compra {compra['folio']} cancelada. Motivo: {motivo}",
            )
        return {"folio": compra["folio"]}


compras_servicio = ComprasServicio()
