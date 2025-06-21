from telethon import TelegramClient, events
from telethon.tl.custom import Button

import configparser
import datetime
import pytz
import requests
import json
import asyncio
import PyPDF2
import io
import traceback

from functions import send_logs, get_user_id, format_display_name
from functions import default_settings, PERSONALITY_PRESETS, get_user_settings, user_settings

# Constants
MAX_MESSAGE_LENGTH = 4000
UPDATE_INTERVAL = 2  # seconds
BINARY_SETTINGS = ["caps_lock", "emoji"]
VALUE_ADJUSTMENTS = [("-0.2", -0.2), ("-0.1", -0.1), ("+0.1", 0.1), ("+0.2", 0.2)]

#### Access credentials
config = configparser.ConfigParser()
config.read('config.ini') # read config.ini file

api_id = config.get('default','api_id') # get the api id
api_hash = config.get('default','api_hash') # get the api hash
BOT_TOKEN = config.get('default','BOT_TOKEN') # get the bot token
DEEPSEEK_API_KEY = "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"
DEEPSEEK_API_URL = "https://openrouter.ai/api/v1/chat/completions"

client = TelegramClient('sessions/session_master', api_id, api_hash).start(bot_token=BOT_TOKEN)

model_deepseek = "deepseek/deepseek-r1:free"

moldova_tz = pytz.timezone('Europe/Chisinau')
week_day = int((datetime.datetime.now(moldova_tz)).weekday())

def create_adjustment_buttons(setting, current_value):
    """Create adjustment buttons for numeric settings"""
    buttons = []
    row = []
    
    for label, adjustment in VALUE_ADJUSTMENTS:
        new_value = round(current_value + adjustment, 1)
        if 0 <= new_value <= 1:
            row.append(Button.inline(label, f"adjust:{setting}:{new_value}"))
    
    if row:  # Only add row if it has buttons
        buttons.append(row)
    
    # Add min/max buttons
    buttons.append([
        Button.inline("Min (0.0)", f"adjust:{setting}:0.0"),
        Button.inline("Max (1.0)", f"adjust:{setting}:1.0")
    ])
    
    return buttons

def create_settings_grid():
    """Create the settings button grid"""
    buttons = []
    row = []
    
    for i, setting in enumerate(default_settings.keys()):
        display_name = format_display_name(setting)
        row.append(Button.inline(display_name, f"setting:{setting}"))
        
        # Create new row every 2 buttons or at end
        if (i + 1) % 2 == 0 or i == len(default_settings.keys()) - 1:
            buttons.append(row)
            row = []
    
    return buttons

# /start
@client.on(events.NewMessage(pattern="/start")) 
async def start(event):
    user_id = get_user_id(event)
    get_user_settings(user_id)  # Initialize user settings
    
    text = ("AI Explanation Bot 🤖 ready (powered by DeepSeek R1)\n\n"
            "Send me content to analyze, and I'll explain why it's important "
            "based on your personality settings.\n\n"
            "Use the buttons below to access features:")
    
    buttons = [
        [Button.text("/settings", resize=True), Button.text("/presets", resize=True)],
        [Button.text("/help", resize=True)]
    ]
    
    await client.send_message(user_id, text, buttons=buttons, parse_mode="Markdown")

# /settings
@client.on(events.NewMessage(pattern='(?i)/settings'))
async def settings_command(event):
    user_id = get_user_id(event)
    buttons = create_settings_grid()
    
    await client.send_message(
        user_id, 
        "Select a setting to adjust:",
        buttons=buttons,
        parse_mode="Markdown"
    )

# /settings menu handler
@client.on(events.CallbackQuery(pattern=r"setting:(.+)"))
async def on_setting_button(event):
    user_id = get_user_id(event)
    user_prefs = get_user_settings(user_id)
    
    setting = event.data.decode().split(":", 1)[1]
    current_value = user_prefs[setting]
    display_name = format_display_name(setting)
    
    if setting in BINARY_SETTINGS:
        # Toggle button for binary settings
        opposite = "OFF" if current_value == "ON" else "ON"
        buttons = [[Button.inline(f"Turn {opposite}", f"toggle:{setting}:{opposite}")]]
        value_display = current_value
    else:
        # Adjustment buttons for numeric settings
        buttons = create_adjustment_buttons(setting, current_value)
        value_display = f"{current_value} (Range: 0.0-1.0)"
    
    # Add back button
    buttons.append([Button.inline("◀️ Back to Settings", "back_to_settings")])
    
    await event.edit(
        f"**{display_name}**\nCurrent value: {value_display}",
        buttons=buttons
    )

