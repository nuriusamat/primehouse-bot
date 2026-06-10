import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
        raise ValueError("Переменная окружения BOT_TOKEN не задана!")

logging.basicConfig(level=logging.INFO)

(VOLUME, HEIGHT, FLOORS, COMPLEXITY_BUILD, COMPLEXITY_WORK,
  LOCATION, WORK_TYPES, ADD_CONDITIONS, RESULT) = range(9)

LOCATION_COEFF = {
        "Москва": 1.20,
        "Санкт-Петербург": 1.15,
        "Махачкала": 1.00,
        "Другой город": 1.00,
}

BUILD_COMPLEXITY = {
        "I — простая прямоугольная форма": 0.85,
        "II — 2-3 прямоугольника (Г/Т/П)": 1.00,
        "III — сложная форма, многоугольники": 1.20,
}

WORK_COMPLEXITY = {
        "I — визуальное (паспортизация)": 0.80,
        "II — инструментальное однократное": 1.00,
        "III — инструментальное повторное": 1.20,
}

WORK_TYPES_LIST = {
        "obmer": ("Обмерные работы", "Обмеры, схемы, чертежи (табл. 1/2)", 690.4),
        "inzh": ("Инженерное обследование конструкций", "Дефекты, расчёты, заключение (табл. 3/4)", 604.8),
}

ADD_CONDITIONS_LIST = {
        "jb": ("Ж/б конструкции", 0.25),
        "gosexpert": ("Гос. экспертиза", 0.20),
        "seism8": ("Сейсмичность 8 баллов", 0.20),
        "seism9": ("Сейсмичность 9 баллов", 0.25),
        "monument": ("Памятник архитектуры", 0.25),
        "cramped": ("Стеснённость/захламлённость", 0.15),
        "unheated": ("Неотапливаемые помещения", 0.20),
        "reinforced": ("Усиленные конструкции", 0.20),
}

INDEX_K = 7.07

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        await update.message.reply_text(
            "🏗 *Калькулятор услуг обследования и проектирования*\n"
            "_Прайм Хаус_ | СБЦП 81-2001-25 | Индекс II кв. 2026: к = 7,07\n"
            "НДС не включён. Вскрытия — за счёт заказчика.\n\n"
            "Введите *строительный объём здания* в м³\n_(например: 5000)_",
            parse_mode="Markdown"
        )
        return VOLUME

async def get_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
                    vol = float(update.message.text.replace(",", ".").replace(" ", ""))
                    if vol <= 0: raise ValueError
                                context.user_data["volume"] = vol
except ValueError:
        await update.message.reply_text("❌ Введите число больше 0, например: 5000")
        return VOLUME
    await update.message.reply_text(
                f"✅ Объём: *{vol:,.0f} м³*\n\nВведите *высоту здания* в метрах _(например: 9)_",
                parse_mode="Markdown"
    )
    return HEIGHT

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
                    h = float(update.message.text.replace(",", "."))
                    if h <= 0: raise ValueError
                                context.user_data["height"] = h
except ValueError:
        await update.message.reply_text("❌ Введите число больше 0, например: 9")
        return HEIGHT
    keyboard = [
                [InlineKeyboardButton("1 этаж", callback_data="floors_1")],
                [InlineKeyboardButton("2–5 этажей (малоэтажное)", callback_data="floors_2_5")],
                [InlineKeyboardButton("6–12 этажей (многоэтажное)", callback_data="floors_6_12")],
                [InlineKeyboardButton("13+ этажей (высотное)", callback_data="floors_13")],
    ]
    await update.message.reply_text(
                "🏢 Укажите *этажность* здания:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
    )
    return FLOORS

