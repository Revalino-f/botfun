import json, os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

# --- Load & Save Data ---
def load_data():
    with open("data.json", "r") as f:
        return json.load(f)

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

# --- Bot Token ---
TOKEN = os.getenv("BOT_TOKEN") or "ISI_TOKEN_BOTMU_DISINI"

# --- Command: Start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Halo! Aku Game Time Bot PRO.\nGunakan /help untuk lihat fitur.")

# --- Help Menu ---
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """📌 Perintah Utama:
- /jadwal → lihat rundown
- /alert YYYY-MM-DD pesan → pasang alert
- /notes → lihat catatan
- /note teks → tambah catatan
- /done mingguX → tandai selesai
- /progress → lihat progress
- /leaderboard → lihat poin tim
- /setrole @user Role → assign role
"""
    await update.message.reply_text(text)

# --- Notes ---
async def note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = " ".join(context.args)
    if not teks:
        return await update.message.reply_text("❌ Gunakan: /note isi_catatan")
    data["notes"].append(teks)
    save_data(data)
    await update.message.reply_text(f"📝 Catatan ditambahkan: {teks}")

async def notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data["notes"]:
        return await update.message.reply_text("📭 Belum ada catatan.")
    teks = "\n".join([f"{i+1}. {n}" for i,n in enumerate(data["notes"])])
    await update.message.reply_text(f"📝 Catatan:\n{teks}")

# --- Alert ---
async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await update.message.reply_text("❌ Format: /alert YYYY-MM-DD pesan")
    tanggal = context.args[0]
    pesan = " ".join(context.args[1:])
    data["alerts"].append({"date": tanggal, "message": pesan, "chat": update.message.chat_id})
    save_data(data)
    await update.message.reply_text(f"🔔 Alert tersimpan: {tanggal} → {pesan}")

# --- Milestone ---
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Gunakan: /done mingguX")
    minggu = context.args[0].lower()
    user = update.message.from_user.username or update.message.from_user.first_name
    data["milestones"][minggu] = True
    data["leaderboard"][user] = data["leaderboard"].get(user, 0) + 10
    save_data(data)
    await update.message.reply_text(f"✅ {minggu} ditandai selesai +10 pts untuk {user}")

async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = 10
    selesai = len([m for m in data["milestones"] if data["milestones"][m]])
    persen = int(selesai/total*100)
    await update.message.reply_text(f"📊 Progress: {selesai}/{total} minggu ({persen}%)")

# --- Leaderboard ---
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data["leaderboard"]:
        return await update.message.reply_text("📭 Belum ada poin.")
    teks = "\n".join([f"{i+1}. {u} - {p} pts" for i,(u,p) in enumerate(sorted(data["leaderboard"].items(), key=lambda x: x[1], reverse=True))])
    await update.message.reply_text(f"🏆 Leaderboard:\n{teks}")

# --- Flask Keep Alive ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# --- Scheduler Cek Alert ---
def cek_alert():
    today = datetime.now().strftime("%Y-%m-%d")
    for alert in data["alerts"]:
        if alert["date"] == today:
            import requests
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            payload = {"chat_id": alert["chat"], "text": f"🔔 ALERT HARI INI: {alert['message']}"}
            requests.post(url, data=payload)

sched = BackgroundScheduler()
sched.add_job(cek_alert, 'interval', hours=24)
sched.start()

# --- Main ---
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("note", note))
    application.add_handler(CommandHandler("notes", notes))
    application.add_handler(CommandHandler("alert", alert))
    application.add_handler(CommandHandler("done", done))
    application.add_handler(CommandHandler("progress", progress))
    application.add_handler(CommandHandler("leaderboard", leaderboard))

    from threading import Thread
    Thread(target=run_flask).start()
    application.run_polling()

if __name__ == "__main__":
    main()
