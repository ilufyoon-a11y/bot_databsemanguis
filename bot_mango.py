import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardRemove
import os
import json
import datetime
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from flask import Flask
from threading import Thread

# --- 1. DESPERTADOR PARA RENDER (FLASK) ---
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
        print("✅ CONECTADO A GOOGLE SHEETS 💜")
    except Exception as e:
        print(f"🚨 ERROR DE CONEXIÓN: {e}")
        sheet = None

# --- 3. ALERTA DE VENCIMIENTOS ---
async def revisar_vencimientos(context: ContextTypes.DEFAULT_TYPE):
    global sheet
    if sheet is None: conectar_google()
    
    try:
        registros = sheet.get_all_records()
        hoy = datetime.date.today()
        proximos = []

        for reg in registros:
            # Busca la columna "FECHA DE VENC"
            fecha_str = str(reg.get('FECHA DE VENC', ''))
            try:
                fecha_v = datetime.datetime.strptime(fecha_str, "%d/%m/%Y").date()
                dias_restantes = (fecha_v - hoy).days
                
                # Alerta si vence hoy o mañana
                if 0 <= dias_restantes <= 1: 
                    proximos.append(f"⚠️ {reg.get('PLATAFORMA')} ({reg.get('CORREO')}) vence en {dias_restantes} día(s).")
            except:
                continue

        if proximos and context.job.chat_id:
            mensaje = "📢 **ALERTAS MANGO** 🥭\n\n" + "\n".join(proximos)
            await context.bot.send_message(chat_id=context.job.chat_id, text=mensaje, parse_mode='Markdown')
    except Exception as e:
        print(f"Error en el sistema de alertas: {e}")

# --- 4. LÓGICA DEL BOT (PASOS) ---
CORREO, CLAVE, IP, PRIV, PLATAFORMA, ESTADO, BIN, TARJETA, FECHA_VEN = range(9)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Programar alertas diarias a las 10:00 AM
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(f"alerta_{chat_id}")
    if not jobs:
        context.job_queue.run_daily(revisar_vencimientos, time=datetime.time(hour=10, minute=0), chat_id=chat_id, name=f"alerta_{chat_id}")

    # Tu mensaje de bienvenida personalizado
    gif_url = "https://i.pinimg.com/originals/f9/a6/4c/f9a64c366580433ae19d021cca11a205.gif"
    await update.message.reply_animation(
        animation=gif_url, 
        caption="¡Holaaa! Que bueno que te dignas a chambear, Valu** 🥭\n\nUsa `/nuevo` para iniciar el registro.",
        parse_mode='Markdown'
    )

async def nuevo_registro(u, c):
    await u.message.reply_text("📧 **Paso 1:** ¿Cuál es el **CORREO**?", parse_mode='Markdown')
    return CORREO

async def p_clave(u, c):
    c.user_data['correo'] = u.message.text
    await u.message.reply_text("🔑 **Paso 2:** ¿Cuál es la **CONTRASEÑA**?", parse_mode='Markdown')
    return CLAVE

async def p_ip(u, c):
    c.user_data['clave'] = u.message.text
    await u.message.reply_text("🌐 **Paso 3:** ¿Qué **IP** tiene?", parse_mode='Markdown')
    return IP

async def p_priv(u, c):
    c.user_data['ip'] = u.message.text
    await u.message.reply_text("🛡️ **Paso 4:** ¿De qué **PRIV** salió?", parse_mode='Markdown')
    return PRIV

async def p_plataforma(u, c):
    c.user_data['priv'] = u.message.text
    await u.message.reply_text("💻 **Paso 5:** ¿Qué **PLATAFORMA** es?", parse_mode='Markdown')
    return PLATAFORMA

async def p_pestado(u, c):
    c.user_data['plataforma'] = u.message.text
    await u.message.reply_text("📊 **Paso 6:** ¿En qué **ESTADO** se encuentra?", parse_mode='Markdown')
    return ESTADO

async def p_bin(u, c):
    c.user_data['estado'] = u.message.text
    await u.message.reply_text("🔢 **Paso 7:** ¿Con qué **BIN** fue?", parse_mode='Markdown')
    return BIN

async def p_tarjeta(u, c):
    c.user_data['bin'] = u.message.text
    await u.message.reply_text("💳 **Paso 8:** ¿Con qué **TARJETA** fue?", parse_mode='Markdown')
    return TARJETA

async def p_fecha_ven(u, c):
    c.user_data['tarjeta'] = u.message.text
    await u.message.reply_text("📅 **Paso 9:** ¿Cuál es su **FECHA DE VENC**?\n*(Usa formato DD/MM/AAAA)*", parse_mode='Markdown')
    return FECHA_VEN

async def finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global sheet
    if sheet is None: conectar_google()
    
    try:
        col_b = sheet.col_values(2) # Columna de correos
        
        # --- BUSCADOR DE FILA (Desde la 4) ---
        siguiente_fila = 4
        for i, valor in enumerate(col_b):
            # i=3 es la fila 4. Si está vacío, nos quedamos con esa fila.
            if i >= 3 and not str(valor).strip(): 
                siguiente_fila = i + 1
                break
        else:
            siguiente_fila = len(col_b) + 1
        
        if siguiente_fila < 4: siguiente_fila = 4

        # Preparamos los datos en el orden de tus columnas (B a J)
        datos = [
            context.user_data['correo'], 
            context.user_data['clave'],
            context.user_data['ip'], 
            context.user_data['priv'],
            context.user_data['plataforma'], 
            context.user_data['estado'],
            context.user_data['bin'], 
            context.user_data['tarjeta'],
            update.message.text # La fecha de vencimiento
        ]

        # Guardar en la hoja
        sheet.update(range_name=f"B{siguiente_fila}:J{siguiente_fila}", values=[datos])
        
        await update.message.reply_text(
            f"✅ **¡REGISTRO EXITOSO!** 🥭💜\nGuardado en la fila: {siguiente_fila}",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error al guardar en Sheets: {e}")
        
    return ConversationHandler.END

# --- 5. EJECUCIÓN PRINCIPAL ---
if __name__ == '__main__':
    TOKEN = os.getenv("TOKEN_TELEGRAM")
    if TOKEN:
        conectar_google()
        keep_alive()
        
        # Build de la aplicación con JobQueue activado
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
        
        print("🥭 Sistema MANGO en línea y buscando desde la fila 4...")
        app.run_polling()
