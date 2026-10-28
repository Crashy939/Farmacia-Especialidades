"""Módulo de almacén: productos, existencias y categorías."""

import customtkinter as ctk

from configuracion import COLORES
from servicios.productos import productos_servicio
from servicios.proveedores import proveedores_servicio
from ui.componentes import (BarraBusqueda, Campo, CampoCombo, CampoTexto, ModalBase,
                            TablaDatos, boton, confirmar, formato_dinero, fuente,
                            mostrar_error, mostrar_exito, texto_activo)
from utilidades import ErrorValidacion


def _formato_stock(valor, fila=None):
    try:
        cantidad = int(valor or 0)
        minimo = int((fila or {}).get("stock_minimo") or 0)
    except Exception:
        return str(valor)
    if cantidad == 0:
        return "⚠ Agotado"
    if cantidad <= minimo:
        return f"⚠ {cantidad}"
    return str(cantidad)


class FormularioProducto(ModalBase):
    def __init__(self, master, sesion, producto=None):
        self.producto = producto
        titulo = "Editar producto" if producto else "Nuevo producto"
        super().__init__(master, titulo,
                         "Datos del medicamento o artículo de la farmacia.",
                         ancho=680, alto=680)
        self.sesion = sesion
        self.guardado = False
        categorias = productos_servicio.listar_categorias()
        proveedores = proveedores_servicio.listar()
        self.mapa_categorias = {"Sin categoría": None}
        self.mapa_categorias.update({c["nombre"]: c["id"] for c in categorias})
        self.mapa_proveedores = {"Sin proveedor": None}
        self.mapa_proveedores.update({p["nombre"]: p["id"] for p in proveedores})

        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=24, pady=18)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_columnconfigure(1, weight=1)

        self.codigo = Campo(contenedor, "Código", requerido=True,
                            placeholder="Ej. MED-011")
        self.codigo.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 10))
        self.nombre = Campo(contenedor, "Nombre del producto", requerido=True,
                            placeholder="Ej. Acetaminofén 500 mg")
        self.nombre.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 10))

        self.descripcion = CampoTexto(contenedor, "Descripción", alto=64)
        self.descripcion.grid(row=1, column=0, columnspan=2, sticky="ew",
                              pady=(0, 10))

        self.categoria = CampoCombo(contenedor, "Categoría",
                                    list(self.mapa_categorias.keys()))
        self.categoria.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(0, 10))
        self.proveedor = CampoCombo(contenedor, "Proveedor",
                                    list(self.mapa_proveedores.keys()))
        self.proveedor.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 10))

        self.precio_compra = Campo(contenedor, "Precio de compra", requerido=True,
                                   placeholder="0.00")
        self.precio_compra.grid(row=3, column=0, sticky="ew", padx=(0, 8),
                                pady=(0, 10))
        self.precio_venta = Campo(contenedor, "Precio de venta", requerido=True,
                                  placeholder="0.00")
        self.precio_venta.grid(row=3, column=1, sticky="ew", padx=(8, 0),
                               pady=(0, 10))

        self.existencia = Campo(contenedor, "Existencia actual", requerido=True,
                                placeholder="0")
        self.existencia.grid(row=4, column=0, sticky="ew", padx=(0, 8),
                             pady=(0, 10))
        self.stock_minimo = Campo(contenedor, "Stock mínimo", requerido=True,
                                  placeholder="5")
        self.stock_minimo.grid(row=4, column=1, sticky="ew", padx=(8, 0),
                               pady=(0, 10))

        self.activo = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            contenedor, text="Producto activo para venta", variable=self.activo,
            font=fuente(12, True), text_color=COLORES["texto"],
            progress_color=COLORES["primario"], fg_color=COLORES["borde"],
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self.error = ctk.CTkLabel(contenedor, text="", font=fuente(11),
                                  text_color=COLORES["peligro"], anchor="w",
                                  justify="left", wraplength=580)
        self.error.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.agregar_boton("Cancelar", self._cancelar, tipo="secundario", ancho=110)
        self.agregar_boton("Guardar producto", self._guardar, tipo="primario",
                           ancho=150)

        if producto:
            self.codigo.establecer(producto["codigo"])
            self.nombre.establecer(producto["nombre"])
            self.descripcion.establecer(producto.get("descripcion") or "")
            self.categoria.establecer(producto.get("categoria") or "Sin categoría")
            self.proveedor.establecer(producto.get("proveedor") or "Sin proveedor")
            self.precio_compra.establecer(producto["precio_compra"])
            self.precio_venta.establecer(producto["precio_venta"])
            self.existencia.establecer(producto["existencia"])
            self.stock_minimo.establecer(producto["stock_minimo"])
            self.activo.set(bool(producto["activo"]))
        else:
            self.codigo.establecer(productos_servicio.sugerir_codigo())
            self.stock_minimo.establecer("10")
            self.existencia.establecer("0")
            self.precio_compra.establecer("0.00")
            self.precio_venta.establecer("0.00")
        self.after(120, self.nombre.enfocar)

    def _guardar(self):
        try:
            categoria_id = self.mapa_categorias.get(self.categoria.obtener())
            proveedor_id = self.mapa_proveedores.get(self.proveedor.obtener())
            if self.producto:
                productos_servicio.actualizar(
                    self.producto["id"], self.codigo.obtener(), self.nombre.obtener(),
                    self.descripcion.obtener(), categoria_id, proveedor_id,
                    self.precio_compra.obtener(), self.precio_venta.obtener(),
                    self.existencia.obtener(), self.stock_minimo.obtener(),
                    self.activo.get(), ejecutor_id=self.sesion.id,
                )
            else:
                productos_servicio.crear(
                    self.codigo.obtener(), self.nombre.obtener(),
                    self.descripcion.obtener(), categoria_id, proveedor_id,
                    self.precio_compra.obtener(), self.precio_venta.obtener(),
                    self.existencia.obtener(), self.stock_minimo.obtener(),
                    ejecutor_id=self.sesion.id,
                )
            self.guardado = True
            self._cerrar()
        except ErrorValidacion as exc:
            self.error.configure(text=str(exc))
        except Exception as exc:
            self.error.configure(text=str(exc))


