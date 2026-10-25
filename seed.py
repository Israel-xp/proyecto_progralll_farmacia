from database import SessionLocal, Usuario, Medicamento, Lote
from datetime import datetime

def poblar_bd():
    db = SessionLocal()
    
    # 1. Crear Usuario Administrador (Tu nombre formal para la rúbrica)
    if not db.query(Usuario).first():
        admin = Usuario(username="Holman.Romero", password="password123", rol="Admin")
        db.add(admin)

    # 2. Crear Medicamentos
    if not db.query(Medicamento).first():
        med1 = Medicamento(codigo_barras="750101", nombre="Paracetamol 500mg (Caja c/20)", requiere_receta=False, precio=2.50)
        med2 = Medicamento(codigo_barras="750102", nombre="Amoxicilina 500mg (Caja c/12)", requiere_receta=True, precio=8.00)
        db.add_all([med1, med2])
        db.commit() # Guardar para generar los IDs

        # 3. Crear Lotes (Aquí preparamos el FEFO: Lotes con distintas caducidades)
        # Lotes de Paracetamol
        lote1_para = Lote(medicamento_id=med1.id, codigo_lote="L-PARA-01", fecha_vencimiento=datetime(2026, 11, 1), stock=20) # Vence primero
        lote2_para = Lote(medicamento_id=med1.id, codigo_lote="L-PARA-02", fecha_vencimiento=datetime(2027, 5, 1), stock=30)  # Vence después
        
        # Lotes de Amoxicilina
        lote1_amox = Lote(medicamento_id=med2.id, codigo_lote="L-AMOX-01", fecha_vencimiento=datetime(2026, 12, 15), stock=20)
        
        db.add_all([lote1_para, lote2_para, lote1_amox])
        db.commit()
        print("✅ Base de datos poblada exitosamente con medicamentos, lotes y el usuario Oscar Durán.")
    else:
        print("⚠️ La base de datos ya contiene información.")
        
    db.close()

if __name__ == "__main__":
    poblar_bd()