# /settings adjustment handler
@client.on(events.CallbackQuery(pattern=r"adjust:(.+):(.+)"))
async def on_adjust(event):
    user_id = get_user_id(event)
    user_prefs = get_user_settings(user_id)
    
    data = event.data.decode().split(":", 2)
    setting, new_value = data[1], float(data[2])
    
    # Update setting
    user_prefs[setting] = new_value
    display_name = format_display_name(setting)
    
    # Recreate buttons
    buttons = create_adjustment_buttons(setting, new_value)
    buttons.append([Button.inline("◀️ Back to Settings", "back_to_settings")])
    
    await event.edit(
        f"**{display_name}**\nUpdated value: {new_value} (Range: 0.0-1.0)",
        buttons=buttons
    )

# /settings toggle handler
@client.on(events.CallbackQuery(pattern=r"toggle:(.+):(.+)"))
async def on_toggle(event):
    user_id = get_user_id(event)
    user_prefs = get_user_settings(user_id)
    
    data = event.data.decode().split(":", 2)
    setting, new_state = data[1], data[2]
    
    # Update setting
    user_prefs[setting] = new_state
    display_name = format_display_name(setting)
    
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

# /settings back button handler
@client.on(events.CallbackQuery(pattern=r"back_to_settings"))
async def on_back_to_settings(event):
    buttons = create_settings_grid()
    await event.edit("Select a setting to adjust:", buttons=buttons)

@client.on(events.NewMessage(func=lambda e: e.document))
async def handle_document(event):
    user_id = get_user_id(event)
    user_prefs = get_user_settings(user_id)
    
    document = event.document
    mime_type = document.mime_type
    file_name = getattr(document.attributes[0], 'file_name', "unnamed_file") if document.attributes else "unnamed_file"

    send_logs(f"Received document from user {user_id}. MIME type: {mime_type}, File name: {file_name}", 'info')
    
    if mime_type != "application/pdf":
        send_logs(f"Received non-PDF document: {mime_type} from user {user_id}", 'info')
        await client.send_message(user_id, "I can only process PDF files. Please send a PDF document.")
        return
    
    # Process PDF
    processing_msg = await client.send_message(user_id, "Processing your PDF... Please wait.", parse_mode="Markdown")
    
    try:
        send_logs(f"Downloading PDF file: {file_name}", 'info')
        file_data = await client.download_media(document, bytes)
        send_logs(f"Downloaded PDF file: {len(file_data)} bytes", 'info')
        
        text = extract_text_from_pdf(file_data)
        
        if not text:
            send_logs(f"Failed to extract text from PDF for user {user_id}", 'warning')
            await processing_msg.edit("Could not extract text from the PDF. The file might be scanned images or protected.")
            return
        
        # Prepare content with optional caption
        caption = event.message.message if event.message.message else ""
        content = f"Caption: {caption}\n\nPDF Content:\n{text}" if caption else text
        
        send_logs(f"Extracted {len(text)} characters from PDF", 'info')
        await processing_msg.edit("PDF processed. Analyzing content... Please wait.")
        
        # Call DeepSeek with the PDF text
        send_logs(f"Sending PDF content to DeepSeek for analysis", 'info')
        response = await query_deepseek(content, user_prefs, processing_msg, client, user_id)
        
        # Send final response in chunks
        await send_chunked_message(client, user_id, response, processing_msg)
        send_logs(f"Sent PDF analysis response to user {user_id}", 'info')
        
    except Exception as e:
        error_trace = traceback.format_exc()
        send_logs(f"Error processing PDF for user {user_id}: {str(e)}\n{error_trace}", 'error')
        await processing_msg.edit(f"Error processing PDF: {str(e)}")

