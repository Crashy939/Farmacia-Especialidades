"""Componentes reutilizables de CustomTkinter para toda la aplicación."""

from decimal import Decimal
import tkinter as tk

import customtkinter as ctk

from autenticacion import ErrorAutenticacion, autorizar_supervisor
from configuracion import COLORES, FUENTE
from utilidades import ErrorValidacion, dinero, fecha_legible


# --------------------------------------------------------------------------
# Tipografía y botones
# --------------------------------------------------------------------------
def fuente(tamano=13, negrita=False):
    return ctk.CTkFont(family=FUENTE, size=tamano, weight="bold" if negrita else "normal")


def boton(master, texto, comando, tipo="primario", ancho=130, alto=36, **kwargs):
    estilos = {
        "primario": dict(fg_color=COLORES["primario"], hover_color=COLORES["primario_hover"],
                         text_color=COLORES["texto_oscuro"]),
        "secundario": dict(fg_color=COLORES["panel_alt"], hover_color=COLORES["panel_hover"],
                           text_color=COLORES["texto"], border_width=1,
                           border_color=COLORES["borde"]),
        "peligro": dict(fg_color=COLORES["peligro"], hover_color=COLORES["peligro_hover"],
                        text_color=COLORES["blanco"]),
        "fantasma": dict(fg_color="transparent", hover_color=COLORES["panel_hover"],
                         text_color=COLORES["texto_suave"], border_width=1,
                         border_color=COLORES["borde"]),
        "exito": dict(fg_color=COLORES["exito"], hover_color="#45DDA3",
                      text_color=COLORES["texto_oscuro"]),
        "advertencia": dict(fg_color=COLORES["acento"], hover_color="#FFC95E",
                            text_color=COLORES["texto_oscuro"]),
    }
    estilo = estilos.get(tipo, estilos["primario"])
    return ctk.CTkButton(
        master, text=texto, command=comando, width=ancho, height=alto,
        corner_radius=8, font=fuente(13, True), **estilo, **kwargs
    )


