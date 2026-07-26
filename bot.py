import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect("approvals.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            status TEXT DEFAULT 'PENDING'
        )
    """)
    conn.commit()
    conn.close()

# /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome = (
        "⚙️ **Welcome to @ContentApproval_1bot!**\n\n"
        "Streamline internal content reviews with AI-assisted approval workflows.\n\n"
        "**Commands:**\n"
        "• `/submit [your text]` — Send content for review & approval\n"
        "• `/status` — View status of your submissions"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")

# /submit command
async def submit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide content to review.\n\n"
            "**Example:** `/submit Check out our new launch starting tomorrow at 9 AM!`",
            parse_mode="Markdown"
        )
        return

    content = " ".join(context.args)

    # Save submission
    conn = sqlite3.connect("approvals.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO submissions (user_id, content) VALUES (?, ?)", (user_id, content))
    sub_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Buttons for approval workflow
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{sub_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{sub_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"📝 **Submission #{sub_id} Received:**\n\n\"{content}\"\n\n**Action Required:**",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Button Callback Handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    action, sub_id = query.data.split("_")

    conn = sqlite3.connect("approvals.db")
    cursor = conn.cursor()

    if action == "approve":
        cursor.execute("UPDATE submissions SET status = 'APPROVED' WHERE id = ?", (sub_id,))
        conn.commit()
        await query.edit_message_text(f"✅ **Submission #{sub_id} has been APPROVED!**", parse_mode="Markdown")

    elif action == "reject":
        cursor.execute("UPDATE submissions SET status = 'REJECTED' WHERE id = ?", (sub_id,))
        conn.commit()
        await query.edit_message_text(
            f"❌ **Submission #{sub_id} REJECTED.**\n\n"
            f"🤖 *AI Rewriter Triggered:* Please resubmit using `/submit [revised text]`.",
            parse_mode="Markdown"
        )

    conn.close()

# /status command
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    conn = sqlite3.connect("approvals.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, content, status FROM submissions WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("No submissions found.")
        return

    msg = "📊 **Your Recent Submissions:**\n\n"
    for sub_id, text, status in rows:
        emoji = "✅" if status == "APPROVED" else ("❌" if status == "REJECTED" else "⏳")
        msg += f"• **#{sub_id}** [{emoji} {status}]: {text[:30]}...\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

def main() -> None:
    init_db()

    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_TOKEN environment variable missing!")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("submit", submit_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("@ContentApproval_1bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