class GestionCategorias(ModalBase):
    def __init__(self, master, sesion):
        super().__init__(master, "Categorías", "Organice los productos del almacén.",
                         ancho=640, alto=650)
        self.sesion = sesion
        self.hubo_cambios = False
        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=20, pady=16)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(0, weight=1)

        self.tabla = TablaDatos(
            contenedor,
            [
                {"titulo": "Categoría", "clave": "nombre", "peso": 2},
                {"titulo": "Descripción", "clave": "descripcion", "peso": 2},
                {"titulo": "Estado", "clave": "activo", "peso": 1,
                 "formato": texto_activo},
            ],
            altura=220,
        )
        self.tabla.grid(row=0, column=0, sticky="nsew")

        formulario = ctk.CTkFrame(contenedor, fg_color=COLORES["panel_alt"],
                                  corner_radius=10)
        formulario.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        formulario.grid_columnconfigure(0, weight=1)
        formulario.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(formulario, text="Nueva categoría", font=fuente(13, True),
                     text_color=COLORES["texto"], anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 8)
        )
        self.nombre = Campo(formulario, "Nombre", requerido=True,
                            placeholder="Ej. Material de curación")
        self.nombre.grid(row=1, column=0, sticky="ew", padx=(16, 8), pady=(0, 10))
        self.descripcion = Campo(formulario, "Descripción", placeholder="Opcional")
        self.descripcion.grid(row=1, column=1, sticky="ew", padx=(8, 16), pady=(0, 10))
        self.error = ctk.CTkLabel(formulario, text="", font=fuente(11),
                                  text_color=COLORES["peligro"])
        self.error.grid(row=2, column=0, columnspan=2, sticky="w", padx=16)
        boton(formulario, "+ Agregar categoría", self._crear, tipo="primario",
              ancho=170).grid(row=3, column=0, sticky="w", padx=16, pady=(6, 14))

        self.agregar_boton("Cerrar", self._cerrar, tipo="secundario", ancho=110)
        self.agregar_boton("Cancelar / Reactivar", self._cambiar_estado,
                           tipo="peligro", ancho=165)
        self.after(120, self._cargar)

    def _cargar(self):
        try:
            self.tabla.cargar(productos_servicio.listar_categorias(True))
        except Exception as exc:
            mostrar_error(self, exc)

    def _crear(self):
        try:
            productos_servicio.crear_categoria(
                self.nombre.obtener(), self.descripcion.obtener(),
                ejecutor_id=self.sesion.id,
            )
        except Exception as exc:
            self.error.configure(text=str(exc))
            return
        self.error.configure(text="")
        self.nombre.establecer("")
        self.descripcion.establecer("")
        self.hubo_cambios = True
        self._cargar()

    def _cambiar_estado(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        activo = bool(fila["activo"])
        if not confirmar(self, "Cambiar estado de categoría",
                         f"¿Desea {'cancelar' if activo else 'reactivar'} "
                         f"la categoría '{fila['nombre']}'?",
                         texto_confirmar="Sí", peligro=activo):
            return
        try:
            productos_servicio.cambiar_estado_categoria(
                fila["id"], not activo, ejecutor_id=self.sesion.id
            )
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self.hubo_cambios = True
        self._cargar()


class ModuloAlmacen(ctk.CTkFrame):
    TITULO = "Almacén"
    SUBTITULO = "Productos, precios, existencias y alertas de inventario."

    def __init__(self, master, sesion, **kwargs):
        super().__init__(master, fg_color=COLORES["fondo"], corner_radius=0)
        self.sesion = sesion
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        if not sesion.puede("almacen", "buscar"):
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
        barra.grid_columnconfigure(2, weight=1)

        self.busqueda = BarraBusqueda(barra, self.cargar,
                                      "Buscar por código, nombre o descripción...",
                                      ancho=300)
        self.busqueda.grid(row=0, column=0, sticky="w")

        filtros = ctk.CTkFrame(barra, fg_color="transparent")
        filtros.grid(row=0, column=1, padx=14, sticky="w")
        self.incluir = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            filtros, text="Incluir cancelados", variable=self.incluir,
            command=self.cargar, font=fuente(11), text_color=COLORES["texto_suave"],
            progress_color=COLORES["primario"], fg_color=COLORES["borde"],
        ).pack(side="left", padx=(0, 12))
        self.bajo = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            filtros, text="Solo stock bajo", variable=self.bajo,
            command=self.cargar, font=fuente(11),
            text_color=COLORES["advertencia"], progress_color=COLORES["advertencia"],
            fg_color=COLORES["borde"],
        ).pack(side="left")

        acciones = ctk.CTkFrame(barra, fg_color="transparent")
        acciones.grid(row=0, column=2, sticky="e")
        boton(acciones, "+ Nuevo", self._nuevo, tipo="primario", ancho=105).pack(
            side="left", padx=(0, 8)
        )
        boton(acciones, "Editar", self._editar, tipo="secundario", ancho=90).pack(
            side="left", padx=(0, 8)
        )
        boton(acciones, "Cancelar / Reactivar", self._cambiar_estado,
              tipo="peligro", ancho=155).pack(side="left", padx=(0, 8))
        boton(acciones, "Categorías", self._categorias, tipo="fantasma",
              ancho=105).pack(side="left")

    def _construir_tabla(self):
        self.tabla = TablaDatos(
            self,
            [
                {"titulo": "Código", "clave": "codigo", "peso": 1},
                {"titulo": "Producto", "clave": "nombre", "peso": 3},
                {"titulo": "Categoría", "clave": "categoria", "peso": 2},
                {"titulo": "P. compra", "clave": "precio_compra", "peso": 1,
                 "formato": formato_dinero, "alineacion": "e"},
                {"titulo": "P. venta", "clave": "precio_venta", "peso": 1,
                 "formato": formato_dinero, "alineacion": "e"},
                {"titulo": "Existencia", "clave": "existencia", "peso": 1,
                 "formato": _formato_stock, "alineacion": "center"},
                {"titulo": "Estado", "clave": "activo", "peso": 1,
                 "formato": texto_activo},
            ],
            on_doble_clic=lambda _fila: self._editar(),
        )
        self.tabla.grid(row=1, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    def cargar(self):
        try:
            filas = productos_servicio.listar(
                self.busqueda.texto(), self.incluir.get(), self.bajo.get()
            )
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self.tabla.cargar(filas)

    def _nuevo(self):
        dialogo = FormularioProducto(self, self.sesion)
        self.wait_window(dialogo)
        if dialogo.guardado:
            self.cargar()
            mostrar_exito(self, "El producto se registró en el almacén.")

    def _editar(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        producto = productos_servicio.obtener(fila["id"])
        if not producto:
            mostrar_error(self, "El producto ya no existe.")
            self.cargar()
            return
        dialogo = FormularioProducto(self, self.sesion, producto)
        self.wait_window(dialogo)
        if dialogo.guardado:
            self.cargar()
            mostrar_exito(self, "El producto se actualizó correctamente.")

    def _cambiar_estado(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        activo = bool(fila["activo"])
        accion = "cancelar" if activo else "reactivar"
        if not confirmar(
            self, f"{accion.capitalize()} producto",
            f"¿Desea {accion} '{fila['codigo']} - {fila['nombre']}'? "
            + ("El producto dejará de estar disponible para venta." if activo else ""),
            texto_confirmar=accion.capitalize(), peligro=activo,
        ):
            return
        try:
            productos_servicio.cambiar_estado(fila["id"], not activo,
                                              ejecutor_id=self.sesion.id)
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self.cargar()
        mostrar_exito(self, f"El producto fue {accion}do correctamente.")

    def _categorias(self):
        dialogo = GestionCategorias(self, self.sesion)
        self.wait_window(dialogo)
        if dialogo.hubo_cambios:
            self.cargar()
