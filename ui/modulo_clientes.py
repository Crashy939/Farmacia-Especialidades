"""Módulo de clientes y formulario reutilizable para el punto de venta."""

import customtkinter as ctk

from configuracion import COLORES
from servicios.clientes import clientes_servicio
from ui.componentes import (BarraBusqueda, Campo, CampoTexto, ModalBase, TablaDatos,
                            boton, confirmar, formato_fecha, fuente, mostrar_error,
                            mostrar_exito, texto_activo)
from utilidades import ErrorValidacion


class FormularioCliente(ModalBase):
    def __init__(self, master, sesion, cliente=None, rapido=False,
                 al_guardar=None):
        self.cliente = cliente
        self.rapido = rapido
        self.al_guardar = al_guardar
        self.cliente_id = None
        self.guardado = False
        titulo = "Editar cliente" if cliente else (
            "Registrar cliente" if rapido else "Nuevo cliente"
        )
        subtitulo = ("Complete los datos para continuar con la venta." if rapido
                     else "Datos de contacto y programa de puntos.")
        super().__init__(master, titulo, subtitulo, ancho=640, alto=570)
        self.sesion = sesion

        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=24, pady=20)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_columnconfigure(1, weight=1)

        self.nombre = Campo(contenedor, "Nombre", requerido=True,
                            placeholder="Ej. María")
        self.nombre.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
        self.apellido = Campo(contenedor, "Apellido", requerido=True,
                              placeholder="Ej. López")
        self.apellido.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 12))

        self.telefono = Campo(contenedor, "Teléfono", placeholder="Ej. 7777-1234")
        self.telefono.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
        self.email = Campo(contenedor, "Correo electrónico",
                           placeholder="cliente@correo.com")
        self.email.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 12))

        self.direccion = CampoTexto(contenedor, "Dirección", alto=70)
        self.direccion.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        if cliente:
            nota = (f"Puntos disponibles: {cliente['puntos']}  ·  "
                    f"Puntos históricos: {cliente['puntos_historicos']}")
            ctk.CTkLabel(contenedor, text=nota, font=fuente(11, True),
                         text_color=COLORES["primario"], anchor="w").grid(
                row=3, column=0, columnspan=2, sticky="w", pady=(0, 4)
            )
        ctk.CTkLabel(
            contenedor,
            text="Los clientes acumulan 1 punto por cada $100.00 de consumo. "
                 "Con 50 puntos pueden aplicar un 50% de descuento en una compra.",
            font=fuente(10), text_color=COLORES["texto_suave"], anchor="w",
            justify="left", wraplength=550,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self.error = ctk.CTkLabel(contenedor, text="", font=fuente(11),
                                  text_color=COLORES["peligro"], anchor="w",
                                  justify="left", wraplength=550)
        self.error.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.agregar_boton("Cancelar", self._cancelar, tipo="secundario", ancho=110)
        self.agregar_boton("Guardar cliente", self._guardar, tipo="primario",
                           ancho=145)

        if cliente:
            self.nombre.establecer(cliente["nombre"])
            self.apellido.establecer(cliente["apellido"])
            self.telefono.establecer(cliente.get("telefono") or "")
            self.email.establecer(cliente.get("email") or "")
            self.direccion.establecer(cliente.get("direccion") or "")
        self.after(120, self.nombre.enfocar)

    def _guardar(self):
        try:
            if self.cliente:
                clientes_servicio.actualizar(
                    self.cliente["id"], self.nombre.obtener(), self.apellido.obtener(),
                    self.telefono.obtener(), self.email.obtener(),
                    self.direccion.obtener(), ejecutor_id=self.sesion.id,
                )
                self.cliente_id = self.cliente["id"]
            else:
                self.cliente_id = clientes_servicio.crear(
                    self.nombre.obtener(), self.apellido.obtener(),
                    self.telefono.obtener(), self.email.obtener(),
                    self.direccion.obtener(), ejecutor_id=self.sesion.id,
                )
            self.guardado = True
            if self.al_guardar:
                try:
                    self.al_guardar(self.cliente_id)
                except Exception:
                    pass
            self._cerrar()
        except ErrorValidacion as exc:
            self.error.configure(text=str(exc))
        except Exception as exc:
            self.error.configure(text=str(exc))


class HistorialPuntos(ModalBase):
    def __init__(self, master, cliente):
        super().__init__(master, "Historial de puntos",
                         f"{cliente['codigo']} · {cliente['nombre']} {cliente['apellido']} "
                         f"· Saldo actual: {cliente['puntos']} pts",
                         ancho=760, alto=560)
        self.cliente = cliente
        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=20, pady=16)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(0, weight=1)
        self.tabla = TablaDatos(
            contenedor,
            [
                {"titulo": "Fecha", "clave": "fecha", "peso": 2,
                 "formato": formato_fecha},
                {"titulo": "Tipo", "clave": "tipo", "peso": 1},
                {"titulo": "Puntos", "clave": "puntos", "peso": 1,
                 "formato": self._formato_puntos, "alineacion": "center"},
                {"titulo": "Detalle", "clave": "descripcion", "peso": 4},
                {"titulo": "Venta", "clave": "folio", "peso": 1},
            ],
            altura=320,
        )
        self.tabla.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(
            contenedor,
            text="Los movimientos GANADO suman puntos; CANJEADO y REVERSO los descuentan.",
            font=fuente(10), text_color=COLORES["texto_suave"], anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.agregar_boton("Cerrar", self._cerrar, tipo="secundario", ancho=110)
        self.after(120, self._cargar)

    @staticmethod
    def _formato_puntos(valor, fila=None):
        try:
            numero = int(valor or 0)
        except Exception:
            return str(valor)
        return f"{numero:+d} pts"

    def _cargar(self):
        try:
            filas = clientes_servicio.historial_puntos(self.cliente["id"])
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self.tabla.cargar(filas)


class ModuloClientes(ctk.CTkFrame):
    TITULO = "Clientes"
    SUBTITULO = "Registro de clientes y programa de puntos."

    def __init__(self, master, sesion, **kwargs):
        super().__init__(master, fg_color=COLORES["fondo"], corner_radius=0)
        self.sesion = sesion
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        if not sesion.puede("clientes", "buscar"):
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
                                      "Buscar por código, nombre, teléfono o correo...",
                                      ancho=320)
        self.busqueda.grid(row=0, column=0, sticky="w")

        self.incluir = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            barra, text="Incluir cancelados", variable=self.incluir,
            command=self.cargar, font=fuente(11), text_color=COLORES["texto_suave"],
            progress_color=COLORES["primario"], fg_color=COLORES["borde"],
        ).grid(row=0, column=1, padx=16, sticky="w")

        acciones = ctk.CTkFrame(barra, fg_color="transparent")
        acciones.grid(row=0, column=2, sticky="e")
        boton(acciones, "+ Nuevo", self._nuevo, tipo="primario", ancho=105).pack(
            side="left", padx=(0, 8)
        )
        boton(acciones, "Editar", self._editar, tipo="secundario", ancho=90).pack(
            side="left", padx=(0, 8)
        )
        boton(acciones, "Puntos", self._ver_puntos, tipo="fantasma", ancho=90).pack(
            side="left", padx=(0, 8)
        )
        boton(acciones, "Cancelar / Reactivar", self._cambiar_estado,
              tipo="peligro", ancho=155).pack(side="left")

    def _construir_tabla(self):
        self.tabla = TablaDatos(
            self,
            [
                {"titulo": "Código", "clave": "codigo", "peso": 1},
                {"titulo": "Cliente", "clave": "nombre_completo", "peso": 3},
                {"titulo": "Teléfono", "clave": "telefono", "peso": 2},
                {"titulo": "Correo", "clave": "email", "peso": 3},
                {"titulo": "Puntos", "clave": "puntos", "peso": 1,
                 "alineacion": "center"},
                {"titulo": "Estado", "clave": "activo", "peso": 1,
                 "formato": texto_activo},
            ],
            on_doble_clic=lambda _fila: self._editar(),
        )
        self.tabla.grid(row=1, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    def cargar(self):
        try:
            filas = clientes_servicio.listar(
                self.busqueda.texto(), self.incluir.get()
            )
            for fila in filas:
                fila["nombre_completo"] = f"{fila['nombre']} {fila['apellido']}"
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self.tabla.cargar(filas)

    def _nuevo(self):
        dialogo = FormularioCliente(self, self.sesion)
        self.wait_window(dialogo)
        if dialogo.guardado:
            self.cargar()
            mostrar_exito(self, "El cliente se registró correctamente.")

    def _editar(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        cliente = clientes_servicio.obtener(fila["id"])
        if not cliente:
            mostrar_error(self, "El cliente ya no existe.")
            self.cargar()
            return
        dialogo = FormularioCliente(self, self.sesion, cliente)
        self.wait_window(dialogo)
        if dialogo.guardado:
            self.cargar()
            mostrar_exito(self, "Los datos del cliente se actualizaron.")

    def _ver_puntos(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        cliente = clientes_servicio.obtener(fila["id"])
        if not cliente:
            mostrar_error(self, "El cliente ya no existe.")
            return
        dialogo = HistorialPuntos(self, cliente)
        self.wait_window(dialogo)

    def _cambiar_estado(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        activo = bool(fila["activo"])
        accion = "cancelar" if activo else "reactivar"
        if not confirmar(
            self, f"{accion.capitalize()} cliente",
            f"¿Desea {accion} a {fila['nombre']} {fila['apellido']} "
            f"({fila['codigo']})?",
            texto_confirmar=accion.capitalize(), peligro=activo,
        ):
            return
        try:
            clientes_servicio.cambiar_estado(fila["id"], not activo,
                                             ejecutor_id=self.sesion.id)
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self.cargar()
        mostrar_exito(self, f"El cliente fue {accion}do correctamente.")
