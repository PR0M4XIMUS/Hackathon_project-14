from telethon import TelegramClient, events
from telethon.tl.custom import Button
from telethon.errors import FloodWaitError
import configparser
import datetime
import requests
import json
import time
import logging
import asyncio
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Access credentials
config = configparser.ConfigParser()
config.read('config.ini')

api_id = config.get('default', 'api_id')
api_hash = config.get('default', 'api_hash')
BOT_TOKEN = config.get('default', 'BOT_TOKEN')
OLLAMA_API = "http://ollama:11434/api/generate"

# Dictionary to store user settings
user_settings = {}

model_ol = "qwen3:1.7b"  # Model to use with Ollama

# Default settings
default_settings = {
    "calmness": 0.0,
    "rage": 1.0,
    "funny": 1.0,
    "ironic": 1.0,
    "brevity": 0.5,
    "curse_words": 1.0,
    "age": 0.5,
    "rudeness": 1.0,
    "caps_lock": "OFF",
    "emoji": "ON"
}

# Function to get user settings
def get_user_settings(user_id):
    if user_id not in user_settings:
        user_settings[user_id] = default_settings.copy()
    return user_settings[user_id]

# Function to create and start the client with retry logic
async def start_client():
    client = TelegramClient('sessions/session_master', api_id, api_hash)
    
    # Connect to Telegram
    await client.connect()
    
    # Try to sign in with bot token
    max_retries = 5
    current_retry = 0
    
    while current_retry < max_retries:
        try:
            logger.info("Attempting to authenticate with Telegram...")
            await client.sign_in(bot_token=BOT_TOKEN)
            logger.info("Authentication successful!")
            return client
        except FloodWaitError as e:
            wait_time = e.seconds
            logger.warning(f"FloodWaitError: Need to wait {wait_time} seconds before retrying")
            
            if current_retry < max_retries - 1:
                logger.info(f"Waiting {wait_time} seconds before retry {current_retry + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                current_retry += 1
            else:
                logger.error(f"Max retries ({max_retries}) reached. Exiting.")
                raise
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {str(e)}")
            raise
    
    raise Exception("Failed to authenticate after maximum retry attempts")

# Function to call Ollama API with streaming support
async def query_ollama(prompt, settings, message_to_update=None, client=None, user_id=None):
    system_prompt = """
You are an advanced AI designed to provide insightful explanations regarding the importance of understanding, managing, or solving various tasks, files, texts, or themes. Your core function is to clearly articulate the "why" behind the necessity of engaging with the provided content.

Your responses are influenced by the following settings:
- Calmness: {calmness}
- Rage: {rage}
- Funny: {funny}
- Ironic: {ironic}
- Brevity: {brevity}
- Curse-Words Usage: {curse_words}
- Age: {age}
- Rudeness: {rudeness}
- Caps-Lock: {caps_lock}
- Emoji: {emoji}
    """.format(**settings)
    
    payload = {
        "model": model_ol,
        "prompt": prompt,
        "system": system_prompt,
        "stream": True  # Enable streaming for live updates
    }
    
    try:
        # If we're doing a live update, we need a message and client
        if message_to_update and client and user_id:
            # Initial response text
            full_response = ""
            last_update_time = time.time()
            update_interval = 1.0  # Update every 1 second
            last_message_content = ""  # Track the last message content to avoid duplicate edits

            # Send streaming request with a session
            with requests.Session() as session:
                response = session.post(OLLAMA_API, json=payload, stream=True)
                response.raise_for_status()
                
                # Process the streaming response
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    try:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            full_response += chunk["response"]
                            
                            # Update the message periodically to avoid rate limits
                            current_time = time.time()
                            if current_time - last_update_time >= update_interval:
                                # Apply caps lock if enabled
                                display_text = full_response
                                if settings["caps_lock"] == "ON":
                                    display_text = display_text.upper()
                                
                                message_content = f"Analyzing... \n\n{display_text}"
                                
                                # Only update if content has changed
                                if message_content != last_message_content:
                                    try:
                                        await client.edit_message(message_to_update, message_content)
                                        last_message_content = message_content
                                    except Exception as e:
                                        # Log but continue if we hit an editing error
                                        if "not modified" not in str(e).lower():
                                            logger.warning(f"Message edit error: {str(e)}")
                                
                                last_update_time = current_time
                                
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON from line: {line}")
                        continue
                    
                    # Check if the response is complete
                    if "done" in chunk and chunk["done"]:
                        break
            
            # Final response text
            if settings["caps_lock"] == "ON":
                full_response = full_response.upper()
                
            return full_response
        
        else:
            # Non-streaming fallback if not updating a message
            payload["stream"] = False
            response = requests.post(OLLAMA_API, json=payload)
            response.raise_for_status()
            result = response.json()
            response_text = result.get("response", "Sorry, I couldn't generate a response.")
            
            # Apply caps lock if enabled
            if settings["caps_lock"] == "ON":
                response_text = response_text.upper()
                
            return response_text
            
    except Exception as e:
        logger.error(f"Error calling Ollama: {str(e)}")
        return f"Error calling Ollama: {str(e)}"

def init_ollama():
    logger.info("Initializing Ollama...")
    try:
        # Model should already be available via volume mount
        # Just check if it's accessible
        response = requests.get("http://ollama:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name") for m in models]
            if model_ol in model_names:
                logger.info(f"Model {model_ol} is available")
            else:
                logger.warning(f"Warning: {model_ol} not found in available models: {model_names}")
        else:
            logger.error(f"Failed to check models: {response.text}")
    except Exception as e:
        logger.error(f"Error initializing Ollama: {str(e)}")
        time.sleep(5)  # Wait and retry
        init_ollama()

