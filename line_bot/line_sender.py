from dotenv import load_dotenv
import os
from linebot import LineBotApi
from linebot.models import TextSendMessage

load_dotenv()
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

line_bot_api = LineBotApi(LINE_TOKEN)

def send_signals(signal_list):
    # TODO: build cleaner message format
    for signal in signal_list:
        message = f"{signal['code']} {signal['name']}\nReason: {signal['reason']}"
        line_bot_api.push_message("USER_ID", TextSendMessage(text=message))