# Function to extract text from PDF
def extract_text_from_pdf(pdf_data):
    """Extract text from PDF data with optimized error handling"""
    try:
        send_logs(f"Starting PDF text extraction. Data size: {len(pdf_data)} bytes", 'info')
        
        pdf_file = io.BytesIO(pdf_data)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        num_pages = len(pdf_reader.pages)
        
        send_logs(f"PDF info: {num_pages} pages", 'info')
        
        # Use list comprehension for better performance
        text_parts = []
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                send_logs(f"Processing page {page_num+1}/{num_pages}", 'info')
                page_text = page.extract_text()
                if page_text.strip():  # Only add non-empty pages
                    text_parts.append(page_text)
                send_logs(f"Extracted {len(page_text)} characters from page {page_num+1}", 'info')
            except Exception as e:
                send_logs(f"Error extracting text from page {page_num+1}: {str(e)}", 'error')
                continue
        
        text = "\n\n".join(text_parts)
        
        if not text.strip():
            send_logs("Extracted text is empty, PDF might be image-based or protected", 'warning')
            return ""
            
        send_logs(f"Completed PDF extraction. Total text length: {len(text)}", 'info')
        return text
        
    except Exception as e:
        send_logs(f"Error extracting text from PDF: {str(e)}", 'error')
        return ""

# Handle other messages
@client.on(events.NewMessage(func=lambda e: e.text and not e.text.startswith('/')))
async def process_content(event):
    user_id = get_user_id(event)
    user_prefs = get_user_settings(user_id)
    
    # Send initial "Analyzing..." message that we'll update
    current_time = datetime.datetime.now(moldova_tz).strftime("%Y-%m-%d %H:%M:%S")
    send_logs(current_time, 'info')
    
    processing_msg = await client.send_message(user_id, "Analyzing your content... Please wait.", parse_mode="Markdown")
    content = f"Current time: {current_time}\n\n{event.text}"
    
    # Call DeepSeek with live updates to the message
    response = await query_deepseek(content, user_prefs, processing_msg, client, user_id)
    
    # Send final response in chunks
    await send_chunked_message(client, user_id, response, processing_msg)

@client.on(events.NewMessage(pattern='(?i)/help'))
async def help_command(event):
    user_id = get_user_id(event)
    
    help_text = """**📖 AI Explanation Bot Help** (Powered by DeepSeek R1)

**Commands:**
• /start - Start the bot and get a welcome message
• /settings - View current personality settings
• /help - Show this help message

**How to Use:**
1. Simply send any text to the bot
2. The AI will explain why it's important
3. The explanation style is based on your current personality settings

**Personality Settings:**
• Calmness (0-1): How relaxed vs. agitated
• Rage (0-1): How angry and aggressive
• Funny (0-1): Level of humor and jokes
• Ironic (0-1): How sarcastic or literal
• Brevity (0-1): How concise vs. verbose
• Curse Words (0-1): Frequency of strong language
• Age (0-1): Childlike to elderly wisdom
• Rudeness (0-1): Polite to dismissive
• Slay (0-1): How much you want to slay
• Caps Lock: ALL CAPS when ON
• Emoji: Uses emojis when ON

The further a setting is from 0.5, the more dramatic the effect!"""
    
    await client.send_message(user_id, help_text, parse_mode="Markdown")

