"""Módulo de compras a proveedores y administración de proveedores."""

import customtkinter as ctk

from configuracion import COLORES
from servicios.compras import compras_servicio
from servicios.productos import productos_servicio
from servicios.proveedores import proveedores_servicio
from ui.componentes import (BarraBusqueda, Campo, CampoCombo, CampoTexto, ModalBase,
                            TablaDatos, boton, confirmar, formato_dinero,
                            formato_fecha, fuente, mostrar_error, mostrar_exito,
                            solicitar_motivo, texto_estado)
from utilidades import ErrorValidacion, a_decimal, a_entero, dinero


class DetalleCompra(ModalBase):
    def __init__(self, master, compra):
        super().__init__(master, f"Compra {compra['folio']}",
                         f"{compra['proveedor']} · {formato_fecha(compra['fecha'])}",
                         ancho=760, alto=620)
        self.compra = compra
        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=20, pady=16)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(2, weight=1)

        datos = ctk.CTkFrame(contenedor, fg_color=COLORES["panel_alt"],
                             corner_radius=9)
        datos.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        datos.grid_columnconfigure(1, weight=1)
        datos.grid_columnconfigure(3, weight=1)
        self._dato(datos, 0, 0, "Proveedor", compra["proveedor"])
        self._dato(datos, 0, 2, "Registró", compra["usuario"])
        self._dato(datos, 1, 0, "Estado", texto_estado(compra["estado"]))
        self._dato(datos, 1, 2, "Total", dinero(compra["total"]))
        if compra.get("observaciones"):
            self._dato(datos, 2, 0, "Observaciones", compra["observaciones"], span=4)

        ctk.CTkLabel(contenedor, text="Detalle de productos", font=fuente(13, True),
                     text_color=COLORES["texto"], anchor="w").grid(
            row=1, column=0, sticky="w", pady=(2, 6)
        )
        self.tabla = TablaDatos(
            contenedor,
            [
                {"titulo": "Código", "clave": "codigo", "peso": 1},
                {"titulo": "Producto", "clave": "nombre", "peso": 3},
                {"titulo": "Cantidad", "clave": "cantidad", "peso": 1,
                 "alineacion": "center"},
                {"titulo": "Costo", "clave": "costo_unitario", "peso": 1,
                 "formato": formato_dinero, "alineacion": "e"},
                {"titulo": "Subtotal", "clave": "subtotal", "peso": 1,
                 "formato": formato_dinero, "alineacion": "e"},
            ],
            altura=260,
        )
        self.tabla.grid(row=2, column=0, sticky="nsew")
        self.agregar_boton("Cerrar", self._cerrar, tipo="secundario", ancho=110)
        self.after(100, self._cargar)

    @staticmethod
    def _dato(master, fila, columna, etiqueta, valor, span=1):
        ctk.CTkLabel(master, text=etiqueta, font=fuente(10, True),
                     text_color=COLORES["texto_suave"], anchor="w").grid(
            row=fila, column=columna, sticky="w", padx=(14, 8), pady=(8 if fila == 0 else 3, 0)
        )
        ctk.CTkLabel(master, text=str(valor or "—"), font=fuente(12, True),
                     text_color=COLORES["texto"], anchor="w").grid(
            row=fila, column=columna + 1, columnspan=span, sticky="w",
            padx=(0, 14), pady=(8 if fila == 0 else 3, 0)
        )

    def _cargar(self):
        try:
            self.tabla.cargar(compras_servicio.detalle(self.compra["id"]))
        except Exception as exc:
            mostrar_error(self, exc)


