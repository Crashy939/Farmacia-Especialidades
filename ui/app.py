"""Aplicación principal: alterna entre login y ventana de trabajo."""

import traceback

import customtkinter as ctk

from configuracion import (ALTO_MINIMO, ALTO_VENTANA, ANCHO_MINIMO, ANCHO_VENTANA,
                           COLORES, TITULO_APP)
from ui.componentes import confirmar, fuente, mostrar_error
from ui.login import MarcoLogin
from ui.ventana_principal import VentanaPrincipal


class Aplicacion(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=COLORES["fondo"])
        self.title(TITULO_APP)
        self.minsize(ANCHO_MINIMO, ALTO_MINIMO)
        self._centrar(ANCHO_VENTANA, ALTO_VENTANA)
        self.protocol("WM_DELETE_WINDOW", self._salir)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.contenedor = ctk.CTkFrame(self, fg_color=COLORES["fondo"], corner_radius=0)
        self.contenedor.grid(row=0, column=0, sticky="nsew")
        self.contenedor.grid_columnconfigure(0, weight=1)
        self.contenedor.grid_rowconfigure(0, weight=1)
        self.sesion = None
        self.mostrar_login()

    def _centrar(self, ancho, alto):
        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - ancho) // 2)
        y = max(0, (self.winfo_screenheight() - alto) // 2 - 10)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _limpiar(self):
        for widget in self.contenedor.winfo_children():
            widget.destroy()

    def mostrar_login(self):
        self._limpiar()
        self.sesion = None
        self.title(f"{TITULO_APP} · Iniciar sesión")
        marco = MarcoLogin(self.contenedor, self.iniciar_sesion)
        marco.grid(row=0, column=0, sticky="nsew")

    def iniciar_sesion(self, sesion):
        self.sesion = sesion
        self._limpiar()
        self.title(f"{TITULO_APP} · {sesion.rol}")
        ventana = VentanaPrincipal(self.contenedor, sesion, self.cerrar_sesion)
        ventana.grid(row=0, column=0, sticky="nsew")

    def cerrar_sesion(self):
        if self.sesion is None:
            self.mostrar_login()
            return
        if confirmar(
            self, "Cerrar sesión",
            f"¿Desea cerrar la sesión de {self.sesion.nombre_completo}?",
            texto_confirmar="Cerrar sesión", peligro=False,
        ):
            self.mostrar_login()

    def _salir(self):
        if self.sesion is None:
            self.destroy()
            return
        if confirmar(self, "Salir del sistema", "¿Desea cerrar la aplicación?",
                     texto_confirmar="Salir", peligro=True):
            self.destroy()

    def report_callback_exception(self, exc, valor, tb):
        traceback.print_exception(exc, valor, tb)
        try:
            mostrar_error(
                self, "Ocurrió un error inesperado en la interfaz.\n\n"
                      f"{exc.__name__}: {valor}\n\n"
                      "Si el problema continúa, revise la consola para más detalles.",
            )
        except Exception:
            pass