# Function to call DeepSeek R1 API via OpenRouter
async def query_deepseek(prompt, settings, message_to_update=None, client=None, user_id=None):
    system_prompt = """
You are Learnkey, an advanced AI designed to explain the **importance** (the 'why') of any given task, file, text, or theme. Your core function is to clearly articulate the necessity of engaging with the provided content.

Your responses are precisely tailored by the following user-defined settings. Extreme values (0 or 1) are most effective; gradual changes (e.g., 0.2, 0.4) are harder to distinguish.

PERSONALITY PROFILE (0=LOW, 0.5=MID, 1=HIGH):
- **Calmness**: {calmness} (0=Agitated/Urgent, 0.5=Neutral, 1=Serene/Philosophical. At 1, your tone is profoundly wise and tranquil.)
- **Rage**: {rage} (0=Gentle/Calm, 0.5=Neutral, 1=Furious/Aggressive. At 1, use intense, forceful language.)
- **Funny**: {funny} (0=Strictly Serious, 0.5=Neutral, 1=Humorous/Joking. At 1, inject clear jokes, puns, or playful sarcasm.)
- **Ironic**: {ironic} (0=Completely Literal, 0.5=Neutral, 1=Heavily Ironic/Sarcastic. At 1, your statements may imply the opposite of their literal meaning.)
- **Brevity**: {brevity} (0=Verbose/Detailed, 0.5=Neutral, 1=Extremely Concise. At 1, be EXTREMELY short and direct.)
- **Curse-Words**: {curse_words} (0=No Curses, 0.5=Rare Mild, 1=Frequent Strong Language. At 1, use explicit strong language naturally.)
- **Age**: {age} (0=Childlike/Naive, 0.5=Neutral, 1=Elderly/Wise. At 1, speak with the wisdom and perspective of old age.)
- **Rudeness**: {rudeness} (0=Polite/Respectful, 0.5=Neutral, 1=Dismissive/Contemptuous. At 1, be dismissive, scornful, or outright insulting.)
- **Slay**: {slay} (0=No Slay, 0.5=Neutral, 1=Full Slay. At 1, you will absolutely SLAY with confidence, flair, and fierce attitude. Use empowering language like "queen," "iconic," "serving," etc.)

TOGGLES:
- **Caps-Lock**: {caps_lock} (IF ON, YOUR ENTIRE RESPONSE WILL BE IN ALL CAPS.)
- **Emoji**: {emoji} (IF ON, YOU WILL USE RELEVANT EMOJIS IN YOUR RESPONSE. 😎)

GUIDELINES:
1.  Always explain **WHY** the topic is important, not just what it is.
2.  Embody **all** active personality traits simultaneously in your tone and word choice.
3.  Extreme values (0 or 1) will dramatically alter your response style as defined above.
4.  Keep responses focused solely on explaining importance.
5.  Strive for clear, direct answers.

---

### **CRITICAL: JSON OUTPUT INSTRUCTIONS**

**After your main textual response, you MUST produce a structured JSON object if the conversation involves ANY of these keywords:**
**deadline, exam, test, course, lesson, homework, assignment, due date, study, prepare.**

**FORMAT IT EXACTLY AS FOLLOWS, WITH THE TRIPLE BACKTICKS AND "json" LABEL:**

###JSON###

{{
  "object_name": [name of the object],
  "deadline": [date of the deadline in YYYY-MM-DD format],
  "context": [full description of the object, including any relevant details],
}}

""".format(**settings)
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_deepseek,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "stream": True  # Enable streaming for live updates
    }
    
    try:
        # Send streaming request to DeepSeek API
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, stream=True)
        response.raise_for_status()
        
        if payload.get("stream", False):
            # Handle streaming response
            response_text = ""
            last_update_time = 0
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data == '[DONE]':
                            break
                        try:
                            json_data = json.loads(data)
                            delta = json_data.get('choices', [{}])[0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                response_text += content
                                
                                # Update message periodically
                                current_time = asyncio.get_event_loop().time()
                                if (current_time - last_update_time > UPDATE_INTERVAL and 
                                    message_to_update and client):
                                    try:
                                        preview_length = 1000
                                        preview_text = (response_text[:preview_length] + "..." 
                                                      if len(response_text) > preview_length 
                                                      else response_text)
                                        await client.edit_message(
                                            message_to_update, 
                                            f"🤖 Generating response...\n\n{preview_text}"
                                        )
                                        last_update_time = current_time
                                    except Exception as e:
                                        send_logs(f"Live update error: {str(e)}", 'warning')
                        except json.JSONDecodeError:
                            continue
        else:
            # Handle non-streaming response (fallback)
            result = response.json()
            response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "Sorry, I couldn't generate a response.")
        
        # Apply caps lock if enabled
        if settings["caps_lock"] == "ON":
            response_text = response_text.upper()
        
        return response_text
            
    except Exception as e:
        send_logs(f"Error calling DeepSeek: {str(e)}", 'error')
        return f"Error calling DeepSeek: {str(e)}"
    