class FormularioCompra(ModalBase):
    def __init__(self, master, sesion, compra=None):
        self.compra = compra
        titulo = "Editar compra" if compra else "Nueva compra"
        super().__init__(master, titulo,
                         "Registre el reabastecimiento; el inventario se actualiza al guardar.",
                         ancho=800, alto=730)
        self.sesion = sesion
        self.guardado = False
        self.items = []
        self.mapa_proveedores = {}
        self.mapa_productos = {}

        proveedores = proveedores_servicio.listar()
        self.mapa_proveedores = {p["nombre"]: p["id"] for p in proveedores}
        productos = productos_servicio.listar(incluir_inactivos=bool(compra))
        for producto in productos:
            clave = f"{producto['codigo']} - {producto['nombre']}"
            self.mapa_productos[clave] = producto

        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=22, pady=16)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(3, weight=1)

        cabecera = ctk.CTkFrame(contenedor, fg_color="transparent")
        cabecera.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        cabecera.grid_columnconfigure(0, weight=1)
        cabecera.grid_columnconfigure(1, weight=1)
        self.proveedor = CampoCombo(cabecera, "Proveedor",
                                    list(self.mapa_proveedores.keys()) or ["Sin proveedores"],
                                    requerido=True)
        self.proveedor.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.observaciones = Campo(cabecera, "Observaciones",
                                   placeholder="Factura, condiciones, etc.")
        self.observaciones.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        agregar = ctk.CTkFrame(contenedor, fg_color=COLORES["panel_alt"],
                               corner_radius=10)
        agregar.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        agregar.grid_columnconfigure(0, weight=2)
        agregar.grid_columnconfigure(1, weight=1)
        agregar.grid_columnconfigure(2, weight=1)
        self.selector = CampoCombo(agregar, "Producto",
                                   list(self.mapa_productos.keys()) or ["Sin productos"],
                                   ancho=280,
                                   comando=self._seleccionar_producto)
        self.selector.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=12)
        self.cantidad = Campo(agregar, "Cantidad", requerido=True, placeholder="1",
                              ancho=80)
        self.cantidad.grid(row=0, column=1, sticky="ew", padx=8, pady=12)
        self.costo = Campo(agregar, "Costo unitario", requerido=True,
                           placeholder="0.00", ancho=100)
        self.costo.grid(row=0, column=2, sticky="ew", padx=8, pady=12)
        boton(agregar, "+ Agregar", self._agregar, tipo="primario", ancho=110,
              alto=38).grid(row=1, column=0, columnspan=3, sticky="e",
                            padx=14, pady=(0, 12))

        self.tabla = TablaDatos(
            contenedor,
            [
                {"titulo": "Código", "clave": "codigo", "peso": 1},
                {"titulo": "Producto", "clave": "nombre", "peso": 3},
                {"titulo": "Cantidad", "clave": "cantidad", "peso": 1,
                 "alineacion": "center"},
                {"titulo": "Costo", "clave": "costo_unitario", "peso": 1,
                 "formato": formato_dinero, "alineacion": "e"},
                {"titulo": "Subtotal", "clave": "subtotal", "peso": 1,
                 "formato": formato_dinero, "alineacion": "e"},
            ],
            altura=240,
        )
        self.tabla.grid(row=3, column=0, sticky="nsew")
        self.tabla.columnas = self.tabla.columnas  # referencia explícita

        pie_tabla = ctk.CTkFrame(contenedor, fg_color="transparent")
        pie_tabla.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        pie_tabla.grid_columnconfigure(1, weight=1)
        boton(pie_tabla, "Quitar seleccionado", self._quitar, tipo="fantasma",
              ancho=150, alto=34).grid(row=0, column=0, sticky="w")
        self.total = ctk.CTkLabel(pie_tabla, text="Total: $0.00",
                                  font=fuente(18, True),
                                  text_color=COLORES["primario"], anchor="e")
        self.total.grid(row=0, column=1, sticky="e")

        self.error = ctk.CTkLabel(contenedor, text="", font=fuente(11),
                                  text_color=COLORES["peligro"], anchor="w",
                                  justify="left", wraplength=680)
        self.error.grid(row=5, column=0, sticky="w", pady=(4, 0))

        self.agregar_boton("Cancelar", self._cancelar, tipo="secundario", ancho=110)
        self.agregar_boton("Guardar compra", self._guardar, tipo="primario",
                           ancho=145)

        if compra:
            self.proveedor.establecer(compra["proveedor"])
            self.observaciones.establecer(compra.get("observaciones") or "")
            detalles = compras_servicio.detalle(compra["id"])
            for detalle in detalles:
                clave = f"{detalle['codigo']} - {detalle['nombre']}"
                if clave not in self.mapa_productos:
                    producto = productos_servicio.obtener(detalle["producto_id"])
                    if producto:
                        self.mapa_productos[clave] = producto
                self.items.append({
                    "producto_id": detalle["producto_id"],
                    "codigo": detalle["codigo"],
                    "nombre": detalle["nombre"],
                    "cantidad": int(detalle["cantidad"]),
                    "costo_unitario": a_decimal(detalle["costo_unitario"]),
                })
        self._seleccionar_producto(self.selector.obtener())
        self._refrescar()

    def _seleccionar_producto(self, valor):
        producto = self.mapa_productos.get(valor)
        if producto:
            self.costo.establecer(producto["precio_compra"])
            self.cantidad.establecer("1")

    def _agregar(self):
        self.error.configure(text="")
        producto = self.mapa_productos.get(self.selector.obtener())
        if not producto:
            self.error.configure(text="Seleccione un producto válido.")
            return
        try:
            cantidad = a_entero(self.cantidad.obtener(), "cantidad", 1)
            costo = a_decimal(self.costo.obtener(), "costo unitario")
            if costo < 0:
                raise ErrorValidacion("El costo no puede ser negativo.")
        except ErrorValidacion as exc:
            self.error.configure(text=str(exc))
            return
        for item in self.items:
            if item["producto_id"] == producto["id"]:
                item["cantidad"] += cantidad
                item["costo_unitario"] = costo
                break
        else:
            self.items.append({
                "producto_id": producto["id"],
                "codigo": producto["codigo"],
                "nombre": producto["nombre"],
                "cantidad": cantidad,
                "costo_unitario": costo,
            })
        self._refrescar()

    def _quitar(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        self.items = [i for i in self.items if i["producto_id"] != fila["producto_id"]]
        self._refrescar()

    def _refrescar(self):
        filas = []
        total = 0
        for item in self.items:
            subtotal = (item["costo_unitario"] * item["cantidad"]).quantize(
                a_decimal("0.01")
            )
            filas.append({**item, "subtotal": subtotal})
            total += subtotal
        self.tabla.cargar(filas)
        self.total.configure(text=f"Total: {dinero(total)}")

    def _guardar(self):
        self.error.configure(text="")
        if not self.items:
            self.error.configure(text="Agregue al menos un producto a la compra.")
            return
        proveedor_id = self.mapa_proveedores.get(self.proveedor.obtener())
        if not proveedor_id:
            self.error.configure(text="Seleccione un proveedor activo.")
            return
        try:
            if self.compra:
                compras_servicio.modificar(
                    self.compra["id"], proveedor_id, self.items,
                    self.observaciones.obtener(), self.sesion.id,
                )
            else:
                compras_servicio.crear(
                    proveedor_id, self.items, self.observaciones.obtener(),
                    self.sesion.id,
                )
            self.guardado = True
            self._cerrar()
        except Exception as exc:
            self.error.configure(text=str(exc))


class GestionProveedores(ModalBase):
    def __init__(self, master, sesion):
        super().__init__(master, "Proveedores", "Catálogo de proveedores de la farmacia.",
                         ancho=780, alto=730)
        self.sesion = sesion
        self.editando_id = None
        self.hubo_cambios = False
        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=18, pady=14)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(0, weight=1)

        self.tabla = TablaDatos(
            contenedor,
            [
                {"titulo": "Proveedor", "clave": "nombre", "peso": 3},
                {"titulo": "Contacto", "clave": "contacto", "peso": 2},
                {"titulo": "Teléfono", "clave": "telefono", "peso": 2},
                {"titulo": "Estado", "clave": "activo", "peso": 1,
                 "formato": lambda v, f: "Activo" if v else "Cancelado"},
            ],
            altura=230,
        )
        self.tabla.grid(row=0, column=0, sticky="nsew")

        formulario = ctk.CTkFrame(contenedor, fg_color=COLORES["panel_alt"],
                                  corner_radius=10)
        formulario.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        formulario.grid_columnconfigure(0, weight=1)
        formulario.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(formulario, text="Datos del proveedor", font=fuente(13, True),
                     text_color=COLORES["texto"], anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 8)
        )
        self.nombre = Campo(formulario, "Nombre o razón social", requerido=True)
        self.nombre.grid(row=1, column=0, sticky="ew", padx=(16, 8), pady=(0, 10))
        self.contacto = Campo(formulario, "Persona de contacto")
        self.contacto.grid(row=1, column=1, sticky="ew", padx=(8, 16), pady=(0, 10))
        self.telefono = Campo(formulario, "Teléfono")
        self.telefono.grid(row=2, column=0, sticky="ew", padx=(16, 8), pady=(0, 10))
        self.email = Campo(formulario, "Correo electrónico")
        self.email.grid(row=2, column=1, sticky="ew", padx=(8, 16), pady=(0, 10))
        self.direccion = Campo(formulario, "Dirección")
        self.direccion.grid(row=3, column=0, columnspan=2, sticky="ew",
                            padx=16, pady=(0, 10))
        self.error = ctk.CTkLabel(formulario, text="", font=fuente(11),
                                  text_color=COLORES["peligro"])
        self.error.grid(row=4, column=0, columnspan=2, sticky="w", padx=16)
        acciones = ctk.CTkFrame(formulario, fg_color="transparent")
        acciones.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=(6, 14))
        boton(acciones, "Limpiar", self._limpiar, tipo="fantasma", ancho=90,
              alto=34).pack(side="left")
        boton(acciones, "Guardar proveedor", self._guardar, tipo="primario",
              ancho=150, alto=34).pack(side="right")

        self.agregar_boton("Cerrar", self._cerrar, tipo="secundario", ancho=110)
        self.agregar_boton("Cancelar / Reactivar", self._cambiar_estado,
                           tipo="peligro", ancho=165)
        self.agregar_boton("Editar seleccionado", self._editar, tipo="secundario",
                           ancho=155)
        self.after(120, self._cargar)

    def _cargar(self):
        try:
            self.tabla.cargar(proveedores_servicio.listar(incluir_inactivos=True))
        except Exception as exc:
            mostrar_error(self, exc)

    def _limpiar(self):
        self.editando_id = None
        for campo in (self.nombre, self.contacto, self.telefono, self.email,
                      self.direccion):
            campo.establecer("")
        self.error.configure(text="")

    def _editar(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        proveedor = proveedores_servicio.obtener(fila["id"])
        if not proveedor:
            mostrar_error(self, "El proveedor ya no existe.")
            return
        self.editando_id = proveedor["id"]
        self.nombre.establecer(proveedor["nombre"])
        self.contacto.establecer(proveedor.get("contacto") or "")
        self.telefono.establecer(proveedor.get("telefono") or "")
        self.email.establecer(proveedor.get("email") or "")
        self.direccion.establecer(proveedor.get("direccion") or "")
        self.error.configure(text="")

    def _guardar(self):
        try:
            if self.editando_id:
                proveedores_servicio.actualizar(
                    self.editando_id, self.nombre.obtener(), self.contacto.obtener(),
                    self.telefono.obtener(), self.email.obtener(),
                    self.direccion.obtener(), ejecutor_id=self.sesion.id,
                )
            else:
                proveedores_servicio.crear(
                    self.nombre.obtener(), self.contacto.obtener(),
                    self.telefono.obtener(), self.email.obtener(),
                    self.direccion.obtener(), ejecutor_id=self.sesion.id,
                )
        except Exception as exc:
            self.error.configure(text=str(exc))
            return
        self._limpiar()
        self.hubo_cambios = True
        self._cargar()

    def _cambiar_estado(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        activo = bool(fila["activo"])
        if not confirmar(self, "Cambiar estado del proveedor",
                         f"¿Desea {'cancelar' if activo else 'reactivar'} a "
                         f"'{fila['nombre']}'?",
                         texto_confirmar="Sí", peligro=activo):
            return
        try:
            proveedores_servicio.cambiar_estado(
                fila["id"], not activo, ejecutor_id=self.sesion.id
            )
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self.hubo_cambios = True
        self._cargar()


class ModuloCompras(ctk.CTkFrame):
    TITULO = "Compras"
    SUBTITULO = "Reabastecimiento de productos y actualización de inventario."

    def __init__(self, master, sesion, **kwargs):
        super().__init__(master, fg_color=COLORES["fondo"], corner_radius=0)
        self.sesion = sesion
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        if not sesion.puede("compras", "buscar"):
            ctk.CTkLabel(self, text="No tiene permisos para acceder a este módulo.",
                         font=fuente(16, True),
                         text_color=COLORES["peligro"]).grid(row=0, column=0, pady=80)
            return

        self._construir_barra()
        self._construir_tabla()
        self.after(100, self.cargar)

    def _construir_barra(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        barra.grid_columnconfigure(1, weight=1)

        self.busqueda = BarraBusqueda(barra, self.cargar,
                                      "Buscar por folio, proveedor o usuario...",
                                      ancho=300)
        self.busqueda.grid(row=0, column=0, sticky="w")

        self.estado = CampoCombo(barra, "Estado",
                                 ["Todas", "Completadas", "Canceladas"], valor="Todas",
                                 ancho=140, comando=lambda _v: self.cargar())
        self.estado.grid(row=0, column=1, padx=14, pady=0, sticky="w")

        acciones = ctk.CTkFrame(barra, fg_color="transparent")
        acciones.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        acciones.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            acciones,
            text="Registre compras a proveedores y consulte su historial.",
            font=fuente(10), text_color=COLORES["texto_suave"], anchor="w",
        ).grid(row=0, column=0, sticky="w")

        botones = ctk.CTkFrame(acciones, fg_color="transparent")
        botones.grid(row=0, column=1, sticky="e")
        boton(botones, "+ Nueva", self._nueva, tipo="primario", ancho=105).pack(
            side="left", padx=(0, 8)
        )
        boton(botones, "Detalle", self._detalle, tipo="secundario", ancho=90).pack(
            side="left", padx=(0, 8)
        )
        boton(botones, "Editar", self._editar, tipo="secundario", ancho=90).pack(
            side="left", padx=(0, 8)
        )
        boton(botones, "Cancelar", self._cancelar, tipo="peligro", ancho=95).pack(
            side="left", padx=(0, 8)
        )
        boton(botones, "Proveedores", self._proveedores, tipo="fantasma",
              ancho=115).pack(side="left")

    def _construir_tabla(self):
        self.tabla = TablaDatos(
            self,
            [
                {"titulo": "Folio", "clave": "folio", "peso": 1},
                {"titulo": "Fecha", "clave": "fecha", "peso": 2,
                 "formato": formato_fecha},
                {"titulo": "Proveedor", "clave": "proveedor", "peso": 3},
                {"titulo": "Registró", "clave": "usuario", "peso": 2},
                {"titulo": "Unidades", "clave": "unidades", "peso": 1,
                 "alineacion": "center"},
                {"titulo": "Total", "clave": "total", "peso": 1,
                 "formato": formato_dinero, "alineacion": "e"},
                {"titulo": "Estado", "clave": "estado", "peso": 1,
                 "formato": texto_estado},
            ],
            on_doble_clic=lambda _fila: self._detalle(),
        )
        self.tabla.grid(row=1, column=0, sticky="nsew")

    def _estado_seleccionado(self):
        return {
            "Todas": "TODAS",
            "Completadas": "COMPLETADA",
            "Canceladas": "CANCELADA",
        }.get(self.estado.obtener(), "TODAS")

    def cargar(self):
        try:
            filas = compras_servicio.listar(self.busqueda.texto(),
                                            self._estado_seleccionado())
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self.tabla.cargar(filas)

    def _nueva(self):
        dialogo = FormularioCompra(self, self.sesion)
        self.wait_window(dialogo)
        if dialogo.guardado:
            self.cargar()
            mostrar_exito(self, "La compra se registró y el inventario se actualizó.")

    def _detalle(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        compra = compras_servicio.obtener(fila["id"])
        if not compra:
            mostrar_error(self, "La compra ya no existe.")
            return
        dialogo = DetalleCompra(self, compra)
        self.wait_window(dialogo)

    def _editar(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        if fila["estado"] == "CANCELADA":
            mostrar_error(self, "No se puede modificar una compra cancelada.")
            return
        compra = compras_servicio.obtener(fila["id"])
        if not compra:
            mostrar_error(self, "La compra ya no existe.")
            return
        dialogo = FormularioCompra(self, self.sesion, compra)
        self.wait_window(dialogo)
        if dialogo.guardado:
            self.cargar()
            mostrar_exito(self, "La compra se modificó y el inventario se ajustó.")

    def _cancelar(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        if fila["estado"] == "CANCELADA":
            mostrar_error(self, "La compra ya está cancelada.")
            return
        motivo = solicitar_motivo(
            self, "Cancelar compra",
            f"Se revertirá el inventario ingresado por la compra {fila['folio']}. "
            "Escriba el motivo de la cancelación.",
            texto_confirmar="Cancelar compra",
        )
        if not motivo:
            return
        try:
            compras_servicio.cancelar(fila["id"], motivo, self.sesion.id)
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self.cargar()
        mostrar_exito(self, f"La compra {fila['folio']} fue cancelada.")

    def _proveedores(self):
        dialogo = GestionProveedores(self, self.sesion)
        self.wait_window(dialogo)
        if dialogo.hubo_cambios:
            self.cargar()
