# Will send an alert when a new high diff is reached on any of your bitaxes/nerdaxes.
# Run on the same lan as the axes 

import requests
import time
import json

# === CONFIG ===
BITAXE_HOSTS = [
    "_____BITAXE_HERE_____",
    "_____NERDAXE_HERE_____",
    "_____MORE_DEVICES_HERE_____"
]

TELEGRAM_BOT_TOKEN = "_____BOT_TOKEN_HERE_____"
TELEGRAM_CHAT_ID = "_____TELEGRAM_ID_HERE_____"
POLL_INTERVAL = 60  # seconds
HTTP_TIMEOUT = 10   # seconds

last_bestshares = {}  

def format_with_suffix(number):
    suffixes = [
        (1e12, "T"),
        (1e9, "G"),
        (1e6, "M"),
        (1e3, "K"),
    ]
    try:
        n = float(number)
    except Exception:
        return str(number)

    for factor, suffix in suffixes:
        if n >= factor:
            return f"{n / factor:.2f}{suffix}".rstrip("0").rstrip(".") + suffix if False else f"{n / factor:.2f}{suffix}"
    return f"{int(n)}"


def send_telegram(worker_name, bestshare, old_bestshare):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    formatted = format_with_suffix(bestshare)
    formatted_old = format_with_suffix(old_bestshare)
    curr_diff = format_with_suffix(get_cur_difficulty())

    message = (f"New best difficulty for *{worker_name}*: *{formatted}*\n"
               f"Previous best difficulty: `{formatted_old}`"
               f"\n\nBitcoin difficulty needed for block = " + curr_diff)

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        r = requests.post(url, json=payload, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram message: {e}")


def get_cur_difficulty():
    diff_url = "https://nd-202-842-353.p2pify.com/788f110831fe13808302bd79796d55e8"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "1.0",
        "method": "getdifficulty",
        "id": 1
    }

    try:
        response = requests.post(diff_url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Extract the result field
        difficulty = data.get("result")
        return (difficulty)

    except Exception as e:
        print(f"[ERROR] {e}")


def fetch_bitaxe_info(host):
    """GET http://<host>/api/system/info and return parsed JSON dict or None."""
    url = f"http://{host}/api/system/info"
    try:
        resp = requests.get(url, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return json.loads(resp.text)
    except Exception as e:
        print(f"[ERROR] {host}: {e}")
        return None

def check_workers():
    global last_bestshares

    for host in BITAXE_HOSTS:
        info = fetch_bitaxe_info(host)
        if not info:
            continue

        display_name = info.get("hostname") or host
        identifier = f"{display_name}@{host}"

        best_nonce_diff = info.get("bestNonceDiff")
        if best_nonce_diff is None:
            best_diff_str = str(info.get("bestDiff", "")).strip()
            if best_diff_str and best_diff_str[-1] in "KMGTT":
                # convert "4.29G" -> int
                try:
                    val = float(best_diff_str[:-1])
                    mul = {"K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}.get(best_diff_str[-1], 1)
                    best_nonce_diff = int(val * mul)
                except Exception:
                    pass

        if best_nonce_diff is None:
            print(f"{identifier}: bestNonceDiff not available in response")
            continue

        print(f"{identifier} bestNonceDiff = {best_nonce_diff}")

        # Initialize first 
        if identifier not in last_bestshares:
            last_bestshares[identifier] = best_nonce_diff
            continue

        # Alert on higher diff
        if best_nonce_diff > last_bestshares[identifier]:
            print("\n\nNew Best Difficulty. Sending Telegram Message\n\n")
            send_telegram(display_name, best_nonce_diff, last_bestshares[identifier])
            last_bestshares[identifier] = best_nonce_diff


if __name__ == "__main__":
    while True:
        check_workers()
        time.sleep(POLL_INTERVAL)
