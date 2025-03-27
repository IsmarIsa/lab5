import json
import re
import requests
import sys
import os

# API-ключ для доступа к ATAIX
API_KEY = "ВАШ_API"

# Функция для выполнения GET-запросов к API
def get_request(endpoint):
    url = f"https://api.ataix.kz{endpoint}"
    headers = {"accept": "application/json", "X-API-Key": API_KEY}
    response = requests.get(url, headers=headers, timeout=20)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Ошибка API: {response.status_code}, {response.text}")
        return {}

# Функция получения доступного баланса
def get_balance(currency):
    balance_info = get_request(f"/api/user/balances/{currency}")
    
    # Отладочный вывод
    print(f"🔍 Отладка: баланс {currency}: {balance_info}")  

    if balance_info.get("status") and "result" in balance_info:
        return balance_info["result"].get("available", "0.000000")
    return None

# Получаем список валют
symbols_data = get_request("/api/symbols")
currencies = [symbol["base"] for symbol in symbols_data.get("result", []) if "base" in symbol]

print("📊 Доступный баланс на бирже в токенах USDT:")
for currency in currencies:
    balance = get_balance(currency)
    if balance:
        print(f"✅ {currency}: {balance} USDT")
    else:
        print(f"⚠ Не удалось получить баланс для {currency}")

# Функция поиска торговых пар
def find_symbols(text, word):
    words = re.findall(r'\b\w+(?:/\w+)?\b', text)
    return [words[i + 1] for i in range(len(words) - 1) if words[i] == word]

# Функция поиска цен
def find_prices(text, word):
    return re.findall(rf'{word}[\s\W]*([-+]?\d*\.\d+|\d+)', text)

# Поиск торговых пар и цен
currencies_less_0_6, price_less_0_6_list = [], {}
symbols = find_symbols(json.dumps(get_request("/api/symbols")), "symbol")
price = find_prices(json.dumps(get_request("/api/prices")), "lastTrade")

print("\n📉 Торговые пары с USDT, где цена ≤ 0.6 USDT:")
for i in range(len(symbols)):
    if "USDT" in symbols[i] and float(price[i]) <= 0.6:
        print(f"🔹 {symbols[i]}: {price[i]} USDT")
        currencies_less_0_6.append(symbols[i])
        price_less_0_6_list[symbols[i]] = price[i]

# Выбор торговой пары
while True:
    current_cur = input("🛒 Выберите торговую пару (например, TRX, IMX, 1INCH) или введите 'exit' для выхода: ").upper()
    if current_cur == "EXIT":
        sys.exit()
    if current_cur + "/USDT" in currencies_less_0_6:
        price_less_0_6 = price_less_0_6_list[current_cur + "/USDT"]
        break
    print("⚠ Такой торговой пары нет в списке. Попробуйте снова.")

print(f"\n📌 Вы выбрали: {current_cur} по цене {price_less_0_6} USDT")
price_levels = {
    "-2%": round(float(price_less_0_6) * 0.98, 4),
    "-5%": round(float(price_less_0_6) * 0.95, 4),
    "-8%": round(float(price_less_0_6) * 0.92, 4),
}
print("🔽 Будут созданы три ордера на покупку {}:".format(current_cur))
for level, price in price_levels.items():
    print(f"  {level}: {price} USDT")

# Подтверждение перед размещением ордеров
while input("✅ Подтвердите действие (введите 'yes' для продолжения или 'exit' для отмены): ").lower() != "yes":
    sys.exit()

# Функция размещения ордеров
def post_orders(symbol, price):
    url = "https://api.ataix.kz/api/orders"
    headers = {"accept": "application/json", "X-API-Key": API_KEY, "Content-Type": "application/json"}
    data = {"symbol": symbol, "side": "buy", "type": "limit", "quantity": 1, "price": price}
    response = requests.post(url, headers=headers, json=data, timeout=20)
    return response.json()

# Размещение ордеров
orders_list = [post_orders(current_cur + "/USDT", price) for price in price_levels.values()]

# Сохранение ордеров в файл
filename = "orders_data.json"
orders = []
if os.path.exists(filename):
    with open(filename, "r") as file:
        try:
            orders = json.load(file)
        except json.JSONDecodeError:
            pass

for order in orders_list:
    if isinstance(order, dict) and "result" in order:
        orders.append({
            "orderID": order["result"].get("orderID", "UNKNOWN"),
            "price": order["result"].get("price", "UNKNOWN"),
            "quantity": order["result"].get("quantity", "UNKNOWN"),
            "symbol": order["result"].get("symbol", "UNKNOWN"),
            "created": order["result"].get("created", "UNKNOWN"),
            "status": order["result"].get("status", "NEW"),
        })

with open(filename, "w") as file:
    json.dump(orders, file, indent=4)

print(f"✅ Ордера успешно созданы! Данные сохранены в {filename}. Для проверки посетите ATAIX, вкладка 'Мои ордера'.")