# --------------------------------------------------------------------------
# Campos de formulario
# --------------------------------------------------------------------------
class Campo(ctk.CTkFrame):
    def __init__(self, master, etiqueta, requerido=False, placeholder="",
                 show="", valor="", ancho=260, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        texto = f"{etiqueta} *" if requerido else etiqueta
        ctk.CTkLabel(self, text=texto, font=fuente(12, True),
                     text_color=COLORES["texto_suave"], anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self.variable = ctk.StringVar(value=str(valor or ""))
        self.entrada = ctk.CTkEntry(
            self, textvariable=self.variable, placeholder_text=placeholder, show=show,
            width=ancho, height=38, corner_radius=8,
            fg_color=COLORES["panel_alt"], border_color=COLORES["borde"],
            text_color=COLORES["texto"], font=fuente(13),
        )
        self.entrada.grid(row=1, column=0, sticky="ew")

    def obtener(self):
        return self.variable.get()

    def establecer(self, valor):
        self.variable.set("" if valor is None else str(valor))

    def enfocar(self):
        self.entrada.focus_set()

    def configurar_estado(self, estado):
        self.entrada.configure(state=estado)

    def configurar_show(self, mostrar):
        self.entrada.configure(show="" if mostrar else "•")


class CampoCombo(ctk.CTkFrame):
    def __init__(self, master, etiqueta, valores, requerido=False, valor=None,
                 ancho=260, comando=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        texto = f"{etiqueta} *" if requerido else etiqueta
        ctk.CTkLabel(self, text=texto, font=fuente(12, True),
                     text_color=COLORES["texto_suave"], anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self.valores = list(valores) if valores else [""]
        self.variable = ctk.StringVar(value=valor or self.valores[0])
        self.combo = ctk.CTkOptionMenu(
            self, values=self.valores, variable=self.variable, width=ancho, height=38,
            corner_radius=8, fg_color=COLORES["panel_alt"],
            button_color=COLORES["primario_oscuro"],
            button_hover_color=COLORES["primario"],
            dropdown_fg_color=COLORES["panel_alt"],
            dropdown_hover_color=COLORES["primario_oscuro"],
            text_color=COLORES["texto"], font=fuente(13), command=comando,
            dropdown_font=fuente(13),
        )
        self.combo.grid(row=1, column=0, sticky="ew")

    def obtener(self):
        return self.variable.get()

    def establecer(self, valor):
        self.variable.set("" if valor is None else str(valor))

    def actualizar_valores(self, valores):
        self.valores = list(valores) if valores else [""]
        self.combo.configure(values=self.valores)
        if self.variable.get() not in self.valores:
            self.variable.set(self.valores[0])


class CampoTexto(ctk.CTkFrame):
    def __init__(self, master, etiqueta, alto=80, requerido=False, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        texto = f"{etiqueta} *" if requerido else etiqueta
        ctk.CTkLabel(self, text=texto, font=fuente(12, True),
                     text_color=COLORES["texto_suave"], anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self.caja = ctk.CTkTextbox(
            self, height=alto, corner_radius=8, fg_color=COLORES["panel_alt"],
            border_width=1, border_color=COLORES["borde"],
            text_color=COLORES["texto"], font=fuente(13),
        )
        self.caja.grid(row=1, column=0, sticky="ew")

    def obtener(self):
        return self.caja.get("1.0", "end").strip()

    def establecer(self, valor):
        self.caja.delete("1.0", "end")
        self.caja.insert("1.0", valor or "")


# --------------------------------------------------------------------------
# Tabla de datos con selección
# --------------------------------------------------------------------------
class TablaDatos(ctk.CTkFrame):
    """Tabla basada en CTkScrollableFrame.

    columnas: lista de diccionarios:
        {"titulo": "...", "clave": "...", "peso": 1, "formato": callable|None,
         "alineacion": "w"}
    """

    def __init__(self, master, columnas, altura=300, on_seleccion=None,
                 on_doble_clic=None, **kwargs):
        super().__init__(master, fg_color=COLORES["panel"], corner_radius=12,
                         border_width=1, border_color=COLORES["borde"], **kwargs)
        self.columnas = columnas
        self.on_seleccion = on_seleccion
        self.on_doble_clic = on_doble_clic
        self.filas = []
        self.seleccionado = None
        self._frame_seleccionado = None
        self._frames = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        cabecera = ctk.CTkFrame(self, fg_color=COLORES["panel_alt"], corner_radius=8,
                                height=40)
        cabecera.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        cabecera.grid_propagate(False)
        for i, col in enumerate(columnas):
            cabecera.grid_columnconfigure(i, weight=col.get("peso", 1))
            ctk.CTkLabel(
                cabecera, text=col["titulo"], font=fuente(11, True),
                text_color=COLORES["texto_suave"],
                anchor=col.get("alineacion", "w"),
            ).grid(row=0, column=i, sticky="ew", padx=10, pady=8)

        self.cuerpo = ctk.CTkScrollableFrame(
            self, fg_color="transparent", height=altura,
            scrollbar_button_color=COLORES["borde"],
            scrollbar_button_hover_color=COLORES["primario"],
        )
        self.cuerpo.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 10))
        for i, col in enumerate(columnas):
            self.cuerpo.grid_columnconfigure(i, weight=col.get("peso", 1))

        self.vacio = ctk.CTkLabel(
            self.cuerpo, text="No hay registros para mostrar.", font=fuente(13),
            text_color=COLORES["texto_suave"],
        )

    def cargar(self, filas):
        for widget in self.cuerpo.winfo_children():
            widget.destroy()
        self.filas = list(filas or [])
        self.seleccionado = None
        self._frame_seleccionado = None
        self._frames = []
        if not self.filas:
            self.vacio = ctk.CTkLabel(
                self.cuerpo, text="No hay registros para mostrar.", font=fuente(13),
                text_color=COLORES["texto_suave"],
            )
            self.vacio.grid(row=0, column=0, columnspan=max(1, len(self.columnas)),
                            pady=40)
            return

        for indice, fila in enumerate(self.filas):
            cancelada = str(fila.get("estado", "")).upper() == "CANCELADA"
            inactivo = fila.get("activo") in (0, False)
            color_fondo = (COLORES["panel_alt"] if indice % 2 == 0
                           else COLORES["panel"])
            frame = ctk.CTkFrame(self.cuerpo, fg_color=color_fondo, corner_radius=7,
                                 height=38)
            frame.grid(row=indice, column=0, columnspan=len(self.columnas),
                       sticky="ew", pady=2, padx=2)
            frame.grid_propagate(False)
            for i, col in enumerate(self.columnas):
                frame.grid_columnconfigure(i, weight=col.get("peso", 1))
                valor = fila.get(col["clave"], "")
                formato = col.get("formato")
                texto = formato(valor, fila) if formato else (
                    "" if valor is None else str(valor)
                )
                color_texto = COLORES["texto"]
                if cancelada or inactivo:
                    color_texto = COLORES["texto_suave"]
                etiqueta = ctk.CTkLabel(
                    frame, text=texto, font=fuente(12), text_color=color_texto,
                    anchor=col.get("alineacion", "w"),
                )
                etiqueta.grid(row=0, column=i, sticky="ew", padx=10, pady=8)
                etiqueta.bind("<Button-1>", lambda _e, f=frame, d=fila: self._seleccionar(f, d))
                if self.on_doble_clic:
                    etiqueta.bind("<Double-Button-1>",
                                  lambda _e, d=fila: self.on_doble_clic(d))
            frame.bind("<Button-1>", lambda _e, f=frame, d=fila: self._seleccionar(f, d))
            if self.on_doble_clic:
                frame.bind("<Double-Button-1>", lambda _e, d=fila: self.on_doble_clic(d))
            self._frames.append(frame)

    def _seleccionar(self, frame, fila):
        if self._frame_seleccionado is not None:
            try:
                indice = self.filas.index(self.seleccionado)
                self._frame_seleccionado.configure(
                    fg_color=COLORES["panel_alt"] if indice % 2 == 0 else COLORES["panel"]
                )
            except (ValueError, tk.TclError):
                pass
        self._frame_seleccionado = frame
        frame.configure(fg_color=COLORES["seleccion"])
        self.seleccionado = fila
        if self.on_seleccion:
            self.on_seleccion(fila)

    def obtener_seleccion(self, mostrar_error=True, master=None):
        if self.seleccionado:
            return self.seleccionado
        if mostrar_error:
            mostrar_mensaje(master or self, "Seleccione un registro",
                            "Primero haga clic sobre la fila que desea utilizar.",
                            tipo="advertencia")
        return None

    def seleccionar_por_clave(self, clave, valor):
        """Selecciona una fila por el valor de una columna (sin callback)."""
        for indice, fila in enumerate(self.filas):
            if fila.get(clave) == valor and indice < len(self._frames):
                self._frame_seleccionado = self._frames[indice]
                self._frame_seleccionado.configure(fg_color=COLORES["seleccion"])
                self.seleccionado = fila
                return fila
        return None


# --------------------------------------------------------------------------
# Búsqueda
# --------------------------------------------------------------------------
class BarraBusqueda(ctk.CTkFrame):
    def __init__(self, master, comando, placeholder="Buscar...", ancho=320, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.comando = comando
        self.grid_columnconfigure(0, weight=1)
        self.variable = ctk.StringVar()
        self.entrada = ctk.CTkEntry(
            self, textvariable=self.variable, placeholder_text=placeholder,
            width=ancho, height=38, corner_radius=8,
            fg_color=COLORES["panel_alt"], border_color=COLORES["borde"],
            text_color=COLORES["texto"], font=fuente(13),
        )
        self.entrada.grid(row=0, column=0, sticky="ew")
        self.entrada.bind("<Return>", lambda _e: self.comando())
        boton(self, "Buscar", self.comando, tipo="secundario", ancho=95, alto=38).grid(
            row=0, column=1, padx=(8, 0)
        )

    def texto(self):
        return self.variable.get().strip()

    def limpiar(self):
        self.variable.set("")


# --------------------------------------------------------------------------
# Ventanas modales
# --------------------------------------------------------------------------
def centrar(ventana, ancho, alto, padre=None):
    ventana.update_idletasks()
    if padre is not None:
        try:
            x = padre.winfo_rootx() + max(0, (padre.winfo_width() - ancho) // 2)
            y = padre.winfo_rooty() + max(0, (padre.winfo_height() - alto) // 2)
        except tk.TclError:
            x = y = 120
    else:
        x = (ventana.winfo_screenwidth() - ancho) // 2
        y = (ventana.winfo_screenheight() - alto) // 2
    x = max(0, min(x, ventana.winfo_screenwidth() - ancho))
    y = max(0, min(y, ventana.winfo_screenheight() - alto))
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")


class ModalBase(ctk.CTkToplevel):
    def __init__(self, master, titulo, subtitulo="", ancho=620, alto=560):
        super().__init__(master, fg_color=COLORES["fondo"])
        self.resultado = None
        self._master = master
        self.title(titulo)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self._cancelar)
        self.bind("<Escape>", lambda _e: self._cancelar())
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
        cabecera.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cabecera, text=titulo, font=fuente(20, True),
                     text_color=COLORES["texto"], anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        if subtitulo:
            ctk.CTkLabel(cabecera, text=subtitulo, font=fuente(12),
                         text_color=COLORES["texto_suave"], anchor="w").grid(
                row=1, column=0, sticky="w", pady=(3, 0)
            )
        ctk.CTkButton(
            cabecera, text="✕", width=32, height=32, corner_radius=8,
            fg_color="transparent", hover_color=COLORES["peligro"],
            text_color=COLORES["texto_suave"], font=fuente(14, True),
            command=self._cancelar,
        ).grid(row=0, column=1, rowspan=2, sticky="e")

        self.cuerpo = ctk.CTkFrame(self, fg_color=COLORES["panel"], corner_radius=12,
                                   border_width=1, border_color=COLORES["borde"])
        self.cuerpo.grid(row=1, column=0, sticky="nsew", padx=24, pady=10)
        self.cuerpo.grid_columnconfigure(0, weight=1)

        self.pie = ctk.CTkFrame(self, fg_color="transparent")
        self.pie.grid(row=2, column=0, sticky="ew", padx=24, pady=(10, 20))
        self.pie.grid_columnconfigure(0, weight=1)

        self.fondo_guardado = None
        self._ancho_inicial = ancho
        self._alto_inicial = alto
        self._padre_inicial = master.winfo_toplevel()
        self.after(60, self._preparar)

    def _preparar(self):
        # La ventana debe estar mapeada para que el gestor de ventanas respete
        # la posición calculada; centrar antes de mostrarla deja el diálogo
        # en la esquina superior izquierda en algunos entornos Linux.
        centrar(self, self._ancho_inicial, self._alto_inicial, self._padre_inicial)
        try:
            self.grab_set()
            self.lift()
            self.focus_force()
        except tk.TclError:
            pass

    def _cancelar(self):
        self.resultado = None
        self._cerrar()

    def _cerrar(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def agregar_boton(self, texto, comando, tipo="primario", ancho=130):
        b = boton(self.pie, texto, comando, tipo=tipo, ancho=ancho, alto=38)
        b.pack(side="right", padx=(8, 0))
        return b


class _DialogoMensaje(ModalBase):
    COLORES_TIPO = {
        "info": ("ℹ", COLORES["info"], "Información"),
        "exito": ("✔", COLORES["exito"], "Operación exitosa"),
        "error": ("✖", COLORES["peligro"], "No se pudo completar"),
        "advertencia": ("⚠", COLORES["advertencia"], "Atención"),
    }

    def __init__(self, master, titulo, mensaje, tipo="info"):
        icono, color, etiqueta = self.COLORES_TIPO.get(tipo, self.COLORES_TIPO["info"])
        super().__init__(master, titulo or etiqueta, ancho=540, alto=380)
        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=26, pady=24)
        ctk.CTkLabel(contenedor, text=icono, font=fuente(40, True),
                     text_color=color).pack(anchor="w")
        ctk.CTkLabel(contenedor, text=titulo or etiqueta, font=fuente(16, True),
                     text_color=COLORES["texto"], anchor="w",
                     justify="left", wraplength=440).pack(anchor="w", pady=(8, 4))
        ctk.CTkLabel(contenedor, text=mensaje, font=fuente(13),
                     text_color=COLORES["texto_suave"], anchor="w",
                     justify="left", wraplength=440).pack(anchor="w")
        self.agregar_boton("Aceptar", self._aceptar, tipo="primario", ancho=120)

    def _aceptar(self):
        self.resultado = True
        self._cerrar()


def mostrar_mensaje(master, titulo, mensaje, tipo="info"):
    dialogo = _DialogoMensaje(master, titulo, mensaje, tipo)
    try:
        master.wait_window(dialogo)
    except tk.TclError:
        pass


def mostrar_error(master, mensaje, titulo="No se pudo completar"):
    mostrar_mensaje(master, titulo, str(mensaje), "error")


def mostrar_exito(master, mensaje, titulo="Operación exitosa"):
    mostrar_mensaje(master, titulo, str(mensaje), "exito")


class _DialogoConfirmacion(ModalBase):
    def __init__(self, master, titulo, mensaje, texto_confirmar="Sí, continuar",
                 peligro=True):
        super().__init__(master, titulo, ancho=520, alto=360)
        self.resultado = False
        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=26, pady=24)
        ctk.CTkLabel(contenedor, text="⚠", font=fuente(36, True),
                     text_color=COLORES["advertencia"]).pack(anchor="w")
        ctk.CTkLabel(contenedor, text=mensaje, font=fuente(13),
                     text_color=COLORES["texto"], anchor="w", justify="left",
                     wraplength=420).pack(anchor="w", pady=(10, 0))
        self.agregar_boton("Cancelar", self._cancelar, tipo="secundario", ancho=110)
        self.agregar_boton(texto_confirmar, self._confirmar,
                           tipo="peligro" if peligro else "primario", ancho=150)

    def _confirmar(self):
        self.resultado = True
        self._cerrar()


def confirmar(master, titulo, mensaje, texto_confirmar="Sí, continuar", peligro=True):
    dialogo = _DialogoConfirmacion(master, titulo, mensaje, texto_confirmar, peligro)
    try:
        master.wait_window(dialogo)
    except tk.TclError:
        return False
    return bool(dialogo.resultado)


class _SolicitarMotivo(ModalBase):
    def __init__(self, master, titulo, mensaje, texto_confirmar="Continuar"):
        super().__init__(master, titulo, ancho=520, alto=360)
        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=24, pady=20)
        ctk.CTkLabel(contenedor, text=mensaje, font=fuente(12),
                     text_color=COLORES["texto_suave"], anchor="w",
                     justify="left", wraplength=430).pack(anchor="w", pady=(0, 12))
        self.campo = CampoTexto(contenedor, "Motivo", alto=90, requerido=True)
        self.campo.pack(fill="x")
        self.error = ctk.CTkLabel(contenedor, text="", font=fuente(12),
                                  text_color=COLORES["peligro"])
        self.error.pack(anchor="w", pady=(6, 0))
        self.agregar_boton("Cancelar", self._cancelar, tipo="secundario", ancho=110)
        self.agregar_boton(texto_confirmar, self._aceptar, tipo="peligro", ancho=130)

    def _aceptar(self):
        texto = self.campo.obtener()
        if len(texto) < 5:
            self.error.configure(text="Escriba un motivo de al menos 5 caracteres.")
            return
        self.resultado = texto
        self._cerrar()


def solicitar_motivo(master, titulo, mensaje, texto_confirmar="Continuar"):
    dialogo = _SolicitarMotivo(master, titulo, mensaje, texto_confirmar)
    try:
        master.wait_window(dialogo)
    except tk.TclError:
        return None
    return dialogo.resultado


class _SolicitarAutorizacion(ModalBase):
    def __init__(self, master, accion="esta operación"):
        super().__init__(master, "Autorización del gerente", ancho=470, alto=430)
        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=26, pady=22)
        ctk.CTkLabel(contenedor, text="🔒", font=fuente(32, True),
                     text_color=COLORES["advertencia"]).pack(anchor="w")
        ctk.CTkLabel(
            contenedor,
            text=(f"Para {accion} se requiere la autorización de un gerente o "
                  "administrador."),
            font=fuente(12), text_color=COLORES["texto_suave"], anchor="w",
            justify="left", wraplength=380,
        ).pack(anchor="w", pady=(6, 14))
        self.usuario = Campo(contenedor, "Usuario autorizador", requerido=True,
                             placeholder="Ej. gerente")
        self.usuario.pack(fill="x", pady=(0, 10))
        self.clave = Campo(contenedor, "Contraseña", requerido=True, show="•")
        self.clave.pack(fill="x")
        self.clave.entrada.bind("<Return>", lambda _e: self._autorizar())
        self.error = ctk.CTkLabel(contenedor, text="", font=fuente(12),
                                  text_color=COLORES["peligro"], wraplength=380,
                                  justify="left")
        self.error.pack(anchor="w", pady=(8, 0))
        self.agregar_boton("Cancelar", self._cancelar, tipo="secundario", ancho=110)
        self.agregar_boton("Autorizar", self._autorizar, tipo="advertencia", ancho=130)
        self.after(120, self.usuario.enfocar)

    def _autorizar(self):
        try:
            self.resultado = autorizar_supervisor(
                self.usuario.obtener(), self.clave.obtener()
            )
            self._cerrar()
        except (ErrorAutenticacion, ErrorValidacion) as exc:
            self.error.configure(text=str(exc))


def solicitar_autorizacion(master, accion="esta operación"):
    dialogo = _SolicitarAutorizacion(master, accion)
    try:
        master.wait_window(dialogo)
    except tk.TclError:
        return None
    return dialogo.resultado


# --------------------------------------------------------------------------
# Formatos comunes para tablas
# --------------------------------------------------------------------------
def texto_estado(valor, fila=None):
    valor = str(valor or "").upper()
    return {"COMPLETADA": "✔ Completada", "CANCELADA": "✖ Cancelada"}.get(valor, valor)


def texto_activo(valor, fila=None):
    return "Activo" if valor else "Cancelado"


def formato_dinero(valor, fila=None):
    return dinero(valor)


def formato_fecha(valor, fila=None):
    return fecha_legible(valor)


def formato_puntos(valor, fila=None):
    return f"{int(valor or 0)} pts"
