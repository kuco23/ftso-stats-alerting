from typing import List
import time
import sys
import os
from dataclasses import dataclass
import requests
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()

NETWORKS = os.getenv("NETWORK", "flare,songbird").lower().split(',')
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ADDRESSES = os.getenv('ADDRESSES').split(',')
MIN_AVAILABILITY = float(os.getenv("MIN_AVAILABILITY", "10"))
MIN_SUCCESS_RATE_PRIMARY = float(os.getenv('MIN_SUCCESS_RATE_PRIMARY', '10'))
MIN_SUCCESS_RATE_SECONDARY = float(os.getenv('MIN_SUCCESS_RATE_SECONDARY', '10'))

CYCLE_SLEEP_SECONDS = 60 * 5 # check every 5 minutes

def get_api_path(address: str) -> str:
    return f'/backend-url/api/v0/entity/{address}/ftso'

@dataclass
class Stats:
    availability: float
    success_rate_primary: float
    success_rate_secondary: float

def get_explorer_url(network: str) -> str:
    if network == "flare":
        return "https://flare-systems-explorer.flare.rocks"
    elif network == "songbird":
        return "https://songbird-systems-explorer.flare.rocks"
    else:
        raise ValueError("Invalid network. Use 'flare' or 'songbird'.")

# === Get wallet stats from systems explorer API ===
def get_stats(network: str, address: str, retries: int = 3, delay: float = 1.0) -> Stats:
    base_url = get_explorer_url(network)
    api_path = get_api_path(address)
    endpoint = base_url + api_path

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(endpoint, timeout=10).json()
            last_6h_data = resp.get('last_6h')
            return Stats(
                availability=float(last_6h_data['availability']),
                success_rate_primary=float(last_6h_data['primary']),
                success_rate_secondary=float(last_6h_data['secondary'])
            )
        except Exception as e:
            print(f"Attempt {attempt} failed for {address}: {e}")
        if attempt < retries:
            time.sleep(delay)

    return -1  # all attempts failed

def send_telegram_alert(message: str):
    print(f"Sending Telegram alert: {message}")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        print("Telegram response:", response.status_code, response.text)
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")


# === Check all addresses and send alerts ===
def check_all_addresses(networks: List[str], addresses: List[str]):
    for network, address in zip(networks, addresses):
        stats = get_stats(network, address)
        if stats == -1:
            send_telegram_alert(f"❌ *Error* retrieving stats for `{address}` (request error on {NETWORKS})")
        if stats.availability < MIN_AVAILABILITY:
            send_telegram_alert(
                f"⚠️ `{address}` has availability *{stats.availability:.4f}* on {NETWORKS} (threshold: {MIN_AVAILABILITY})"
            )
        if stats.success_rate_primary < MIN_SUCCESS_RATE_PRIMARY:
            send_telegram_alert(
                f"⚠️ `{address}` has primary success rate *{stats.success_rate_primary:.4f}* on ${NETWORKS} (threshold: {MIN_SUCCESS_RATE_PRIMARY})"
            )
        if stats.success_rate_secondary < MIN_SUCCESS_RATE_SECONDARY:
            send_telegram_alert(
                f"⚠️ `{address}` has secondary success rate *{stats.success_rate_secondary:.4f}* on {NETWORKS} (threshold: {MIN_SUCCESS_RATE_SECONDARY})"
            )
        print(f"{address}: {stats} {network}")

# === Main entry point ===
if __name__ == "__main__":
    while True:
        try:
            check_all_addresses(NETWORKS, ADDRESSES)
        except Exception as err:
            send_telegram_alert(f"❌ Error in the script: {err} on {NETWORKS}")
            sys.exit(1)
        time.sleep(CYCLE_SLEEP_SECONDS)

# This is a test alert from the script.
#send_telegram_alert("✅ *This is a test alert from the script.*")
