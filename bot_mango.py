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

@app_web.route('/alertas')
def trigger_alertas():
    import asyncio
    try:
        registros = sheet.get_all_records()
        hoy = datetime.date.today()
        proximos = []

        for reg in registros:
            fecha_str = str(reg.get('FECHA DE VENC', '')).strip()
            if not fecha_str:
                continue
            try:
                fecha_v = datetime.datetime.strptime(fecha_str, "%d/%m/%Y").date()
                dias_restantes = (fecha_v - hoy).days
                if 0 <= dias_restantes <= 1:
                    proximos.append(
                        f"⚠️ {reg.get('PLATAFORMA', 'N/A')} ({reg.get('CORREO', 'N/A')}) "
                        f"vence en {dias_restantes} diɑ(s)."
                    )
            except ValueError:
                continue

        if proximos:
            mensaje = "𝗢𝗝𝗢 𝗩𝗔𝗟𝗨\n\n" + "\n".join(proximos)
            TOKEN = os.getenv("TOKEN_TELEGRAM")
            CHAT_ID = os.getenv("CHAT_ID")
            async def enviar():
                from telegram import Bot
                bot = Bot(token=TOKEN)
                await bot.send_message(chat_id=CHAT_ID, text=mensaje, parse_mode='Markdown')
            asyncio.run(enviar())
            return "✅ 𝖠𝗅𝖾𝗋𝗍𝖺𝗌 𝖿𝗎𝗇𝖼𝗂𝗈𝗇𝖺𝗇𝖽𝗈"
        else:
            return "🕰️ 𝖲𝗂𝗇 𝗏𝖾𝗇𝖼𝗂𝗆𝗂𝖾𝗇𝗍𝗈𝗌 𝗉𝗋𝗈𝗑𝗂𝗆𝗈𝗌"

    except Exception as e:
        return f"🚨 Error: {e}"

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
        if not creds_json:
            print("🚨 No se encontró GOOGLE_CREDS en las variables de entorno.")
            return
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

# --- 3. LÓGICA DEL BOT (PASOS) ---
CORREO, CLAVE, IP, PRIV, PLATAFORMA, ESTADO, BIN, TARJETA, FECHA_VEN = range(9)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_url = "https://i.pinimg.com/originals/f9/a6/4c/f9a64c366580433ae19d021cca11a205.gif"
    await update.message.reply_animation(
        animation=gif_url,
        caption="¡Holaaa! Que bueno que te dignas a chambear, Valu \n\nUsa /nuevo para iniciar el registro.\nUsa /cancelar si quieres abortar en cualquier momento.",
        parse_mode='Markdown'
    )

async def nuevo_registro(u, c):
    await u.message.reply_text("⭒    ۪   𝖢𝗈𝗋𝗋𝖾𝗈   ֹ    ۪   💌", parse_mode='Markdown')
    return CORREO

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "𝗥𝗘𝗚𝗜𝗦𝗧𝗥𝗢 𝗖𝗔𝗡𝗖𝗘𝗟𝗔𝗗𝗢. 𝖭𝗂𝗇𝗀𝗎𝗇 𝖽𝖺𝗍𝗈 𝖿𝗎𝖾 𝗀𝗎𝖺𝗋𝖽𝖺𝖽𝗈.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def p_clave(u, c):
    c.user_data['correo'] = u.message.text
    await u.message.reply_text("⭒    ۪   𝖯𝖺𝗌𝗌𝗐𝗈𝗋𝖽   ֹ    ۪   🗝️", parse_mode='Markdown')
    return CLAVE

async def p_ip(u, c):
    c.user_data['clave'] = u.message.text
    await u.message.reply_text("⭒    ۪   𝖨𝖯   ֹ    ۪   🗺️", parse_mode='Markdown')
    return IP

async def p_priv(u, c):
    c.user_data['ip'] = u.message.text
    await u.message.reply_text("⭒    ۪   𝖯𝗋𝗂𝗏   ֹ    ۪   🗃️", parse_mode='Markdown')
    return PRIV

async def p_plataforma(u, c):
    c.user_data['priv'] = u.message.text
    await u.message.reply_text("⭒    ۪   𝖯𝗅𝖺𝗍𝖺𝖿𝗈𝗋𝗆𝖺   ֹ    ۪   💻", parse_mode='Markdown')
    return PLATAFORMA

