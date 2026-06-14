from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.cost_calculator import calculate
from bot.sheets_client import SheetsClient

# ---------------------------------------------------------------------------
# Conversation states (integers)
# ---------------------------------------------------------------------------
ASK_TAILOR_NAME = 1
ASK_PRODUCT_NAME = 2
ASK_BATCH_COUNT = 3
ASK_BATCH_DETAILS = 4
ASK_SEWING_COST = 5
ASK_ACCESSORIES_COST = 6
ASK_DELIVERY_COST = 7
ASK_ADDITIONAL_COST = 8
ASK_SIZE_COUNT = 9
ASK_SIZE_DETAILS = 10
SHOW_RESULT = 11
CONFIRM_SAVE = 12


def _get_sheets(context) -> SheetsClient | None:
    """Return a SheetsClient instance from bot_data or None if not configured."""
    return context.bot_data.get("sheets_client")


# ---------------------------------------------------------------------------
# Entry point – /start
# ---------------------------------------------------------------------------
async def start(update: Update, _context) -> int:
    """Greet the user and ask for the tailor name."""
    await update.message.reply_text(
        "مرحباً بك في بوت حساب تكاليف الخياطة 👋\n\n"
        "سأساعدك في حساب تكلفة إنتاج منتج خطوة بخطوة.\n"
        "لإلغاء الحساب في أي وقت اكتب /cancel\n\n"
        "الرجاء إدخال اسم الخياط:"
    )
    return ASK_TAILOR_NAME


# ---------------------------------------------------------------------------
# State 1 – Tailor name
# ---------------------------------------------------------------------------
async def ask_tailor_name(update: Update, context) -> int:
    """Store tailor name and ask for product name."""
    context.user_data["tailor_name"] = update.message.text.strip()
    await update.message.reply_text(
        f"اسم الخياط: {context.user_data['tailor_name']}\n\n"
        "الرجاء إدخال اسم المنتج:"
    )
    return ASK_PRODUCT_NAME


# ---------------------------------------------------------------------------
# State 2 – Product name
# ---------------------------------------------------------------------------
async def ask_product_name(update: Update, context) -> int:
    """Store product name and ask for batch count."""
    context.user_data["product_name"] = update.message.text.strip()
    await update.message.reply_text(
        f"اسم المنتج: {context.user_data['product_name']}\n\n"
        "ما عدد مصادر القماش؟ (أدخل رقم)"
    )
    return ASK_BATCH_COUNT


# ---------------------------------------------------------------------------
# State 2 – Number of fabric batches
# ---------------------------------------------------------------------------
async def ask_batch_count(update: Update, context) -> int:
    """Validate N and start collecting batch #1."""
    text = update.message.text.strip()
    if not text.isdigit() or int(text) < 1:
        await update.message.reply_text(
            "❌ الرجاء إدخال رقم صحيح أكبر من 0.\n"
            "ما عدد مصادر القماش؟"
        )
        return ASK_BATCH_COUNT

    context.user_data["batch_count"] = int(text)
    context.user_data["current_batch"] = 0
    context.user_data["fabric_batches"] = []

    return await _ask_next_batch(update, context)


async def _ask_next_batch(update: Update, context) -> int:
    """Ask for the next fabric batch details, or move to sewing cost."""
    current = context.user_data["current_batch"]
    total = context.user_data["batch_count"]

    if current >= total:
        return await _transition_from_fabric(update, context)

    i = current + 1
    await update.message.reply_text(
        f"الدفعة رقم {i}:\n"
        "- اسم اللون أو نوع القماش:\n"
        "- الكمية بالمتر:\n"
        "- سعر المتر (دج):\n\n"
        "الرجاء إرسال الإجابة في ثلاث أسطر (قيمة واحدة في كل سطر)."
    )
    return ASK_BATCH_DETAILS


async def _transition_from_fabric(update: Update, context) -> int:
    """Move to asking sewing cost per unit after all batches collected."""
    await update.message.reply_text("تم جمع كل أنواع القماش ✅\n\nأدخل تكلفة خياطة القطعة الواحدة (دج):")
    return ASK_SEWING_COST


