"""Módulo de administración de usuarios (solo Administrador)."""

import customtkinter as ctk

from configuracion import COLORES
from servicios.usuarios import usuarios_servicio
from ui.componentes import (BarraBusqueda, Campo, CampoCombo, ModalBase, TablaDatos,
                            boton, formato_fecha, fuente, mostrar_error,
                            mostrar_exito, texto_activo)

from utilidades import ErrorValidacion


class FormularioUsuario(ModalBase):
    def __init__(self, master, sesion, usuario=None):
        self.usuario = usuario
        titulo = "Editar usuario" if usuario else "Nuevo usuario"
        subtitulo = ("Actualice los datos de la cuenta." if usuario
                     else "Cree una cuenta y asigne un rol de acceso.")
        super().__init__(master, titulo, subtitulo, ancho=640, alto=580)
        self.sesion = sesion
        self.guardado = False

        contenedor = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=24, pady=20)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_columnconfigure(1, weight=1)

        self.nombre = Campo(contenedor, "Nombre completo", requerido=True,
                            placeholder="Ej. Ana María Rivera")
        self.nombre.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        self.usuario_campo = Campo(contenedor, "Nombre de usuario", requerido=True,
                                   placeholder="Ej. arivera")
        self.usuario_campo.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))

        self.rol = CampoCombo(contenedor, "Rol", ["Administrador", "Gerente", "Cajero"],
                             requerido=True)
        self.rol.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 12))

        self.clave = Campo(contenedor, "Contraseña", requerido=not usuario, show="•",
                           placeholder="Mínimo 8 caracteres")
        self.clave.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))

        self.confirmar = Campo(contenedor, "Confirmar contraseña", requerido=not usuario,
                               show="•", placeholder="Repita la contraseña")
        self.confirmar.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 12))

        self.activo = ctk.BooleanVar(value=True)
        self.switch = ctk.CTkSwitch(
            contenedor, text="Cuenta activa", variable=self.activo,
            font=fuente(12, True), text_color=COLORES["texto"],
            progress_color=COLORES["primario"], button_color=COLORES["blanco"],
            fg_color=COLORES["borde"],
        )
        self.switch.grid(row=3, column=0, sticky="w", pady=(4, 0))

        ctk.CTkLabel(
            contenedor,
            text="Los usuarios cancelados no pueden iniciar sesión. "
                 "Siempre debe existir al menos un administrador activo.",
            font=fuente(10), text_color=COLORES["texto_suave"], anchor="w",
            justify="left", wraplength=540,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(16, 0))

        self.error = ctk.CTkLabel(contenedor, text="", font=fuente(11),
                                  text_color=COLORES["peligro"], anchor="w",
                                  justify="left", wraplength=540)
        self.error.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.agregar_boton("Cancelar", self._cancelar, tipo="secundario", ancho=110)
        self.agregar_boton("Guardar usuario", self._guardar, tipo="primario", ancho=150)

        if usuario:
            self.nombre.establecer(usuario["nombre_completo"])
            self.usuario_campo.establecer(usuario["usuario"])
            self.rol.establecer(usuario["rol"])
            self.activo.set(bool(usuario["activo"]))
        self.after(120, self.nombre.enfocar)

    def _guardar(self):
        nombre = self.nombre.obtener()
        usuario = self.usuario_campo.obtener()
        rol = self.rol.obtener()
        clave = self.clave.obtener()
        confirmar = self.confirmar.obtener()
        if clave and clave != confirmar:
            self.error.configure(text="Las contraseñas no coinciden.")
            return
        if not self.usuario and (not clave or not confirmar):
            self.error.configure(text="Debe definir una contraseña para la nueva cuenta.")
            return
        try:
            if self.usuario:
                usuarios_servicio.actualizar(
                    self.usuario["id"], nombre, usuario, rol,
                    self.activo.get(), clave=clave or None,
                    ejecutor_id=self.sesion.id,
                )
            else:
                usuarios_servicio.crear(nombre, usuario, clave, rol,
                                        ejecutor_id=self.sesion.id)
            self.guardado = True
            self._cerrar()
        except ErrorValidacion as exc:
            self.error.configure(text=str(exc))
        except Exception as exc:
            self.error.configure(text=str(exc))


