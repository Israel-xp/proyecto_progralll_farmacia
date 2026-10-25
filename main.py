import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from sqlalchemy import func
import google.generativeai as genai

# Importamos tu base de datos y modelos intactos
from database import SessionLocal, Medicamento, Lote, Venta, DetalleVenta

app = Flask(__name__)
# CORS permite que tu index.html se conecte sin bloqueos de seguridad del navegador
CORS(app)

# ==========================================
# CONFIGURACIÓN DE LA INTELIGENCIA ARTIFICIAL
# ==========================================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ==========================================
# 1. RUTA PRINCIPAL (SIRVE EL HTML AL NAVEGADOR)
# ==========================================
@app.route("/", methods=["GET"])
def inicio():
    # Corregido: apunta a la carpeta frontend_web donde realmente está tu archivo
    ruta_html = os.path.join(os.path.dirname(__file__), "..", "frontend_web", "index.html")
    return send_file(ruta_html)

# ==========================================
# 2. RUTA DEL ASISTENTE IA (SÍNTOMAS -> RECOMENDACIÓN)
# ==========================================
@app.route("/api/ia/consultar", methods=["POST"])
def asistente_ia():
    try:
        req = request.json
        sintoma = req.get("sintoma")

        if not sintoma:
            return jsonify({"detail": "Por favor, ingresa un síntoma."}), 400

        # Utilizamos el modelo actualizado exigido por la API
        modelo = genai.GenerativeModel('gemini-3.8-flash')
        prompt = f"Actúa como un farmacéutico profesional y amable de El Salvador. Un paciente te dice que tiene este síntoma: '{sintoma}'. En un solo párrafo corto de 2 a 3 líneas, recomiéndale qué categoría de medicamentos de venta libre buscar en la farmacia (ej. analgésicos, antigripales) y recuérdale brevemente que consulte a un médico."

        respuesta = modelo.generate_content(prompt)
        return jsonify({"respuesta": respuesta.text})
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

# ==========================================
# 3. RUTAS DE INVENTARIO Y VENTAS
# ==========================================
@app.route("/api/medicamentos/buscar/<codigo>", methods=["GET"])
def buscar_medicamento(codigo):
    db = SessionLocal()
    try:
        med = db.query(Medicamento).filter(Medicamento.codigo_barras == codigo).first()
        if not med:
            return jsonify({"detail": "Medicamento no encontrado en el sistema"}), 404

        stock_total = db.query(func.sum(Lote.stock)).filter(Lote.medicamento_id == med.id).scalar() or 0
        lote_proximo = db.query(Lote).filter(Lote.medicamento_id == med.id, Lote.stock > 0).order_by(Lote.fecha_vencimiento.asc()).first()
        lote_str = lote_proximo.codigo_lote if lote_proximo else "Sin Lotes"
        fecha_venc_str = lote_proximo.fecha_vencimiento.strftime("%Y-%m-%d") if lote_proximo else "N/A"

        return jsonify({
            "id": med.id, "codigo_barras": med.codigo_barras, "nombre": med.nombre,
            "categoria": med.categoria, "laboratorio": med.laboratorio,
            "requiere_receta": med.requiere_receta, "precio": float(med.precio),
            "lote": lote_str, "fecha_vencimiento": fecha_venc_str, "stock": float(stock_total)
        })
    finally:
        db.close()

@app.route("/api/catalogo", methods=["GET"])
def obtener_catalogo():
    db = SessionLocal()
    try:
        medicamentos = db.query(Medicamento).all()
        catalogo = []
        for med in medicamentos:
            stock_total = db.query(func.sum(Lote.stock)).filter(Lote.medicamento_id == med.id).scalar() or 0
            catalogo.append({
                "id": med.id, "nombre": med.nombre, "categoria": med.categoria or "General",
                "laboratorio": med.laboratorio or "N/A", "precio": float(med.precio),
                "requiere_receta": med.requiere_receta,
                "imagen_url": med.imagen_url or "https://via.placeholder.com/150?text=Farmacia+San+Benito",
                "stock": float(stock_total)
            })
        return jsonify(catalogo)
    finally:
        db.close()