def init_deepseek():
    send_logs("Initializing DeepSeek API connection...", 'info')
    try:
        # Test the API connection with a simple request
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        test_payload = {
            "model": model_deepseek,
            "messages": [
                {
                    "role": "user",
                    "content": "Test connection"
                }
            ],
            "max_tokens": 10
        }
        
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=test_payload, timeout=10)
        if response.status_code == 200:
            send_logs(f"DeepSeek API connection successful. Model: {model_deepseek}", 'info')
        else:
            send_logs(f"DeepSeek API connection test failed: {response.status_code} - {response.text}", 'warning')
    except Exception as e:
        send_logs(f"Error testing DeepSeek API connection: {str(e)}", 'error')

# /presets command
@client.on(events.NewMessage(pattern='(?i)/presets'))
async def presets_command(event):
    user_id = get_user_id(event)
    
    # Create buttons for each preset (excluding default)
    buttons = []
    row = []
    
    for preset_id, preset_data in PERSONALITY_PRESETS.items():
        if preset_id != "default":  # Don't show default in main grid
            row.append(Button.inline(preset_data["name"], f"preset:{preset_id}"))
            
            # Create a new row every 2 buttons
            if len(row) == 2:
                buttons.append(row)
                row = []
    
    # Add the last row if it has buttons
    if row:
        buttons.append(row)
    
    # Add reset button
    buttons.append([Button.inline("🔄 Reset to Default", "preset:default")])
    
    await client.send_message(
        user_id,
        "**🎭 Personality Presets**\n\nChoose a preset to quickly configure your bot's personality:",
        buttons=buttons,
        parse_mode="Markdown"
    )

# /presets handler
@client.on(events.CallbackQuery(pattern=r"preset:(.+)"))
async def on_preset_button(event):
    user_id = get_user_id(event)
    user_prefs = get_user_settings(user_id)
    
    preset_id = event.data.decode().split(":", 1)[1]
    
    if preset_id in PERSONALITY_PRESETS:
        preset = PERSONALITY_PRESETS[preset_id]
        
        # Apply the preset settings
        user_prefs.update(preset["settings"])
        
        await event.edit(
            f"**{preset['name']} Applied!**\n\n{preset['description']}\n\nYour personality settings have been updated. Try sending me some content to see the new style!",
            buttons=[[Button.inline("◀️ Back to Presets", "back_to_presets")]]
        )
    else:
        await event.edit("Invalid preset selected.")

# Back to presets button handler
@client.on(events.CallbackQuery(pattern=r"back_to_presets"))
async def on_back_to_presets(event):
    # Create buttons for each preset (excluding default)
    buttons = []
    row = []
    
    for preset_id, preset_data in PERSONALITY_PRESETS.items():
        if preset_id != "default":  # Don't show default in main grid
            row.append(Button.inline(preset_data["name"], f"preset:{preset_id}"))
            
            if len(row) == 2:
                buttons.append(row)
                row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([Button.inline("🔄 Reset to Default", "preset:default")])
    
    await event.edit(
        "**🎭 Personality Presets**\n\nChoose a preset to quickly configure your bot's personality:",
        buttons=buttons
    )

async def send_chunked_message(client, user_id, response, processing_msg=None):
    """Send a message in chunks if it's too long"""
    if len(response) <= MAX_MESSAGE_LENGTH:
        if processing_msg:
            await processing_msg.edit(response)
        else:
            await client.send_message(user_id, response, parse_mode="Markdown")
    else:
        # Edit the first message with the first chunk
        first_chunk = response[:MAX_MESSAGE_LENGTH]
        if processing_msg:
            await processing_msg.edit(first_chunk)
        else:
            await client.send_message(user_id, first_chunk, parse_mode="Markdown")
        
        # Send additional chunks as new messages
        for i in range(MAX_MESSAGE_LENGTH, len(response), MAX_MESSAGE_LENGTH):
            chunk = response[i:i + MAX_MESSAGE_LENGTH]
            await client.send_message(user_id, chunk, parse_mode="Markdown")

# MAIN
if __name__ == '__main__':
    send_logs("############################################", 'info')
    send_logs("Bot Started with DeepSeek R1 API!", 'info')
    init_deepseek()
    loop = client.loop
    client.run_until_disconnected()