"""Configuración central del sistema Farmacia Especialidades."""

import os

# Conexión a MySQL / MariaDB de LAMPP.
# Todos los valores se pueden sobrescribir con variables de entorno.
CONFIG_BD = {
    "host": os.getenv("FARMACIA_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("FARMACIA_DB_PORT", "3306")),
    "user": os.getenv("FARMACIA_DB_USER", "root"),
    "password": os.getenv("FARMACIA_DB_PASSWORD", ""),
    "database": os.getenv("FARMACIA_DB_NAME", "FARMACIA_ESPECIALIDADES"),
    "charset": "utf8mb4",
    "use_pure": True,
    "connection_timeout": 6,
    "autocommit": False,
}

NOMBRE_BD = CONFIG_BD["database"]
TITULO_APP = "Farmacia Especialidades"
SUBTITULO_APP = "Sistema de administración farmacéutica"

# Paleta visual (tema oscuro).
COLORES = {
    "fondo": "#0D1719",
    "panel": "#132225",
    "panel_alt": "#192C30",
    "panel_hover": "#1E353A",
    "borde": "#274247",
    "primario": "#18A88F",
    "primario_hover": "#21C4A8",
    "primario_oscuro": "#0D7A68",
    "acento": "#F2B544",
    "texto": "#EAF4F2",
    "texto_suave": "#9DB5B1",
    "texto_oscuro": "#06201C",
    "exito": "#2ECC8F",
    "peligro": "#E05C5C",
    "peligro_hover": "#F07171",
    "advertencia": "#F2B544",
    "info": "#4CA6E8",
    "seleccion": "#1D4A47",
    "blanco": "#FFFFFF",
}

FUENTE = "DejaVu Sans"
ANCHO_VENTANA = 1360
ALTO_VENTANA = 840
ANCHO_MINIMO = 1120
ALTO_MINIMO = 700

# Reglas de negocio.
UMBRAL_DESCUENTO_VOLUMEN = 500.00
PORCENTAJE_DESCUENTO_VOLUMEN = 0.10
PUNTOS_PARA_CANJE = 50
PORCENTAJE_DESCUENTO_PUNTOS = 0.50
PESOS_POR_PUNTO = 100
LONGITUD_MINIMA_CLAVE = 8
