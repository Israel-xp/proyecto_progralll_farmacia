import google.generativeai as genai

# Usamos tu clave exacta
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

try:
    print("Buscando modelos disponibles...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- Encontrado: {m.name}")
    
    print("\nProbando conexión con el modelo flash...")
    modelo = genai.GenerativeModel('gemini-1.5-flash')
    respuesta = modelo.generate_content("Hola, responde solo con la palabra 'Conectado'.")
    print("🤖 Respuesta de la IA:", respuesta.text)
except Exception as e:
    print("\n❌ Error detectado:", e)