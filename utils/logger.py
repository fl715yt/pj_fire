import datetime

def log_info(message):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[INFO] {now} - {message}"
    print(log_line)
    with open("logs/pj_fire.log", "a") as f:
        f.write(log_line + "\n")
