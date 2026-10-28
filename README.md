# Farmacia Especialidades

Sistema de administración farmacéutica de escritorio desarrollado en **Python** con
**CustomTkinter** y **MySQL/MariaDB (LAMPP)** para la materia de Ingeniería de
Software.

El sistema permite administrar usuarios, almacén, compras a proveedores, clientes y
ventas, aplicando reglas de negocio de descuentos y un programa de puntos.

---

## 1. Funcionalidades

### Por rol

| Módulo | Administrador | Gerente | Cajero |
|---|:---:|:---:|:---:|
| Inicio / panel | ✔ | ✔ | ✔ |
| Usuarios (crear, editar, cancelar) | ✔ | — | — |
| Almacén y categorías | ✔ | — | — |
| Compras y proveedores | ✔ | — | — |
| Clientes | ✔ | ✔ | Buscar y registrar |
| Ventas | ✔ | ✔ | Registrar y consultar |
| Modificar / cancelar venta | ✔ | ✔ | Requiere autorización |

### Reglas de venta

- El cajero debe seleccionar o registrar un cliente antes de cobrar.
- Solo se pueden vender productos activos y con existencia disponible.
- La cantidad solicitada no puede superar el stock.
- El monto recibido debe ser mayor o igual al total a pagar.
- **Descuento por volumen:** 10 % cuando el subtotal supera los **$500.00**.
- **Programa de puntos:** se gana **1 punto por cada $100.00** pagados.
- **Canje:** con **50 puntos** se aplica **50 % de descuento** sobre el subtotal
  después del descuento por volumen. Los puntos se descuentan del saldo del cliente.
- Los puntos se calculan sobre el **total final pagado**.
- El cajero puede quitar productos del carrito antes de cobrar sin autorización.
- Para **modificar o cancelar** una venta ya completada, el cajero necesita las
  credenciales de un gerente o administrador.
- Al cancelar una venta se devuelven las existencias y se revierten los puntos.

### Inventario y compras

- El administrador registra compras a proveedores; al guardar, el inventario se
  incrementa automáticamente.
- Al modificar o cancelar una compra se ajusta el inventario y se registra el
  movimiento en la bitácora de auditoría.
- El catálogo de productos incluye precio de compra, precio de venta, existencia,
  stock mínimo y alertas de stock bajo.
- Las bajas son lógicas (`activo = 0`), por lo que se conserva el historial.

---

## 2. Requisitos

- Linux (probado en Ubuntu), Windows o macOS.
- Python **3.10 o superior** con Tkinter.
- **LAMPP** instalado en `/opt/lampp` con el servicio MySQL/MariaDB disponible.
- Dependencias de Python del archivo `requirements.txt`.

En Ubuntu, si Tkinter no está instalado:

```bash
sudo apt install python3-tk python3-venv
```

---

## 3. Instalación paso a paso

### 3.1 Iniciar MySQL de LAMPP

```bash
sudo /opt/lampp/lampp startmysql
# o bien, para iniciar Apache y MySQL:
sudo /opt/lampp/lampp start
```

Verificar que el puerto 3306 esté escuchando:

```bash
ss -ltn | grep 3306
```

### 3.2 Crear el entorno virtual e instalar dependencias

Desde la carpeta del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3.3 Crear la base de datos y cargar los datos de demostración

```bash
python scripts/instalar_bd.py
```

Para eliminar y recrear la base de datos desde cero:

```bash
python scripts/instalar_bd.py --reiniciar
```

El instalador usa por defecto:

| Parámetro | Valor |
|---|---|
| Host | `127.0.0.1` |
| Puerto | `3306` |
| Usuario | `root` |
| Contraseña | vacía (valor habitual de LAMPP) |
| Base de datos | `FARMACIA_ESPECIALIDADES` |

Si su instalación de MySQL tiene contraseña u otro usuario, configure las variables
de entorno antes de ejecutar:

```bash
export FARMACIA_DB_USER=root
export FARMACIA_DB_PASSWORD=su_contraseña
export FARMACIA_DB_HOST=127.0.0.1
export FARMACIA_DB_PORT=3306
python scripts/instalar_bd.py
```

### 3.4 Ejecutar la aplicación

```bash
python principal.py
```

