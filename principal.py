#!/usr/bin/env python3
"""Punto de entrada del sistema Farmacia Especialidades."""

import sys


def main():
    try:
        import customtkinter as ctk
        import mysql.connector  # noqa: F401
        import bcrypt  # noqa: F401
    except ImportError as exc:
        print("Faltan dependencias para ejecutar la aplicación.")
        print(f"Detalle: {exc}")
        print("\nInstale las dependencias con:")
        print("  python3 -m venv .venv")
        print("  .venv/bin/pip install -r requirements.txt")
        return 1

    from configuracion import TITULO_APP
    from ui.app import Aplicacion

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")
    ctk.set_widget_scaling(1.0)
    ctk.set_window_scaling(1.0)

    app = Aplicacion()
    app.title(TITULO_APP)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
