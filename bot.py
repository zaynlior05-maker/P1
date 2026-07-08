import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Menu Functions ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the main welcome screen."""
    text = (
        "👋 **Welcome to The Arcade 🕹️ P1 Bot!**\n\n"
        "This dialler bot is officially provided by The Arcade 🕹️, "
        "giving you access to a private, fully automated mass-calling system "
        "with real-time lead detection.\n\n"
        "🚀 **Features**\n"
        "• Upload your leads and start dialling instantly\n"
        "• Custom Caller ID & multi-trunk SIP support\n"
        "• Real-time press-1 detection with instant alerts\n"
        "• Crypto payments (BTC, ETH, LTC) — confirmed on-chain automatically\n\n"
        "**Powered by The Arcade 🕹️**"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Purchase Subscription", callback_data="view_subscription")],
        [
            InlineKeyboardButton("📢 The Arcade C...", url="https://t.me/your_channel_link"), # Replace with your link
            InlineKeyboardButton("🎫 Support", callback_data="view_support")
        ],
        [InlineKeyboardButton("❓ What is P1?", callback_data="what_is_p1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Check if the trigger came from a command or a callback button
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the subscription tier pricing selection."""
    query = update.callback_query
    await query.answer()
    
    text = (
        "🛍️ **Purchase a Subscription**\n\n"
        "Select a plan below. Payment is accepted in BTC, ETH or LTC "
        "and confirmed automatically on-chain."
    )
    
    keyboard = [
        [InlineKeyboardButton("📅 Monthly — £450", callback_data="sub_monthly_450")],
        [InlineKeyboardButton("📆 Yearly — £2,249", callback_data="sub_yearly_2249")],
        [InlineKeyboardButton("∞ Lifetime — £2,699", callback_data="sub_lifetime_2699")],
        [InlineKeyboardButton("← Back", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def sip_addon_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, base_plan: str, base_price: int, include_sip: bool = False) -> None:
    """Displays the SIP setup add-on step."""
    query = update.callback_query
    await query.answer()
    
    sip_cost = 250 if include_sip else 0
    total_price = base_price + sip_cost
    
    text = (
        "🔧 **SIP Setup — Optional Add-on**\n\n"
        "Save the hassle of sourcing a SIP provider yourself.\n\n"
        "For an extra **£250**, we'll configure a working SIP trunk on your account "
        "using our own routes — ready to dial from day one.\n\n"
        f"**Plan total with add-on: £{total_price:,}**"
    )
    
    # Dynamic button showing checkbox state
    sip_button_text = "✅ Add SIP Setup (+£250)" if include_sip else "⬜ Add SIP Setup (+£250)"
    sip_callback = f"toggle_sip_{base_plan}_{base_price}_0" if include_sip else f"toggle_sip_{base_plan}_{base_price}_1"
    
    keyboard = [
        [InlineKeyboardButton(sip_button_text, callback_data=sip_callback)],
        [InlineKeyboardButton("➡️ No thanks, continue" if not include_sip else "➡️ Continue", callback_data=f"checkout_{base_plan}_{total_price}")],
        [InlineKeyboardButton("← Change Plan", callback_data="view_subscription")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str, price: int) -> None:
    """Placeholder checkout screen for crypto payment processing."""
    query = update.callback_query
    await query.answer()
    
    text = (
        f"💳 **Checkout**\n\n"
        f"Selected Plan: **{plan.capitalize()}**\n"
        f"Total Amount: **£{price:,}**\n\n"
        "⚠️ _Crypto address generation features will be linked here in the next build step._"
    )
    keyboard = [[InlineKeyboardButton("← Back", callback_data="view_subscription")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# --- Button Routing Logic ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Routes all incoming inline button clicks to their proper screens."""
    query = update.callback_query
    data = query.data
    
    if data == "main_menu":
        await start(update, context)
    elif data == "view_subscription":
        await subscription_menu(update, context)
    elif data.startswith("sub_"):
        # Parsing data strings like: sub_monthly_450
        parts = data.split("_")
        plan = parts[1]
        price = int(parts[2])
        await sip_addon_menu(update, context, base_plan=plan, base_price=price, include_sip=False)
    elif data.startswith("toggle_sip_"):
        # Parsing data strings like: toggle_sip_monthly_450_1
        parts = data.split("_")
        plan = parts[2]
        price = int(parts[3])
        state = parts[4] == "1"
        await sip_addon_menu(update, context, base_plan=plan, base_price=price, include_sip=state)
    elif data.startswith("checkout_"):
        parts = data.split("_")
        plan = parts[1]
        price = int(parts[2])
        await handle_checkout(update, context, plan=plan, price=price)
    elif data == "view_support":
        await query.answer("Support portal link coming soon!", show_alert=True)
    elif data == "what_is_p1":
        await query.answer("P1 refers to Automated Press-1 Interactive Voice Response (IVR) dialing.", show_alert=True)

def main() -> None:
    """Starts the bot application."""
    # Retrieve token from environment variables
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN found in environment variables!")
        return

    application = Application.builder().token(token).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Start the Bot
    application.run_polling()

if __name__ == "__main__":
    main()