async def get_floors(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        floors_map = {
            "floors_1": "Одноэтажное",
            "floors_2_5": "Малоэтажное (2–5)",
            "floors_6_12": "Многоэтажное (6–12)",
            "floors_13": "Высотное (13+)",
        }
        context.user_data["floors"] = floors_map[query.data]
        keyboard = [[InlineKeyboardButton(k, callback_data=f"cb_{i}")] for i, k in enumerate(BUILD_COMPLEXITY)]
        await query.edit_message_text(
            "🏛 *Категория сложности здания* (табл. 5 СБЦП):\n\n"
            "• *I* — простая прямоугольная форма\n"
            "• *II* — 2-3 прямоугольника, Г/Т/П-образная\n"
            "• *III* — сложная форма, многоугольники, криволинейные",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return COMPLEXITY_BUILD

async def get_complexity_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        idx = int(query.data.split("_")[1])
        context.user_data["complexity_build"] = list(BUILD_COMPLEXITY.keys())[idx]
        keyboard = [[InlineKeyboardButton(k, callback_data=f"cw_{i}")] for i, k in enumerate(WORK_COMPLEXITY)]
        await query.edit_message_text(
            "🔧 *Категория сложности работ* (табл. 6/7 СБЦП):\n\n"
            "• *I* — только визуальный осмотр, паспортизация\n"
            "• *II* — инструментальное обследование (однократное)\n"
            "• *III* — инструментальное обследование (повторное/мониторинг)",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return COMPLEXITY_WORK

async def get_complexity_work(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        idx = int(query.data.split("_")[1])
        context.user_data["complexity_work"] = list(WORK_COMPLEXITY.keys())[idx]
        keyboard = [[InlineKeyboardButton(loc, callback_data=f"loc_{i}")] for i, loc in enumerate(LOCATION_COEFF)]
        await query.edit_message_text(
            "📍 *Расположение объекта:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        idx = int(query.data.split("_")[1])
        context.user_data["location"] = list(LOCATION_COEFF.keys())[idx]
        context.user_data["work_types"] = []
        keyboard = [
            [InlineKeyboardButton("📐 Обмерные работы (табл. 1/2)", callback_data="wt_obmer")],
            [InlineKeyboardButton("🔍 Инженерное обследование (табл. 3/4)", callback_data="wt_inzh")],
            [InlineKeyboardButton("✅ Оба вида работ", callback_data="wt_both")],
        ]
        await query.edit_message_text(
            "📋 *Выберите виды работ:*\n\n"
            "📐 *Обмерные работы* — обмеры всех помещений, схемы, чертежи\n"
            "🔍 *Инженерное обследование* — дефекты конструкций, расчёты несущей способности, техническое заключение",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return WORK_TYPES

async def get_work_types(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == "wt_obmer": context.user_data["work_types"] = ["obmer"]
elif query.data == "wt_inzh": context.user_data["work_types"] = ["inzh"]
elif query.data == "wt_both": context.user_data["work_types"] = ["obmer", "inzh"]
    context.user_data["add_conditions"] = []
    return await show_add_conditions_menu(query, context)

async def show_add_conditions_menu(query, context):
        selected = context.user_data.get("add_conditions", [])
        keyboard = []
        for key, (name, pct) in ADD_CONDITIONS_LIST.items():
                    mark = "✅" if key in selected else "☐"
                    keyboard.append([InlineKeyboardButton(f"{mark} {name} (+{int(pct*100)}%)", callback_data=f"ac_{key}")])
                keyboard.append([InlineKeyboardButton("➡️ Рассчитать стоимость", callback_data="ac_done")])
    await query.edit_message_text(
                f"➕ *Дополнительные условия* (табл. 10 СБЦП):\n"
                f"_Выбрано: {len(selected)} из {len(ADD_CONDITIONS_LIST)}_\n\n"
                "Нажмите для выбора/снятия. Затем нажмите *Рассчитать*:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
    )
    return ADD_CONDITIONS

async def get_add_conditions(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
    await query.answer()
    if query.data == "ac_done":
                return await calculate_result(query, context)
            key = query.data.replace("ac_", "")
    selected = context.user_data.get("add_conditions", [])
    if key in selected: selected.remove(key)
else: selected.append(key)
    context.user_data["add_conditions"] = selected
    return await show_add_conditions_menu(query, context)

async def calculate_result(query, context: ContextTypes.DEFAULT_TYPE):
        ud = context.user_data
    volume = ud["volume"]
    build_coeff = BUILD_COMPLEXITY[ud["complexity_build"]]
    work_coeff = WORK_COMPLEXITY[ud["complexity_work"]]
    loc_coeff = LOCATION_COEFF[ud["location"]]
    work_types = ud["work_types"]
    add_conditions = ud.get("add_conditions", [])
    add_pct = sum(ADD_CONDITIONS_LIST[k][1] for k in add_conditions)
    total_coeff = build_coeff * work_coeff * loc_coeff * (1 + add_pct) * INDEX_K
    lines = []
    grand_total = 0
    for wt in work_types:
                name, desc, base_rate = WORK_TYPES_LIST[wt]
                cost = base_rate * (volume / 100) * total_coeff
                grand_total += cost
                lines.append(f"📌 *{name}*\n   Ставка: {base_rate} руб/100 м³\n   Стоимость: *≈ {cost:,.0f} ₽*")
            add_list = ""
    if add_conditions:
                add_list = "\n➕ *Доп. условия:* " + ", ".join(ADD_CONDITIONS_LIST[k][0] for k in add_conditions)
            text = (
                        f"📊 *РЕЗУЛЬТАТ РАСЧЁТА — Прайм Хаус*\n{'─'*32}\n"
                        f"🏗 Объём: *{volume:,.0f} м³* | Высота: {ud['height']} м\n"
                        f"🏢 Этажность: {ud['floors']}\n"
                        f"🏛 Сложность здания: {ud['complexity_build']}\n"
                        f"🔧 Сложность работ: {ud['complexity_work']}\n"
                        f"📍 Расположение: {ud['location']}\n"
                        f"{'─'*32}\n\n"
                        + "\n\n".join(lines)
                        + add_list
                        + f"\n\n{'─'*32}\n"
                        f"💰 *ИТОГО: ≈ {grand_total:,.0f} ₽*\n{'─'*32}\n\n"
                        f"⚠️ _НДС не включён. Вскрытия конструкций — за счёт заказчика (п. 1.4 СБЦП)._\n"
                        f"_Базовые цены по СБЦП 81-2001-25. Индекс II кв. 2026: к = 7,07_\n\n"
                        f"📞 *Для оформления заявки свяжитесь с менеджером Прайм Хаус.*\n\n"
                        f"🔄 /start — новый расчёт"
            )
    keyboard = [[InlineKeyboardButton("🔄 Новый расчёт", callback_data="restart")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return RESULT

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
                "🏗 *Калькулятор обследований — Прайм Хаус*\n\nВведите *строительный объём здания* в м³:",
                parse_mode="Markdown"
    )
    return VOLUME

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("❌ Расчёт отменён. Введите /start чтобы начать заново.")
    return ConversationHandler.END

def main():
        app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
                entry_points=[CommandHandler("start", start)],
                states={
                                VOLUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_volume)],
                                HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
                                FLOORS: [CallbackQueryHandler(get_floors, pattern="^floors_")],
                                COMPLEXITY_BUILD: [CallbackQueryHandler(get_complexity_build, pattern="^cb_")],
                                COMPLEXITY_WORK: [CallbackQueryHandler(get_complexity_work, pattern="^cw_")],
                                LOCATION: [CallbackQueryHandler(get_location, pattern="^loc_")],
                                WORK_TYPES: [CallbackQueryHandler(get_work_types, pattern="^wt_")],
                                ADD_CONDITIONS: [CallbackQueryHandler(get_add_conditions, pattern="^ac_")],
                                RESULT: [CallbackQueryHandler(restart, pattern="^restart$")],
                },
                fallbacks=[CommandHandler("cancel", cancel)],
                allow_reentry=True,
    )
    app.add_handler(conv)
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
        main()
