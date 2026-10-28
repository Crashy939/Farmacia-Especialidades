-- Datos iniciales del sistema Farmacia Especialidades.
USE FARMACIA_ESPECIALIDADES;

INSERT IGNORE INTO roles (id, nombre, descripcion) VALUES
    (1, 'Administrador', 'Control total del sistema, usuarios, almacén y compras.'),
    (2, 'Gerente', 'Administra clientes y ventas, autoriza cancelaciones.'),
    (3, 'Cajero', 'Registra ventas y consulta información.');

-- Contraseñas de demostración:
--   admin   / Admin123!
--   gerente / Gerente123!
--   cajero  / Cajero123!
INSERT IGNORE INTO usuarios (id, nombre_completo, usuario, clave_hash, rol_id, activo) VALUES
    (1, 'Administrador General', 'admin',
     '$2b$12$guTm62JWsRWJph9SrY/2U.MKk/yUSpjj5IYzHIbe2xtovcURJwwh.', 1, 1),
    (2, 'Gerente de Farmacia', 'gerente',
     '$2b$12$ufqLNJolCxLwZTIs6lhVfOtgFoeH2PkflnA0LJW09k6V.I5c6Pomq', 2, 1),
    (3, 'Cajero de Mostrador', 'cajero',
     '$2b$12$bNKm2UdNHEDLDLl7/9rsnuXf5mTX5QbV3D3M.XfVWNBwvsnFmKTg2', 3, 1);

INSERT IGNORE INTO categorias (id, nombre, descripcion) VALUES
    (1, 'Analgésicos', 'Medicamentos para el dolor y la fiebre.'),
    (2, 'Antibióticos', 'Medicamentos para infecciones bacterianas.'),
    (3, 'Antiinflamatorios', 'Control de inflamación y dolor.'),
    (4, 'Vitaminas y suplementos', 'Apoyo nutricional y defensas.'),
    (5, 'Dermatología', 'Cuidado de la piel y protectores solares.'),
    (6, 'Cuidado personal', 'Higiene y bienestar diario.');

INSERT IGNORE INTO proveedores (id, nombre, contacto, telefono, email, direccion) VALUES
    (1, 'Distribuidora FarmaVida', 'Laura Méndez', '2222-1100', 'ventas@farmavida.com', 'Av. Central #120'),
    (2, 'Laboratorios San Rafael', 'Carlos Ortiz', '2222-2200', 'pedidos@sanrafael.com', 'Calle Salud #45'),
    (3, 'Insumos Médicos del Norte', 'Ana Rivas', '2222-3300', 'contacto@imdnorte.com', 'Blvd. Norte #890');

INSERT IGNORE INTO clientes
    (id, codigo, nombre, apellido, telefono, email, direccion, puntos, puntos_historicos, activo) VALUES
    (1, 'CLI-0001', 'María', 'López', '7777-1001', 'maria.lopez@correo.com', 'Col. Escalón, Pasaje 4', 60, 110, 1),
    (2, 'CLI-0002', 'Carlos', 'Ramírez', '7777-1002', 'carlos.ramirez@correo.com', 'Col. San Benito, Calle 2', 15, 65, 1),
    (3, 'CLI-0003', 'Ana', 'Martínez', '7777-1003', 'ana.martinez@correo.com', 'Col. Layco, Av. 3', 0, 20, 1),
    (4, 'CLI-0004', 'José', 'Hernández', '7777-1004', 'jose.hernandez@correo.com', 'Col. Miramonte, #12', 5, 55, 1),
    (5, 'CLI-0005', 'Lucía', 'Gómez', '7777-1005', 'lucia.gomez@correo.com', 'Col. Modelo, Calle 5', 0, 0, 1),
    (6, 'CLI-0006', 'Pedro', 'Castro', '7777-1006', NULL, 'Col. Centro, #8', 0, 0, 0);

INSERT IGNORE INTO productos
    (id, codigo, nombre, descripcion, categoria_id, proveedor_id, precio_compra,
     precio_venta, existencia, stock_minimo, activo) VALUES
    (1, 'MED-001', 'Acetaminofén 500 mg', 'Caja con 20 tabletas', 1, 1, 1.20, 2.50, 120, 20, 1),
    (2, 'MED-002', 'Ibuprofeno 400 mg', 'Caja con 20 tabletas', 1, 1, 1.80, 3.75, 90, 15, 1),
    (3, 'MED-003', 'Amoxicilina 500 mg', 'Caja con 12 cápsulas', 2, 2, 4.50, 8.90, 45, 10, 1),
    (4, 'MED-004', 'Azitromicina 500 mg', 'Caja con 3 tabletas', 2, 2, 6.20, 11.50, 28, 8, 1),
    (5, 'MED-005', 'Diclofenaco 50 mg', 'Caja con 20 tabletas', 3, 1, 2.10, 4.20, 8, 10, 1),
    (6, 'MED-006', 'Naproxeno 250 mg', 'Caja con 20 tabletas', 3, 1, 2.40, 4.80, 60, 12, 1),
    (7, 'MED-007', 'Loratadina 10 mg', 'Caja con 10 tabletas', 1, 3, 1.10, 2.75, 75, 15, 1),
    (8, 'MED-008', 'Omeprazol 20 mg', 'Caja con 14 cápsulas', 1, 3, 2.80, 5.60, 55, 10, 1),
    (9, 'VIT-001', 'Vitamina C 1000 mg', 'Frasco con 60 tabletas', 4, 2, 7.50, 14.90, 40, 8, 1),
    (10, 'VIT-002', 'Multivitamínico adulto', 'Frasco con 30 cápsulas', 4, 2, 9.80, 18.50, 32, 6, 1),
    (11, 'VIT-003', 'Vitamina D3 2000 UI', 'Frasco con 60 cápsulas', 4, 2, 6.40, 12.75, 25, 6, 1),
    (12, 'DER-001', 'Protector solar SPF 50', 'Tubo 120 ml', 5, 3, 8.90, 16.95, 22, 5, 1),
    (13, 'DER-002', 'Crema hidratante facial', 'Pote 100 ml', 5, 3, 7.20, 13.80, 4, 6, 1),
    (14, 'CP-001', 'Alcohol etílico 70%', 'Frasco 500 ml', 6, 3, 1.60, 3.50, 85, 20, 1),
    (15, 'CP-002', 'Gel antibacterial 250 ml', 'Frasco con dosificador', 6, 3, 2.25, 4.95, 48, 10, 1),
    (16, 'MED-009', 'Suero oral sabor fresa', 'Sobre 500 ml', 1, 1, 0.95, 2.00, 0, 15, 1),
    (17, 'MED-010', 'Jarabe para la tos infantil', 'Frasco 120 ml', 1, 2, 3.40, 7.25, 18, 5, 1),
    (18, 'DER-003', 'Mascarilla facial de tela', 'Unidad reutilizable', 6, 3, 0.80, 2.25, 35, 10, 1);
