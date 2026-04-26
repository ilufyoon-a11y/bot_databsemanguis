import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardRemove
import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from flask import Flask
from threading import Thread

# --- 1. DESPERTADOR ---
app_web = Flask('')
@app_web.route('/')
def home(): return "🥭 MANGO ON"

def keep_alive():
    t = Thread(target=lambda: app_web.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080))))
    t.daemon = True
    t.start()

# --- 2. CONEXIÓN (CON DIAGNÓSTICO) ---
sheet = None

def conectar_google():
    global sheet
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # ¿Existe el archivo?
        if not os.path.exists('credenciales.json'):
            print("🚨 ERROR: El archivo 'credenciales.json' NO ESTÁ en GitHub.")
            return
        
        creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
        client = gspread.authorize(creds)
        
        # Intentamos abrir con los nombres nuevos en minúsculas
        sheet = client.open("mango").worksheet("datos")
        print("✅ ¡CONECTADO CON ÉXITO!")
    except Exception as e:
        print(f"🚨 ERROR DETALLADO: {e}")
        sheet = None

# --- 3. LÓGICA (Simplificada para evitar errores) ---
PASOS = range(9)

async def start(u, c):
    await u.message.reply_text("✨ **Sistema MANGO**\nUsa `/nuevo` para registrar datos.")

async def nuevo(u, c):
    await u.message.reply_text("📧 Paso 1: Correo?")
    return 0

async def p2(u, c):
    c.user_data['1'] = u.message.text
    await u.message.reply_text("🔑 Paso 2: Clave?")
    return 1

async def p3(u, c):
    c.user_data['2'] = u.message.text
    await u.message.reply_text("🌐 Paso 3: IP?")
    return 2

async def p4(u, c):
    c.user_data['3'] = u.message.text
    await u.message.reply_text("🛡️ Paso 4: PRIV?")
    return 3

async def p5(u, c):
    c.user_data['4'] = u.message.text
    await u.message.reply_text("💻 Paso 5: Plataforma?")
    return 4

async def p6(u, c):
    c.user_data['5'] = u.message.text
    await u.message.reply_text("📊 Paso 6: Estado?")
    return 5

async def p7(u, c):
    c.user_data['6'] = u.message.text
    await u.message.reply_text("🔢 Paso 7: BIN?")
    return 6

async def p8(u, c):
    c.user_data['7'] = u.message.text
    await u.message.reply_text("💳 Paso 8: Tarjeta?")
    return 7

async def p9(u, c):
    c.user_data['8'] = u.message.text
    await u.message.reply_text("📅 Paso 9: Vencimiento?")
    return 8

async def fin(u, c):
    global sheet
    if sheet is None: conectar_google()
    if sheet is None:
        await u.message.reply_text("❌ ERROR DE CONEXIÓN. Mira los logs de Render.")
        return -1

    datos = [c.user_data['1'], c.user_data['2'], c.user_data['3'], c.user_data['4'], 
             c.user_data['5'], c.user_data['6'], c.user_data['7'], c.user_data['8'], u.message.text]
    
    try:
        col_b = sheet.col_values(2)
        fila = max(len(col_b) + 1, 4)
        sheet.update(range_name=f"B{fila}:J{fila}", values=[datos])
        await u.message.reply_text("✅ GUARDADO EN GOOGLE SHEETS 💜")
    except Exception as e:
        await u.message.reply_text(f"❌ Error al guardar: {e}")
    return -1

# --- 4. ARRANQUE ---
if __name__ == '__main__':
    token = os.getenv("TOKEN_TELEGRAM")
    if token:
        conectar_google()
        keep_alive()
        app = ApplicationBuilder().token(token).build()
        conv = ConversationHandler(
            entry_points=[CommandHandler("nuevo", nuevo)],
            states={i: [MessageHandler(filters.TEXT & ~filters.COMMAND, globals()[f'p{i+2}' if i<7 else 'p9' if i==7 else 'fin'])] for i in range(9)},
            fallbacks=[CommandHandler("cancelar", lambda u, c: -1)],
        )
        app.add_handler(CommandHandler("start", start))
        app.add_handler(conv)
        app.run_polling()
