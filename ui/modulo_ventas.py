"""Punto de venta y administración de ventas."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import customtkinter as ctk

from configuracion import (COLORES, PESOS_POR_PUNTO, PORCENTAJE_DESCUENTO_PUNTOS,
                           PORCENTAJE_DESCUENTO_VOLUMEN, PUNTOS_PARA_CANJE,
                           UMBRAL_DESCUENTO_VOLUMEN)
from servicios.clientes import clientes_servicio
from servicios.productos import productos_servicio
from servicios.ventas import ventas_servicio
from ui.componentes import (BarraBusqueda, Campo, CampoCombo, ModalBase, TablaDatos,
                            boton, confirmar, formato_dinero, formato_fecha, fuente,
                            mostrar_error, mostrar_exito, solicitar_autorizacion,
                            solicitar_motivo, texto_estado)
from ui.modulo_clientes import FormularioCliente
from utilidades import ErrorValidacion, a_decimal, dinero

CENTAVOS = Decimal("0.01")
METODOS = {
    "Efectivo": "EFECTIVO",
    "Tarjeta": "TARJETA",
    "Transferencia": "TRANSFERENCIA",
}
METODOS_INVERSO = {valor: clave for clave, valor in METODOS.items()}


def _redondear(valor):
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _formato_metodo(valor, fila=None):
    return METODOS_INVERSO.get(str(valor or "").upper(), str(valor or "—"))


class DetalleVenta(ModalBase):
    def __init__(self, master, venta):
        super().__init__(master, f"Venta {venta['folio']}",
                         f"{venta['cliente']} · {formato_fecha(venta['fecha'])}",
                         ancho=790, alto=700)
        self.venta = venta
        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=20, pady=16)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(2, weight=1)

        datos = ctk.CTkFrame(contenedor, fg_color=COLORES["panel_alt"],
                             corner_radius=9)
        datos.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        datos.grid_columnconfigure(1, weight=1)
        datos.grid_columnconfigure(3, weight=1)
        self._dato(datos, 0, 0, "Cliente", f"{venta['codigo']} · {venta['cliente']}")
        self._dato(datos, 0, 2, "Atendió", venta["usuario"])
        self._dato(datos, 1, 0, "Método de pago",
                   _formato_metodo(venta["metodo_pago"]))
        self._dato(datos, 1, 2, "Estado", texto_estado(venta["estado"]))
        self._dato(datos, 2, 0, "Subtotal", dinero(venta["subtotal"]))
        self._dato(datos, 2, 2, "Descuento 10%", dinero(venta["descuento_volumen"]))
        self._dato(datos, 3, 0, "Descuento 50%", dinero(venta["descuento_puntos"]))
        self._dato(datos, 3, 2, "Total pagado", dinero(venta["total"]))
        self._dato(datos, 4, 0, "Monto recibido", dinero(venta["monto_recibido"]))
        self._dato(datos, 4, 2, "Cambio", dinero(venta["cambio"]))
        self._dato(datos, 5, 0, "Puntos ganados", f"+{venta['puntos_ganados']}")
        self._dato(datos, 5, 2, "Puntos canjeados", f"-{venta['puntos_canjeados']}")

        if venta.get("estado") == "CANCELADA":
            cancelacion = (
                f"Cancelada el {formato_fecha(venta.get('cancelada_en'))} por "
                f"{venta.get('cancelada_por_nombre') or 'usuario'}. "
                f"Motivo: {venta.get('motivo_cancelacion') or '—'}."
            )
            ctk.CTkLabel(contenedor, text=cancelacion, font=fuente(11),
                         text_color=COLORES["peligro"], anchor="w",
                         justify="left", wraplength=700).grid(
                row=1, column=0, sticky="w", pady=(0, 8)
            )
        else:
            ctk.CTkLabel(contenedor, text="Productos vendidos", font=fuente(13, True),
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
                {"titulo": "Precio", "clave": "precio_unitario", "peso": 1,
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
    def _dato(master, fila, columna, etiqueta, valor):
        ctk.CTkLabel(master, text=etiqueta, font=fuente(10, True),
                     text_color=COLORES["texto_suave"], anchor="w").grid(
            row=fila, column=columna, sticky="w", padx=(14, 8),
            pady=(9 if fila == 0 else 3, 0),
        )
        ctk.CTkLabel(master, text=str(valor if valor is not None else "—"),
                     font=fuente(12, True), text_color=COLORES["texto"],
                     anchor="w").grid(
            row=fila, column=columna + 1, sticky="w", padx=(0, 14),
            pady=(9 if fila == 0 else 3, 0),
        )

    def _cargar(self):
        try:
            self.tabla.cargar(ventas_servicio.detalle(self.venta["id"]))
        except Exception as exc:
            mostrar_error(self, exc)


class FormularioVenta(ModalBase):
    def __init__(self, master, sesion, venta=None, autorizado_por_id=None):
        self.venta = venta
        self.sesion = sesion
        self.autorizado_por_id = autorizado_por_id
        self.guardado = False
        self.resultado_venta = None
        self.cliente = None
        self.items = []
        self._puntos_disponibles = 0
        self._monto_auto = True
        self._stock_extra = {}
        self._totales = {}

        titulo = f"Modificar venta {venta['folio']}" if venta else "Punto de venta"
        subtitulo = ("Ajuste los productos y guarde los cambios." if venta
                     else "Busque al cliente, agregue productos y registre el cobro.")
        super().__init__(master, titulo, subtitulo, ancho=1180, alto=770)
        self._construir_interfaz()
        if venta:
            self._cargar_venta()
        else:
            self._buscar_productos()
        self.after(160, self.busqueda_cliente.focus_set)

    # ------------------------------------------------------------------
    def _construir_interfaz(self):
        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=16, pady=12)
        contenedor.grid_columnconfigure(0, weight=7)
        contenedor.grid_columnconfigure(1, weight=4)
        contenedor.grid_rowconfigure(1, weight=1)

        # Barra de cliente
        clientes_barra = ctk.CTkFrame(contenedor, fg_color=COLORES["panel_alt"],
                                      corner_radius=10)
        clientes_barra.grid(row=0, column=0, columnspan=2, sticky="ew",
                            pady=(0, 10))
        clientes_barra.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(clientes_barra, text="Cliente", font=fuente(11, True),
                     text_color=COLORES["texto_suave"]).grid(
            row=0, column=0, padx=(14, 8), pady=10
        )
        self.busqueda_cliente = ctk.CTkEntry(
            clientes_barra, placeholder_text="Código, nombre o teléfono...",
            width=235, height=34, corner_radius=8,
            fg_color=COLORES["panel"], border_color=COLORES["borde"],
            text_color=COLORES["texto"], font=fuente(12),
        )
        self.busqueda_cliente.grid(row=0, column=1, sticky="w")
        self.busqueda_cliente.bind("<Return>", lambda _e: self._buscar_clientes())
        boton(clientes_barra, "Buscar", self._buscar_clientes, tipo="secundario",
              ancho=80, alto=34).grid(row=0, column=2, padx=6)
        if self.sesion.puede("clientes", "crear"):
            boton(clientes_barra, "+ Registrar", self._registrar_cliente,
                  tipo="primario", ancho=105, alto=34).grid(row=0, column=3, padx=(0, 8))

        self.info_cliente = ctk.CTkLabel(
            clientes_barra, text="Ningún cliente seleccionado",
            font=fuente(12, True), text_color=COLORES["texto_suave"], anchor="w",
        )
        self.info_cliente.grid(row=0, column=5, sticky="w", padx=10)

        self.resultados_clientes = ctk.CTkFrame(clientes_barra, fg_color=COLORES["panel"],
                                                corner_radius=8)
        self.resultados_clientes.grid(row=1, column=0, columnspan=6, sticky="ew",
                                      padx=14, pady=(0, 10))
        self.resultados_clientes.grid_columnconfigure(0, weight=1)
        self.resultados_clientes.grid_remove()

        # Zona izquierda: productos y carrito
        izquierda = ctk.CTkFrame(contenedor, fg_color=COLORES["panel"],
                                 corner_radius=12, border_width=1,
                                 border_color=COLORES["borde"])
        izquierda.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        izquierda.grid_columnconfigure(0, weight=1)
        izquierda.grid_rowconfigure(2, weight=0)
        izquierda.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(izquierda, text="1. Buscar producto", font=fuente(13, True),
                     text_color=COLORES["primario"], anchor="w").grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 6)
        )
        busqueda = ctk.CTkFrame(izquierda, fg_color="transparent")
        busqueda.grid(row=1, column=0, sticky="ew", padx=16)
        busqueda.grid_columnconfigure(0, weight=1)
        self.busqueda_producto = ctk.CTkEntry(
            busqueda, placeholder_text="Código, nombre o descripción del producto...",
            height=36, corner_radius=8, fg_color=COLORES["panel_alt"],
            border_color=COLORES["borde"], text_color=COLORES["texto"],
            font=fuente(12),
        )
        self.busqueda_producto.grid(row=0, column=0, sticky="ew")
        self.busqueda_producto.bind("<Return>", lambda _e: self._buscar_productos())
        boton(busqueda, "Buscar", self._buscar_productos, tipo="secundario",
              ancho=85, alto=36).grid(row=0, column=1, padx=(8, 0))

        self.resultados_productos = ctk.CTkScrollableFrame(
            izquierda, fg_color=COLORES["panel_alt"], corner_radius=8, height=130,
            scrollbar_button_color=COLORES["borde"],
            scrollbar_button_hover_color=COLORES["primario"],
        )
        self.resultados_productos.grid(row=2, column=0, sticky="ew", padx=16,
                                       pady=(8, 0))
        self.resultados_productos.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(izquierda, text="2. Productos en la venta", font=fuente(13, True),
                     text_color=COLORES["primario"], anchor="w").grid(
            row=3, column=0, sticky="w", padx=16, pady=(10, 4)
        )
        self.tabla = TablaDatos(
            izquierda,
            [
                {"titulo": "Código", "clave": "codigo", "peso": 1},
                {"titulo": "Producto", "clave": "nombre", "peso": 3},
                {"titulo": "Cant.", "clave": "cantidad", "peso": 1,
                 "alineacion": "center"},
                {"titulo": "Precio", "clave": "precio_venta", "peso": 1,
                 "formato": formato_dinero, "alineacion": "e"},
                {"titulo": "Subtotal", "clave": "subtotal", "peso": 1,
                 "formato": formato_dinero, "alineacion": "e"},
            ],
            altura=190,
            on_seleccion=self._al_seleccionar_carrito,
        )
        self.tabla.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 4))

        acciones = ctk.CTkFrame(izquierda, fg_color="transparent")
        acciones.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 6))
        boton(acciones, "−  Quitar 1", lambda: self._cambiar_cantidad(-1),
              tipo="secundario", ancho=100, alto=32).pack(side="left", padx=(0, 6))
        boton(acciones, "+  Agregar 1", lambda: self._cambiar_cantidad(1),
              tipo="secundario", ancho=110, alto=32).pack(side="left", padx=(0, 6))
        boton(acciones, "Quitar producto", self._quitar_producto, tipo="peligro",
              ancho=120, alto=32).pack(side="right")

        self.error_pos = ctk.CTkLabel(
            izquierda, text="", font=fuente(11), text_color=COLORES["peligro"],
            anchor="w", justify="left", wraplength=620,
        )
        self.error_pos.grid(row=6, column=0, sticky="w", padx=16, pady=(0, 10))

        # Zona derecha: totales y cobro
        derecha = ctk.CTkFrame(contenedor, fg_color=COLORES["panel"],
                               corner_radius=12, border_width=1,
                               border_color=COLORES["borde"])
        derecha.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        derecha.grid_columnconfigure(1, weight=1)

        fila = 0
        ctk.CTkLabel(derecha, text="Resumen de la venta", font=fuente(14, True),
                     text_color=COLORES["texto"], anchor="w").grid(
            row=fila, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 2)
        )
        fila += 1
        self.lbl_disponibles = ctk.CTkLabel(
            derecha, text="Seleccione un cliente para ver sus puntos.",
            font=fuente(10), text_color=COLORES["texto_suave"], anchor="w",
        )
        self.lbl_disponibles.grid(row=fila, column=0, columnspan=2, sticky="w",
                                  padx=16, pady=(0, 8))
        fila += 1

        def fila_total(etiqueta, tamano=12, color=COLORES["texto_suave"]):
            nonlocal fila
            ctk.CTkLabel(derecha, text=etiqueta, font=fuente(tamano),
                         text_color=color, anchor="w").grid(
                row=fila, column=0, sticky="w", padx=16, pady=1
            )
            valor = ctk.CTkLabel(derecha, text="$0.00", font=fuente(tamano, True),
                                 text_color=COLORES["texto"], anchor="e")
            valor.grid(row=fila, column=1, sticky="e", padx=16, pady=1)
            fila += 1
            return valor

        self.lbl_subtotal = fila_total("Subtotal")
        self.lbl_volumen = fila_total("Descuento 10% (compra > $500)")
        self.lbl_puntos_desc = fila_total("Descuento 50% (50 puntos)")

        ctk.CTkFrame(derecha, height=1, fg_color=COLORES["borde"]).grid(
            row=fila, column=0, columnspan=2, sticky="ew", padx=16, pady=(6, 2)
        )
        fila += 1
        ctk.CTkLabel(derecha, text="TOTAL A PAGAR", font=fuente(12, True),
                     text_color=COLORES["texto"], anchor="w").grid(
            row=fila, column=0, sticky="w", padx=16, pady=(2, 0)
        )
        self.lbl_total = ctk.CTkLabel(derecha, text="$0.00", font=fuente(27, True),
                                      text_color=COLORES["primario"], anchor="e")
        self.lbl_total.grid(row=fila, column=1, sticky="e", padx=16, pady=(0, 2))
        fila += 1

        self.lbl_ganados = ctk.CTkLabel(
            derecha, text="Puntos a ganar: 0", font=fuente(10),
            text_color=COLORES["exito"], anchor="w",
        )
        self.lbl_ganados.grid(row=fila, column=0, columnspan=2, sticky="w",
                               padx=16, pady=(0, 6))
        fila += 1

        self.canjear = ctk.BooleanVar(value=False)
        self.switch_puntos = ctk.CTkSwitch(
            derecha, text=f"Canjear {PUNTOS_PARA_CANJE} puntos (50% desc.)",
            variable=self.canjear, command=self._recalcular,
            font=fuente(11, True), text_color=COLORES["texto_suave"],
            progress_color=COLORES["primario"], fg_color=COLORES["borde"],
            state="disabled",
        )
        self.switch_puntos.grid(row=fila, column=0, columnspan=2, sticky="w",
                                padx=16, pady=(0, 2))
        fila += 1
        ctk.CTkLabel(
            derecha,
            text=f"Se requieren {PUNTOS_PARA_CANJE} puntos. Se descuenta el 50% "
                 "del subtotal con descuento.",
            font=fuente(9), text_color=COLORES["texto_suave"], anchor="w",
            justify="left", wraplength=320,
        ).grid(row=fila, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 6))
        fila += 1

        ctk.CTkFrame(derecha, height=1, fg_color=COLORES["borde"]).grid(
            row=fila, column=0, columnspan=2, sticky="ew", padx=16, pady=(2, 4)
        )
        fila += 1

        ctk.CTkLabel(derecha, text="Método de pago", font=fuente(10, True),
                     text_color=COLORES["texto_suave"], anchor="w").grid(
            row=fila, column=0, columnspan=2, sticky="w", padx=16
        )
        fila += 1
        self.metodo_var = ctk.StringVar(value="Efectivo")
        self.metodo = ctk.CTkOptionMenu(
            derecha, values=list(METODOS.keys()), variable=self.metodo_var,
            height=32, corner_radius=8, fg_color=COLORES["panel_alt"],
            button_color=COLORES["primario_oscuro"],
            button_hover_color=COLORES["primario"],
            dropdown_fg_color=COLORES["panel_alt"],
            dropdown_hover_color=COLORES["primario_oscuro"],
            text_color=COLORES["texto"], font=fuente(11),
            command=lambda _v: self._cambio_metodo(),
        )
        self.metodo.grid(row=fila, column=0, columnspan=2, sticky="ew", padx=16,
                         pady=(2, 4))
        fila += 1

        ctk.CTkLabel(derecha, text="Monto recibido", font=fuente(10, True),
                     text_color=COLORES["texto_suave"], anchor="w").grid(
            row=fila, column=0, columnspan=2, sticky="w", padx=16
        )
        fila += 1
        self.monto_var = ctk.StringVar(value="0.00")
        self.monto = ctk.CTkEntry(
            derecha, textvariable=self.monto_var, height=32, corner_radius=8,
            fg_color=COLORES["panel_alt"], border_color=COLORES["borde"],
            text_color=COLORES["texto"], font=fuente(12),
        )
        self.monto.grid(row=fila, column=0, columnspan=2, sticky="ew", padx=16,
                        pady=(2, 2))
        self.monto.bind("<KeyRelease>", lambda _e: setattr(self, "_monto_auto", False))
        fila += 1

        self.lbl_cambio = ctk.CTkLabel(derecha, text="Cambio: $0.00",
                                       font=fuente(11, True),
                                       text_color=COLORES["texto_suave"], anchor="w")
        self.lbl_cambio.grid(row=fila, column=0, columnspan=2, sticky="w",
                             padx=16, pady=(0, 4))
        fila += 1

        if self.venta:
            ctk.CTkLabel(derecha, text="Motivo de la modificación *",
                         font=fuente(10, True), text_color=COLORES["advertencia"],
                         anchor="w").grid(row=fila, column=0, columnspan=2,
                                          sticky="w", padx=16)
            fila += 1
            self.motivo = ctk.CTkTextbox(
                derecha, height=48, corner_radius=8, fg_color=COLORES["panel_alt"],
                border_width=1, border_color=COLORES["borde"],
                text_color=COLORES["texto"], font=fuente(11),
            )
            self.motivo.grid(row=fila, column=0, columnspan=2, sticky="ew",
                             padx=16, pady=(2, 4))
            fila += 1
            if self.autorizado_por_id:
                ctk.CTkLabel(derecha, text="Operación autorizada por gerencia.",
                             font=fuente(9, True), text_color=COLORES["exito"],
                             anchor="w").grid(row=fila, column=0, columnspan=2,
                                              sticky="w", padx=16)
                fila += 1

        self.error = ctk.CTkLabel(
            derecha, text="", font=fuente(10), text_color=COLORES["peligro"],
            anchor="w", justify="left", wraplength=340,
        )
        self.error.grid(row=fila, column=0, columnspan=2, sticky="w",
                        padx=16, pady=(4, 12))

        texto_accion = "Guardar cambios" if self.venta else "Cobrar venta"
        self.agregar_boton("Cerrar", self._cancelar, tipo="secundario", ancho=100)
        self.agregar_boton(texto_accion, self._guardar, tipo="primario", ancho=165)

    # ------------------------------------------------------------------
    def _restaurar_grab(self):
        try:
            self.grab_set()
            self.lift()
        except Exception:
            pass

    def _buscar_clientes(self):
        texto = self.busqueda_cliente.get().strip()
        try:
            resultados = clientes_servicio.buscar_activos(texto, limite=6)
        except Exception as exc:
            self.error.configure(text=str(exc))
            return
        for widget in self.resultados_clientes.winfo_children():
            widget.destroy()
        self.resultados_clientes.grid()
        if not resultados:
            ctk.CTkLabel(
                self.resultados_clientes,
                text="No se encontraron clientes. Use '+ Registrar' para crear uno nuevo.",
                font=fuente(11), text_color=COLORES["texto_suave"], anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=10, pady=8)
            return
        for indice, cliente in enumerate(resultados):
            texto_boton = (f"{cliente['codigo']}  ·  {cliente['nombre']} "
                           f"{cliente['apellido']}  ·  {cliente['puntos']} puntos")
            ctk.CTkButton(
                self.resultados_clientes, text=texto_boton, anchor="w", height=28,
                corner_radius=6, fg_color="transparent",
                hover_color=COLORES["panel_hover"], text_color=COLORES["texto"],
                font=fuente(11),
                command=lambda c=cliente: self._elegir_cliente(c),
            ).grid(row=indice, column=0, sticky="ew", padx=4, pady=1)

    def _elegir_cliente(self, cliente):
        completo = clientes_servicio.obtener(cliente["id"])
        if not completo:
            self.error.configure(text="El cliente ya no existe.")
            return
        self._seleccionar_cliente(completo)
        self.resultados_clientes.grid_remove()

    def _seleccionar_cliente(self, cliente):
        self.cliente = cliente
        self._puntos_disponibles = self._calcular_disponibles(cliente)
        self.info_cliente.configure(
            text=f"{cliente['codigo']}  ·  {cliente['nombre']} {cliente['apellido']}  ·  "
                 f"{self._puntos_disponibles} pts",
            text_color=COLORES["texto"],
        )
        self.lbl_disponibles.configure(
            text=f"Puntos disponibles: {self._puntos_disponibles}. "
                 f"Puede canjear con {PUNTOS_PARA_CANJE} o más."
        )
        self.canjear.set(False)
        self._actualizar_switch()
        self._recalcular()

    def _calcular_disponibles(self, cliente):
        if self.venta and int(cliente["id"]) == int(self.venta["cliente_id"]):
            return int(ventas_servicio.puntos_disponibles_edicion(self.venta["id"]))
        return int(cliente["puntos"] or 0)

    def _registrar_cliente(self):
        dialogo = FormularioCliente(self, self.sesion, rapido=True)
        self.wait_window(dialogo)
        self._restaurar_grab()
        if not dialogo.guardado or not dialogo.cliente_id:
            return
        cliente = clientes_servicio.obtener(dialogo.cliente_id)
        if cliente:
            self._seleccionar_cliente(cliente)
            self.busqueda_cliente.delete(0, "end")
            self.busqueda_cliente.insert(0, cliente["codigo"])

    def _buscar_productos(self):
        texto = self.busqueda_producto.get().strip()
        try:
            productos = productos_servicio.buscar_para_venta(texto, limite=10)
        except Exception as exc:
            self.error_pos.configure(text=str(exc))
            return
        for widget in self.resultados_productos.winfo_children():
            widget.destroy()
        if not productos:
            ctk.CTkLabel(
                self.resultados_productos,
                text="No se encontraron productos con ese criterio.",
                font=fuente(11), text_color=COLORES["texto_suave"],
            ).grid(row=0, column=0, sticky="w", padx=8, pady=12)
            return
        for indice, producto in enumerate(productos):
            disponible = self._disponible(producto)
            fila = ctk.CTkFrame(self.resultados_productos, fg_color="transparent")
            fila.grid(row=indice, column=0, sticky="ew", pady=1)
            fila.grid_columnconfigure(0, weight=3)
            fila.grid_columnconfigure(1, weight=1)
            fila.grid_columnconfigure(2, weight=1)
            ctk.CTkLabel(
                fila, text=f"{producto['codigo']}  {producto['nombre']}",
                font=fuente(10, True), text_color=COLORES["texto"], anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=6)
            ctk.CTkLabel(fila, text=dinero(producto["precio_venta"]),
                         font=fuente(10), text_color=COLORES["primario"],
                         anchor="e").grid(row=0, column=1, sticky="e", padx=6)
            ctk.CTkLabel(
                fila, text=f"Stock: {disponible}", font=fuente(9),
                text_color=(COLORES["peligro"] if disponible <= 0
                            else COLORES["texto_suave"]),
                anchor="e",
            ).grid(row=0, column=2, sticky="e", padx=6)
            agregar = ctk.CTkButton(
                fila, text="Agregar", width=68, height=25, corner_radius=6,
                fg_color=COLORES["primario"], hover_color=COLORES["primario_hover"],
                text_color=COLORES["texto_oscuro"], font=fuente(10, True),
                command=lambda p=producto: self._agregar_producto(p),
            )
            agregar.grid(row=0, column=3, padx=4, pady=2)
            if disponible <= 0:
                agregar.configure(state="disabled", text="Agotado",
                                  fg_color=COLORES["panel_hover"],
                                  text_color=COLORES["texto_suave"])

    def _disponible(self, producto):
        return int(producto.get("existencia") or 0) + int(
            self._stock_extra.get(producto["id"], 0)
        )

    def _agregar_producto(self, producto):
        self.error_pos.configure(text="")
        disponible = self._disponible(producto)
        if disponible <= 0:
            self.error_pos.configure(
                text=f"'{producto['codigo']} - {producto['nombre']}' no tiene existencias."
            )
            return
        for item in self.items:
            if int(item["producto_id"]) == int(producto["id"]):
                if item["cantidad"] + 1 > disponible:
                    self.error_pos.configure(
                        text=f"No hay existencias suficientes. Disponible: {disponible}."
                    )
                    return
                item["cantidad"] += 1
                self._refrescar_carrito(producto["id"])
                return
        self.items.append({
            "producto_id": producto["id"],
            "codigo": producto["codigo"],
            "nombre": producto["nombre"],
            "precio_venta": _redondear(producto["precio_venta"]),
            "existencia": disponible,
            "cantidad": 1,
        })
        self._refrescar_carrito(producto["id"])

    def _al_seleccionar_carrito(self, fila):
        pass

    def _cambiar_cantidad(self, delta):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        producto_id = fila["producto_id"]
        for item in self.items:
            if int(item["producto_id"]) == int(producto_id):
                nueva = item["cantidad"] + delta
                if nueva <= 0:
                    self.items.remove(item)
                    self._refrescar_carrito()
                    return
                if nueva > item["existencia"]:
                    self.error_pos.configure(
                        text=f"No hay existencias suficientes. Disponible: "
                             f"{item['existencia']}."
                    )
                    return
                item["cantidad"] = nueva
                self._refrescar_carrito(producto_id)
                return

    def _quitar_producto(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        self.items = [i for i in self.items
                      if int(i["producto_id"]) != int(fila["producto_id"])]
        self._refrescar_carrito()
        self.error_pos.configure(text="")

    def _refrescar_carrito(self, seleccionar_id=None):
        filas = []
        for item in self.items:
            subtotal = _redondear(item["precio_venta"] * item["cantidad"])
            filas.append({**item, "subtotal": subtotal})
        self.tabla.cargar(filas)
        if seleccionar_id is not None:
            self.tabla.seleccionar_por_clave("producto_id", seleccionar_id)
        self._recalcular()

    def _cambio_metodo(self):
        self._monto_auto = True
        self._recalcular()

    def _actualizar_switch(self):
        if self.cliente and self._puntos_disponibles >= PUNTOS_PARA_CANJE:
            self.switch_puntos.configure(state="normal")
            self.lbl_disponibles.configure(
                text=f"Puntos disponibles: {self._puntos_disponibles}. "
                     f"Puede canjear {PUNTOS_PARA_CANJE} puntos por un 50% de descuento."
            )
        else:
            self.switch_puntos.configure(state="disabled")
            self.canjear.set(False)
            if self.cliente:
                self.lbl_disponibles.configure(
                    text=f"Puntos disponibles: {self._puntos_disponibles}. "
                         f"Faltan {max(0, PUNTOS_PARA_CANJE - self._puntos_disponibles)} "
                         "para el descuento del 50%."
                )

    def _recalcular(self):
        subtotal = _redondear(sum(
            (item["precio_venta"] * item["cantidad"] for item in self.items),
            Decimal("0.00"),
        ))
        descuento_volumen = Decimal("0.00")
        if subtotal > _redondear(UMBRAL_DESCUENTO_VOLUMEN):
            descuento_volumen = _redondear(
                subtotal * Decimal(str(PORCENTAJE_DESCUENTO_VOLUMEN))
            )
        base = _redondear(subtotal - descuento_volumen)
        canjear = bool(self.canjear.get()) and self.cliente is not None
        if canjear and self._puntos_disponibles < PUNTOS_PARA_CANJE:
            canjear = False
            self.canjear.set(False)
        descuento_puntos = (_redondear(base * Decimal(str(PORCENTAJE_DESCUENTO_PUNTOS)))
                            if canjear else Decimal("0.00"))
        total = _redondear(base - descuento_puntos)
        if total < 0:
            total = Decimal("0.00")
        puntos_ganados = int(total // Decimal(str(PESOS_POR_PUNTO)))

        self.lbl_subtotal.configure(text=dinero(subtotal))
        self.lbl_volumen.configure(text=f"-{dinero(descuento_volumen)}")
        self.lbl_puntos_desc.configure(text=f"-{dinero(descuento_puntos)}")
        self.lbl_total.configure(text=dinero(total))
        self.lbl_ganados.configure(
            text=f"Puntos a ganar: {puntos_ganados}  "
                 f"(1 por cada ${PESOS_POR_PUNTO}.00)"
        )
        self._totales = {
            "subtotal": subtotal,
            "descuento_volumen": descuento_volumen,
            "descuento_puntos": descuento_puntos,
            "total": total,
            "puntos_ganados": puntos_ganados,
            "canjear": canjear,
        }

        metodo = METODOS.get(self.metodo_var.get(), "EFECTIVO")
        if metodo != "EFECTIVO":
            self.monto.configure(state="normal")
            self.monto_var.set(f"{total:.2f}")
            self.monto.configure(state="disabled")
            self.lbl_cambio.configure(text="Cambio: $0.00 (pago electrónico)",
                                       text_color=COLORES["texto_suave"])
        else:
            self.monto.configure(state="normal")
            if self._monto_auto:
                self.monto_var.set(f"{total:.2f}")
            try:
                recibido = a_decimal(self.monto_var.get() or 0, "monto recibido")
            except ErrorValidacion:
                recibido = Decimal("0.00")
            if recibido >= total:
                cambio = _redondear(recibido - total)
                self.lbl_cambio.configure(text=f"Cambio: {dinero(cambio)}",
                                          text_color=COLORES["exito"])
            else:
                self.lbl_cambio.configure(text="Monto insuficiente",
                                          text_color=COLORES["peligro"])

    # ------------------------------------------------------------------
    def _cargar_venta(self):
        self.cliente = clientes_servicio.obtener(self.venta["cliente_id"])
        if self.cliente:
            self._puntos_disponibles = self._calcular_disponibles(self.cliente)
            self.info_cliente.configure(
                text=f"{self.cliente['codigo']}  ·  {self.cliente['nombre']} "
                     f"{self.cliente['apellido']}  ·  {self._puntos_disponibles} pts",
                text_color=COLORES["texto"],
            )
            self.lbl_disponibles.configure(
                text=f"Puntos disponibles al modificar: {self._puntos_disponibles}."
            )
        detalles = ventas_servicio.detalle(self.venta["id"])
        for detalle in detalles:
            producto = productos_servicio.obtener(detalle["producto_id"])
            if not producto:
                continue
            self._stock_extra[producto["id"]] = (
                self._stock_extra.get(producto["id"], 0) + int(detalle["cantidad"])
            )
            self.items.append({
                "producto_id": producto["id"],
                "codigo": producto["codigo"],
                "nombre": producto["nombre"],
                "precio_venta": _redondear(producto["precio_venta"]),
                "existencia": int(producto["existencia"]) + int(detalle["cantidad"]),
                "cantidad": int(detalle["cantidad"]),
            })
        self.metodo_var.set(METODOS_INVERSO.get(self.venta["metodo_pago"], "Efectivo"))
        if self.venta["metodo_pago"] == "EFECTIVO":
            self._monto_auto = False
            self.monto_var.set(f"{Decimal(self.venta['monto_recibido']):.2f}")
        else:
            self._monto_auto = True
        self.canjear.set(bool(self.venta["puntos_canjeados"]))
        self._actualizar_switch()
        self._refrescar_carrito()

    # ------------------------------------------------------------------
    def _leer_motivo(self):
        if not self.venta:
            return ""
        return self.motivo.get("1.0", "end").strip()

    def _guardar(self):
        self.error.configure(text="")
        self.error_pos.configure(text="")
        if not self.cliente:
            self.error.configure(text="Seleccione o registre un cliente.")
            return
        if not self.items:
            self.error.configure(text="Agregue al menos un producto a la venta.")
            return
        self._recalcular()
        total = self._totales.get("total", Decimal("0.00"))
        metodo = METODOS.get(self.metodo_var.get(), "EFECTIVO")
        if metodo == "EFECTIVO":
            try:
                recibido = a_decimal(self.monto_var.get(), "monto recibido")
            except ErrorValidacion as exc:
                self.error.configure(text=str(exc))
                return
            if recibido < total:
                self.error.configure(
                    text=f"El monto recibido ({dinero(recibido)}) es menor que el "
                         f"total a pagar ({dinero(total)})."
                )
                return
            cambio = _redondear(recibido - total)
        else:
            recibido = total
            cambio = Decimal("0.00")

        motivo = self._leer_motivo()
        if self.venta and len(motivo) < 5:
            self.error.configure(
                text="Escriba el motivo de la modificación (mínimo 5 caracteres)."
            )
            return
        if (self.venta and self.sesion.es_cajero()
                and not self.autorizado_por_id):
            self.error.configure(
                text="Un gerente debe autorizar la modificación de esta venta."
            )
            return

        if self.venta:
            mensaje = (f"Total anterior: {dinero(self.venta['total'])}\n"
                       f"Nuevo total: {dinero(total)}\n"
                       f"Motivo: {motivo}")
            texto_confirmar = "Guardar cambios"
        else:
            mensaje = (f"Total a cobrar: {dinero(total)}\n"
                       f"Método: {self.metodo_var.get()}\n"
                       f"Recibido: {dinero(recibido)}  ·  Cambio: {dinero(cambio)}\n"
                       f"Puntos a ganar: {self._totales.get('puntos_ganados', 0)}")
            texto_confirmar = "Cobrar venta"

        if not confirmar(self, "Confirmar operación", mensaje,
                         texto_confirmar=texto_confirmar, peligro=False):
            self._restaurar_grab()
            return
        self._restaurar_grab()

        items = [{"producto_id": item["producto_id"], "cantidad": item["cantidad"]}
                 for item in self.items]
        try:
            if self.venta:
                self.resultado_venta = ventas_servicio.modificar_venta(
                    self.venta["id"], self.cliente["id"], items, metodo, recibido,
                    bool(self.canjear.get()), self.sesion.id, motivo,
                    autorizado_por_id=self.autorizado_por_id,
                )
            else:
                self.resultado_venta = ventas_servicio.registrar_venta(
                    self.cliente["id"], items, metodo, recibido,
                    bool(self.canjear.get()), self.sesion.id,
                )
        except Exception as exc:
            self.error.configure(text=str(exc))
            return
        self.guardado = True
        self._cerrar()


class ModuloVentas(ctk.CTkFrame):
    TITULO = "Ventas"
    SUBTITULO = "Punto de venta, consulta y control de operaciones."

    def __init__(self, master, sesion, abrir_nueva=False, **kwargs):
        super().__init__(master, fg_color=COLORES["fondo"], corner_radius=0)
        self.sesion = sesion
        self.abrir_nueva = abrir_nueva
        if abrir_nueva:
            self.TITULO = "Punto de venta"
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        if not sesion.puede("ventas", "buscar"):
            ctk.CTkLabel(self, text="No tiene permisos para acceder a este módulo.",
                         font=fuente(16, True),
                         text_color=COLORES["peligro"]).grid(row=0, column=0, pady=80)
            return

        self._construir_barra()
        self._construir_tabla()
        self.after(100, self.cargar)
        if abrir_nueva and sesion.puede("ventas", "crear"):
            self.after(220, self._nueva)

    def _construir_barra(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        barra.grid_columnconfigure(4, weight=1)

        self.busqueda = BarraBusqueda(barra, self.cargar,
                                      "Folio, cliente o cajero...", ancho=260)
        self.busqueda.grid(row=0, column=0, sticky="w")

        self.estado = CampoCombo(barra, "Estado",
                                 ["Todas", "Completadas", "Canceladas"],
                                 valor="Todas", ancho=130,
                                 comando=lambda _v: self.cargar())
        self.estado.grid(row=0, column=1, padx=10, sticky="w")

        fechas = ctk.CTkFrame(barra, fg_color="transparent")
        fechas.grid(row=0, column=2, padx=(0, 10), sticky="w")
        self.desde = Campo(fechas, "Desde", placeholder="AAAA-MM-DD", ancho=120)
        self.desde.grid(row=0, column=0, padx=(0, 6))
        self.hasta = Campo(fechas, "Hasta", placeholder="AAAA-MM-DD", ancho=120)
        self.hasta.grid(row=0, column=1)

        boton(barra, "Limpiar", self._limpiar_filtros, tipo="fantasma",
              ancho=85, alto=38).grid(row=0, column=3, padx=6, pady=(18, 0))

        acciones_sup = ctk.CTkFrame(barra, fg_color="transparent")
        acciones_sup.grid(row=0, column=4, sticky="e")
        boton(acciones_sup, "+ Nueva venta", self._nueva, tipo="primario",
              ancho=140, alto=38).grid(row=0, column=0, pady=(18, 0))

        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        acciones.grid_columnconfigure(0, weight=1)
        if self.sesion.es_cajero():
            ctk.CTkLabel(
                acciones,
                text="Las modificaciones y cancelaciones requieren autorización "
                     "de un gerente o administrador.",
                font=fuente(10), text_color=COLORES["advertencia"], anchor="w",
            ).grid(row=0, column=0, sticky="w")
        else:
            ctk.CTkLabel(
                acciones,
                text="Consulte el detalle, modifique o cancele una venta completada.",
                font=fuente(10), text_color=COLORES["texto_suave"], anchor="w",
            ).grid(row=0, column=0, sticky="w")
        boton(acciones, "Ver detalle", self._detalle, tipo="secundario",
              ancho=110, alto=34).grid(row=0, column=1, padx=4)
        if self.sesion.puede("ventas", "modificar"):
            boton(acciones, "Modificar", self._modificar, tipo="secundario",
                  ancho=105, alto=34).grid(row=0, column=2, padx=4)
        if self.sesion.puede("ventas", "cancelar"):
            boton(acciones, "Cancelar", self._cancelar, tipo="peligro",
                  ancho=100, alto=34).grid(row=0, column=3, padx=4)

    def _construir_tabla(self):
        self.tabla = TablaDatos(
            self,
            [
                {"titulo": "Folio", "clave": "folio", "peso": 1},
                {"titulo": "Fecha", "clave": "fecha", "peso": 2,
                 "formato": formato_fecha},
                {"titulo": "Cliente", "clave": "cliente", "peso": 3},
                {"titulo": "Atendió", "clave": "usuario", "peso": 2},
                {"titulo": "Descuentos", "clave": "descuento_total", "peso": 1,
                 "formato": formato_dinero, "alineacion": "e"},
                {"titulo": "Total", "clave": "total", "peso": 1,
                 "formato": formato_dinero, "alineacion": "e"},
                {"titulo": "Pago", "clave": "metodo_pago", "peso": 1,
                 "formato": _formato_metodo},
                {"titulo": "Estado", "clave": "estado", "peso": 1,
                 "formato": texto_estado},
            ],
            on_doble_clic=lambda _fila: self._detalle(),
        )
        self.tabla.grid(row=2, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    def _fecha(self, valor):
        valor = valor.strip()
        if not valor:
            return None
        try:
            datetime.strptime(valor, "%Y-%m-%d")
            return valor
        except ValueError:
            raise ErrorValidacion(
                f"La fecha '{valor}' no es válida. Use el formato AAAA-MM-DD."
            )

    def cargar(self):
        try:
            desde = self._fecha(self.desde.obtener())
            hasta = self._fecha(self.hasta.obtener())
            estado = {
                "Todas": "TODAS",
                "Completadas": "COMPLETADA",
                "Canceladas": "CANCELADA",
            }.get(self.estado.obtener(), "TODAS")
            filas = ventas_servicio.listar(
                self.busqueda.texto(), estado, desde, hasta
            )
            for fila in filas:
                fila["descuento_total"] = (
                    Decimal(fila["descuento_volumen"] or 0)
                    + Decimal(fila["descuento_puntos"] or 0)
                )
        except ErrorValidacion as exc:
            mostrar_error(self, exc)
            return
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self.tabla.cargar(filas)

    def _limpiar_filtros(self):
        self.busqueda.limpiar()
        self.estado.establecer("Todas")
        self.desde.establecer("")
        self.hasta.establecer("")
        self.cargar()

    def _autorizar(self, accion):
        if not self.sesion.es_cajero():
            return True, None
        supervisor = solicitar_autorizacion(self, accion)
        if not supervisor:
            return False, None
        return True, supervisor.id

    def _nueva(self):
        if not self.sesion.puede("ventas", "crear"):
            mostrar_error(self, "No tiene permisos para registrar ventas.")
            return
        dialogo = FormularioVenta(self, self.sesion)
        self.wait_window(dialogo)
        if dialogo.guardado and dialogo.resultado_venta:
            self.cargar()
            r = dialogo.resultado_venta
            mensaje = (
                f"Venta {r['folio']} registrada correctamente.\n\n"
                f"Total: {dinero(r['total'])}\n"
                f"Cambio: {dinero(r['cambio'])}\n"
                f"Puntos ganados: {r['puntos_ganados']}"
            )
            if r["puntos_canjeados"]:
                mensaje += f"\nPuntos canjeados: {r['puntos_canjeados']}"
            mostrar_exito(self, mensaje, "Venta registrada")

    def _detalle(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        venta = ventas_servicio.obtener(fila["id"])
        if not venta:
            mostrar_error(self, "La venta ya no existe.")
            return
        dialogo = DetalleVenta(self, venta)
        self.wait_window(dialogo)

    def _modificar(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        if fila["estado"] == "CANCELADA":
            mostrar_error(self, "No se puede modificar una venta cancelada.")
            return
        autorizado, autorizado_id = self._autorizar(
            "modificar la venta seleccionada"
        )
        if not autorizado:
            return
        venta = ventas_servicio.obtener(fila["id"])
        if not venta:
            mostrar_error(self, "La venta ya no existe.")
            return
        dialogo = FormularioVenta(self, self.sesion, venta,
                                  autorizado_por_id=autorizado_id)
        self.wait_window(dialogo)
        if dialogo.guardado and dialogo.resultado_venta:
            self.cargar()
            mostrar_exito(
                self,
                f"La venta {dialogo.resultado_venta['folio']} fue modificada.\n"
                f"Nuevo total: {dinero(dialogo.resultado_venta['total'])}",
                "Venta modificada",
            )

    def _cancelar(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        if fila["estado"] == "CANCELADA":
            mostrar_error(self, "La venta ya está cancelada.")
            return
        motivo = solicitar_motivo(
            self, "Cancelar venta",
            f"Se devolverán las existencias y se ajustarán los puntos del cliente. "
            f"Venta {fila['folio']} por {dinero(fila['total'])}. "
            "Escriba el motivo de la cancelación.",
            texto_confirmar="Cancelar venta",
        )
        if not motivo:
            return
        autorizado, autorizado_id = self._autorizar("cancelar la venta seleccionada")
        if not autorizado:
            return
        try:
            ventas_servicio.cancelar_venta(
                fila["id"], motivo, self.sesion.id, autorizado_id
            )
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self.cargar()
        mostrar_exito(self, f"La venta {fila['folio']} fue cancelada.",
                      "Venta cancelada")
