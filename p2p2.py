import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8493681803:AAFzzsbt_Kc4y5FAJpfhrKyKDhdG91n7kgA"
SPREAD_FEE = 1.8  # комиссия в %

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_path = "input.csv"
    await file.download_to_drive(file_path)

    df = pd.read_csv(file_path)

    if not {"Creation Time", "Ad Type", "Price", "Fiat Amount", "Net Crypto Amount"}.issubset(df.columns):
        await update.message.reply_text("Файл не содержит нужных колонок!")
        return

    df["Date"] = pd.to_datetime(df["Creation Time"]).dt.date

    results = []

    for date, group in df.groupby("Date"):
        sales = group[group["Ad Type"] == "SALE"]
        purchases = group[group["Ad Type"] == "PURCHASE"]

        if sales.empty or purchases.empty:
            continue

        # Средние цены (объемно-взвешенные)
        avg_sell = sales["Fiat Amount"].sum() / sales["Net Crypto Amount"].sum()
        avg_buy = purchases["Fiat Amount"].sum() / purchases["Net Crypto Amount"].sum()

        # Новая формула спреда: (P_sell - P_buy)/P_sell *100 - 1.8
        raw_spread = (avg_sell - avg_buy) / avg_sell * 100
        net_spread = raw_spread - SPREAD_FEE

        # Формула дохода: Чистый спред * сумма продаж в рублях / 100
        total_sales_rub = sales["Fiat Amount"].sum()
        profit_rub = total_sales_rub * net_spread / 100

        # Распределение доходов
        dani = profit_rub * 0.15
        nik = profit_rub * 0.425
        worker = profit_rub * 0.425

        results.append({
            "Дата": date,
            "Цена продажи (RUB/USDT)": round(avg_sell, 2),
            "Цена закупа (RUB/USDT)": round(avg_buy, 2),
            "Спред %": round(raw_spread, 2),
            "Чистый спред %": round(net_spread, 2),
            "Объем продаж (RUB)": round(total_sales_rub, 2),
            "Прибыль (RUB)": round(profit_rub, 2),
            "Исполнитель (RUB)": round(worker, 2),
            "Данил (RUB)": round(dani, 2),
            "Ник (RUB)": round(nik, 2),
        })

    result_df = pd.DataFrame(results)

    if not result_df.empty:
        # Итоговая строка только с финансовыми показателями
        finance_columns = [
            "Объем продаж (RUB)",
            "Прибыль (RUB)",
            "Исполнитель (RUB)",
            "Данил (RUB)",
            "Ник (RUB)"
        ]
        totals = result_df[finance_columns].sum()
        totals["Дата"] = "Итого"
        result_df = pd.concat([result_df, pd.DataFrame([totals])], ignore_index=True)

    output_file = "result.xlsx"
    result_df.to_excel(output_file, index=False)

    await update.message.reply_document(document=open(output_file, "rb"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь мне CSV-файл с выгрузкой P2P операций, и я пришлю отчет в XLSX.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.FileExtension("csv"), handle_file))
    app.run_polling()

if __name__ == "__main__":
    main()