# ---------------------------------------------------------------------------
# State 3 – Fabric batch details (loop)
# ---------------------------------------------------------------------------
async def ask_batch_details(update: Update, context) -> int:
    """Parse multi-line batch input: colour, metres, price."""
    text = update.message.text.strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    if len(lines) < 3:
        await update.message.reply_text(
            "❌ الرجاء إدخال ثلاث قيم في ثلاث أسطر:\n"
            "- السطر الأول: اسم اللون أو نوع القماش\n"
            "- السطر الثاني: الكمية بالمتر\n"
            "- السطر الثالث: سعر المتر (دج)\n\n"
            "حاول مرة أخرى:"
        )
        return ASK_BATCH_DETAILS

    color = lines[0]
    try:
        meters = float(lines[1])
        price = float(lines[2])
    except ValueError:
        await update.message.reply_text(
            "❌ الكمية والسعر يجب أن يكونا أرقاماً صحيحة.\n"
            "حاول مرة أخرى:"
        )
        return ASK_BATCH_DETAILS

    if meters <= 0 or price < 0:
        await update.message.reply_text(
            "❌ الكمية يجب أن تكون أكبر من 0، والسعر يجب أن يكون 0 أو أكثر.\n"
            "حاول مرة أخرى:"
        )
        return ASK_BATCH_DETAILS

    context.user_data["fabric_batches"].append(
        {"color": color, "meters": meters, "price_per_meter": price}
    )
    context.user_data["current_batch"] += 1

    return await _ask_next_batch(update, context)


# ---------------------------------------------------------------------------
# State 4 – Sewing cost per unit
# ---------------------------------------------------------------------------
async def ask_sewing_cost(update: Update, context) -> int:
    """Validate and store sewing cost per unit, then ask for accessories total."""
    try:
        val = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ الرجاء إدخال رقم صحيح.\nأدخل تكلفة خياطة القطعة الواحدة (دج):"
        )
        return ASK_SEWING_COST

    if val < 0:
        await update.message.reply_text(
            "❌ التكلفة لا يمكن أن تكون سالبة.\nأدخل تكلفة خياطة القطعة الواحدة (دج):"
        )
        return ASK_SEWING_COST

    context.user_data["sewing_cost_per_unit"] = val
    await update.message.reply_text("أدخل تكلفة الإكسسوارات الإجمالية (دج):")
    return ASK_ACCESSORIES_COST


# ---------------------------------------------------------------------------
# State 5 – Accessories cost (total)
# ---------------------------------------------------------------------------
async def ask_accessories_cost(update: Update, context) -> int:
    """Validate and store accessories total cost, then ask for delivery cost."""
    try:
        val = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ الرجاء إدخال رقم صحيح.\nأدخل تكلفة الإكسسوارات الإجمالية (دج):"
        )
        return ASK_ACCESSORIES_COST

    if val < 0:
        await update.message.reply_text(
            "❌ التكلفة لا يمكن أن تكون سالبة.\nأدخل تكلفة الإكسسوارات الإجمالية (دج):"
        )
        return ASK_ACCESSORIES_COST

    context.user_data["accessories_cost"] = val
    await update.message.reply_text("أدخل تكلفة التوصيل الإجمالية (دج):")
    return ASK_DELIVERY_COST


# ---------------------------------------------------------------------------
# State 6 – Delivery cost (total)
# ---------------------------------------------------------------------------
async def ask_delivery_cost(update: Update, context) -> int:
    """Validate and store delivery total cost, then ask for additional costs."""
    try:
        val = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ الرجاء إدخال رقم صحيح.\nأدخل تكلفة التوصيل الإجمالية (دج):"
        )
        return ASK_DELIVERY_COST

    if val < 0:
        await update.message.reply_text(
            "❌ التكلفة لا يمكن أن تكون سالبة.\nأدخل تكلفة التوصيل الإجمالية (دج):"
        )
        return ASK_DELIVERY_COST

    context.user_data["delivery_cost"] = val
    await update.message.reply_text("أدخل التكاليف الإضافية للقطعة الواحدة (دج):")
    return ASK_ADDITIONAL_COST