# Main async function to set up the bot
async def main():
    # Initialize Ollama
    init_ollama()
    
    try:
        # Start the client with retry logic
        client = await start_client()
        
        # Define the /start command
        @client.on(events.NewMessage(pattern='(?i)/start'))
        async def start(event):
            sender = await event.get_sender()
            SENDER = sender.id
            
            # Initialize user settings
            get_user_settings(SENDER)
            
            text = "AI Explanation Bot 🤖 ready\n\nSend me content to analyze, and I'll explain why it's important based on your personality settings.\n\nUse /settings to view and adjust my personality traits."
            await client.send_message(SENDER, text, parse_mode="HTML")

        # Settings command with inline buttons
        @client.on(events.NewMessage(pattern='(?i)/settings'))
        async def settings_command(event):
            sender = await event.get_sender()
            SENDER = sender.id
            
            # Create buttons for each setting
            buttons = []
            row = []
            
            # Create a 2-column layout for settings
            for i, setting in enumerate(default_settings.keys()):
                display_name = setting.replace('_', ' ').title()
                row.append(Button.inline(display_name, f"setting:{setting}"))
                
                # Create a new row every 2 buttons
                if (i + 1) % 2 == 0 or i == len(default_settings.keys()) - 1:
                    buttons.append(row)
                    row = []
            
            await client.send_message(
                SENDER, 
                "Select a setting to adjust:",
                buttons=buttons
            )

        # Handle button callbacks for settings menu
        @client.on(events.CallbackQuery(pattern=r"setting:(.+)"))
        async def on_setting_button(event):
            sender = await event.get_sender()
            SENDER = sender.id
            user_prefs = get_user_settings(SENDER)
            
            # Get selected setting
            setting = event.data.decode().split(":", 1)[1]
            current_value = user_prefs[setting]
            display_name = setting.replace('_', ' ').title()
            
            # Create adjustment buttons based on setting type
            buttons = []
            
            if setting in ["caps_lock", "emoji"]:
                # Toggle buttons for binary settings
                current = "ON" if user_prefs[setting] == "ON" else "OFF"
                opposite = "OFF" if current == "ON" else "ON"
                buttons.append([Button.inline(f"Turn {opposite}", f"toggle:{setting}:{opposite}")])
            else:
                # Adjustment buttons for numeric settings
                # Create buttons for numeric settings with different increments
                value_adjustments = [
                    ["-0.2", -0.2], ["-0.1", -0.1], ["+0.1", 0.1], ["+0.2", 0.2]
                ]
                
                row = []
                for label, adjustment in value_adjustments:
                    new_value = round(current_value + adjustment, 1)
                    # Only add button if the resulting value would be valid
                    if 0 <= new_value <= 1:
                        row.append(Button.inline(label, f"adjust:{setting}:{new_value}"))
                
                buttons.append(row)
                
                # Add preset buttons for min and max
                min_max_buttons = []
                min_max_buttons.append(Button.inline("Min (0.0)", f"adjust:{setting}:0.0"))
                min_max_buttons.append(Button.inline("Max (1.0)", f"adjust:{setting}:1.0"))
                buttons.append(min_max_buttons)
            
            # Add back button
            buttons.append([Button.inline("◀️ Back to Settings", "back_to_settings")])
            
            # Show current setting value with range for numeric settings
            if setting in ["caps_lock", "emoji"]:
                value_display = current_value
            else:
                # Show min/max range for numeric settings
                value_display = f"{current_value} (Range: 0.0-1.0)"
                
            await event.edit(
                f"**{display_name}**\nCurrent value: {value_display}",
                buttons=buttons
            )

        # Handle adjustments to settings
        @client.on(events.CallbackQuery(pattern=r"adjust:(.+):(.+)"))
        async def on_adjust(event):
            sender = await event.get_sender()
            SENDER = sender.id
            user_prefs = get_user_settings(SENDER)
            
            # Parse setting and new value
            data = event.data.decode().split(":", 2)
            setting = data[1]
            new_value = float(data[2])
            
            # Update setting
            user_prefs[setting] = new_value
            
            # Recreate the setting page with updated value
            display_name = setting.replace('_', ' ').title()
            
            # Create adjustment buttons
            buttons = []
            value_adjustments = [
                ["-0.2", -0.2], ["-0.1", -0.1], ["+0.1", 0.1], ["+0.2", 0.2]
            ]
            
            row = []
            for label, adjustment in value_adjustments:
                adjusted_value = round(new_value + adjustment, 1)
                if 0 <= adjusted_value <= 1:
                    row.append(Button.inline(label, f"adjust:{setting}:{adjusted_value}"))
            
            buttons.append(row)
            
            # Add preset buttons for min and max
            min_max_buttons = []
            min_max_buttons.append(Button.inline("Min (0.0)", f"adjust:{setting}:0.0"))
            min_max_buttons.append(Button.inline("Max (1.0)", f"adjust:{setting}:1.0"))
            buttons.append(min_max_buttons)
            
            buttons.append([Button.inline("◀️ Back to Settings", "back_to_settings")])
            
            # Show value with range
            value_display = f"{new_value} (Range: 0.0-1.0)"
            
            await event.edit(
                f"**{display_name}**\nUpdated value: {value_display}",
                buttons=buttons
            )

        # Handle toggle for binary settings
        @client.on(events.CallbackQuery(pattern=r"toggle:(.+):(.+)"))
        async def on_toggle(event):
            sender = await event.get_sender()
            SENDER = sender.id
            user_prefs = get_user_settings(SENDER)
            
            # Parse setting and new state
            data = event.data.decode().split(":", 2)
            setting = data[1]
            new_state = data[2]
            
            # Update setting
            user_prefs[setting] = new_state
            
            # Recreate the setting page with updated value
            display_name = setting.replace('_', ' ').title()
            
            # Create toggle button
            opposite = "OFF" if new_state == "ON" else "ON"
            buttons = [
                [Button.inline(f"Turn {opposite}", f"toggle:{setting}:{opposite}")],
                [Button.inline("◀️ Back to Settings", "back_to_settings")]
            ]
            
            await event.edit(
                f"**{display_name}**\nUpdated value: {new_state}",
                buttons=buttons
            )

        # Handle back button
        @client.on(events.CallbackQuery(pattern=r"back_to_settings"))
        async def on_back_to_settings(event):
            sender = await event.get_sender()
            SENDER = sender.id
            
            # Recreate settings menu
            buttons = []
            row = []
            
            # Create a 2-column layout for settings
            for i, setting in enumerate(default_settings.keys()):
                display_name = setting.replace('_', ' ').title()
                row.append(Button.inline(display_name, f"setting:{setting}"))
                
                # Create a new row every 2 buttons
                if (i + 1) % 2 == 0 or i == len(default_settings.keys()) - 1:
                    buttons.append(row)
                    row = []
            
            await event.edit(
                "Select a setting to adjust:",
                buttons=buttons
            )

        # Handle other messages
        @client.on(events.NewMessage(func=lambda e: e.text and not e.text.startswith('/')))
        async def process_content(event):
            sender = await event.get_sender()
            SENDER = sender.id
            user_prefs = get_user_settings(SENDER)
            
            # Send initial "Analyzing..." message that we'll update
            processing_msg = await client.send_message(SENDER, "Analyzing your content... Please wait.")
            
            content = event.text
            
            # Call Ollama with live updates to the message
            response = await query_ollama(
                content, 
                user_prefs, 
                message_to_update=processing_msg, 
                client=client, 
                user_id=SENDER
            )
            
            # Send final response in chunks if too long
            max_length = 4000
            if len(response) <= max_length:
                await processing_msg.edit(response)
            else:
                # Edit the first message with the first chunk
                await processing_msg.edit(response[:max_length])
                
                # Send additional chunks as new messages
                for i in range(max_length, len(response), max_length):
                    chunk = response[i:i + max_length]
                    await client.send_message(SENDER, chunk)

        # Get time command
        @client.on(events.NewMessage(pattern='(?i)/time'))
        async def time_command(event):
            sender = await event.get_sender()
            SENDER = sender.id
            text = "Received! Day and time: " + str(datetime.datetime.now())
            await client.send_message(SENDER, text, parse_mode="HTML")

        # Run the client until disconnected
        logger.info("Bot is now running!")
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

# MAIN
if __name__ == '__main__':
    print("Bot Started!")
    asyncio.run(main())