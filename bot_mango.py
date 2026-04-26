import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardRemove
import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from flask import Flask
from threading import Thread

# --- 1. DESPERTADOR PARA RENDER (FLASK) ---
app_web = Flask('')

@app_web.route('/')
def home():
    return "🥭 Sistema MANGO - Proceso Activo"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
sheet = None

def conectar_google():
    global sheet
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # IMPORTANTE: El archivo DEBE llamarse credenciales.json en GitHub
        creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
        client = gspread.authorize(creds)
        # Asegúrate de que tu hoja se llame MANGO y la pestaña Sacadaas
        sheet = client.open("MANGO").worksheet("Sacadaas")
        print("✅ Conectado a Google Sheets")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

# --- 3. DEFINICIÓN DE PASOS (9 PASOS TOTALES) ---
CORREO, CLAVE, IP, PRIV, PLATAFORMA, ESTADO, BIN, TARJETA, FECHA_VEN = range(9)

# --- 4. LÓGICA DEL BOT ---

# Mensaje de bienvenida con tu GIF de Pinterest
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_url = "https://i.pinimg.com/originals/f9/a6/4c/f9a64c366580433ae19d021cca11a205.gif"
    await update.message.reply_animation(
        animation=gif_url,
        caption= "¡Holaaa! Que bueno que te dignas a chambear, Valu** 🥭\n\nUsa `/nuevo` para iniciar el registro.",
        parse_mode='Markdown'
    )

# Paso 1: Correo
async def nuevo_registro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📧 **Paso 1:** ¿Cuál es el **CORREO**?", parse_mode='Markdown')
    return CORREO

# Paso 2: Clave
async def p_clave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['correo'] = update.message.text
    await update.message.reply_text("🔑 **Paso 2:** ¿Cuál es la **CONTRASEÑA**?", parse_mode='Markdown')
    return CLAVE

# Paso 3: IP
async def p_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['clave'] = update.message.text
    await update.message.reply_text("🌐 **Paso 3:** ¿Qué **IP** tiene?", parse_mode='Markdown')
    return IP

# Paso 4: Priv
async def p_priv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ip'] = update.message.text
    await update.message.reply_text("🛡️ **Paso 4:** ¿De qué **PRIV** salió?", parse_mode='Markdown')
    return PRIV

# Paso 5: Plataforma
async def p_plataforma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['priv'] = update.message.text
    await update.message.reply_text("💻 **Paso 5:** ¿Qué **PLATAFORMA** es?", parse_mode='Markdown')
    return PLATAFORMA

# Paso 6: Estado
async def p_pestado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['plataforma'] = update.message.text
    await update.message.reply_text("📊 **Paso 6:** ¿En qué **ESTADO** se encuentra?", parse_mode='Markdown')
    return ESTADO

# Paso 7: BIN
async def p_bin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['estado'] = update.message.text
    await update.message.reply_text("🔢 **Paso 7:** ¿Con qué **BIN** fue?", parse_mode='Markdown')
    return BIN

# Paso 8: Tarjeta
async def p_tarjeta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bin'] = update.message.text
    await update.message.reply_text("💳 **Paso 8:** ¿Con qué **TARJETA** fue?", parse_mode='Markdown')
    return TARJETA

# Paso 9: Fecha Vencimiento
async def p_fecha_ven(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tarjeta'] = update.message.text
    await update.message.reply_text("📅 **Paso 9:** ¿Cuál es su **FECHA DE VENC**?", parse_mode='Markdown')
    return FECHA_VEN

# FINALIZAR Y GUARDAR
async def finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fecha_venc = update.message.text
    
    # Creamos la lista con TODOS los datos en orden para las columnas B a J
    datos_finales = [
        context.user_data['correo'],      # Columna B
        context.user_data['clave'],       # Columna C
        context.user_data['ip'],          # Columna D
        context.user_data['priv'],        # Columna E
        context.user_data['plataforma'],  # Columna F
        context.user_data['estado'],      # Columna G
        context.user_data['bin'],         # Columna H
        context.user_data['tarjeta'],     # Columna I
        fecha_venc                        # Columna J
    ]

    try:
        # Buscamos la fila vacía
        col_b = sheet.col_values(2) 
        siguiente_fila = len(col_b) + 1
        if siguiente_fila < 4: siguiente_fila = 4 

        rango = f"B{siguiente_fila}:J{siguiente_fila}"
        sheet.update(range_name=rango, values=[datos_finales])

        await update.message.reply_text(
            f"✅ **REGISTRO EXITOSO** 💜\n\n"
            f"👤 `User:` {context.user_data['correo']}\n"
            f"💳 `BIN:` {context.user_data['bin']}\n"
            f"📅 `Venc:` {fecha_venc}\n\n"
            "Todo guardado en la hoja MANGO.",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error al guardar: {e}")
        
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Registro cancelado. Borahae! 💜", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- 5. INICIO DEL PROGRAMA ---
if __name__ == '__main__':
    TOKEN = os.getenv("TOKEN_TELEGRAM")
    
    if not TOKEN:
        print("❌ Error: No existe TOKEN_TELEGRAM en las variables de Render")
    else:
        conectar_google()
        keep_alive()
        
        app = ApplicationBuilder().token(TOKEN).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("nuevo", nuevo_registro)],
            states={
                CORREO: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_clave)],
                CLAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_ip)],
                IP: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_priv)],
                PRIV: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_plataforma)],
                PLATAFORMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_pestado)],
                ESTADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_bin)],
                BIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_tarjeta)],
                TARJETA: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_fecha_ven)],
                FECHA_VEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, finalizar)],
            },
            fallbacks=[CommandHandler("cancelar", cancel)],
        )

        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(conv_handler)
        
        print("✅ Sistema MANGO Funcionando...")
        app.run_polling()
