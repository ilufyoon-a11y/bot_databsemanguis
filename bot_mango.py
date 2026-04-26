import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardRemove
import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from flask import Flask
from threading import Thread

# --- 1. MINI SERVIDOR WEB PARA RENDER (GRATIS) ---
app_web = Flask('')

@app_web.route('/')
def home():
    return "Sistema MANGO Online 🥭"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- 2. CONFIGURACIÓN DE GOOGLE SHEETS ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open("MANGO").worksheet("Sacadaas")
except Exception as e:
    print(f"Error de configuración (Sheets/JSON): {e}")

# --- 3. ESTADOS DE LA CONVERSACIÓN ---
CORREO, CLAVE, IP, PRIV, PLATAFORMA, ESTADO, BIN, TARJETA, FECHA_VEN = range(9)

# --- 4. FUNCIONES DEL BOT ---

# Comando /start: Bienvenida con GIF
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Puedes cambiar esta URL por cualquier GIF de BTS que te guste
    gif_url = "https://i.pinimg.com/originals/f9/a6/4c/f9a64c366580433ae19d021cca11a205.gif"
    
    await update.message.reply_animation(
        animation=gif_url,
        caption=(
            "**¡Holaaa! Que bueno que te dignas a chambear, Valu** 🥭\n\n"
            "🔹 Usa `/nuevo` para registrar una nueva cuenta.\n"
            "🔹 Usa `/cancelar` si te equivocas en algo."
        ),
        parse_mode='Markdown'
    )

# Inicio del registro con /nuevo
async def nuevo_registro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✨ **Iniciando nuevo registro...**\n¿Cuál es el **CORREO**?", parse_mode='Markdown')
    return CORREO

async def p_clave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['correo'] = update.message.text
    await update.message.reply_text("¿Cuál es la **CONTRASEÑA**?")
    return CLAVE

async def p_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['clave'] = update.message.text
    await update.message.reply_text("¿Qué **IP** tiene?")
    return IP

async def p_priv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ip'] = update.message.text
    await update.message.reply_text("¿De qué **PRIV** salió?")
    return PRIV

async def p_plataforma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['priv'] = update.message.text
    await update.message.reply_text("¿Qué **PLATAFORMA** es?")
    return PLATAFORMA

async def p_pestado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['plataforma'] = update.message.text
    await update.message.reply_text("¿En qué **ESTADO** se encuentra?")
    return ESTADO

async def p_bin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['estado'] = update.message.text
    await update.message.reply_text("¿Con qué **BIN** fue?")
    return BIN

async def p_tarjeta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bin'] = update.message.text
    await update.message.reply_text("¿Con qué **TARJETA** fue?")
    return TARJETA

async def p_fecha_ven(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tarjeta'] = update.message.text
    await update.message.reply_text("¿Cuál es su **FECHA DE VENC**?")
    return FECHA_VEN

async def finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fecha_venc = update.message.text
    datos_finales = [
        context.user_data['correo'], context.user_data['clave'],
        context.user_data['ip'], context.user_data['priv'],
        context.user_data['plataforma'], context.user_data['estado'],
        context.user_data['bin'], context.user_data['tarjeta'], fecha_venc
    ]

    try:
        col_b = sheet.col_values(2) 
        siguiente_fila = len(col_b) + 1
        if siguiente_fila < 4: siguiente_fila = 4 
        rango = f"B{siguiente_fila}:J{siguiente_fila}"
        sheet.update(range_name=rango, values=[datos_finales])
        
        await update.message.reply_text(
            f"✅ **REGISTRO COMPLETADO** \n\n"
            f"👤 `User:` {context.user_data['correo']}\n"
            f"💳 `BIN:` {context.user_data['bin']}\n"
            f"📅 `Venc:` {fecha_venc}\n\n"
            "*Datos guardados en MANGO.*",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error al guardar en Sheets: {e}")
        
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registro cancelado. ¡Borahae! 💜", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- 5. EJECUCIÓN ---
if __name__ == '__main__':
    TOKEN = os.getenv("TOKEN_TELEGRAM")
    
    if not TOKEN:
        print("❌ ERROR: No se encontró la variable TOKEN_TELEGRAM")
    else:
        keep_alive() # Inicia el servidor web para Render
        
        app = ApplicationBuilder().token(TOKEN).build()

        # Handler para el comando /start solo (con el GIF)
        app.add_handler(CommandHandler("start", start_command))

        # Handler de conversación para /nuevo
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

        app.add_handler(conv_handler)
        print("✅ Bot MANGO listo con GIF y comandos separados.")
        app.run_polling()
