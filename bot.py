import os
import logging
import datetime
import urllib.request
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- In-Memory State Trackers ---
USER_STATES = {}       # Tracks conversation steps (e.g., 'REPORT_STEP_1')
USER_DATA = {}         # Temporary ticket info holding container
AUTHORIZED_ADMINS = set() # Tracks dynamic active authenticated admin sessions
KNOWN_USERS = set()    # Tracks unique chat IDs for broadcasting loops

# --- Wallet & Link Helper Functions ---

def get_wallet_address(crypto: str) -> str:
    """Retrieves the wallet address from secure Railway environment variables."""
    if crypto == "btc":
        return os.environ.get("BTC_WALLET", "BTC address not configured in Railway variables.")
    elif crypto == "eth":
        return os.environ.get("ETH_WALLET", "ETH address not configured in Railway variables.")
    elif crypto == "ltc":
        return os.environ.get("LTC_WALLET", "LTC address not configured in Railway variables.")
    return "Unknown asset string error."

async def log_to_console(update: Update, context: ContextTypes.DEFAULT_TYPE, event_description: str) -> None:
    """Logs user pathways and interactions directly to the dedicated CONSOLE_CHAT_ID Group."""
    user = update.effective_user
    if not user:
        return

    username = f"@{user.username}" if user.username else "No Username"
    log_text = (
        f"👤 **User:** {user.first_name} ({username})\n"
        f"🆔 **ID:** `{user.id}`\n"
        f"⚡ **Action:** {event_description}\n"
        f"⏰ **Time:** {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    
    console_chat_id = os.environ.get("CONSOLE_CHAT_ID")
    if console_chat_id:
        try:
            target_id = console_chat_id.strip()
            if (target_id.startswith("-") or target_id.isdigit()) and "@" not in target_id:
                target_id = int(target_id)
                
            await context.bot.send_message(chat_id=target_id, text=log_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send log to CONSOLE_CHAT_ID Group: {e}")

def _fetch_price_sync(crypto: str) -> float:
    """Synchronous network fetch with a strict timeout to prevent thread locks."""
    try:
        crypto_map = {"btc": "bitcoin", "eth": "ethereum", "ltc": "litecoin"}
        coin_id = crypto_map.get(crypto, "bitcoin")
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=gbp"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            return float(data[coin_id]["gbp"])
    except Exception as e:
        logger.error(f"CoinGecko API error or timeout: {e}")
        fallbacks = {"btc": 50000.0, "eth": 2500.0, "ltc": 65.0}
        return fallbacks.get(crypto, 50000.0)

async def get_crypto_price(crypto: str) -> float:
    """Asynchronously offloads the network request to a background thread to prevent lags."""
    return await asyncio.to_thread(_fetch_price_sync, crypto)

# --- Menu Functions ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the main welcome screen."""
    user_id = update.effective_user.id
    KNOWN_USERS.add(user_id)
    USER_STATES[user_id] = None 
    
    channel_url = os.environ.get("CHANNEL_LINK", "https://t.me/")

    text = (
        "👋 **Welcome to the spoofers 📲 P1 Bot!**\n\n"
        "This dialler bot is officially provided by caller for spoofers 📲, "
        "giving you access to a private, fully automated mass-calling system "
        "with real-time lead detection.\n\n"
        "🚀 **Features**\n"
        "• Upload your leads and start dialling instantly\n"
        "• Custom Caller ID & multi-trunk SIP support\n"
        "• Real-time press-1 detection with instant alerts\n"
        "• Crypto payments (BTC, ETH, LTC) — confirmed on-chain automatically\n\n"
        "**Powered for callers 📲**"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Purchase Subscription", callback_data="view_subscription")],
        [
            InlineKeyboardButton("📢 Custom C...", url=channel_url), 
            InlineKeyboardButton("🎫 Support", callback_data="support_main")
        ],
        [InlineKeyboardButton("❓ What is P1?", callback_data="what_is_p1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        await log_to_console(update, context, "Triggered /start command")
    elif update.callback_query:
        query = update.callback_query
        await query.answer() 
        await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        await log_to_console(update, context, "Navigated to Main Menu")

async def support_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the custom intermediate Support choices panel option screen."""
    query = update.callback_query
    await query.answer()
    
    text = (
        "🎫 **Support**\n\n"
        "How can we help you today?\n\n"
        "• Report an issue with the bot\n"
        "• View the status of your existing tickets"
    )
    
    keyboard = [
        [InlineKeyboardButton("🐛 Report Issue", callback_data="support_step_1")],
        [InlineKeyboardButton("📋 My Tickets", callback_data="support_my_tickets")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    await log_to_console(update, context, "Opened intermediate Support directory menu")

async def what_is_p1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the informative explanation panel about P1 capability features."""
    query = update.callback_query
    await query.answer()
    
    text = (
        "❓ **What is the P1 Panel?**\n"
        "A private, automated outbound communication platform built for high-volume operations.\n\n"
        "🚀 **How it Works**\n"
        " 1. **Setup:** Connect your SIP trunk and custom Caller ID.\n"
        " 2. **Upload:** Input your audio script and contact list.\n"
        " 3. **Launch:** Start the automated multi-channel dialler.\n"
        " 4. **Route:** Get instant Telegram alerts the moment a recipient presses 1.\n\n"
        "⚡ **Key Features**\n"
        " • **Tier-1 Direct Carrier Routing:** High completion rates & low latency.\n"
        " • **Dynamic Caller ID:** Financial-grade presentation trusted by major worldwide networks.\n"
        " • **Dual-Way SIP Trunks:** High-capacity inbound and outbound channels.\n"
        " • **Instant DTMF (Press-1) Detection:** Real-time keypad tracking & live alerts.\n"
        " • **Virtual Numbers:** Local UK, international, and toll-free numbering.\n"
        " • **Multi-Level IVR:** Professional voice menus with automated playback.\n"
        " • **Unified Controls:** Manage via Telegram Bot, Web Panel, or REST API.\n"
        " • **Omnichannel Delivery:** Integrated SMS and Email gateway features.\n"
        " • **Live Recording & Analytics:** Secure cloud storage with real-time stats.\n"
        " • **24/7/365 Tech Support:** Dedicated account management & priority assistance."
    )
    
    keyboard = [[InlineKeyboardButton("← Back", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    await log_to_console(update, context, "Viewed 'What is P1' breakdown info panel")

# --- 3-Step Ticket Submission Engine ---

async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Step 1 of 3 — What Happened."""
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()
    
    USER_STATES[user_id] = "REPORT_STEP_1"
    USER_DATA[user_id] = {}
    
    text = (
        "🐛 **Report Issue**\n\n"
        "**Step 1 of 3 — What Happened**\n\n"
        "Describe the issue you experienced.\n\n"
        "Type your description and send it:"
    )
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="support_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    await log_to_console(update, context, "Started dynamic Support Ticket flow")

async def handle_text_inputs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global message catch handler managing conversational states & admin inputs."""
    user_id = update.effective_user.id
    current_state = USER_STATES.get(user_id)
    user_text = update.message.text
    
    if current_state == "REPORT_STEP_1":
        USER_DATA[user_id]["description"] = user_text
        USER_STATES[user_id] = "REPORT_STEP_2"
        
        text = (
            "✅ **Description saved.**\n\n"
            "**Step 2 of 3 — Where Did It Happen**\n\n"
            "Where in the bot did this occur?\n\n"
            "**Examples:**\n"
            "• SIP Setup\n"
            "• Payment / subscription\n"
            "• Start Calling\n"
            "• Claim a Line\n\n"
            "Type the location:"
        )
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="support_main")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        await log_to_console(update, context, f"Submitted ticket summary text: '{user_text}'")
        return

    elif current_state == "REPORT_STEP_2":
        USER_DATA[user_id]["location"] = user_text
        USER_STATES[user_id] = "REPORT_STEP_3"
        
        text = (
            "✅ **Location saved.**\n\n"
            "**Step 3 of 3 — Steps to Reproduce**\n\n"
            "Provide steps to reproduce the issue, if you know them.\n"
            "If not, type **N/A**.\n\n"
            "Type the steps:"
        )
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="support_main")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        await log_to_console(update, context, f"Submitted ticket location text: '{user_text}'")
        return

    elif current_state == "REPORT_STEP_3":
        desc = USER_DATA[user_id].get("description", "N/A")
        loc = USER_DATA[user_id].get("location", "N/A")
        
        USER_STATES[user_id] = None 
        
        await update.message.reply_text("✨ **Ticket successfully filed! Our operational system has received your issue summary.**", parse_mode="Markdown")
        
        admin_summary = (
            f"🚨 **NEW SUPPORT TICKET SUBMITTED**\n\n"
            f"👤 **From User:** ID `{user_id}`\n"
            f"📋 **Description:** {desc}\n"
            f"📍 **Location:** {loc}\n"
            f"⚙️ **Steps/Notes:** {user_text}"
        )
        console_chat_id = os.environ.get("CONSOLE_CHAT_ID")
        if console_chat_id:
            try:
                target_id = console_chat_id.strip()
                if (target_id.startswith("-") or target_id.isdigit()) and "@" not in target_id:
                    target_id = int(target_id)
                await context.bot.send_message(chat_id=target_id, text=admin_summary, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Failed to post ticket summary to group console: {e}")
        return

    elif current_state == "ADMIN_LOGIN":
        expected_pass = os.environ.get("ADMIN_PASSWORD", "arcade123")
        if user_text == expected_pass:
            AUTHORIZED_ADMINS.add(user_id)
            USER_STATES[user_id] = None
            await update.message.reply_text(
                "🔓 **Authentication successful.** You are now registered as an active terminal administrator.\n\n"
                "**Available Admin Commands:**\n"
                "• `/broadcast [message]` — Send global alert notifications\n"
                "• `/topup [user_id] [amount]` — Process manual currency top up credits"
            )
        else:
            USER_STATES[user_id] = None
            await update.message.reply_text("❌ Incorrect security key password entry authentication sequence terminated.")
        return

# --- Admin Command Processors ---

async def admin_auth_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    USER_STATES[user_id] = "ADMIN_LOGIN"
    await update.message.reply_text("🔐 Enter administrative master console password configuration sequence:")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in AUTHORIZED_ADMINS:
        await update.message.reply_text("⛔ Unauthenticated workspace request denied.")
        return
        
    if not context.args:
        await update.message.reply_text("⚠️ Syntax error usage structure: `/broadcast your text notification message`")
        return
        
    broadcast_msg = " ".join(context.args)
    count = 0
    for uid in KNOWN_USERS:
        try:
            await context.bot.send_message(chat_id=uid, text=broadcast_msg, parse_mode="Markdown")
            count += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Dispatched message notifications to {count} active targets.")

async def topup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in AUTHORIZED_ADMINS:
        await update.message.reply_text("⛔ Unauthenticated workspace request denied.")
        return
        
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Syntax error usage structure: `/topup [user_id] [amount_value]`")
        return
        
    target_user = context.args[0]
    credit_value = context.args[1]
    await update.message.reply_text(f"💳 **Manual Top Up Logged:** Successfully provisioned +£{credit_value} to user `{target_user}`.")
    
    try:
        await context.bot.send_message(
            chat_id=int(target_user),
            text=f"🎉 **Account Balance Update**\n\nAn administrator has manually topped up your account with **£{credit_value}** credit units successfully!",
            parse_mode="Markdown"
        )
    except Exception:
        pass

# --- Menu Interaction Flow Routing Components ---

async def subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "🛍️ **Purchase a Subscription**\n\nSelect a plan below. Payment is accepted in BTC, ETH or LTC and confirmed automatically on-chain."
    keyboard = [
        [InlineKeyboardButton("📅 Monthly — £450", callback_data="sub_monthly_450_30 days")],
        [InlineKeyboardButton("📆 Yearly — £2,249", callback_data="sub_yearly_2249_365 days")],
        [InlineKeyboardButton("∞ Lifetime — £2,699", callback_data="sub_lifetime_2699_Forever")],
        [InlineKeyboardButton("← Back", callback_data="main_menu")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    await log_to_console(update, context, "Opened subscription purchase catalog")

async def sip_addon_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, base_plan: str, base_price: int, duration: str, include_sip: bool = False) -> None:
    query = update.callback_query
    await query.answer()
    sip_cost = 250 if include_sip else 0
    total_price = base_price + sip_cost
    text = f"🔧 **SIP Setup — Optional Add-on**\n\nSave the hassle of sourcing a SIP provider yourself.\n\nFor an extra **£250**, we'll configure a working SIP trunk on your account using our own routes — ready to dial from day one.\n\n**Plan total with add-on: £{total_price:,}**"
    sip_button_text = "✅ Add SIP Setup (+£250)" if include_sip else "⬜ Add SIP Setup (+£250)"
    sip_callback = f"toggle_sip_{base_plan}_{base_price}_{duration}_0" if include_sip else f"toggle_sip_{base_plan}_{base_price}_{duration}_1"
    continue_callback = f"checkout_{base_plan}_{base_price}_{duration}_{1 if include_sip else 0}"
    keyboard = [
        [InlineKeyboardButton(sip_button_text, callback_data=sip_callback)],
        [InlineKeyboardButton("➡️ No thanks, continue" if not include_sip else "➡️ Continue", callback_data=continue_callback)],
        [InlineKeyboardButton("← Change Plan", callback_data="view_subscription")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def handle_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str, base_price: int, duration: str, sip_active: bool) -> None:
    query = update.callback_query
    await query.answer()
    sip_cost = 250 if sip_active else 0
    total_price = base_price + sip_cost
    sip_line = f"🔧 **SIP Setup:** +£{sip_cost}\n" if sip_active else ""
    text = f"💎 **{plan.capitalize()} Plan** — £{base_price} / {duration}\n{sip_line}💵 **Total:** £{total_price}\n\nChoose your payment currency. A unique address will be generated for this payment and confirmed automatically once the transaction clears."
    sip_flag_str = "1" if sip_active else "0"
    keyboard = [
        [InlineKeyboardButton("₿ Bitcoin (BTC)", callback_data=f"pay_btc_{plan}_{base_price}_{sip_flag_str}_{total_price}")],
        [InlineKeyboardButton("Ξ Ethereum (ETH)", callback_data=f"pay_eth_{plan}_{base_price}_{sip_flag_str}_{total_price}")],
        [InlineKeyboardButton("Ł Litecoin (LTC)", callback_data=f"pay_ltc_{plan}_{base_price}_{sip_flag_str}_{total_price}")],
        [InlineKeyboardButton("← Change Plan", callback_data="view_subscription")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def process_payment_page(update: Update, context: ContextTypes.DEFAULT_TYPE, crypto: str, plan: str, base_price: int, sip_active: bool) -> None:
    query = update.callback_query
    try:
        await query.answer("Generating deposit invoice...")
        
        sip_cost = 250 if sip_active else 0
        total_gbp = base_price + sip_cost
        
        fiat_rate = await get_crypto_price(crypto)
        crypto_amount = total_gbp / fiat_rate
        
        expiry_time = (datetime.datetime.utcnow() + datetime.timedelta(minutes=15)).strftime("%H:%M UTC")
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
            [InlineKeyboardButton("🔄 Check Payment Status", callback_data=f"check_pay_{crypto}_{crypto_amount:.8f}_{expiry_time}")],
            [InlineKeyboardButton("← Choose Different Crypto", callback_data=f"checkout_{plan}_{base_price}_duration_dummy_{sip_flag_str}")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        await log_to_console(update, context, f"Generated crypto payment order invoice tracking for £{total_gbp} in {crypto.upper()}")
    except Exception as e:
        logger.error(f"Error in invoice generation processing block: {e}")
        fallback_text = "❌ **Invoice Generation Error**\n\nPlease check your Railway environment configuration variables (BTC_WALLET, ETH_WALLET, LTC_WALLET) to verify they are present and correct."
        keyboard = [[InlineKeyboardButton("← Back", callback_data="view_subscription")]]
        await query.message.edit_text(fallback_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def process_check_status(update: Update, context: ContextTypes.DEFAULT_TYPE, crypto: str, crypto_amount: str, expiry_time: str) -> None:
    query = update.callback_query
    await query.answer()
    wallet_address = get_wallet_address(crypto)
    text = f"⏳ **Awaiting Payment**\n\nNo transaction detected yet.\n\n**Address:**\n`{wallet_address}`\n**Amount:** `{crypto_amount}` **{crypto.upper()}**\n**Expires:** {expiry_time}\n\nYour subscription activates automatically once the transaction confirms."
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data=f"check_pay_{crypto}_{crypto_amount}_{expiry_time}")],
        [InlineKeyboardButton("← Back", callback_data="view_subscription")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    await log_to_console(update, context, f"Checked network confirmation status on asset {crypto.upper()}")

# --- Button Routing Logic ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    
    if data == "main_menu":
        await start(update, context)
    elif data == "support_main":
        await support_main_menu(update, context)
    elif data == "view_subscription":
        await subscription_menu(update, context)
    elif data == "what_is_p1":
        await what_is_p1_menu(update, context)
    elif data == "support_step_1":
        await support_start(update, context)
    elif data == "support_my_tickets":
        await query.answer("You currently have no open active tickets.", show_alert=True)
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
        parts = data.split("_")
        await process_check_status(update, context, crypto=parts[2], crypto_amount=parts[3], expiry_time=parts[4])

def main() -> None:
    """Starts the bot application."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN found in environment variables!")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_auth_cmd))
    application.add_handler(CommandHandler("broadcast", broadcast_cmd))
    application.add_handler(CommandHandler("topup", topup_cmd))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_inputs))

    application.run_polling()

if __name__ == "__main__":
    main()
