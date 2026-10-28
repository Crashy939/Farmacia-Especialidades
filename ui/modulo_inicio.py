"""Panel de inicio con indicadores y actividad reciente."""

import customtkinter as ctk

from configuracion import COLORES
from servicios.reportes import resumen_inicio
from ui.componentes import (TablaDatos, boton, formato_dinero, fuente,
                            mostrar_error, texto_estado)


class TarjetaIndicador(ctk.CTkFrame):
    def __init__(self, master, titulo, valor, detalle, color, icono="◈"):
        super().__init__(master, fg_color=COLORES["panel"], corner_radius=12,
                         border_width=1, border_color=COLORES["borde"])
        self.grid_columnconfigure(1, weight=1)
        caja = ctk.CTkFrame(self, width=44, height=44, corner_radius=11, fg_color=color)
        caja.grid(row=0, column=0, rowspan=3, padx=(16, 12), pady=16)
        caja.grid_propagate(False)
        ctk.CTkLabel(caja, text=icono, font=fuente(20, True),
                     text_color=COLORES["texto_oscuro"]).place(relx=0.5, rely=0.5,
                                                               anchor="center")
        ctk.CTkLabel(self, text=titulo, font=fuente(11, True),
                     text_color=COLORES["texto_suave"], anchor="w").grid(
            row=0, column=1, sticky="w", pady=(14, 0)
        )
        ctk.CTkLabel(self, text=valor, font=fuente(22, True),
                     text_color=COLORES["texto"], anchor="w").grid(
            row=1, column=1, sticky="w"
        )
        ctk.CTkLabel(self, text=detalle, font=fuente(10),
                     text_color=color, anchor="w").grid(
            row=2, column=1, sticky="w", pady=(0, 12)
        )


