-- =====================================================================
-- Sistema: Farmacia Especialidades
-- Base de datos: FARMACIA_ESPECIALIDADES  (MySQL / MariaDB - LAMPP)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS FARMACIA_ESPECIALIDADES
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE FARMACIA_ESPECIALIDADES;

CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(30) NOT NULL UNIQUE,
    descripcion VARCHAR(150)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_completo VARCHAR(120) NOT NULL,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    clave_hash VARCHAR(255) NOT NULL,
    rol_id INT NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    ultimo_acceso DATETIME NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_usuario_rol FOREIGN KEY (rol_id) REFERENCES roles (id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL UNIQUE,
    descripcion VARCHAR(200),
    activo TINYINT(1) NOT NULL DEFAULT 1
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS proveedores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL UNIQUE,
    contacto VARCHAR(120),
    telefono VARCHAR(30),
    email VARCHAR(120),
    direccion VARCHAR(200),
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(80) NOT NULL,
    apellido VARCHAR(80) NOT NULL,
    telefono VARCHAR(30),
    email VARCHAR(120),
    direccion VARCHAR(200),
    puntos INT NOT NULL DEFAULT 0,
    puntos_historicos INT NOT NULL DEFAULT 0,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_clientes_nombre (nombre, apellido),
    INDEX idx_clientes_telefono (telefono)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS productos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL UNIQUE,
    nombre VARCHAR(120) NOT NULL,
    descripcion VARCHAR(250),
    categoria_id INT NULL,
    proveedor_id INT NULL,
    precio_compra DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    precio_venta DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    existencia INT NOT NULL DEFAULT 0,
    stock_minimo INT NOT NULL DEFAULT 5,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_producto_categoria FOREIGN KEY (categoria_id) REFERENCES categorias (id)
        ON DELETE SET NULL,
    CONSTRAINT fk_producto_proveedor FOREIGN KEY (proveedor_id) REFERENCES proveedores (id)
        ON DELETE SET NULL,
    INDEX idx_productos_nombre (nombre),
    INDEX idx_productos_activo (activo)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS compras (
    id INT AUTO_INCREMENT PRIMARY KEY,
    folio VARCHAR(20) NOT NULL UNIQUE,
    proveedor_id INT NOT NULL,
    usuario_id INT NOT NULL,
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subtotal DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    total DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    estado ENUM('COMPLETADA', 'CANCELADA') NOT NULL DEFAULT 'COMPLETADA',
    observaciones VARCHAR(300),
    cancelada_en DATETIME NULL,
    cancelada_por INT NULL,
    motivo_cancelacion VARCHAR(300),
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_compra_proveedor FOREIGN KEY (proveedor_id) REFERENCES proveedores (id),
    CONSTRAINT fk_compra_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    CONSTRAINT fk_compra_cancela FOREIGN KEY (cancelada_por) REFERENCES usuarios (id),
    INDEX idx_compras_fecha (fecha),
    INDEX idx_compras_estado (estado)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS compra_detalle (
    id INT AUTO_INCREMENT PRIMARY KEY,
    compra_id INT NOT NULL,
    producto_id INT NOT NULL,
    cantidad INT NOT NULL,
    costo_unitario DECIMAL(12, 2) NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL,
    CONSTRAINT fk_compra_detalle_compra FOREIGN KEY (compra_id) REFERENCES compras (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_compra_detalle_producto FOREIGN KEY (producto_id) REFERENCES productos (id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS ventas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    folio VARCHAR(20) NOT NULL UNIQUE,
    cliente_id INT NOT NULL,
    usuario_id INT NOT NULL,
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subtotal DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    descuento_volumen DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    descuento_puntos DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    total DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    puntos_ganados INT NOT NULL DEFAULT 0,
    puntos_canjeados INT NOT NULL DEFAULT 0,
    metodo_pago ENUM('EFECTIVO', 'TARJETA', 'TRANSFERENCIA') NOT NULL DEFAULT 'EFECTIVO',
    monto_recibido DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    cambio DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    estado ENUM('COMPLETADA', 'CANCELADA') NOT NULL DEFAULT 'COMPLETADA',
    observaciones VARCHAR(300),
    cancelada_en DATETIME NULL,
    cancelada_por INT NULL,
    motivo_cancelacion VARCHAR(300),
    autorizado_por INT NULL,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_venta_cliente FOREIGN KEY (cliente_id) REFERENCES clientes (id),
    CONSTRAINT fk_venta_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    CONSTRAINT fk_venta_cancela FOREIGN KEY (cancelada_por) REFERENCES usuarios (id),
    CONSTRAINT fk_venta_autoriza FOREIGN KEY (autorizado_por) REFERENCES usuarios (id),
    INDEX idx_ventas_fecha (fecha),
    INDEX idx_ventas_estado (estado),
    INDEX idx_ventas_cliente (cliente_id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS venta_detalle (
    id INT AUTO_INCREMENT PRIMARY KEY,
    venta_id INT NOT NULL,
    producto_id INT NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(12, 2) NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL,
    CONSTRAINT fk_venta_detalle_venta FOREIGN KEY (venta_id) REFERENCES ventas (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_venta_detalle_producto FOREIGN KEY (producto_id) REFERENCES productos (id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS movimientos_puntos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT NOT NULL,
    venta_id INT NULL,
    usuario_id INT NULL,
    tipo ENUM('GANADO', 'CANJEADO', 'REVERSO', 'AJUSTE') NOT NULL,
    puntos INT NOT NULL,
    descripcion VARCHAR(250),
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_movimiento_cliente FOREIGN KEY (cliente_id) REFERENCES clientes (id),
    CONSTRAINT fk_movimiento_venta FOREIGN KEY (venta_id) REFERENCES ventas (id)
        ON DELETE SET NULL,
    CONSTRAINT fk_movimiento_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    INDEX idx_movimientos_cliente (cliente_id),
    INDEX idx_movimientos_fecha (fecha)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS auditoria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NULL,
    accion VARCHAR(60) NOT NULL,
    entidad VARCHAR(40) NOT NULL,
    entidad_id INT NULL,
    detalle VARCHAR(500),
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_auditoria_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    INDEX idx_auditoria_fecha (fecha)
) ENGINE = InnoDB;
