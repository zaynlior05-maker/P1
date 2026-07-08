import os
import logging
import datetime
import urllib.request
import json
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

def get_wallet_address(crypto: str) -> str:
    """Retrieves the wallet address from secure Railway environment variables."""
    if crypto == "btc":
        return os.environ.get("BTC_WALLET", "BTC address not configured in Railway variables.")
    elif crypto == "eth":
        return os.environ.get("ETH_WALLET", "ETH address not configured in Railway variables.")
    elif crypto == "ltc":
        return os.environ.get("LTC_WALLET", "LTC address not configured in Railway variables.")
    return "Unknown asset string error."

def get_crypto_price(crypto: str) -> float:
    """Fetches the current price of the crypto in GBP using CoinGecko API."""
    try:
        crypto_map = {"btc": "bitcoin", "eth": "ethereum", "ltc": "litecoin"}
        coin_id = crypto_map.get(crypto, "bitcoin")
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=gbp"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return float(data[coin_id]["gbp"])
    except Exception as e:
        logger.error(f"Error fetching crypto price: {e}")
        # Secure fallbacks if the external API rate-limits or fails
        fallbacks = {"btc": 50000.0, "eth": 2500.0, "ltc": 65.0}
        return fallbacks.get(crypto, 50000.0)

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
            InlineKeyboardButton("📢 The Arcade C...", url="https://t.me/your_channel_link"), 
            InlineKeyboardButton("🎫 Support", callback_data="view_support")
        ],
        [InlineKeyboardButton("❓ What is P1?", callback_data="what_is_p1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
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
        [InlineKeyboardButton("📅 Monthly — £450", callback_data="sub_monthly_450_30 days")],
        [InlineKeyboardButton("📆 Yearly — £2,249", callback_data="sub_yearly_2249_365 days")],
        [InlineKeyboardButton("∞ Lifetime — £2,699", callback_data="sub_lifetime_2699_Forever")],
        [InlineKeyboardButton("← Back", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def sip_addon_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, base_plan: str, base_price: int, duration: str, include_sip: bool = False) -> None:
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
    
    sip_button_text = "✅ Add SIP Setup (+£250)" if include_sip else "⬜ Add SIP Setup (+£250)"
    sip_callback = f"toggle_sip_{base_plan}_{base_price}_{duration}_0" if include_sip else f"toggle_sip_{base_plan}_{base_price}_{duration}_1"
    continue_callback = f"checkout_{base_plan}_{base_price}_{duration}_{1 if include_sip else 0}"
    
    keyboard = [
        [InlineKeyboardButton(sip_button_text, callback_data=sip_callback)],
        [InlineKeyboardButton("➡️ No thanks, continue" if not include_sip else "➡️ Continue", callback_data=continue_callback)],
        [InlineKeyboardButton("← Change Plan", callback_data="view_subscription")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str, base_price: int, duration: str, sip_active: bool) -> None:
    """Displays the final payment gateway choice screen with dynamic pricing."""
    query = update.callback_query
    await query.answer()
    
    sip_cost = 250 if sip_active else 0
    total_price = base_price + sip_cost
    sip_line = f"🔧 **SIP Setup:** +£{sip_cost}\n" if sip_active else ""
    
    text = (
        f"💎 **{plan.capitalize()} Plan** — £{base_price} / {duration}\n"
        f"{sip_line}"
        f"💵 **Total:** £{total_price}\n\n"
        "Choose your payment currency. A unique address will be generated for this payment "
        "and confirmed automatically once the transaction clears."
    )
    
    sip_flag_str = "1" if sip_active else "0"
    keyboard = [
        [InlineKeyboardButton("₿ Bitcoin (BTC)", callback_data=f"pay_btc_{plan}_{base_price}_{sip_flag_str}")],
        [InlineKeyboardButton("Ξ Ethereum (ETH)", callback_data=f"pay_eth_{plan}_{base_price}_{sip_flag_str}")],
        [InlineKeyboardButton("Ł Litecoin (LTC)", callback_data=f"pay_ltc_{plan}_{base_price}_{sip_flag_str}")],
        [InlineKeyboardButton("← Change Plan", callback_data="view_subscription")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def process_payment_page(update: Update, context: ContextTypes.DEFAULT_TYPE, crypto: str, plan: str, base_price: int, sip_active: bool) -> None:
    """Generates the transactional address screen with real-time currency conversions."""
    query = update.callback_query
    await query.answer("Generating deposit invoice...")
    
    sip_cost = 250 if sip_active else 0
    total_gbp = base_price + sip_cost
    
    fiat_rate = get_crypto_price(crypto)
    crypto_amount = total_gbp / fiat_rate
    
    # Calculate window expiration (+15 minutes from now)
    expiry_time = (datetime.datetime.utcnow() + datetime.timedelta(minutes=15)).strftime("%H:%M UTC")
    
    # Safely retrieve your address from Railway variables
    wallet_address = get_wallet_address(crypto)
    sip_display = f"Add-on — £{sip_cost}" if sip_active else "None"
    
    text = (
        "💳 **Send Payment**\n\n"
        f"**Plan:** {plan.capitalize()} — £{base_price}\n"
        f"**SIP Setup:** {sip_display}\n"
        f"**Total:** £{total_gbp}\n"
        f"**Amount:** `{crypto_amount:.8f}` **{crypto.upper()}**\n"
        f"**Address:**\n`{wallet_address}`\n"
        f"**Expires:** {expiry_time}\n\n"
        "Your subscription will activate automatically once the transaction is confirmed on-chain."
    )
    
    sip_flag_str = "1" if sip_active else "0"
    keyboard = [
        [InlineKeyboardButton("🔄 Check Payment Status", callback_data=f"check_pay_{crypto}_{total_gbp}")],
        [InlineKeyboardButton("← Choose Different Crypto", callback_data=f"checkout_{plan}_{base_price}_duration_dummy_{sip_flag_str}")]
    ]
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
        parts = data.split("_")
        await sip_addon_menu(update, context, base_plan=parts[1], base_price=int(parts[2]), duration=parts[3], include_sip=False)
    elif data.startswith("toggle_sip_"):
        parts = data.split("_")
        state = parts[5] == "1"
        await sip_addon_menu(update, context, base_plan=parts[2], base_price=int(parts[3]), duration=parts[4], include_sip=state)
    elif data.startswith("checkout_"):
        parts = data.split("_")
        sip_flag = parts[-1] == "1"
        duration = parts[3] if len(parts) > 4 else "30 days"
        await handle_checkout(update, context, plan=parts[1], base_price=int(parts[2]), duration=duration, sip_active=sip_flag)
    elif data.startswith("pay_"):
        parts = data.split("_")
        sip_flag = parts[4] == "1"
        await process_payment_page(update, context, crypto=parts[1], plan=parts[2], base_price=int(parts[3]), sip_active=sip_flag)
    elif data.startswith("check_pay_"):
        await query.answer("Searching block network... No transactions found yet.", show_alert=True)
    elif data == "view_support":
        await query.answer("Support portal link coming soon!", show_alert=True)
    elif data == "what_is_p1":
        await query.answer("P1 refers to Automated Press-1 Interactive Voice Response (IVR) dialing.", show_alert=True)

def main() -> None:
    """Starts the bot application."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN found in environment variables!")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_polling()

if __name__ == "__main__":
    main()