class PanelInicio(ctk.CTkFrame):
    TITULO = "Inicio"
    SUBTITULO = "Resumen general de la farmacia."

    def __init__(self, master, sesion, **kwargs):
        super().__init__(master, fg_color=COLORES["fondo"], corner_radius=0)
        self.sesion = sesion
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._construir_encabezado()
        self._construir_indicadores()
        self._construir_detalle()
        self.after(120, self._recargar)

    def _construir_encabezado(self):
        bienvenida = ctk.CTkFrame(self, fg_color=COLORES["panel"], corner_radius=14,
                                  border_width=1, border_color=COLORES["borde"])
        bienvenida.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        bienvenida.grid_columnconfigure(0, weight=1)

        mensajes = {
            "Administrador": "Tiene acceso total a usuarios, almacén, compras, clientes y ventas.",
            "Gerente": "Puede administrar clientes y ventas, y autorizar operaciones del cajero.",
            "Cajero": "Registre ventas, busque clientes y consulte sus operaciones del día.",
        }
        saludo = self._saludo()
        ctk.CTkLabel(
            bienvenida, text=f"{saludo}, {self.sesion.nombre_completo.split()[0]}.",
            font=fuente(20, True), text_color=COLORES["texto"], anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(18, 2))
        ctk.CTkLabel(
            bienvenida, text=mensajes.get(self.sesion.rol, ""),
            font=fuente(12), text_color=COLORES["texto_suave"], anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 18))

        boton(bienvenida, "Actualizar", self._recargar, tipo="secundario",
              ancho=110, alto=36).grid(row=0, column=1, rowspan=2, padx=20)

    @staticmethod
    def _saludo():
        from datetime import datetime
        hora = datetime.now().hour
        if hora < 12:
            return "Buenos días"
        if hora < 19:
            return "Buenas tardes"
        return "Buenas noches"

    def _construir_indicadores(self):
        self.marco_indicadores = ctk.CTkFrame(self, fg_color="transparent")
        self.marco_indicadores.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        for i in range(4):
            self.marco_indicadores.grid_columnconfigure(i, weight=1)

    def _construir_detalle(self):
        detalle = ctk.CTkFrame(self, fg_color="transparent")
        detalle.grid(row=2, column=0, sticky="nsew")
        detalle.grid_columnconfigure(0, weight=1)
        detalle.grid_columnconfigure(1, weight=1)
        detalle.grid_rowconfigure(0, weight=1)

        izquierda = ctk.CTkFrame(detalle, fg_color=COLORES["panel"], corner_radius=12,
                                 border_width=1, border_color=COLORES["borde"])
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        izquierda.grid_columnconfigure(0, weight=1)
        izquierda.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(izquierda, text="⚠  Productos con stock bajo",
                     font=fuente(14, True), text_color=COLORES["advertencia"],
                     anchor="w").grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))
        self.tabla_stock = TablaDatos(
            izquierda,
            [
                {"titulo": "Código", "clave": "codigo", "peso": 1},
                {"titulo": "Producto", "clave": "nombre", "peso": 2},
                {"titulo": "Stock", "clave": "existencia", "peso": 1, "alineacion": "center"},
                {"titulo": "Mínimo", "clave": "stock_minimo", "peso": 1, "alineacion": "center"},
            ],
            altura=260,
        )
        self.tabla_stock.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        derecha = ctk.CTkFrame(detalle, fg_color=COLORES["panel"], corner_radius=12,
                               border_width=1, border_color=COLORES["borde"])
        derecha.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        derecha.grid_columnconfigure(0, weight=1)
        derecha.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(derecha, text="▤  Ventas recientes", font=fuente(14, True),
                     text_color=COLORES["primario"], anchor="w").grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 8)
        )
        self.tabla_ventas = TablaDatos(
            derecha,
            [
                {"titulo": "Folio", "clave": "folio", "peso": 1},
                {"titulo": "Cliente", "clave": "cliente", "peso": 2},
                {"titulo": "Total", "clave": "total", "peso": 1,
                 "formato": formato_dinero, "alineacion": "e"},
                {"titulo": "Estado", "clave": "estado", "peso": 1,
                 "formato": texto_estado},
            ],
            altura=260,
        )
        self.tabla_ventas.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    # ------------------------------------------------------------------
    def _recargar(self):
        try:
            datos = resumen_inicio(self.sesion.id, solo_propias=self.sesion.es_cajero())
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self._actualizar_indicadores(datos)
        self.tabla_stock.cargar(datos["bajo_stock"])
        self.tabla_ventas.cargar(datos["recientes"])

    def _actualizar_indicadores(self, datos):
        for widget in self.marco_indicadores.winfo_children():
            widget.destroy()
        ventas = datos["ventas_hoy"] or {"cantidad": 0, "total": 0}
        productos = datos["productos"] or {}
        clientes = datos["clientes"] or {"total": 0}
        puntos = datos["puntos_hoy"] or {"total": 0}
        titulo_ventas = "Mis ventas de hoy" if self.sesion.es_cajero() else "Ventas de hoy"
        tarjetas = [
            ("◈", titulo_ventas, str(ventas["cantidad"]),
             f"{formato_dinero(ventas['total'])} facturado", COLORES["primario"]),
            ("☺", "Clientes activos", str(clientes["total"]),
             "Registrados en el programa de puntos", COLORES["info"]),
            ("▣", "Productos activos", str(productos.get("total", 0) or 0),
             f"{productos.get('bajo_stock', 0) or 0} con stock bajo", COLORES["advertencia"]),
            ("✦", "Puntos otorgados hoy", str(puntos["total"]),
             "1 punto por cada $100.00 de consumo", COLORES["exito"]),
        ]
        for i, (icono, titulo, valor, detalle, color) in enumerate(tarjetas):
            tarjeta = TarjetaIndicador(self.marco_indicadores, titulo, valor, detalle,
                                      color, icono)
            tarjeta.grid(row=0, column=i, sticky="nsew",
                         padx=(0 if i == 0 else 7, 0 if i == 3 else 7))
