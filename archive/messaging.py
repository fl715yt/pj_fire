"""
PJ Fire — Messaging & User Interface Logic

Handles sending messages and notifications to users (LINE or other interface).
Includes message templates and formatting for simulation results, trade alerts, summaries, etc.
"""

# from linebot import LineBotApi, WebhookHandler  # Uncomment if you use official LINE SDK
from utils.logger import log_info, log_error
from config.config import LINE_BOT_NAME, LINE_LANGUAGE

# Placeholder for LINE API client setup (customize with your secrets)
# line_bot_api = LineBotApi('YOUR_CHANNEL_ACCESS_TOKEN')

def send_message(user_id, message):
    """
    Sends a plain text message to the specified user (LINE user ID).
    (Replace with actual API call in production)
    """
    try:
        # Uncomment and customize for actual LINE integration:
        # line_bot_api.push_message(user_id, TextSendMessage(text=message))
        log_info(f"Sent message to {user_id}: {message}")
    except Exception as e:
        log_error(f"Failed to send message to {user_id}: {e}")

def format_trade_signal_message(stock_info):
    """
    Returns a formatted trade signal message for user (in Japanese).
    """
    msg = (
        f"【{LINE_BOT_NAME} シグナル】\n"
        f"銘柄: {stock_info['ticker']}\n"
        f"価格: {stock_info['close']}円\n"
        f"理由: {stock_info.get('reason', 'ー')}\n"
        "シミュレーション買いまたはスキップを選択してください。"
    )
    return msg

def format_summary_message(summary_info):
    """
    Returns a formatted weekly or daily summary message.
    """
    msg = (
        f"【{LINE_BOT_NAME} 週間サマリー】\n"
        f"今週の取引回数: {summary_info['num_trades']}回\n"
        f"累積損益: {summary_info['cumulative_pl']}円\n"
        f"TP/SLヒット数: TP={summary_info['tp_hits']} SL={summary_info['sl_hits']}\n"
        f"今週のトップシグナル: {summary_info['top_signal']}\n"
        "来週も頑張りましょう！"
    )
    return msg

# Example usage (pseudo-code):
# user_id = "Uxxxxxxxxxxxx"
# message = format_trade_signal_message(stock_info)
# send_message(user_id, message)

