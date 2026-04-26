import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardRemove
import os
import json
import datetime
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from flask import Flask
from threading import Thread

# --- 1. DESPERTADOR PARA RENDER ---
app_web = Flask('')
@app_web.route('/')
def home(): return "🥭 Sistema MANGO - Activo"

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
        creds_json = os.getenv("GOOGLE_CREDS")
        if not creds_json: return
        info = json.loads(creds_json)
        if 'private_key' in info:
            info['private_key'] = info['private_key'].replace('\\n', '\n')
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        sheet = client.open("mango").worksheet("datos")
        print("✅ CONECTADO 💜")
    except Exception as e:
        print(f"🚨 ERROR: {e}")
        sheet = None

# --- 3. ALERTA DE VENCIMIENTOS ---
async def revisar_vencimientos(context: ContextTypes.DEFAULT_TYPE):
    global sheet
    if sheet is None: conectar_google()
    
    try:
        # Chat ID de Valu (el bot te mandará el mensaje a ti)
        # Puedes sacarlo usando /start y viendo los logs o fijarlo si ya lo sabes
        # Por ahora, esta función se activará cada 24 horas
        registros = sheet.get_all_records()
        hoy = datetime.date.today()
        proximos = []

        for reg in registros:
            fecha_str = str(reg.get('FECHA DE VENC', ''))
            try:
                # Intentamos convertir la fecha (ajusta el formato si usas otro)
                fecha_v = datetime.datetime.strptime(fecha_str, "%d/%m/%Y").date()
                dias_restantes = (fecha_v - hoy).days
                
                if 0 <= dias_restantes <= 1: # Alerta si faltan 3 días o menos
                    proximos.append(f"⚠️ {reg.get('PLATAFORMA')} ({reg.get('CORREO')}) vence en {dias_restantes} días.")
            except:
                continue

        if proximos and context.job.chat_id:
            mensaje = "📢 **ALERTAS MANGO** 🥭\n\n" + "\n".join(proximos)
            await context.bot.send_message(chat_id=context.job.chat_id, text=mensaje, parse_mode='Markdown')
    except Exception as e:
        print(f"Error en alertas: {e}")

# --- 4. LÓGICA DEL BOT ---
CORREO, CLAVE, IP, PRIV, PLATAFORMA, ESTADO, BIN, TARJETA, FECHA_VEN = range(9)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Programar la alerta la primera vez que se usa (cada 24 horas)
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(f"alerta_{chat_id}")
    if not jobs:
        context.job_queue.run_daily(revisar_vencimientos, time=datetime.time(hour=10, minute=0), chat_id=chat_id, name=f"alerta_{chat_id}")

    gif_url = "https://i.pinimg.com/originals/f9/a6/4c/f9a64c366580433ae19d021cca11a205.gif"
    await update.message.reply_animation(animation=gif_url, caption="¡Hola Valu! 🥭\nUsa `/nuevo` para registrar.")

async def nuevo_registro(u, c):
    await u.message.reply_text("📧 **Paso 1:** ¿CORREO?")
    return CORREO

async def p_clave(u, c):
    c.user_data['correo'] = u.message.text
    await u.message.reply_text("🔑 **Paso 2:** ¿CLAVE?")
    return CLAVE

async def p_ip(u, c):
    c.user_data['clave'] = u.message.text
    await u.message.reply_text("🌐 **Paso 3:** ¿IP?")
    return IP

async def p_priv(u, c):
    c.user_data['ip'] = u.message.text
    await u.message.reply_text("🛡️ **Paso 4:** ¿PRIV?")
    return PRIV

async def p_plataforma(u, c):
    c.user_data['priv'] = u.message.text
    await u.message.reply_text("💻 **Paso 5:** ¿PLATAFORMA?")
    return PLATAFORMA

async def p_pestado(u, c):
    c.user_data['plataforma'] = u.message.text
    await u.message.reply_text("📊 **Paso 6:** ¿ESTADO?")
    return ESTADO

async def p_bin(u, c):
    c.user_data['estado'] = u.message.text
    await u.message.reply_text("🔢 **Paso 7:** ¿BIN?")
    return BIN

async def p_tarjeta(u, c):
    c.user_data['bin'] = u.message.text
    await u.message.reply_text("💳 **Paso 8:** ¿TARJETA?")
    return TARJETA

async def p_fecha_ven(u, c):
    c.user_data['tarjeta'] = u.message.text
    await u.message.reply_text("📅 **Paso 9:** ¿VENCIMIENTO? (DD/MM/AAAA)")
    return FECHA_VEN

async def finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global sheet
    if sheet is None: conectar_google()
    
    # --- CORRECCIÓN DE POSICIÓN ---
    try:
        col_b = sheet.col_values(2) # Columna de correos
        # Buscamos la primera fila realmente vacía después de la 11
        siguiente_fila = 11
        for i, valor in enumerate(col_b):
            if i >= 10 and not valor.strip(): # Si a partir de la 11 está vacío
                siguiente_fila = i + 1
                break
            siguiente_fila = len(col_b) + 1
        
        # Si la tabla está muy vacía, forzamos la 11
        if siguiente_fila < 11: siguiente_fila = 11

        datos = [
            context.user_data['correo'], context.user_data['clave'],
            context.user_data['ip'], context.user_data['priv'],
            context.user_data['plataforma'], context.user_data['estado'],
            context.user_data['bin'], context.user_data['tarjeta'],
            update.message.text
        ]

        sheet.update(range_name=f"B{siguiente_fila}:J{siguiente_fila}", values=[datos])
        await update.message.reply_text("✅ **¡DENTRO DE LA TABLA!** 🥭💜")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    return ConversationHandler.END

# --- 5. INICIO ---
if __name__ == '__main__':
    TOKEN = os.getenv("TOKEN_TELEGRAM")
    if TOKEN:
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
            fallbacks=[CommandHandler("cancelar", lambda u,c: ConversationHandler.END)],
        )
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(conv_handler)
        app.run_polling()
