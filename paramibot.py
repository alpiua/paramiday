import os, csv, logging, random, asyncio
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
    'ukrainian': '@paramiday_ua',
    'english': '@paramiday_en',
    'russian': '@paramiday_ru'
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


# Command handler to show paramis based on the given language
async def paramis_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Loads and sends paramis based on the specified language."""
    # Determine the language from the command
    command = update.message.text.split('_')[-1]  # Extracts 'uk', 'en', or 'ru'
    language = {
        'uk': 'ukrainian',
        'en': 'english',
        'ru': 'russian'
    }.get(command, 'ukrainian')  # Default to Ukrainian if not found

    # Load paramis from the appropriate Google Sheet
    parami_list = load_parami_from_sheet(SHEET_IDS[language])

    # Define language-specific headers
    headers = {
        'ukrainian': "     ⭐ *Десять досконалих якостей* ⭐",
        'english': "     ⭐ *The Ten Perfections* ⭐",
        'russian': "     ⭐ *Десять благих качеств* ⭐"
    }
    header = headers[language]

    # Send the paramis using the chunked send logic
    await split_and_send_by_parami(update.effective_chat.id, parami_list, context, header)

# Function to split and send paramis with stylish formatting
async def split_and_send_by_parami(chat_id, parami_list, context, header, chunk_size=4000):
    """Splits paramis into chunks and sends them one by one."""
    message = f"{header}\n\n\n"  # Start the message with the header

    for parami in parami_list:
        # Format each parami with a separator
        parami_block = (
            f"☸️ *{parami['Parami']}*: \n{parami['Description']}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        # If the current message chunk is too large, send it
        if len(message) + len(parami_block) > chunk_size:
            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            message = ""  # Reset message for the next chunk

        # Add the parami block to the current message
        message += parami_block

    # Send the remaining part of the message, if any
    if message:
        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

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

    application.add_handler(CommandHandler(["paramis_uk", "paramis_en", "paramis_ru"], paramis_handler))

    LOCAL_UTC_OFFSET = timedelta(hours=3)

    application.job_queue.run_daily(
        post_daily_parami,
        time=time(6, 18, tzinfo=timezone(LOCAL_UTC_OFFSET))  # Adjust timezone
    )

    application.run_polling()

if __name__ == '__main__':
    main()