@app.route("/api/medicamentos/crear", methods=["POST"])
def crear_medicamento():
    db = SessionLocal()
    try:
        req = request.json
        existe = db.query(Medicamento).filter(Medicamento.codigo_barras == req.get("codigo_barras")).first()
        if existe:
            return jsonify({"detail": "Ese código de barras ya está registrado."}), 400

        nuevo_med = Medicamento(
            codigo_barras=req.get("codigo_barras"), nombre=req.get("nombre"),
            precio=req.get("precio"), requiere_receta=req.get("requiere_receta"),
            categoria=req.get("categoria"), laboratorio=req.get("laboratorio"),
            imagen_url=req.get("imagen_url"), ubicacion_fisica="Bodega Central"
        )
        db.add(nuevo_med)
        db.flush()

        nuevo_lote = Lote(
            medicamento_id=nuevo_med.id, codigo_lote=req.get("lote"),
            stock=req.get("cantidad"), fecha_vencimiento=req.get("fecha_vencimiento")
        )
        db.add(nuevo_lote)
        db.commit()
        return jsonify({"mensaje": "Producto guardado exitosamente"})
    except Exception as e:
        db.rollback()
        return jsonify({"detail": str(e)}), 500
    finally:
        db.close()

@app.route("/api/ventas/procesar", methods=["POST"])
def procesar_venta():
    db = SessionLocal()
    try:
        req = request.json
        id_med = req.get("id_medicamento")
        cant = req.get("cantidad")
        num_col = req.get("num_colegiado_medico")

        med = db.query(Medicamento).filter(Medicamento.id == id_med).first()
        if not med:
            return jsonify({"detail": "Medicamento no encontrado"}), 404

        if med.requiere_receta == 0 and (not num_col or str(num_col).strip() == ""):
            return jsonify({"detail": "⚠️ Venta denegada: Este medicamento es controlado. Ingrese el N° de Colegiado Médico."}), 400

        stock_total = db.query(func.sum(Lote.stock)).filter(Lote.medicamento_id == med.id).scalar() or 0
        if stock_total < cant:
            return jsonify({"detail": "Stock insuficiente en el inventario general."}), 400

        lotes_disponibles = db.query(Lote).filter(Lote.medicamento_id == med.id, Lote.stock > 0).order_by(Lote.fecha_vencimiento.asc()).all()

        cantidad_restante = cant
        total_a_pagar = med.precio * cant

        nueva_venta = Venta(total_pagado=total_a_pagar, num_colegiado_medico=num_col)
        db.add(nueva_venta)
        db.flush()

        for lote in lotes_disponibles:
            if cantidad_restante <= 0: break
            if lote.stock >= cantidad_restante:
                descuento = cantidad_restante
                lote.stock -= cantidad_restante
                cantidad_restante = 0
            else:
                descuento = lote.stock
                cantidad_restante -= lote.stock
                lote.stock = 0

            detalle = DetalleVenta(
                venta_id=nueva_venta.id, lote_id=lote.id,
                cantidad=descuento, precio_unitario=med.precio,
                subtotal=descuento * med.precio
            )
            db.add(detalle)

        db.commit()
        return jsonify({
            "estatus": "Venta procesada con FEFO exitosamente",
            "producto": med.nombre, "cantidad": cant, "precio_unitario": float(med.precio),
            "total_pagado": float(total_a_pagar), "stock_restante": float(stock_total - cant),
            "colegiado_medico": num_col if med.requiere_receta == 0 else "N/A"
        })
    except Exception as e:
        db.rollback()
        return jsonify({"detail": str(e)}), 500
    finally:
        db.close()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)