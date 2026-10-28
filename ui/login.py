"""Pantalla de inicio de sesión."""

import tkinter as tk

import customtkinter as ctk

from autenticacion import ErrorAutenticacion, iniciar_sesion
from base_datos import ErrorBaseDatos
from configuracion import COLORES, SUBTITULO_APP, TITULO_APP
from ui.componentes import Campo, boton, fuente


class MarcoLogin(ctk.CTkFrame):
    def __init__(self, master, al_ingresar):
        super().__init__(master, fg_color=COLORES["fondo"])
        self.al_ingresar = al_ingresar
        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=1)

        self._construir_marca()
        self._construir_formulario()
        self.after(250, self.campo_usuario.enfocar)

    # ------------------------------------------------------------------
    def _construir_marca(self):
        marca = ctk.CTkFrame(self, fg_color=COLORES["panel"], corner_radius=0)
        marca.grid(row=0, column=0, sticky="nsew")
        marca.grid_columnconfigure(0, weight=1)
        marca.grid_rowconfigure(0, weight=1)

        contenido = ctk.CTkFrame(marca, fg_color="transparent")
        contenido.grid(row=0, column=0, sticky="nsew", padx=70, pady=60)
        contenido.grid_columnconfigure(0, weight=1)

        logo = ctk.CTkFrame(contenido, width=82, height=82, corner_radius=22,
                            fg_color=COLORES["primario"])
        logo.grid(row=0, column=0, sticky="w")
        logo.grid_propagate(False)
        ctk.CTkLabel(logo, text="✚", font=fuente(42, True),
                     text_color=COLORES["texto_oscuro"]).place(relx=0.5, rely=0.5,
                                                               anchor="center")

        ctk.CTkLabel(contenido, text=TITULO_APP, font=fuente(38, True),
                     text_color=COLORES["texto"], anchor="w").grid(
            row=1, column=0, sticky="w", pady=(28, 4)
        )
        ctk.CTkLabel(contenido, text=SUBTITULO_APP, font=fuente(16),
                     text_color=COLORES["texto_suave"], anchor="w").grid(
            row=2, column=0, sticky="w"
        )

        ctk.CTkFrame(contenido, height=1, fg_color=COLORES["borde"]).grid(
            row=3, column=0, sticky="ew", pady=32
        )

        caracteristicas = [
            ("▣", "Control de inventario y almacén", "Productos, existencias y alertas de stock."),
            ("◈", "Punto de venta ágil", "Búsqueda de clientes, descuentos y puntos."),
            ("✦", "Compras y proveedores", "Reabastecimiento con actualización automática."),
            ("◉", "Perfiles y permisos", "Administrador, gerente y cajero."),
        ]
        for indice, (icono, titulo, detalle) in enumerate(caracteristicas, start=4):
            fila = ctk.CTkFrame(contenido, fg_color="transparent")
            fila.grid(row=indice, column=0, sticky="ew", pady=8)
            ctk.CTkLabel(fila, text=icono, font=fuente(20, True),
                         text_color=COLORES["primario"], width=36).grid(
                row=0, column=0, rowspan=2, sticky="n", padx=(0, 12)
            )
            ctk.CTkLabel(fila, text=titulo, font=fuente(14, True),
                         text_color=COLORES["texto"], anchor="w").grid(
                row=0, column=1, sticky="w"
            )
            ctk.CTkLabel(fila, text=detalle, font=fuente(12),
                         text_color=COLORES["texto_suave"], anchor="w").grid(
                row=1, column=1, sticky="w"
            )

        ctk.CTkLabel(
            contenido, text="Sistema académico · Ingeniería de Software · 2026",
            font=fuente(11), text_color=COLORES["texto_suave"], anchor="w",
        ).grid(row=20, column=0, sticky="sw", pady=(40, 0))
        contenido.grid_rowconfigure(19, weight=1)

    # ------------------------------------------------------------------
    def _construir_formulario(self):
        lateral = ctk.CTkFrame(self, fg_color=COLORES["fondo"], corner_radius=0)
        lateral.grid(row=0, column=1, sticky="nsew")
        lateral.grid_columnconfigure(0, weight=1)
        lateral.grid_rowconfigure(0, weight=1)

        tarjeta = ctk.CTkFrame(
            lateral, fg_color=COLORES["panel"], corner_radius=18,
            border_width=1, border_color=COLORES["borde"], width=410,
        )
        tarjeta.grid(row=0, column=0, padx=54, pady=60)
        tarjeta.grid_propagate(False)
        tarjeta.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(tarjeta, text="Bienvenido", font=fuente(26, True),
                     text_color=COLORES["texto"], anchor="w").grid(
            row=0, column=0, sticky="w", padx=34, pady=(34, 2)
        )
        ctk.CTkLabel(tarjeta, text="Ingrese sus credenciales para continuar.",
                     font=fuente(12), text_color=COLORES["texto_suave"], anchor="w").grid(
            row=1, column=0, sticky="w", padx=34, pady=(0, 24)
        )

        self.campo_usuario = Campo(tarjeta, "Usuario", requerido=True,
                                   placeholder="Nombre de usuario", ancho=340)
        self.campo_usuario.grid(row=2, column=0, sticky="ew", padx=34, pady=(0, 14))
        self.campo_usuario.entrada.bind("<Return>", lambda _e: self._ingresar())

        self.campo_clave = Campo(tarjeta, "Contraseña", requerido=True,
                                 placeholder="Contraseña", show="•", ancho=340)
        self.campo_clave.grid(row=3, column=0, sticky="ew", padx=34)
        self.campo_clave.entrada.bind("<Return>", lambda _e: self._ingresar())

        self.mostrar = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            tarjeta, text="Mostrar contraseña", variable=self.mostrar,
            command=self._alternar_clave,
            font=fuente(11), text_color=COLORES["texto_suave"],
            fg_color=COLORES["primario"], hover_color=COLORES["primario_hover"],
            checkmark_color=COLORES["texto_oscuro"],
            border_color=COLORES["borde"], checkbox_width=18, checkbox_height=18,
        ).grid(row=4, column=0, sticky="w", padx=34, pady=(12, 0))

        self.error = ctk.CTkLabel(
            tarjeta, text="", font=fuente(11), text_color=COLORES["peligro"],
            anchor="w", justify="left", wraplength=330,
        )
        self.error.grid(row=5, column=0, sticky="ew", padx=34, pady=(12, 4))

        self.boton_ingresar = boton(tarjeta, "Iniciar sesión", self._ingresar,
                                    tipo="primario", ancho=340, alto=42)
        self.boton_ingresar.grid(row=6, column=0, padx=34, pady=(4, 18))

        ctk.CTkFrame(tarjeta, height=1, fg_color=COLORES["borde"]).grid(
            row=7, column=0, sticky="ew", padx=34, pady=(0, 14)
        )
        ctk.CTkLabel(
            tarjeta, text="Acceso restringido. Solo personal autorizado.",
            font=fuente(10), text_color=COLORES["texto_suave"],
        ).grid(row=8, column=0, pady=(0, 24))

        tarjeta.configure(height=500)

    # ------------------------------------------------------------------
    def _alternar_clave(self):
        self.campo_clave.configurar_show(self.mostrar.get())

    def _ingresar(self):
        usuario = self.campo_usuario.obtener().strip()
        clave = self.campo_clave.obtener()
        self.error.configure(text="")
        if not usuario or not clave:
            self.error.configure(text="Ingrese su usuario y contraseña.")
            return
        self.boton_ingresar.configure(state="disabled", text="Validando...")
        self.update_idletasks()
        try:
            sesion = iniciar_sesion(usuario, clave)
        except (ErrorAutenticacion, ErrorBaseDatos) as exc:
            self.error.configure(text=str(exc))
            self.boton_ingresar.configure(state="normal", text="Iniciar sesión")
            self.campo_clave.establecer("")
            self.campo_clave.enfocar()
            return
        except Exception as exc:  # pragma: no cover - protección de la interfaz
            self.error.configure(text=f"Error inesperado: {exc}")
            self.boton_ingresar.configure(state="normal", text="Iniciar sesión")
            return
        self.al_ingresar(sesion)