class ModuloUsuarios(ctk.CTkFrame):
    TITULO = "Usuarios"
    SUBTITULO = "Cuentas, roles y estados de acceso al sistema."

    def __init__(self, master, sesion, **kwargs):
        super().__init__(master, fg_color=COLORES["fondo"], corner_radius=0)
        self.sesion = sesion
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        if not sesion.puede("usuarios", "buscar"):
            ctk.CTkLabel(self, text="No tiene permisos para acceder a este módulo.",
                         font=fuente(16, True), text_color=COLORES["peligro"]).grid(
                row=0, column=0, pady=80
            )
            return

        self._construir_barra()
        self._construir_tabla()
        self.after(100, self.cargar)

    def _construir_barra(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        barra.grid_columnconfigure(1, weight=1)

        self.busqueda = BarraBusqueda(barra, self.cargar,
                                      "Buscar por nombre, usuario o rol...", ancho=300)
        self.busqueda.grid(row=0, column=0, sticky="w")

        self.incluir = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            barra, text="Incluir cancelados", variable=self.incluir,
            command=self.cargar, font=fuente(11), text_color=COLORES["texto_suave"],
            progress_color=COLORES["primario"], fg_color=COLORES["borde"],
        ).grid(row=0, column=1, padx=16, sticky="w")

        acciones = ctk.CTkFrame(barra, fg_color="transparent")
        acciones.grid(row=0, column=2, sticky="e")
        boton(acciones, "+ Nuevo", self._nuevo, tipo="primario", ancho=110).pack(
            side="left", padx=(0, 8)
        )
        boton(acciones, "Editar", self._editar, tipo="secundario", ancho=95).pack(
            side="left", padx=(0, 8)
        )
        boton(acciones, "Cancelar / Reactivar", self._cambiar_estado, tipo="peligro",
              ancho=155).pack(side="left")

    def _construir_tabla(self):
        self.tabla = TablaDatos(
            self,
            [
                {"titulo": "Nombre completo", "clave": "nombre_completo", "peso": 3},
                {"titulo": "Usuario", "clave": "usuario", "peso": 2},
                {"titulo": "Rol", "clave": "rol", "peso": 2},
                {"titulo": "Estado", "clave": "activo", "peso": 1,
                 "formato": texto_activo},
                {"titulo": "Último acceso", "clave": "ultimo_acceso", "peso": 2,
                 "formato": formato_fecha},
            ],
            on_doble_clic=lambda _fila: self._editar(),
        )
        self.tabla.grid(row=1, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    def cargar(self):
        try:
            filas = usuarios_servicio.listar(
                self.busqueda.texto(), self.incluir.get()
            )
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self.tabla.cargar(filas)

    def _nuevo(self):
        dialogo = FormularioUsuario(self, self.sesion)
        self.wait_window(dialogo)
        if dialogo.guardado:
            self.cargar()
            mostrar_exito(self, "El usuario se creó correctamente.")

    def _editar(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        usuario = usuarios_servicio.obtener(fila["id"])
        if not usuario:
            mostrar_error(self, "El usuario ya no existe.")
            self.cargar()
            return
        dialogo = FormularioUsuario(self, self.sesion, usuario)
        self.wait_window(dialogo)
        if dialogo.guardado:
            self.cargar()
            mostrar_exito(self, "Los datos del usuario se actualizaron.")

    def _cambiar_estado(self):
        fila = self.tabla.obtener_seleccion(master=self)
        if not fila:
            return
        activo = bool(fila["activo"])
        accion = "cancelar" if activo else "reactivar"
        if not self._confirmar_cambio(fila, accion):
            return
        try:
            usuarios_servicio.cambiar_estado(
                fila["id"], not activo, ejecutor_id=self.sesion.id,
                ejecutor_actual_id=self.sesion.id,
            )
        except Exception as exc:
            mostrar_error(self, exc)
            return
        self.cargar()
        mostrar_exito(
            self,
            f"El usuario '{fila['usuario']}' fue {'cancelado' if activo else 'reactivado'}.",
        )

    def _confirmar_cambio(self, fila, accion):
        from ui.componentes import confirmar
        return confirmar(
            self, f"{accion.capitalize()} usuario",
            f"¿Desea {accion} la cuenta de {fila['nombre_completo']} "
            f"({fila['usuario']})?",
            texto_confirmar=accion.capitalize(), peligro=accion == "cancelar",
        )
