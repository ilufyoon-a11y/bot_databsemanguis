import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# --- 1. CONFIGURACIÓN DE GOOGLE SHEETS ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
client = gspread.authorize(creds)

try:
    sheet = client.open("MANGO").worksheet("Sacadaas")
except Exception as e:
    print(f"Error al abrir la hoja: {e}")

# --- 2. ESTADOS DE LA CONVERSACIÓN ---
# Añadimos todos los pasos nuevos aquí
CORREO, CLAVE, IP, PRIV, PLATAFORMA, ESTADO, BIN, TARJETA, FECHA_VEN = range(9)

# --- 3. FUNCIONES DEL BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("?? Iniciando registro... ¿Cuál es el **CORREO**?", parse_mode='Markdown')
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
    await update.message.reply_text("Qué **PLATAFORMA** es:")
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
    # Último dato recibido
    fecha_venc = update.message.text
    
    # Recuperamos todo lo guardado en memoria
    datos_finales = [
        context.user_data['correo'],
        context.user_data['clave'],
        context.user_data['ip'],
        context.user_data['priv'],
        context.user_data['plataforma'],
        context.user_data['estado'],
        context.user_data['bin'],
        context.user_data['tarjeta'],
        fecha_venc
    ]

    # Buscamos fila libre
    col_b = sheet.col_values(2) 
    siguiente_fila = len(col_b) + 1
    if siguiente_fila < 4: siguiente_fila = 4 

    # Rango extendido de B hasta J (9 columnas)
    rango = f"B{siguiente_fila}:J{siguiente_fila}"
    sheet.update(range_name=rango, values=[datos_finales])

    await update.message.reply_text(
        f"? **REGISTRO BANCARIO COMPLETADO** ??\n\n"
        f"?? `User:` {context.user_data['correo']}\n"
        f"?? `BIN:` {context.user_data['bin']}\n"
        f"?? `Venc:` {fecha_venc}\n\n"
        "*Operación finalizada con éxito.*",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Simulación cancelada. Borahae! ??", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__ == '__main__':
    TOKEN = "TU_TOKEN_DE_TELEGRAM_AQUI"
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("nuevo", start)],
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
    print("Sistema MANGO activo...")
    app.run_polling()