# ---------------------------------------------------------------------------
# State 7 – Additional costs per unit
# ---------------------------------------------------------------------------
async def ask_additional_cost(update: Update, context) -> int:
    """Validate and store additional costs per unit, then ask for size count."""
    try:
        val = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ الرجاء إدخال رقم صحيح.\nأدخل التكاليف الإضافية للقطعة الواحدة (دج):"
        )
        return ASK_ADDITIONAL_COST

    if val < 0:
        await update.message.reply_text(
            "❌ التكلفة لا يمكن أن تكون سالبة.\nأدخل التكاليف الإضافية للقطعة الواحدة (دج):"
        )
        return ASK_ADDITIONAL_COST

    context.user_data["additional_costs_per_unit"] = val
    await update.message.reply_text(
        "كم عدد الأحجام المختلفة؟ (مثال: XS, S, M, L, XL)"
    )
    return ASK_SIZE_COUNT


# ---------------------------------------------------------------------------
# State 8 – Number of sizes
# ---------------------------------------------------------------------------
async def ask_size_count(update: Update, context) -> int:
    """Validate M and start collecting size #1."""
    text = update.message.text.strip()
    if not text.isdigit() or int(text) < 1:
        await update.message.reply_text(
            "❌ الرجاء إدخال رقم صحيح أكبر من 0.\n"
            "كم عدد الأحجام المختلفة؟"
        )
        return ASK_SIZE_COUNT

    context.user_data["size_count"] = int(text)
    context.user_data["current_size"] = 0
    context.user_data["sizes"] = []

    return await _ask_next_size(update, context)


async def _ask_next_size(update: Update, context) -> int:
    """Ask for the next size details, or show result."""
    current = context.user_data["current_size"]
    total = context.user_data["size_count"]

    if current >= total:
        return await _show_result(update, context)

    i = current + 1
    await update.message.reply_text(
        f"الحجم رقم {i}:\n"
        "- اسم الحجم (مثال: S, M, L):\n"
        "- الكمية:\n\n"
        "الرجاء إرسال الإجابة في سطرين (قيمة واحدة في كل سطر)."
    )
    return ASK_SIZE_DETAILS


# ---------------------------------------------------------------------------
# State 9 – Size details (loop)
# ---------------------------------------------------------------------------
async def ask_size_details(update: Update, context) -> int:
    """Parse multi-line size input: label and quantity."""
    text = update.message.text.strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    if len(lines) < 2:
        await update.message.reply_text(
            "❌ الرجاء إدخال قيمتين في سطرين:\n"
            "- السطر الأول: اسم الحجم\n"
            "- السطر الثاني: الكمية\n\n"
            "حاول مرة أخرى:"
        )
        return ASK_SIZE_DETAILS

    label = lines[0]
    try:
        qty = int(lines[1])
    except ValueError:
        await update.message.reply_text(
            "❌ الكمية يجب أن تكون رقماً صحيحاً.\nحاول مرة أخرى:"
        )
        return ASK_SIZE_DETAILS

    if qty <= 0:
        await update.message.reply_text(
            "❌ الكمية يجب أن تكون أكبر من 0.\nحاول مرة أخرى:"
        )
        return ASK_SIZE_DETAILS

    context.user_data["sizes"].append({"label": label, "quantity": qty})
    context.user_data["current_size"] += 1

    return await _ask_next_size(update, context)


# ---------------------------------------------------------------------------
# State 10 – Show result
# ---------------------------------------------------------------------------
async def _show_result(update: Update, context) -> int:
    """Calculate and display the cost breakdown."""
    result = calculate(context.user_data)

    lines = [f"━━━━━━━━━━━━━━━━━━━━━━\n🧵 الخياط: {context.user_data.get('tailor_name', '—')}\n📦 المنتج: {context.user_data['product_name']}\n━━━━━━━━━━━━━━━━━━━━━━\n"]
    lines.append("🧵 تفاصيل القماش:")
    for b in context.user_data["fabric_batches"]:
        lines.append(f"  • {b['color']}: {b['meters']}م × {b['price_per_meter']}دج")
    lines.append(f"💰 تكلفة القماش الإجمالية: {result['fabric_cost']} دج")
    lines.append(f"📏 تكلفة القماش للقطعة: {result['fabric_unit_cost']} دج\n")

    lines.append(f"✂️ الخياطة الإجمالية: {result['sewing_cost']} دج")
    lines.append(f"✂️ الخياطة للقطعة: {result['sewing_unit_cost']} دج\n")

    lines.append(f"🪡 الإكسسوارات الإجمالية: {result['accessories_cost']} دج")
    lines.append(f"🪡 الإكسسوارات للقطعة: {result['accessories_unit_cost']} دج\n")

    lines.append(f"🚚 التوصيل الإجمالي: {result['delivery_cost']} دج")
    lines.append(f"🚚 التوصيل للقطعة: {result['delivery_unit_cost']} دج\n")

    lines.append(f"➕ تكاليف إضافية إجمالية: {result['additional_costs']} دج")
    lines.append(f"➕ التكاليف الإضافية للقطعة: {result['additional_unit_cost']} دج\n")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"💵 التكلفة الكلية: {result['total_cost']} دج")
    lines.append(f"📦 مجموع القطع: {result['total_units']}")
    lines.append(f"🏷️ تكلفة القطعة الواحدة: {result['unit_cost']} دج")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━\n")
    lines.append("📐 توزيع الأحجام:")
    for s in result["size_breakdown"]:
        lines.append(f"  • {s['size']}: {s['qty']} قطعة = {s['subtotal']} دج")
    lines.append("")

    await update.message.reply_text("\n".join(lines))

    context.user_data["_result"] = result
    await update.message.reply_text("هل تريد حفظ هذا الحساب في Google Sheets؟ (نعم / لا)")
    return CONFIRM_SAVE


