"""Ventana de trabajo con barra lateral y navegación según el rol."""

import customtkinter as ctk

from configuracion import COLORES, TITULO_APP
from ui.componentes import boton, fuente
from utilidades import fecha_larga


class VentanaPrincipal(ctk.CTkFrame):
    def __init__(self, master, sesion, al_cerrar_sesion):
        super().__init__(master, fg_color=COLORES["fondo"], corner_radius=0)
        self.sesion = sesion
        self.al_cerrar_sesion = al_cerrar_sesion
        self.botones_nav = {}
        self.modulo_actual = None
        self.clave_actual = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._construir_barra_lateral()
        self._construir_contenido()
        self.after(80, lambda: self.mostrar_modulo("inicio"))

    # ------------------------------------------------------------------
    def _construir_barra_lateral(self):
        barra = ctk.CTkFrame(self, fg_color=COLORES["panel"], corner_radius=0, width=248)
        barra.grid(row=0, column=0, sticky="nsew")
        barra.grid_propagate(False)
        barra.grid_columnconfigure(0, weight=1)
        barra.grid_rowconfigure(2, weight=1)

        marca = ctk.CTkFrame(barra, fg_color="transparent")
        marca.grid(row=0, column=0, sticky="ew", padx=22, pady=(26, 22))
        marca.grid_columnconfigure(1, weight=1)
        logo = ctk.CTkFrame(marca, width=44, height=44, corner_radius=12,
                            fg_color=COLORES["primario"])
        logo.grid(row=0, column=0, rowspan=2, padx=(0, 12))
        logo.grid_propagate(False)
        ctk.CTkLabel(logo, text="✚", font=fuente(24, True),
                     text_color=COLORES["texto_oscuro"]).place(relx=0.5, rely=0.5,
                                                               anchor="center")
        ctk.CTkLabel(marca, text="Farmacia", font=fuente(17, True),
                     text_color=COLORES["texto"], anchor="w").grid(
            row=0, column=1, sticky="w"
        )
        ctk.CTkLabel(marca, text="Especialidades", font=fuente(11),
                     text_color=COLORES["primario"], anchor="w").grid(
            row=1, column=1, sticky="w"
        )

        ctk.CTkLabel(
            barra, text="MENÚ PRINCIPAL", font=fuente(10, True),
            text_color=COLORES["texto_suave"], anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=26, pady=(0, 8))

        navegacion = ctk.CTkFrame(barra, fg_color="transparent")
        navegacion.grid(row=2, column=0, sticky="new", padx=14)
        navegacion.grid_columnconfigure(0, weight=1)

        definicion = self._menu_para_rol()
        for indice, (clave, etiqueta, extra) in enumerate(definicion):
            boton_nav = ctk.CTkButton(
                navegacion, text=etiqueta, anchor="w", height=42, corner_radius=9,
                fg_color="transparent", hover_color=COLORES["panel_alt"],
                text_color=COLORES["texto_suave"], font=fuente(13, True),
                command=lambda c=clave, e=extra: self.mostrar_modulo(c, **e),
            )
            boton_nav.grid(row=indice, column=0, sticky="ew", pady=2)
            self.botones_nav[clave] = boton_nav

        pie = ctk.CTkFrame(barra, fg_color="transparent")
        pie.grid(row=3, column=0, sticky="ew", padx=18, pady=(10, 18))
        pie.grid_columnconfigure(0, weight=1)

        tarjeta_usuario = ctk.CTkFrame(pie, fg_color=COLORES["panel_alt"],
                                       corner_radius=10, border_width=1,
                                       border_color=COLORES["borde"])
        tarjeta_usuario.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        tarjeta_usuario.grid_columnconfigure(1, weight=1)

        iniciales = "".join(
            parte[0] for parte in self.sesion.nombre_completo.split()[:2]
        ).upper() or "U"
        avatar = ctk.CTkFrame(tarjeta_usuario, width=38, height=38, corner_radius=19,
                              fg_color=COLORES["primario_oscuro"])
        avatar.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        avatar.grid_propagate(False)
        ctk.CTkLabel(avatar, text=iniciales, font=fuente(13, True),
                     text_color=COLORES["texto"]).place(relx=0.5, rely=0.5,
                                                       anchor="center")
        ctk.CTkLabel(tarjeta_usuario, text=self.sesion.nombre_completo,
                     font=fuente(11, True), text_color=COLORES["texto"],
                     anchor="w", wraplength=130).grid(row=0, column=1, sticky="w",
                                                      pady=(9, 0))
        ctk.CTkLabel(tarjeta_usuario, text=self.sesion.rol, font=fuente(10),
                     text_color=COLORES["primario"], anchor="w").grid(
            row=1, column=1, sticky="w", pady=(0, 9)
        )

        boton(pie, "Cerrar sesión", self.al_cerrar_sesion, tipo="fantasma",
              ancho=210, alto=36).grid(row=1, column=0, sticky="ew")
        ctk.CTkLabel(pie, text="v1.0 · LAMPP / MySQL", font=fuente(9),
                     text_color=COLORES["texto_suave"]).grid(row=2, column=0,
                                                             pady=(10, 0))

    def _menu_para_rol(self):
        if self.sesion.es_admin():
            return [
                ("inicio", "◉   Inicio", {}),
                ("usuarios", "◈   Usuarios", {}),
                ("almacen", "▣   Almacén", {}),
                ("compras", "⇄   Compras", {}),
                ("clientes", "☺   Clientes", {}),
                ("ventas", "▤   Ventas", {}),
            ]
        if self.sesion.es_gerente():
            return [
                ("inicio", "◉   Inicio", {}),
                ("clientes", "☺   Clientes", {}),
                ("ventas", "▤   Ventas", {}),
            ]
        return [
            ("inicio", "◉   Inicio", {}),
            ("pos", "▤   Punto de venta", {"abrir_nueva": True}),
            ("ventas", "⌕   Consultar ventas", {"abrir_nueva": False}),
        ]

    # ------------------------------------------------------------------
    def _construir_contenido(self):
        contenido = ctk.CTkFrame(self, fg_color=COLORES["fondo"], corner_radius=0)
        contenido.grid(row=0, column=1, sticky="nsew")
        contenido.grid_columnconfigure(0, weight=1)
        contenido.grid_rowconfigure(2, weight=1)

        cabecera = ctk.CTkFrame(contenido, fg_color="transparent", height=88)
        cabecera.grid(row=0, column=0, sticky="ew", padx=30, pady=(22, 8))
        cabecera.grid_columnconfigure(0, weight=1)
        cabecera.grid_propagate(False)

        self.titulo = ctk.CTkLabel(cabecera, text="Inicio", font=fuente(26, True),
                                   text_color=COLORES["texto"], anchor="w")
        self.titulo.grid(row=0, column=0, sticky="w")
        self.subtitulo = ctk.CTkLabel(
            cabecera, text="Resumen general del sistema", font=fuente(12),
            text_color=COLORES["texto_suave"], anchor="w",
        )
        self.subtitulo.grid(row=1, column=0, sticky="w", pady=(3, 0))

        info = ctk.CTkFrame(cabecera, fg_color="transparent")
        info.grid(row=0, column=1, rowspan=2, sticky="e")
        ctk.CTkLabel(info, text=fecha_larga(),
                     font=fuente(11), text_color=COLORES["texto_suave"]).grid(
            row=0, column=0, sticky="e"
        )
        ctk.CTkLabel(info, text=f"Sesión: {self.sesion.usuario}  ·  {self.sesion.rol}",
                     font=fuente(11, True), text_color=COLORES["primario"]).grid(
            row=1, column=0, sticky="e", pady=(2, 0)
        )

        ctk.CTkFrame(contenido, height=1, fg_color=COLORES["borde"]).grid(
            row=1, column=0, sticky="ew", padx=30
        )

        self.cuerpo = ctk.CTkFrame(contenido, fg_color="transparent")
        self.cuerpo.grid(row=2, column=0, sticky="nsew", padx=30, pady=(18, 24))
        self.cuerpo.grid_columnconfigure(0, weight=1)
        self.cuerpo.grid_rowconfigure(0, weight=1)

    # ------------------------------------------------------------------
    def mostrar_modulo(self, clave, **kwargs):
        from ui.modulo_almacen import ModuloAlmacen
        from ui.modulo_clientes import ModuloClientes
        from ui.modulo_compras import ModuloCompras
        from ui.modulo_inicio import PanelInicio
        from ui.modulo_usuarios import ModuloUsuarios
        from ui.modulo_ventas import ModuloVentas

        clases = {
            "inicio": PanelInicio,
            "usuarios": ModuloUsuarios,
            "almacen": ModuloAlmacen,
            "compras": ModuloCompras,
            "clientes": ModuloClientes,
            "ventas": ModuloVentas,
            "pos": ModuloVentas,
        }
        clase = clases.get(clave, PanelInicio)
        self._marcar_nav(clave)

        for widget in self.cuerpo.winfo_children():
            widget.destroy()

        self.clave_actual = clave
        if clave == "pos":
            kwargs["abrir_nueva"] = True
        modulo = clase(self.cuerpo, self.sesion, **kwargs)
        modulo.grid(row=0, column=0, sticky="nsew")
        self.modulo_actual = modulo
        self.titulo.configure(text=getattr(modulo, "TITULO", "Inicio"))
        self.subtitulo.configure(text=getattr(modulo, "SUBTITULO", ""))

    def _marcar_nav(self, clave):
        for nombre, widget in self.botones_nav.items():
            if nombre == clave:
                widget.configure(fg_color=COLORES["panel_alt"],
                                 text_color=COLORES["primario"])
            else:
                widget.configure(fg_color="transparent",
                                 text_color=COLORES["texto_suave"])
