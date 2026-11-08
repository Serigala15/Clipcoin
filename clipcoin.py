 

import requests
import time
import random
import sys
import os
from datetime import datetime
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"

if os.name == "nt":
    os.system("")
BANNER = f"""{C.CYAN}{C.BOLD}
   ███████╗ █████╗ ██╗███╗   ██╗███████╗
   ██╔════╝██╔══██╗██║████╗  ██║╚══███╔╝
   ███████╗███████║██║██╔██╗ ██║  ███╔╝ 
   ╚════██║██╔══██║██║██║╚██╗██║ ███╔╝  
   ███████║██║  ██║██║██║ ╚████║███████╗
   ╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝
{C.RESET}{C.YELLOW}      ⚡ CLIPCOIN AUTO-WATCH BOT v2 ⚡
{C.DIM}      ── Powered by Sainz Sama ──{C.RESET}
"""
BASE_URL = "https://clipcoin.pro"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "content-type": "application/x-www-form-urlencoded",
    "origin": BASE_URL,
    "referer": f"{BASE_URL}/watch",
    "user-agent": (
        "Mozilla/5.0 (Linux; Android 12; Infinix X6817 Build/SP1A.210812.016) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.5195.136 "
        "Mobile Safari/537.36"
    ),
    "x-requested-with": "mark.via",
}

DELAY_MIN       = 30
DELAY_MAX       = 60
RETRY_ON_EMPTY  = 120
MAX_FAIL_STREAK = 5

