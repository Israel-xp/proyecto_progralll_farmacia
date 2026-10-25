from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

# Conexión directa a tu base de datos en XAMPP
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:@localhost/farmacia_sanbenito"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    password = Column(String(100))
    rol = Column(String(20))

class Medicamento(Base):
    __tablename__ = "medicamentos"
    id = Column(Integer, primary_key=True, index=True)
    codigo_barras = Column(String(50), unique=True, index=True)
    nombre = Column(String(100))
    requiere_receta = Column(Boolean, default=False)
    precio = Column(Float)
    
    # Nuevas columnas para el inventario expandido
    categoria = Column(String(100), nullable=True)
    laboratorio = Column(String(100), nullable=True)
    ubicacion_fisica = Column(String(100), nullable=True)
    imagen_url = Column(String(255), nullable=True)

class Lote(Base):
    __tablename__ = "lotes"
    id = Column(Integer, primary_key=True, index=True)
    medicamento_id = Column(Integer, ForeignKey("medicamentos.id"))
    codigo_lote = Column(String(50))
    stock = Column(Integer)
    fecha_vencimiento = Column(Date)

class Venta(Base):
    __tablename__ = "ventas"
    id = Column(Integer, primary_key=True, index=True)
    total_pagado = Column(Float)
    num_colegiado_medico = Column(String(50), nullable=True)

class DetalleVenta(Base):
    __tablename__ = "detalles_venta"
    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"))
    lote_id = Column(Integer, ForeignKey("lotes.id"))
    cantidad = Column(Integer)
    precio_unitario = Column(Float)
    subtotal = Column(Float)

Base.metadata.create_all(bind=engine)