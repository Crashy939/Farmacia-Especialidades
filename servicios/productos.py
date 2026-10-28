"""CRUD de productos, categorías y consultas de inventario."""

from base_datos import bd
from servicios import auditoria
from utilidades import (ErrorValidacion, a_decimal, a_entero, limpiar_texto,
                        texto_requerido)


class ProductosServicio:
    def listar(self, texto="", incluir_inactivos=False, solo_bajo_stock=False):
        filtro = f"%{limpiar_texto(texto).lower()}%"
        condiciones = []
        if not incluir_inactivos:
            condiciones.append("p.activo = 1")
        if solo_bajo_stock:
            condiciones.append("p.existencia <= p.stock_minimo")
        where = " AND ".join(condiciones) if condiciones else "1 = 1"
        return bd.obtener_todos(
            f"""
            SELECT p.id, p.codigo, p.nombre, p.descripcion, p.precio_compra,
                   p.precio_venta, p.existencia, p.stock_minimo, p.activo,
                   p.categoria_id, p.proveedor_id,
                   COALESCE(c.nombre, 'Sin categoría') AS categoria,
                   COALESCE(pr.nombre, 'Sin proveedor') AS proveedor
            FROM productos p
            LEFT JOIN categorias c ON c.id = p.categoria_id
            LEFT JOIN proveedores pr ON pr.id = p.proveedor_id
            WHERE (LOWER(p.codigo) LIKE %s OR LOWER(p.nombre) LIKE %s
                   OR LOWER(COALESCE(p.descripcion, '')) LIKE %s)
              AND {where}
            ORDER BY p.activo DESC, p.nombre
            """,
            (filtro, filtro, filtro),
        )

    def obtener(self, producto_id):
        return bd.obtener_uno(
            """
            SELECT p.*, COALESCE(c.nombre, 'Sin categoría') AS categoria,
                   COALESCE(pr.nombre, 'Sin proveedor') AS proveedor
            FROM productos p
            LEFT JOIN categorias c ON c.id = p.categoria_id
            LEFT JOIN proveedores pr ON pr.id = p.proveedor_id
            WHERE p.id = %s
            """,
            (producto_id,),
        )

    def sugerir_codigo(self, prefijo="MED"):
        fila = bd.obtener_uno("SELECT COALESCE(MAX(id), 0) + 1 AS siguiente FROM productos")
        numero = int(fila["siguiente"]) if fila else 1
        while True:
            codigo = f"{prefijo.upper()}-{numero:03d}"
            if not bd.obtener_uno("SELECT id FROM productos WHERE codigo = %s", (codigo,)):
                return codigo
            numero += 1


    def buscar_para_venta(self, texto="", limite=25):
        """Solo productos activos con existencia disponible (requisito 8)."""
        filtro = f"%{limpiar_texto(texto).lower()}%"
        return bd.obtener_todos(
            """
            SELECT p.id, p.codigo, p.nombre, p.descripcion, p.precio_venta,
                   p.existencia, COALESCE(c.nombre, 'Sin categoría') AS categoria
            FROM productos p
            LEFT JOIN categorias c ON c.id = p.categoria_id
            WHERE p.activo = 1
              AND (LOWER(p.codigo) LIKE %s OR LOWER(p.nombre) LIKE %s
                   OR LOWER(COALESCE(p.descripcion, '')) LIKE %s)
            ORDER BY (p.existencia > 0) DESC, p.nombre
            LIMIT %s
            """,
            (filtro, filtro, filtro, limite),
        )

    def _validar_datos(self, codigo, nombre, precio_compra, precio_venta,
                       existencia, stock_minimo):
        codigo = texto_requerido(codigo, "código", 2, 30).upper()
        nombre = texto_requerido(nombre, "nombre", 2, 120)
        costo = a_decimal(precio_compra, "precio de compra")
        precio = a_decimal(precio_venta, "precio de venta")
        stock = a_entero(existencia, "existencia", 0)
        minimo = a_entero(stock_minimo, "stock mínimo", 0)
        if costo < 0 or precio < 0:
            raise ErrorValidacion("Los precios no pueden ser negativos.")
        if precio == 0:
            raise ErrorValidacion("El precio de venta debe ser mayor que cero.")
        return codigo, nombre, costo, precio, stock, minimo

    def crear(self, codigo, nombre, descripcion, categoria_id, proveedor_id,
              precio_compra, precio_venta, existencia, stock_minimo, ejecutor_id=None):
        codigo, nombre, costo, precio, stock, minimo = self._validar_datos(
            codigo, nombre, precio_compra, precio_venta, existencia, stock_minimo
        )
        with bd.transaccion() as cursor:
            cursor.execute("SELECT id FROM productos WHERE codigo = %s", (codigo,))
            if cursor.fetchone():
                raise ErrorValidacion(f"El código '{codigo}' ya está registrado.")
            cursor.execute(
                """
                INSERT INTO productos
                    (codigo, nombre, descripcion, categoria_id, proveedor_id,
                     precio_compra, precio_venta, existencia, stock_minimo, activo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                """,
                (codigo, nombre, limpiar_texto(descripcion)[:250],
                 categoria_id or None, proveedor_id or None,
                 costo, precio, stock, minimo),
            )
            producto_id = cursor.lastrowid
            auditoria.registrar(
                cursor, ejecutor_id, "CREAR", "PRODUCTO", producto_id,
                f"Producto {codigo} - {nombre}, existencia inicial {stock}.",
            )
        return producto_id

    def actualizar(self, producto_id, codigo, nombre, descripcion, categoria_id,
                   proveedor_id, precio_compra, precio_venta, existencia,
                   stock_minimo, ejecutor_id=None):
        codigo, nombre, costo, precio, stock, minimo = self._validar_datos(
            codigo, nombre, precio_compra, precio_venta, existencia, stock_minimo
        )
        with bd.transaccion() as cursor:
            cursor.execute("SELECT id, codigo FROM productos WHERE id = %s FOR UPDATE",
                           (producto_id,))
            actual = cursor.fetchone()
            if not actual:
                raise ErrorValidacion("El producto ya no existe.")
            cursor.execute(
                "SELECT id FROM productos WHERE codigo = %s AND id <> %s",
                (codigo, producto_id),
            )
            if cursor.fetchone():
                raise ErrorValidacion(f"El código '{codigo}' pertenece a otro producto.")
            cursor.execute(
                """
                UPDATE productos
                SET codigo = %s, nombre = %s, descripcion = %s, categoria_id = %s,
                    proveedor_id = %s, precio_compra = %s, precio_venta = %s,
                    existencia = %s, stock_minimo = %s
                WHERE id = %s
                """,
                (codigo, nombre, limpiar_texto(descripcion)[:250], categoria_id or None,
                 proveedor_id or None, costo, precio, stock, minimo, producto_id),
            )
            auditoria.registrar(
                cursor, ejecutor_id, "MODIFICAR", "PRODUCTO", producto_id,
                f"Producto {codigo} actualizado. Existencia {stock}.",
            )

    def cambiar_estado(self, producto_id, activo, ejecutor_id=None):
        with bd.transaccion() as cursor:
            cursor.execute(
                "SELECT id, codigo, nombre FROM productos WHERE id = %s FOR UPDATE",
                (producto_id,),
            )
            producto = cursor.fetchone()
            if not producto:
                raise ErrorValidacion("El producto ya no existe.")
            cursor.execute("UPDATE productos SET activo = %s WHERE id = %s",
                           (1 if activo else 0, producto_id))
            auditoria.registrar(
                cursor, ejecutor_id, "ACTIVAR" if activo else "CANCELAR", "PRODUCTO",
                producto_id,
                f"Producto {producto['codigo']} {'reactivado' if activo else 'cancelado'}.",
            )

    # ------------------------- Categorías -------------------------
    def listar_categorias(self, incluir_inactivas=False):
        condicion = "" if incluir_inactivas else "WHERE activo = 1"
        return bd.obtener_todos(
            f"SELECT id, nombre, descripcion, activo FROM categorias {condicion} "
            "ORDER BY nombre"
        )

    def crear_categoria(self, nombre, descripcion="", ejecutor_id=None):
        nombre = texto_requerido(nombre, "nombre de categoría", 2, 80)
        with bd.transaccion() as cursor:
            cursor.execute("SELECT id FROM categorias WHERE LOWER(nombre) = LOWER(%s)",
                           (nombre,))
            if cursor.fetchone():
                raise ErrorValidacion(f"La categoría '{nombre}' ya existe.")
            cursor.execute(
                "INSERT INTO categorias (nombre, descripcion, activo) VALUES (%s, %s, 1)",
                (nombre, limpiar_texto(descripcion)[:200]),
            )
            categoria_id = cursor.lastrowid
            auditoria.registrar(cursor, ejecutor_id, "CREAR", "CATEGORIA", categoria_id,
                                f"Categoría {nombre}.")
        return categoria_id

    def cambiar_estado_categoria(self, categoria_id, activo, ejecutor_id=None):
        with bd.transaccion() as cursor:
            cursor.execute("SELECT nombre FROM categorias WHERE id = %s FOR UPDATE",
                           (categoria_id,))
            categoria = cursor.fetchone()
            if not categoria:
                raise ErrorValidacion("La categoría ya no existe.")
            cursor.execute("UPDATE categorias SET activo = %s WHERE id = %s",
                           (1 if activo else 0, categoria_id))
            auditoria.registrar(
                cursor, ejecutor_id, "ACTIVAR" if activo else "CANCELAR", "CATEGORIA",
                categoria_id, f"Categoría {categoria['nombre']}.",
            )


productos_servicio = ProductosServicio()