# ============================================
# UTIL
# ============================================
def log(level: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {"INFO": C.CYAN, "OK": C.GREEN, "WARN": C.YELLOW,
              "ERR": C.RED, "STEP": C.MAGENTA, "WAIT": C.BLUE}
    icons  = {"INFO": "ℹ", "OK": "✓", "WARN": "⚠", "ERR": "✗",
              "STEP": "▸", "WAIT": "⏳"}
    print(f"{C.DIM}[{ts}]{C.RESET} {colors.get(level, C.WHITE)}"
          f"{icons.get(level, '•')} {msg}{C.RESET}")


def clear_line():
    print("\033[K", end="")


def parse_cookie_string(s: str) -> dict:
    out = {}
    for part in s.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


# ============================================
# INPUT COOKIE MANUAL
# ============================================
def prompt_cookie() -> dict:
    """
    Minta user input cookie via terminal, dengan validasi.
    Return: dict cookie siap pakai.
    Loop sampai valid atau user Ctrl+C.
    """
    print(f"\n{C.BOLD}{C.YELLOW}{'═' * 58}{C.RESET}")
    print(f"{C.BOLD}{C.YELLOW}  🔐 MASUKKAN COOKIE ANDA{C.RESET}")
    print(f"{C.BOLD}{C.YELLOW}{'═' * 58}{C.RESET}")
    print(f"{C.DIM}  Format (satu baris):{C.RESET}")
    print(f"{C.CYAN}  cc-theme=system; hash=xxx; signed=1; newUser=1; "
          f"i18n_language=en; PHPSESSID=xxx{C.RESET}")
    print(f"{C.DIM}  Ambil dari browser → DevTools → Application → Cookies{C.RESET}\n")

    while True:
        try:
            raw = input(f"{C.GREEN}➜ Paste cookie: {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C.YELLOW}Dibatalkan.{C.RESET}")
            sys.exit(0)

        if not raw:
            log("WARN", "Cookie kosong. Coba lagi.")
            continue

        cookies = parse_cookie_string(raw)

        # Validasi field wajib
        required = ["PHPSESSID"]
        missing = [k for k in required if k not in cookies or not cookies[k]]

        if missing:
            log("ERR", f"Cookie tidak lengkap. Field wajib: "
                       f"{C.RED}{', '.join(missing)}{C.RESET}")
            log("INFO", "Pastikan ada 'PHPSESSID=...' di dalamnya.")
            continue

        # Info ringkas (sensor PHPSESSID)
        phpsess = cookies["PHPSESSID"]
        masked  = phpsess[:6] + "..." + phpsess[-4:] if len(phpsess) > 12 else "***"
        print(f"\n{C.DIM}  Cookies terdeteksi:{C.RESET}")
        for k, v in cookies.items():
            if k == "PHPSESSID":
                print(f"    {C.WHITE}{k:<16}{C.RESET}: {C.DIM}{masked}{C.RESET}")
            else:
                print(f"    {C.WHITE}{k:<16}{C.RESET}: {v}")
        print()

        confirm = input(f"{C.YELLOW}  Gunakan cookie ini? (y/n): {C.RESET}").strip().lower()
        if confirm in ("y", "yes", ""):
            return cookies
        log("INFO", "Ulangi input cookie.")


# ============================================
# SESSION FACTORY
# ============================================
def build_session(cookies: dict) -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    s.cookies.update(cookies)
    return s


# ============================================
# API (butuh SESSION global)
# ============================================
SESSION: requests.Session | None = None


def post_method(path: str, payload: dict) -> dict | None:
    try:
        r = SESSION.post(f"{BASE_URL}{path}", data=payload, timeout=20)
        if r.status_code != 200:
            log("ERR", f"HTTP {r.status_code} @ {path}: {r.text[:120]}")
            return None
        data = r.json()
        if data.get("status") != "ok":
            log("WARN", f"status!=ok @ {path}: {data.get('message')!r}")
            return None
        return data
    except requests.exceptions.Timeout:
        log("ERR", f"Timeout @ {path}")
    except requests.exceptions.RequestException as e:
        log("ERR", f"Request error @ {path}: {e}")
    except ValueError:
        log("ERR", f"Bukan JSON @ {path}")
    return None


def get_current_user():
    return post_method("/api/user/", {"method": "getCurrentUser"})


def get_task(mac: str = "0"):
    return post_method("/api/user/tasks/", {"method": "get", "mac": mac})


def start_task(task_id: str):
    payload = {"TaskId": str(task_id)}
    payload.update(build_fingerprint())
    return post_method("/api/user/tasks/start/", payload)


def claim_reward(refresh_task: int = 0):
    return post_method("/api/user/captcha/check/",
                       {"refreshTask": str(refresh_task)})


def build_fingerprint() -> dict:
    return {
        "fin[videoCard][vendor]": "ARM",
        "fin[videoCard][renderer]": "Mali-G52 MC2",
        "fin[viewPort][h]": "640", "fin[viewPort][w]": "360",
        "fin[viewPort][hM]": "820", "fin[viewPort][wM]": "360",
        "fin[platform]": "Linux armv8l", "fin[dpr]": "2",
        "fin[multi][speakers]": "1", "fin[multi][micros]": "1",
        "fin[multi][webcams]": "2", "fin[multi][devices]": "1",
        "fin[ori][alpha]": "261.2", "fin[ori][beta]": "61.900000000000006",
        "fin[ori][gamma]": "3.1", "fin[ori][is]": "1", "fin[v]": "2.7",
        "fin[cl][x]": "309", "fin[cl][y]": "270",
        "fin[webDef]": "false", "fin[navName]": "Navigator",
        "fin[touch]": "true", "fin[memory]": "4", "fin[concur]": "8",
        "fin[en][noF]": "1", "fin[bat][charging]": "1", "fin[bat][lvl]": "0.68",
        "fin[x][gl][tc]": "astc,etc,etc1", "fin[x][gl][n]": "17",
        "fin[x][gl][h]": "9e6b43ce",
        "fin[x][gl][p]": "4096|16383|16383|4096|4096|31|16|4095.9375|23",
        "fin[x][tp][t]": "touch", "fin[x][tp][pr]": "1",
        "fin[x][tp][w]": "0", "fin[x][tp][h]": "0",
        "fin[x][tp][d]": "66", "fin[x][tp][tr]": "1",
        "fin[x][mq][f]": "0", "fin[x][mq][hv]": "0",
        "fin[x][mq][c]": "1", "fin[x][mq][mt]": "5",
        "fin[x][mo][n]": "588", "fin[x][mo][g]": "9.829",
        "fin[x][mo][s]": "0.1033", "fin[x][mo][z]": "0",
        "fin[x][tz][z]": "Asia/Jakarta", "fin[x][tz][o]": "-420",
        "fin[x][tz][l]": "id-ID,en-US",
        "fin[x][au][wd]": "0", "fin[x][au][cdc]": "0",
        "fin[x][au][cdp]": "0", "fin[x][au][mv]": "0", "fin[x][au][mt]": "0",
        "fin[x][cn][t]": "wifi", "fin[x][cn][e]": "4g",
        "fin[x][cn][r]": "0", "fin[x][cn][d]": "9.2",
        "fin[x][bt][ct]": "2061", "fin[x][bt][dt]": "-1",
    }


# ============================================
# SIKLUS SATU TASK
# ============================================
def watch_one() -> tuple[bool, float, int]:
    t_resp = get_task()
    if not t_resp:
        return False, 0.0, 0

    task = t_resp["data"]
    task_id  = task["id"]
    duration = int(task["duration"])
    yt_id    = task["ytId"]

    log("STEP", f"Task #{task_id} | {C.CYAN}yt={yt_id}{C.RESET} | "
                 f"durasi={duration}s | sisa hari ini={task.get('limitDay')}")

    if not start_task(task_id):
        return False, 0.0, 0

    wait = duration + random.uniform(3, 8)
    log("WAIT", f"Menonton {wait:.1f} detik (simulasi)...")
    time.sleep(wait)

    claim = claim_reward()
    if not claim:
        return False, 0.0, 0

    reward = float(claim["data"]["reward"])
    coins  = int(claim["data"]["coins"])
    msg    = claim.get("message", "")
    log("OK", f"{C.GREEN}{C.BOLD}REWARD +${reward:.8f}{C.RESET} "
              f"(+{coins} coins) — {C.DIM}{msg}{C.RESET}")
    return True, reward, coins


# ============================================
# HEADER INFO AKUN
# ============================================
def print_session_header(user: dict):
    u = user["data"]
    print(f"\n{C.BOLD}  ┌─ INFO AKUN ─────────────────────────────┐{C.RESET}")
    print(f"  │ {C.WHITE}Email   :{C.RESET} {C.GREEN}{u['email']}{C.RESET}")
    print(f"  │ {C.WHITE}User ID :{C.RESET} {u['id']}")
    print(f"  │ {C.WHITE}Coins   :{C.RESET} {C.YELLOW}{u['coins']}{C.RESET}")
    print(f"  │ {C.WHITE}Balance :{C.RESET} {C.GREEN}${u['balance']}{C.RESET}")
    ban_status = (C.RED + "BANNED" + C.RESET) if u["ban"] else (C.GREEN + "aman" + C.RESET)
    print(f"  │ {C.WHITE}Status  :{C.RESET} {ban_status}")
    print(f"  └─────────────────────────────────────────┘\n")


# ============================================
# LOOP UTAMA
# ============================================
def run_loop(cookies: dict):
    global SESSION
    SESSION = build_session(cookies)

    # Verifikasi login
    log("STEP", "Verifikasi cookie & login...")
    u = get_current_user()
    if not u:
        log("ERR", f"{C.RED}Login GAGAL! Cookie expired atau salah.{C.RESET}")
        log("INFO", "Ambil ulang PHPSESSID dari browser DevTools.")
        ans = input(f"\n{C.YELLOW}Coba login dengan cookie baru? (y/n): {C.RESET}").strip().lower()
        if ans in ("y", "yes"):
            return run_loop(prompt_cookie())
        sys.exit(1)

    print_session_header(u)

    start_coins = int(u["data"]["coins"])
    start_bal   = float(u["data"]["balance"])
    start_time  = datetime.now()

    total_success = total_fail = 0
    total_reward  = 0.0
    total_coins   = 0
    fail_streak   = 0

    log("OK", f"{C.GREEN}Bot aktif! Mode loop terus-menerus.{C.RESET}")
    log("INFO", f"Jeda antar task: {DELAY_MIN}-{DELAY_MAX}s")
    log("INFO", f"Tekan {C.BOLD}Ctrl+C{C.RESET} untuk berhenti.\n")

    try:
        cycle = 0
        while True:
            cycle += 1
            print(f"\n{C.BOLD}{C.CYAN}{'═' * 58}{C.RESET}")
            print(f"{C.BOLD}{C.CYAN}  SIKLUS #{cycle}   "
                  f"{C.DIM}({datetime.now().strftime('%H:%M:%S')}){C.RESET}")
            print(f"{C.BOLD}{C.CYAN}{'═' * 58}{C.RESET}\n")

            ok, reward, coins = watch_one()

            if ok:
                total_success += 1
                total_reward  += reward
                total_coins   += coins
                fail_streak    = 0
            else:
                total_fail += 1
                fail_streak += 1
                log("WARN", f"Gagal (streak: {fail_streak}/{MAX_FAIL_STREAK})")

                if fail_streak >= MAX_FAIL_STREAK:
                    log("ERR", f"{C.RED}{MAX_FAIL_STREAK}x gagal berturut-turut. "
                               f"Kemungkinan limit / ban / cookie expired.{C.RESET}")
                    log("WAIT", f"Jeda {RETRY_ON_EMPTY * 2}s sebelum retry...")
                    time.sleep(RETRY_ON_EMPTY * 2)
                    fail_streak = 0
                    ur = get_current_user()
                    if not ur:
                        log("ERR", "Sesi benar-benar mati. Coba re-login.")
                        ans = input(f"\n{C.YELLOW}Masukkan cookie baru? (y/n): {C.RESET}").strip().lower()
                        if ans in ("y", "yes"):
                            return run_loop(prompt_cookie())
                        break
                    continue

                log("WAIT", f"Tunggu {RETRY_ON_EMPTY}s sebelum task berikutnya...")
                time.sleep(RETRY_ON_EMPTY)
                continue

            # Statistik live
            elapsed = datetime.now() - start_time
            mins = elapsed.total_seconds() / 60
            rate = (total_coins / mins * 60) if mins > 0 else 0
            print(f"\n  {C.DIM}┌─ STATISTIK ──────────────────────────────┐{C.RESET}")
            print(f"  {C.DIM}│{C.RESET} Sukses : {C.GREEN}{total_success}{C.RESET}"
                  f"  |  Gagal: {C.RED}{total_fail}{C.RESET}")
            print(f"  {C.DIM}│{C.RESET} Reward : {C.GREEN}{total_coins} coins{C.RESET}"
                  f" (${total_reward:.8f})")
            print(f"  {C.DIM}│{C.RESET} Runtime: {str(elapsed).split('.')[0]}"
                  f"  |  ~{rate:.0f} coins/jam")
            print(f"  {C.DIM}└──────────────────────────────────────────┘{C.RESET}")

            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            log("WAIT", f"Jeda {delay:.0f}s sebelum task berikutnya...")
            time.sleep(delay)

    except KeyboardInterrupt:
        print(f"\n\n{C.YELLOW}{C.BOLD}⏹  Dihentikan oleh user (Ctrl+C).{C.RESET}\n")

    # Ringkasan akhir
    print(f"{C.BOLD}{C.MAGENTA}{'═' * 58}{C.RESET}")
    print(f"{C.BOLD}{C.MAGENTA}  RINGKASAN SESI{C.RESET}")
    print(f"{C.BOLD}{C.MAGENTA}{'═' * 58}{C.RESET}")
    print(f"  Runtime      : {str(datetime.now() - start_time).split('.')[0]}")
    print(f"  Task sukses  : {C.GREEN}{total_success}{C.RESET}")
    print(f"  Task gagal   : {C.RED}{total_fail}{C.RESET}")
    print(f"  Total coins  : {C.YELLOW}+{total_coins}{C.RESET}")
    print(f"  Total reward : {C.GREEN}+${total_reward:.8f}{C.RESET}")

    u_end = get_current_user()
    if u_end:
        end_coins = int(u_end["data"]["coins"])
        end_bal   = float(u_end["data"]["balance"])
        print(f"\n  Saldo awal   : {start_coins} coins / ${start_bal:.8f}")
        print(f"  Saldo akhir  : {C.BOLD}{end_coins} coins / ${end_bal:.8f}{C.RESET}")
        print(f"  Δ saldo      : {C.GREEN}+{end_coins - start_coins} coins{C.RESET} / "
              f"{C.GREEN}+${end_bal - start_bal:.8f}{C.RESET}")
    print(f"{C.BOLD}{C.MAGENTA}{'═' * 58}{C.RESET}\n")


# ============================================
# MAIN
# ============================================
def main():
    print(BANNER)
    cookies = prompt_cookie()
    run_loop(cookies)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n{C.RED}Fatal error: {e}{C.RESET}")
        sys.exit(1)