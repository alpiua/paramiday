import os, csv, logging, random
import gspread
from dotenv import load_dotenv
from datetime import time, timezone, timedelta
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
CREDENTIALS_FILE = os.path.join(BASE_DIR, "paramibot-googleapi-credentials.json")

CHANNEL_IDS = {
    'ukrainian': '@paramiday_ukr',
    'english': '@paramiday_eng',
    'russian': '@paramiday_rus'
}

# Google sheet documents with Parami description
SHEET_IDS = {
    'ukrainian': '1bCkn8RzSa08wdK1tln2JgJNuO2rHkhSVaKvePllPwdU',
    'english': '1XpvTmRkK-Xuws_RWQhYoGejT_MrcWu5Op_aV8o3H9rE',
    'russian': '1Pb2wpjZowGNRC9qjtxdnG0_Q2DVYzqFsoElu-8xA8G8'
}

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.info("ParamiBot script has started.")

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Google Sheets API Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
gc = gspread.authorize(credentials)

# Function to load parami from a specific sheet in the Google Sheets file
def load_parami_from_sheet(sheet_id):
    try:
        worksheet = gc.open_by_key(sheet_id).sheet1  # Access the first sheet
        records = worksheet.get_all_records()
        return records
    except gspread.exceptions.SpreadsheetNotFound as e:
        logging.error(f"Spreadsheet not found: {sheet_id}")
        raise e

# Send parami to all channels
async def post_daily_parami(context: ContextTypes.DEFAULT_TYPE):
    for lang, channel_id in CHANNEL_IDS.items():
        parami_list = load_parami_from_sheet(SHEET_IDS[lang])
        parami = random.choice(parami_list)
        message = f"☸️ {parami['Parami']}\n\n{parami['Description']}"
        await context.bot.send_message(chat_id=channel_id, text=message)

# Command handler to show all paramis for a specific channel
async def all_paramis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = context.args[0] if context.args else 'ukrainian'
    parami_list = load_parami_from_sheet(SHEET_IDS[language])
    message = "☸️ *Усі Парамі:*\n\n"
    for parami in parami_list:
        message += f"☸️ {parami['Parami']}: {parami['Description']}\n\n"
    await update.message.reply_text(message, parse_mode='Markdown')

# Error handler
async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    """Log the error and notify the user if possible."""
    logging.error(f"An error occurred: {context.error}")

    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="An unexpected error occurred. Please try again later."
        )

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_error_handler(error_handler)

    application.add_handler(CommandHandler("all_paramis", all_paramis))

    LOCAL_UTC_OFFSET = timedelta(hours=3)

    application.job_queue.run_daily(
        post_daily_parami,
        time=time(3, 33, tzinfo=timezone(LOCAL_UTC_OFFSET))  # Adjust timezone
    )

    application.run_polling()

if __name__ == '__main__':
    main()