async def p_pestado(u, c):
    c.user_data['plataforma'] = u.message.text
    await u.message.reply_text("⭒    ۪   𝖤𝗌𝗍𝖺𝖽𝗈   ֹ    ۪   🪁", parse_mode='Markdown')
    return ESTADO

async def p_bin(u, c):
    c.user_data['estado'] = u.message.text
    await u.message.reply_text("⭒    ۪   𝖡𝖨𝖭   ֹ    ۪   🔢", parse_mode='Markdown')
    return BIN

async def p_tarjeta(u, c):
    c.user_data['bin'] = u.message.text
    await u.message.reply_text("⭒    ۪   𝖳𝖺𝗋𝗃𝖾𝗍𝖺   ֹ    ۪   💳", parse_mode='Markdown')
    return TARJETA

async def p_fecha_ven(u, c):
    c.user_data['tarjeta'] = u.message.text
    await u.message.reply_text(
        "⭒    ۪   𝖵𝖾𝗇𝖼𝗂𝗆𝗂𝖾𝗇𝗍𝗈   ֹ    ۪   ⏰",
        parse_mode='Markdown'
    )
    return FECHA_VEN

async def finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global sheet
    if sheet is None:
        conectar_google()

    try:
        col_b = sheet.col_values(2)

        siguiente_fila = 4
        for i, valor in enumerate(col_b):
            if i >= 3 and not str(valor).strip():
                siguiente_fila = i + 1
                break
        else:
            siguiente_fila = max(len(col_b) + 1, 4)

        if siguiente_fila < 4:
            siguiente_fila = 4

        datos = [
            context.user_data.get('correo', ''),
            context.user_data.get('clave', ''),
            context.user_data.get('ip', ''),
            context.user_data.get('priv', ''),
            context.user_data.get('plataforma', ''),
            context.user_data.get('estado', ''),
            context.user_data.get('bin', ''),
            context.user_data.get('tarjeta', ''),
            update.message.text
        ]

        sheet.update(range_name=f"B{siguiente_fila}:J{siguiente_fila}", values=[datos])
        context.user_data.clear()

        await update.message.reply_text(
            f"𝗥𝗘𝗚𝗜𝗦𝗧𝗥𝗢 𝗘𝗫𝗜𝗧𝗢𝗦𝗢\n𝖦𝗎𝖺𝗋𝖽𝖺𝖽𝗈 𝖾𝗇 𝗅𝖺 𝖿𝗂𝗅𝖺: {siguiente_fila}",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error al guardar en Sheets: `{e}`", parse_mode='Markdown')

    return ConversationHandler.END

# --- 4. EJECUCIÓN PRINCIPAL ---
if __name__ == '__main__':
    TOKEN = os.getenv("TOKEN_TELEGRAM")
    if not TOKEN:
        print("🚨 No se encontró TOKEN_TELEGRAM en las variables de entorno.")
    else:
        conectar_google()
        keep_alive()

        app = ApplicationBuilder().token(TOKEN).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("nuevo", nuevo_registro)],
            states={
                CORREO:    [MessageHandler(filters.TEXT & ~filters.COMMAND, p_clave)],
                CLAVE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, p_ip)],
                IP:        [MessageHandler(filters.TEXT & ~filters.COMMAND, p_priv)],
                PRIV:      [MessageHandler(filters.TEXT & ~filters.COMMAND, p_plataforma)],
                PLATAFORMA:[MessageHandler(filters.TEXT & ~filters.COMMAND, p_pestado)],
                ESTADO:    [MessageHandler(filters.TEXT & ~filters.COMMAND, p_bin)],
                BIN:       [MessageHandler(filters.TEXT & ~filters.COMMAND, p_tarjeta)],
                TARJETA:   [MessageHandler(filters.TEXT & ~filters.COMMAND, p_fecha_ven)],
                FECHA_VEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, finalizar)],
            },
            fallbacks=[CommandHandler("cancelar", cancelar)],
        )

        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(conv_handler)

        print("🥭 Sistema MANGO en línea y buscando desde la fila 4...")
        app.run_polling()