# ---------------------------------------------------------------------------
# State 11 – Confirm save
# ---------------------------------------------------------------------------
async def confirm_save(update: Update, context) -> int:
    """Save to Sheets or skip, then end."""
    answer = update.message.text.strip()
    sheets = _get_sheets(context)
    result = context.user_data.get("_result")

    if answer == "نعم":
        if sheets and result:
            ok = sheets.save_calculation(
                update.effective_user.id,
                context.user_data["tailor_name"],
                context.user_data["product_name"],
                result,
                context.user_data,
            )
            if ok:
                await update.message.reply_text("✅ تم حفظ الحساب بنجاح في Google Sheets!")
            else:
                await update.message.reply_text(
                    "⚠️ تعذر الحفظ في Google Sheets. يرجى التحقق من الإعدادات."
                )
        else:
            await update.message.reply_text(
                "⚠️ Google Sheets غير مهيأ. لم يتم الحفظ."
            )
    else:
        await update.message.reply_text("❌ لم يتم حفظ الحساب.")

    await update.message.reply_text("اكتب /start لحساب جديد.")
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# /cancel – abort at any state
# ---------------------------------------------------------------------------
async def cancel(update: Update, context) -> int:
    """Clear session and end the conversation."""
    context.user_data.clear()
    await update.message.reply_text(
        "تم إلغاء الحساب ❌\n\nاكتب /start لحساب جديد."
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# /history – show past calculations
# ---------------------------------------------------------------------------
async def history(update: Update, context) -> None:
    """Retrieve and display the last 10 calculations for this user."""
    sheets = _get_sheets(context)
    if not sheets:
        await update.message.reply_text("⚠️ Google Sheets غير مهيأ.")
        return

    rows = sheets.get_history(update.effective_user.id, limit=10)
    if not rows:
        await update.message.reply_text("لا توجد حسابات سابقة ❕")
        return

    parts = ["📊 تاريخ حساباتك:\n"]
    for r in reversed(rows):
        parts.append(
            f"• {r.get('product_name', '—')} | "
            f"{r.get('total_cost', '0')} دج | "
            f"{r.get('total_units', '0')} قطعة | "
            f"{r.get('unit_cost', '0')} دج/قطعة"
        )
    await update.message.reply_text("\n".join(parts))


# ---------------------------------------------------------------------------
# Conversation handler
# ---------------------------------------------------------------------------
handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASK_TAILOR_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_tailor_name)
        ],
        ASK_PRODUCT_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_product_name)
        ],
        ASK_BATCH_COUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_batch_count)
        ],
        ASK_BATCH_DETAILS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_batch_details)
        ],
        ASK_SEWING_COST: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_sewing_cost)
        ],
        ASK_ACCESSORIES_COST: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_accessories_cost)
        ],
        ASK_DELIVERY_COST: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_delivery_cost)
        ],
        ASK_ADDITIONAL_COST: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_additional_cost)
        ],
        ASK_SIZE_COUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_size_count)
        ],
        ASK_SIZE_DETAILS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_size_details)
        ],
        SHOW_RESULT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_save)
        ],
        CONFIRM_SAVE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_save)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    name="cost_calculator",
    persistent=False,
)