También puede ejecutarse con el Python del entorno virtual directamente:

```bash
.venv/bin/python principal.py
```

---

## 4. Credenciales de demostración

| Rol | Usuario | Contraseña |
|---|---|---|
| Administrador | `admin` | `Admin123!` |
| Gerente | `gerente` | `Gerente123!` |
| Cajero | `cajero` | `Cajero123!` |

> Las contraseñas se almacenan con hash **bcrypt**; nunca en texto plano.

El cliente de prueba **CLI-0001 · María López** inicia con **60 puntos** para poder
probar el canje del 50 %.

---

## 5. Estructura del proyecto

```
.
├── principal.py                 # Punto de entrada
├── configuracion.py             # Conexión, colores y reglas de negocio
├── base_datos.py                # Conexiones y transacciones MySQL
├── autenticacion.py             # Login bcrypt, sesión, roles y permisos
├── utilidades.py                # Validaciones y formatos compartidos
├── sql/
│   ├── esquema.sql              # Tablas, llaves y restricciones
│   └── datos_iniciales.sql      # Roles, usuarios, productos y clientes demo
├── scripts/
│   └── instalar_bd.py           # Instalador / reinicio de la base de datos
├── servicios/
│   ├── usuarios.py              # CRUD de usuarios y roles
│   ├── clientes.py              # CRUD de clientes y puntos
│   ├── productos.py             # Productos, categorías y stock
│   ├── proveedores.py           # Catálogo de proveedores
│   ├── compras.py               # Compras y actualización de inventario
│   ├── ventas.py                # Ventas, descuentos, puntos y cancelaciones
│   ├── reportes.py              # Indicadores del panel de inicio
│   └── auditoria.py             # Bitácora de operaciones
└── ui/
    ├── app.py                   # Ventana raíz y cambio login/sesión
    ├── login.py                 # Pantalla de inicio de sesión
    ├── ventana_principal.py     # Barra lateral y navegación por rol
    ├── componentes.py           # Tablas, campos, modales y mensajes
    ├── modulo_inicio.py         # Panel con indicadores y actividad
    ├── modulo_usuarios.py       # Gestión de usuarios
    ├── modulo_almacen.py        # Productos y categorías
    ├── modulo_compras.py        # Compras y proveedores
    ├── modulo_clientes.py       # Clientes e historial de puntos
    └── modulo_ventas.py         # Punto de venta y control de ventas
```

---

## 6. Base de datos

Tablas principales:

- `roles`, `usuarios`
- `categorias`, `proveedores`, `productos`
- `clientes`, `movimientos_puntos`
- `compras`, `compra_detalle`
- `ventas`, `venta_detalle`
- `auditoria`

Todas las operaciones que afectan inventario, puntos o dinero se ejecutan dentro de
**transacciones** con bloqueo de filas (`SELECT ... FOR UPDATE`), para evitar
inconsistencias por operaciones simultáneas.

---

## 7. Solución de problemas

### “No se pudo conectar con MySQL/MariaDB”

1. Inicie el servicio:
   ```bash
   sudo /opt/lampp/lampp startmysql
   ```
2. Compruebe el puerto:
   ```bash
   ss -ltn | grep 3306
   ```
3. Revise usuario y contraseña en `configuracion.py` o con las variables de
   entorno `FARMACIA_DB_*`.
4. Verifique que la base exista:
   ```bash
   /opt/lampp/bin/mysql -u root -e "SHOW DATABASES;"
   ```

### La aplicación no abre en Linux

- Confirme que está en una sesión gráfica (X11 o Wayland con XWayland).
- Instale Tkinter: `sudo apt install python3-tk`.
- Ejecute desde una terminal para ver el detalle de cualquier error.

### Reiniciar los datos de demostración

```bash
python scripts/instalar_bd.py --reiniciar
```

Esto elimina todas las ventas, compras y movimientos creados durante las pruebas.

---

## 8. Notas académicas

- Proyecto desarrollado para el módulo de **Requerimientos de Software**.
- La prioridad fue el cumplimiento funcional de los requerimientos; la interfaz
  puede seguir evolucionando.
- El diseño aplica una paleta oscura, navegación por roles y componentes
  reutilizables para mantener consistencia entre módulos.
