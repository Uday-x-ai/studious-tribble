import telebot
import requests
import json
import os

# Replace with your Telegram bot token
TOKEN = '7541405374:AAFI-r25zSFrpc-TnYLQxUuuv4xLuFN6gZY'
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 1489381549

# Path to the JSON file
USER_DATA_FILE = 'usersdata.json'

# Function to load user IDs from the JSON file
def load_user_ids():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as file:
            return set(json.load(file))
    return set()

# Function to save user IDs to the JSON file
def save_user_ids(user_ids):
    with open(USER_DATA_FILE, 'w') as file:
        json.dump(list(user_ids), file)

# Load user IDs from the JSON file
user_ids = load_user_ids()

# Variable to store the user's state
user_states = {}

def notify_admin_of_error(error, msg):
    """Send error message to admin"""
    error_msg = f"""
Error in chat with user: {msg.chat.id}
Username: @{msg.from_user.username or 'N/A'}
Message: {msg.text or 'N/A'}
Error: {str(error)}
    """
    bot.send_message(ADMIN_ID, error_msg)

@bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        chat_id = message.chat.id
        user_ids.add(chat_id)  # Add user to the set
        save_user_ids(user_ids)  # Save updated user IDs to the JSON file

        param = message.text.split(' ', 1)[-1].strip() if ' ' in message.text else ''

        if param.startswith('status'):
            unique_id = param.replace('status', '').strip()

            if unique_id:
                url = f'https://api-hub.pw/status.php?id={unique_id}'
                try:
                    response = requests.get(url)
                    data = response.json()  # Assuming the API returns JSON
                    bot.send_message(chat_id, f"<b>STATUS:</b> {data['status']}\n<b>AMOUNT:</b> ₹{data['amount']}\n<b>ORDER ID:</b> <code>{data['order_id']}</code>", parse_mode='HTML')
                except Exception as error:
                    bot.send_message(chat_id, f"Error retrieving status: {str(error)}")
                    notify_admin_of_error(error, message)
            else:
                bot.send_message(chat_id, 'Invalid status ID.')
        else:
            bot.send_message(chat_id, '<b>Welcome! Send /create_order to create a new order.</b>', parse_mode='HTML')
    except Exception as error:
        notify_admin_of_error(error, message)

@bot.message_handler(commands=['create_order'])
def handle_create_order(message):
    try:
        chat_id = message.chat.id
        user_states[chat_id] = {'step': 'enter_amount'}
        bot.send_message(chat_id, '<b>Enter Amount You Want To Pay</b>', parse_mode='HTML')
    except Exception as error:
        notify_admin_of_error(error, message)

@bot.message_handler(commands=['payments'])
def handle_payments(message):
    try:
        chat_id = message.chat.id

        # Check if the user is the admin
        if chat_id == ADMIN_ID:
            payments_url = 'https://api-hub.pw/payments.php'
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton('View Payments', web_app=telebot.types.WebAppInfo(url=payments_url)))
            bot.send_message(chat_id, 'Click the button below to view all payments.', reply_markup=markup)
    except Exception as error:
        notify_admin_of_error(error, message)

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    try:
        chat_id = message.chat.id

        # Check if the user is the admin
        if chat_id == ADMIN_ID:
            bot.send_message(chat_id, 'Please enter the message or forward the message you want to broadcast:')
            user_states[chat_id] = {'step': 'broadcast_message'}
        else:
            bot.send_message(chat_id, 'You are not authorized to use this command.')
    except Exception as error:
        notify_admin_of_error(error, message)

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'audio', 'sticker', 'voice', 'location', 'contact', 'venue', 'animation'])
def handle_message(message):
    try:
        chat_id = message.chat.id

        if chat_id in user_states:
            state = user_states[chat_id]['step']

            if state == 'enter_amount':
                if message.content_type == 'text':
                    text = message.text.strip()

                    # Validate amount
                    if not text.isdigit() or int(text) <= 0:
                        bot.send_message(chat_id, 'Please enter a valid amount.')
                        del user_states[chat_id]
                        return

                    # Proceed to create the order
                    amount = text
                    url = f'https://api-hub.pw/create.php?amount={amount}&chat_id={chat_id}'

                    try:
                        response = requests.get(url)
                        data = response.json()  # Assuming the API returns JSON
                        urll = f"https://api-hub.pw/payment.php?id={data['unique_id']}"
                        oid = data['order_id']
                        markup = telebot.types.InlineKeyboardMarkup()
                        markup.add(telebot.types.InlineKeyboardButton('Pay Now', web_app=telebot.types.WebAppInfo(url=urll)))

                        bot.send_message(chat_id, f"<b>Order Created Successfully!\nOrder Id:</b> <code>{oid}</code>\n<a href='https://t.me/everything_testing_bot?start=status{data['unique_id']}'>Check Status</a>", parse_mode='HTML', reply_markup=markup)
                    except Exception as error:
                        bot.send_message(chat_id, f"Error creating order: {str(error)}")
                        notify_admin_of_error(error, message)

                    # Reset the user's state
                    del user_states[chat_id]

            elif state == 'broadcast_message':
                # Broadcast the message to all users
                for user_id in user_ids:
                    try:
                        if message.content_type == 'text':
                            bot.send_message(user_id, f"<b>Message From Admin:</b>\n\n {message.text}", parse_mode='HTML')
                        else:
                            bot.forward_message(user_id, chat_id, message.message_id)
                    except Exception as error:
                        notify_admin_of_error(error, message)

                bot.send_message(chat_id, 'Message broadcasted to all users.')
                del user_states[chat_id]
        else:
            bot.send_message(chat_id, 'Please Contact @uday_x For Any Help')
    except Exception as error:
        notify_admin_of_error(error, message)

if __name__ == '__main__':
    print("Bot is starting...")
    bot.polling(none_stop=True)
