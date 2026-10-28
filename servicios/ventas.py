"""Ventas: descuentos, puntos, pagos, cancelaciones y modificaciones."""

import uuid
from decimal import Decimal, ROUND_HALF_UP

from base_datos import bd
from configuracion import (PORCENTAJE_DESCUENTO_PUNTOS, PORCENTAJE_DESCUENTO_VOLUMEN,
                           PUNTOS_PARA_CANJE, PESOS_POR_PUNTO,
                           UMBRAL_DESCUENTO_VOLUMEN)
from servicios import auditoria
from utilidades import (ErrorPermiso, ErrorValidacion, a_decimal, a_entero,
                        limpiar_texto, texto_requerido)

CENTAVOS = Decimal("0.01")
CIEN = Decimal("100.00")
METODOS_PAGO = ("EFECTIVO", "TARJETA", "TRANSFERENCIA")


def _redondear(valor):
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _normalizar_entradas(items):
    if not items:
        raise ErrorValidacion("Agregue al menos un producto a la venta.")
    agrupados = {}
    for item in items:
        producto_id = int(item.get("producto_id") or 0)
        cantidad = a_entero(item.get("cantidad"), "cantidad", 1)
        if producto_id <= 0:
            raise ErrorValidacion("Seleccione un producto válido.")
        if producto_id in agrupados:
            agrupados[producto_id]["cantidad"] += cantidad
        else:
            agrupados[producto_id] = {
                "producto_id": producto_id,
                "cantidad": cantidad,
            }
    return list(agrupados.values())


