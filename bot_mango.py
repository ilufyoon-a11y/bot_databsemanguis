import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardRemove
import os
import json # <--- IMPORTANTE: Para leer la variable de Render
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

# --- 2. CONEXIÓN A GOOGLE SHEETS (MÉTODO INDESTRUCTIBLE) ---
sheet = None

def conectar_google():
    global sheet
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Intentamos leer el texto del JSON desde la variable de entorno de Render
        creds_json = os.getenv("GOOGLE_CREDS")
        
        if not creds_json:
            print("🚨 ERROR: No se encontró la variable GOOGLE_CREDS en Render")
            return

        # Cargamos la info directamente desde el texto
        info = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        
        # Usamos los nombres nuevos en minúsculas (más seguros)
        sheet = client.open("mango").worksheet("datos")
        print("✅ ¡CONECTADO CON ÉXITO A GOOGLE SHEETS!")
    except Exception as e:
        print(f"🚨 ERROR DETALLADO: {e}")
        sheet = None

# --- 3. DEFINICIÓN DE PASOS (9 PASOS TOTALES) ---
CORREO, CLAVE, IP, PRIV, PLATAFORMA, ESTADO, BIN, TARJETA, FECHA_VEN = range(9)

# --- 4. LÓGICA DEL BOT ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_url = "https://i.pinimg.com/originals/f9/a6/4c/f9a64c366580433ae19d021cca11a205.gif"
    await update.message.reply_animation(
        animation=gif_url,
        caption="¡Holaaa! Que bueno que te dignas a chambear, Valu** 🥭\n\nUsa `/nuevo` para iniciar el registro.",
        parse_mode='Markdown'
    )

async def nuevo_registro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📧 **Paso 1:** ¿Cuál es el **CORREO**?", parse_mode='Markdown')
    return CORREO

async def p_clave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['correo'] = update.message.text
    await update.message.reply_text("🔑 **Paso 2:** ¿Cuál es la **CONTRASEÑA**?", parse_mode='Markdown')
    return CLAVE

async def p_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['clave'] = update.message.text
    await update.message.reply_text("🌐 **Paso 3:** ¿Qué **IP** tiene?", parse_mode='Markdown')
    return IP

async def p_priv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ip'] = update.message.text
    await update.message.reply_text("🛡️ **Paso 4:** ¿De qué **PRIV** salió?", parse_mode='Markdown')
    return PRIV

async def p_plataforma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['priv'] = update.message.text
    await update.message.reply_text("💻 **Paso 5:** ¿Qué **PLATAFORMA** es?", parse_mode='Markdown')
    return PLATAFORMA

async def p_pestado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['plataforma'] = update.message.text
    await update.message.reply_text("📊 **Paso 6:** ¿En qué **ESTADO** se encuentra?", parse_mode='Markdown')
    return ESTADO

async def p_bin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['estado'] = update.message.text
    await update.message.reply_text("🔢 **Paso 7:** ¿Con qué **BIN** fue?", parse_mode='Markdown')
    return BIN

async def p_tarjeta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bin'] = update.message.text
    await update.message.reply_text("💳 **Paso 8:** ¿Con qué **TARJETA** fue?", parse_mode='Markdown')
    return TARJETA

async def p_fecha_ven(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tarjeta'] = update.message.text
    await update.message.reply_text("📅 **Paso 9:** ¿Cuál es su **FECHA DE VENC**?", parse_mode='Markdown')
    return FECHA_VEN

async def finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global sheet
    fecha_venc = update.message.text
    
    if sheet is None: conectar_google()

    if sheet is None:
        await update.message.reply_text("❌ Error: Sigo sin conexión. Revisa GOOGLE_CREDS en Render.")
        return ConversationHandler.END

    datos_finales = [
        context.user_data['correo'], context.user_data['clave'],
        context.user_data['ip'], context.user_data['priv'],
        context.user_data['plataforma'], context.user_data['estado'],
        context.user_data['bin'], context.user_data['tarjeta'],
        fecha_venc
    ]

    try:
        col_b = sheet.col_values(2) 
        siguiente_fila = max(len(col_b) + 1, 4) 
        rango = f"B{siguiente_fila}:J{siguiente_fila}"
        sheet.update(range_name=rango, values=[datos_finales])

        await update.message.reply_text(
            f"✅ **REGISTRO EXITOSO** 💜\n\nTodo guardado en la hoja mango.",
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
        print("❌ Error: No existe TOKEN_TELEGRAM")
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