class VentasServicio:
    # ------------------------- utilidades internas -------------------------
    def _folio(self, cursor, venta_id):
        folio = f"VEN-{venta_id:06d}"
        cursor.execute("UPDATE ventas SET folio = %s WHERE id = %s", (folio, venta_id))
        return folio

    def _rol_usuario(self, cursor, usuario_id):
        cursor.execute(
            """
            SELECT r.nombre AS rol
            FROM usuarios u INNER JOIN roles r ON r.id = u.rol_id
            WHERE u.id = %s AND u.activo = 1
            """,
            (usuario_id,),
        )
        fila = cursor.fetchone()
        if not fila:
            raise ErrorValidacion("El usuario que realiza la operación no está activo.")
        return fila["rol"]

    def _verificar_autorizacion(self, cursor, usuario_id, autorizado_por_id):
        rol = self._rol_usuario(cursor, usuario_id)
        if rol == "Cajero":
            if not autorizado_por_id:
                raise ErrorPermiso(
                    "El cajero requiere autorización de un gerente o administrador "
                    "para esta operación."
                )
            cursor.execute(
                """
                SELECT r.nombre AS rol
                FROM usuarios u INNER JOIN roles r ON r.id = u.rol_id
                WHERE u.id = %s AND u.activo = 1
                """,
                (autorizado_por_id,),
            )
            autorizador = cursor.fetchone()
            if not autorizador or autorizador["rol"] not in ("Gerente", "Administrador"):
                raise ErrorPermiso(
                    "La autorización debe provenir de un gerente o administrador activo."
                )

    def _obtener_cliente(self, cursor, cliente_id, bloquear=False):
        sufijo = " FOR UPDATE" if bloquear else ""
        cursor.execute(
            f"""
            SELECT id, codigo, nombre, apellido, telefono, email, puntos,
                   puntos_historicos, activo
            FROM clientes WHERE id = %s{sufijo}
            """,
            (cliente_id,),
        )
        cliente = cursor.fetchone()
        if not cliente:
            raise ErrorValidacion("El cliente seleccionado no existe.")
        if not cliente["activo"]:
            raise ErrorValidacion("El cliente está cancelado. Seleccione o registre otro cliente.")
        return cliente

    def _productos(self, cursor, entradas, bloquear=True):
        preparados = []
        sufijo = " FOR UPDATE" if bloquear else ""
        for item in entradas:
            cursor.execute(
                f"""
                SELECT p.id, p.codigo, p.nombre, p.descripcion, p.precio_venta,
                       p.existencia, p.activo, COALESCE(c.nombre, 'Sin categoría') AS categoria
                FROM productos p
                LEFT JOIN categorias c ON c.id = p.categoria_id
                WHERE p.id = %s{sufijo}
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
            if producto["existencia"] < item["cantidad"]:
                raise ErrorValidacion(
                    f"Existencias insuficientes de '{producto['codigo']} - "
                    f"{producto['nombre']}'. Disponible: {producto['existencia']}, "
                    f"solicitado: {item['cantidad']}."
                )
            precio = _redondear(producto["precio_venta"])
            preparado = dict(producto)
            preparado["cantidad"] = item["cantidad"]
            preparado["precio_venta"] = precio
            preparado["subtotal"] = _redondear(precio * item["cantidad"])
            preparados.append(preparado)
        return preparados

    def _calcular(self, preparados, puntos_cliente, canjear_puntos):
        subtotal = sum((item["subtotal"] for item in preparados), Decimal("0.00"))
        subtotal = _redondear(subtotal)
        descuento_volumen = Decimal("0.00")
        if subtotal > _redondear(UMBRAL_DESCUENTO_VOLUMEN):
            descuento_volumen = _redondear(
                subtotal * Decimal(str(PORCENTAJE_DESCUENTO_VOLUMEN))
            )
        base = _redondear(subtotal - descuento_volumen)
        descuento_puntos = Decimal("0.00")
        puntos_canjeados = 0
        if canjear_puntos:
            if puntos_cliente < PUNTOS_PARA_CANJE:
                raise ErrorValidacion(
                    f"El cliente necesita al menos {PUNTOS_PARA_CANJE} puntos para "
                    f"aplicar el descuento del 50%. Puntos disponibles: {puntos_cliente}."
                )
            descuento_puntos = _redondear(
                base * Decimal(str(PORCENTAJE_DESCUENTO_PUNTOS))
            )
            puntos_canjeados = PUNTOS_PARA_CANJE
        total = _redondear(base - descuento_puntos)
        if total < 0:
            total = Decimal("0.00")
        puntos_ganados = int(total // Decimal(str(PESOS_POR_PUNTO)))
        return {
            "subtotal": subtotal,
            "descuento_volumen": descuento_volumen,
            "descuento_puntos": descuento_puntos,
            "total": total,
            "puntos_ganados": puntos_ganados,
            "puntos_canjeados": puntos_canjeados,
            "puntos_disponibles": int(puntos_cliente),
        }

    def _validar_pago(self, metodo_pago, total, monto_recibido):
        metodo_pago = (metodo_pago or "").upper()
        if metodo_pago not in METODOS_PAGO:
            raise ErrorValidacion("Seleccione un método de pago válido.")
        if metodo_pago == "EFECTIVO":
            recibido = a_decimal(monto_recibido, "monto recibido")
            if recibido < total:
                raise ErrorValidacion(
                    f"El monto recibido ({recibido}) es menor que el total a pagar ({total})."
                )
            cambio = _redondear(recibido - total)
        else:
            recibido = total
            cambio = Decimal("0.00")
        return metodo_pago, recibido, cambio

    def _movimiento(self, cursor, cliente_id, venta_id, usuario_id, tipo, puntos,
                    descripcion):
        if puntos == 0:
            return
        cursor.execute(
            """
            INSERT INTO movimientos_puntos
                (cliente_id, venta_id, usuario_id, tipo, puntos, descripcion)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (cliente_id, venta_id, usuario_id, tipo, int(puntos), descripcion[:250]),
        )

    def _aplicar_puntos(self, cursor, cliente_id, venta_id, usuario_id,
                        puntos_ganados, puntos_canjeados, folio):
        cursor.execute(
            """
            UPDATE clientes
            SET puntos = puntos - %s + %s,
                puntos_historicos = puntos_historicos + %s
            WHERE id = %s
            """,
            (puntos_canjeados, puntos_ganados, puntos_ganados, cliente_id),
        )
        self._movimiento(
            cursor, cliente_id, venta_id, usuario_id, "CANJEADO", -puntos_canjeados,
            f"Canje de {puntos_canjeados} puntos en venta {folio} (50% de descuento).",
        )
        self._movimiento(
            cursor, cliente_id, venta_id, usuario_id, "GANADO", puntos_ganados,
            f"Puntos ganados en venta {folio} (1 punto por cada $100.00).",
        )

    # ------------------------------ consultas ------------------------------
    def listar(self, texto="", estado="TODAS", fecha_desde=None, fecha_hasta=None,
               cliente_id=None, usuario_id=None):
        filtro = f"%{limpiar_texto(texto).lower()}%"
        condiciones = [
            "(LOWER(v.folio) LIKE %s OR LOWER(c.codigo) LIKE %s "
            "OR LOWER(CONCAT(c.nombre, ' ', c.apellido)) LIKE %s "
            "OR LOWER(u.nombre_completo) LIKE %s)"
        ]
        params = [filtro, filtro, filtro, filtro]
        if estado in ("COMPLETADA", "CANCELADA"):
            condiciones.append("v.estado = %s")
            params.append(estado)
        if fecha_desde:
            condiciones.append("DATE(v.fecha) >= %s")
            params.append(fecha_desde)
        if fecha_hasta:
            condiciones.append("DATE(v.fecha) <= %s")
            params.append(fecha_hasta)
        if cliente_id:
            condiciones.append("v.cliente_id = %s")
            params.append(cliente_id)
        if usuario_id:
            condiciones.append("v.usuario_id = %s")
            params.append(usuario_id)
        where = " AND ".join(condiciones)
        return bd.obtener_todos(
            f"""
            SELECT v.id, v.folio, v.fecha, v.subtotal, v.descuento_volumen,
                   v.descuento_puntos, v.total, v.puntos_ganados, v.puntos_canjeados,
                   v.metodo_pago, v.estado, v.monto_recibido, v.cambio,
                   c.codigo, CONCAT(c.nombre, ' ', c.apellido) AS cliente,
                   u.nombre_completo AS usuario
            FROM ventas v
            INNER JOIN clientes c ON c.id = v.cliente_id
            INNER JOIN usuarios u ON u.id = v.usuario_id
            WHERE {where}
            ORDER BY v.fecha DESC, v.id DESC
            LIMIT 500
            """,
            tuple(params),
        )

    def obtener(self, venta_id):
        return bd.obtener_uno(
            """
            SELECT v.*, c.codigo, CONCAT(c.nombre, ' ', c.apellido) AS cliente,
                   c.puntos AS puntos_cliente, u.nombre_completo AS usuario,
                   cu.nombre_completo AS cancelada_por_nombre,
                   au.nombre_completo AS autorizado_por_nombre
            FROM ventas v
            INNER JOIN clientes c ON c.id = v.cliente_id
            INNER JOIN usuarios u ON u.id = v.usuario_id
            LEFT JOIN usuarios cu ON cu.id = v.cancelada_por
            LEFT JOIN usuarios au ON au.id = v.autorizado_por
            WHERE v.id = %s
            """,
            (venta_id,),
        )

    def detalle(self, venta_id):
        return bd.obtener_todos(
            """
            SELECT vd.id, vd.producto_id, vd.cantidad, vd.precio_unitario, vd.subtotal,
                   p.codigo, p.nombre
            FROM venta_detalle vd
            INNER JOIN productos p ON p.id = vd.producto_id
            WHERE vd.venta_id = %s
            ORDER BY vd.id
            """,
            (venta_id,),
        )

    def puntos_disponibles_edicion(self, venta_id):
        fila = bd.obtener_uno(
            """
            SELECT v.cliente_id, v.puntos_ganados, v.puntos_canjeados, c.puntos,
                   c.codigo, c.nombre, c.apellido
            FROM ventas v
            INNER JOIN clientes c ON c.id = v.cliente_id
            WHERE v.id = %s
            """,
            (venta_id,),
        )
        if not fila:
            return 0
        return max(0, fila["puntos"] - fila["puntos_ganados"] + fila["puntos_canjeados"])

    def vista_previa(self, cliente_id, items, canjear_puntos=False,
                     venta_editada_id=None, cliente_editado_id=None):
        """Calcula totales y descuentos sin guardar, para mostrarlos en el POS."""
        entradas = _normalizar_entradas(items)
        with bd.transaccion() as cursor:
            cliente = self._obtener_cliente(cursor, cliente_id)
            puntos = cliente["puntos"]
            if venta_editada_id and cliente_editado_id == cliente["id"]:
                puntos = self.puntos_disponibles_edicion(venta_editada_id)
            preparados = self._productos(cursor, entradas, bloquear=False)
            calculo = self._calcular(preparados, puntos, canjear_puntos)
        calculo["cliente"] = cliente
        calculo["items"] = preparados
        return calculo

    # ------------------------------ comandos ------------------------------
    def registrar_venta(self, cliente_id, items, metodo_pago, monto_recibido,
                        canjear_puntos, usuario_id, observaciones=""):
        entradas = _normalizar_entradas(items)
        with bd.transaccion() as cursor:
            self._rol_usuario(cursor, usuario_id)
            cliente = self._obtener_cliente(cursor, cliente_id, bloquear=True)
            preparados = self._productos(cursor, entradas, bloquear=True)
            calculo = self._calcular(preparados, cliente["puntos"], canjear_puntos)
            metodo, recibido, cambio = self._validar_pago(
                metodo_pago, calculo["total"], monto_recibido
            )
            cursor.execute(
                """
                INSERT INTO ventas
                    (folio, cliente_id, usuario_id, subtotal, descuento_volumen,
                     descuento_puntos, total, puntos_ganados, puntos_canjeados,
                     metodo_pago, monto_recibido, cambio, estado, observaciones)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        'COMPLETADA', %s)
                """,
                (f"TMP-{uuid.uuid4().hex[:12]}", cliente_id, usuario_id,
                 calculo["subtotal"], calculo["descuento_volumen"],
                 calculo["descuento_puntos"], calculo["total"],
                 calculo["puntos_ganados"], calculo["puntos_canjeados"],
                 metodo, recibido, cambio, limpiar_texto(observaciones)[:300]),
            )
            venta_id = cursor.lastrowid
            folio = self._folio(cursor, venta_id)
            for item in preparados:
                cursor.execute(
                    """
                    INSERT INTO venta_detalle
                        (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (venta_id, item["id"], item["cantidad"], item["precio_venta"],
                     item["subtotal"]),
                )
                cursor.execute(
                    "UPDATE productos SET existencia = existencia - %s WHERE id = %s",
                    (item["cantidad"], item["id"]),
                )
            self._aplicar_puntos(
                cursor, cliente_id, venta_id, usuario_id, calculo["puntos_ganados"],
                calculo["puntos_canjeados"], folio,
            )
            auditoria.registrar(
                cursor, usuario_id, "CREAR", "VENTA", venta_id,
                f"Venta {folio} al cliente {cliente['codigo']} por {calculo['total']}. "
                f"Puntos ganados: {calculo['puntos_ganados']}.",
            )
        calculo.update({
            "id": venta_id,
            "folio": folio,
            "metodo_pago": metodo,
            "monto_recibido": recibido,
            "cambio": cambio,
            "cliente": cliente,
            "items": preparados,
        })
        return calculo

    def cancelar_venta(self, venta_id, motivo, usuario_id, autorizado_por_id=None):
        motivo = texto_requerido(motivo, "motivo de cancelación", 5, 300)
        with bd.transaccion() as cursor:
            self._verificar_autorizacion(cursor, usuario_id, autorizado_por_id)
            cursor.execute(
                "SELECT * FROM ventas WHERE id = %s FOR UPDATE", (venta_id,)
            )
            venta = cursor.fetchone()
            if not venta:
                raise ErrorValidacion("La venta ya no existe.")
            if venta["estado"] == "CANCELADA":
                raise ErrorValidacion("La venta ya está cancelada.")
            cursor.execute(
                """
                SELECT vd.producto_id, vd.cantidad, p.codigo, p.nombre
                FROM venta_detalle vd
                INNER JOIN productos p ON p.id = vd.producto_id
                WHERE vd.venta_id = %s
                FOR UPDATE
                """,
                (venta_id,),
            )
            partidas = cursor.fetchall()
            for item in partidas:
                cursor.execute(
                    "UPDATE productos SET existencia = existencia + %s WHERE id = %s",
                    (item["cantidad"], item["producto_id"]),
                )
            cliente = self._obtener_cliente(cursor, venta["cliente_id"], bloquear=True)
            nuevo_saldo = max(
                0,
                cliente["puntos"] - venta["puntos_ganados"] + venta["puntos_canjeados"],
            )
            delta = nuevo_saldo - cliente["puntos"]
            cursor.execute(
                """
                UPDATE clientes
                SET puntos = %s,
                    puntos_historicos = GREATEST(0, puntos_historicos - %s)
                WHERE id = %s
                """,
                (nuevo_saldo, venta["puntos_ganados"], cliente["id"]),
            )
            self._movimiento(
                cursor, cliente["id"], venta_id, usuario_id, "REVERSO", delta,
                f"Ajuste de puntos por cancelación de venta {venta['folio']}.",
            )
            cursor.execute(
                """
                UPDATE ventas
                SET estado = 'CANCELADA', cancelada_en = NOW(), cancelada_por = %s,
                    motivo_cancelacion = %s, autorizado_por = %s
                WHERE id = %s
                """,
                (usuario_id, motivo, autorizado_por_id, venta_id),
            )
            auditoria.registrar(
                cursor, usuario_id, "CANCELAR", "VENTA", venta_id,
                f"Venta {venta['folio']} cancelada. Motivo: {motivo}. "
                f"Autorizó: {autorizado_por_id or 'no aplica'}.",
            )
        return {"folio": venta["folio"]}

    def modificar_venta(self, venta_id, cliente_id, items, metodo_pago, monto_recibido,
                        canjear_puntos, usuario_id, motivo,
                        autorizado_por_id=None, observaciones=None):
        entradas = _normalizar_entradas(items)
        motivo = texto_requerido(motivo, "motivo de modificación", 5, 300)
        with bd.transaccion() as cursor:
            self._verificar_autorizacion(cursor, usuario_id, autorizado_por_id)
            cursor.execute("SELECT * FROM ventas WHERE id = %s FOR UPDATE", (venta_id,))
            venta = cursor.fetchone()
            if not venta:
                raise ErrorValidacion("La venta ya no existe.")
            if venta["estado"] == "CANCELADA":
                raise ErrorValidacion("No se puede modificar una venta cancelada.")

            cliente_anterior = self._obtener_cliente(
                cursor, venta["cliente_id"], bloquear=True
            )
            cursor.execute(
                """
                SELECT vd.producto_id, vd.cantidad, p.codigo, p.nombre
                FROM venta_detalle vd
                INNER JOIN productos p ON p.id = vd.producto_id
                WHERE vd.venta_id = %s
                FOR UPDATE
                """,
                (venta_id,),
            )
            partidas_anteriores = cursor.fetchall()
            for item in partidas_anteriores:
                cursor.execute(
                    "UPDATE productos SET existencia = existencia + %s WHERE id = %s",
                    (item["cantidad"], item["producto_id"]),
                )

            disponibles_anteriores = max(
                0,
                cliente_anterior["puntos"] - venta["puntos_ganados"]
                + venta["puntos_canjeados"],
            )
            delta_anterior = disponibles_anteriores - cliente_anterior["puntos"]
            cursor.execute(
                """
                UPDATE clientes
                SET puntos = %s,
                    puntos_historicos = GREATEST(0, puntos_historicos - %s)
                WHERE id = %s
                """,
                (disponibles_anteriores, venta["puntos_ganados"], cliente_anterior["id"]),
            )
            self._movimiento(
                cursor, cliente_anterior["id"], venta_id, usuario_id, "REVERSO",
                delta_anterior,
                f"Ajuste por modificación de la venta {venta['folio']}.",
            )

            mismo_cliente = int(cliente_id) == cliente_anterior["id"]
            if mismo_cliente:
                cliente_nuevo = dict(cliente_anterior)
                cliente_nuevo["puntos"] = disponibles_anteriores
            else:
                cliente_nuevo = self._obtener_cliente(cursor, cliente_id, bloquear=True)

            preparados = self._productos(cursor, entradas, bloquear=True)
            calculo = self._calcular(
                preparados, cliente_nuevo["puntos"], canjear_puntos
            )
            metodo, recibido, cambio = self._validar_pago(
                metodo_pago, calculo["total"], monto_recibido
            )

            cursor.execute(
                """
                UPDATE ventas
                SET cliente_id = %s, subtotal = %s, descuento_volumen = %s,
                    descuento_puntos = %s, total = %s, puntos_ganados = %s,
                    puntos_canjeados = %s, metodo_pago = %s, monto_recibido = %s,
                    cambio = %s, observaciones = %s, autorizado_por = %s
                WHERE id = %s
                """,
                (cliente_id, calculo["subtotal"], calculo["descuento_volumen"],
                 calculo["descuento_puntos"], calculo["total"],
                 calculo["puntos_ganados"], calculo["puntos_canjeados"], metodo,
                 recibido, cambio,
                 limpiar_texto(observaciones if observaciones is not None
                               else venta["observaciones"])[:300],
                 autorizado_por_id, venta_id),
            )
            cursor.execute("DELETE FROM venta_detalle WHERE venta_id = %s", (venta_id,))
            for item in preparados:
                cursor.execute(
                    """
                    INSERT INTO venta_detalle
                        (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (venta_id, item["id"], item["cantidad"], item["precio_venta"],
                     item["subtotal"]),
                )
                cursor.execute(
                    "UPDATE productos SET existencia = existencia - %s WHERE id = %s",
                    (item["cantidad"], item["id"]),
                )
            self._aplicar_puntos(
                cursor, cliente_nuevo["id"], venta_id, usuario_id,
                calculo["puntos_ganados"], calculo["puntos_canjeados"],
                venta["folio"],
            )
            auditoria.registrar(
                cursor, usuario_id, "MODIFICAR", "VENTA", venta_id,
                f"Venta {venta['folio']} modificada. Motivo: {motivo}. "
                f"Nuevo total: {calculo['total']}.",
            )
        calculo.update({
            "id": venta_id,
            "folio": venta["folio"],
            "metodo_pago": metodo,
            "monto_recibido": recibido,
            "cambio": cambio,
            "cliente": cliente_nuevo,
            "items": preparados,
        })
        return calculo

    def resumen_hoy(self, usuario_id=None):
        condicion = "AND v.usuario_id = %s" if usuario_id else ""
        params = (usuario_id,) if usuario_id else ()
        fila = bd.obtener_uno(
            f"""
            SELECT COUNT(*) AS cantidad, COALESCE(SUM(v.total), 0) AS total,
                   COALESCE(SUM(v.puntos_ganados), 0) AS puntos
            FROM ventas v
            WHERE v.estado = 'COMPLETADA' AND DATE(v.fecha) = CURDATE() {condicion}
            """,
            params,
        )
        return fila


ventas_servicio = VentasServicio()
