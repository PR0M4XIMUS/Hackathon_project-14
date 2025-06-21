import numpy as np 
import datetime
import pytz

import time
from collections import defaultdict

moldova_tz = pytz.timezone('Europe/Chisinau')
time_zone = pytz.timezone('Europe/Chisinau')
#logs
import logging

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '\033[92m',   # Green
        'WARNING': '\033[93m', # Yellow
        'ERROR': '\033[91m',   # Red
        'CRITICAL': '\033[91m\033[1m', # Bold Red
        'RESET': '\033[0m'    # Reset color
    }

    def format(self, record):
        # Format without the levelname, which we'll add separately with color
        formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Get the log message without the level
        log_message = formatter.format(record)
        
        # Add the colored level tag
        colored_level = f"{self.COLORS.get(record.levelname, self.COLORS['RESET'])}[{record.levelname}]{self.COLORS['RESET']}"
        
        # Insert the colored level at the position after the timestamp
        parts = log_message.split(' | ', 1)
        if len(parts) == 2:
            return f"{parts[0]} | {colored_level} {parts[1]}"
        return log_message
    
# Create formatters - one with color for console, one without for file
file_formatter = logging.Formatter(
    '%(asctime)s.%(msecs)03d | [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_formatter = ColoredFormatter(
    '%(asctime)s.%(msecs)03d | [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create handlers
file_handler = logging.FileHandler("learnkeybot.log")
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logging.Formatter.converter = lambda *args: \
    datetime.datetime.now(time_zone).timetuple()

#week days
week_days = {
    0 : "Luni",
    1 : "Marţi",
    2 : "Miercuri",
    3 : "Joi",
    4 : "Vineri",
    5 : "Sâmbătă",
    6 : "Duminica"
}

default_settings = {
    "calmness": 0.5,
    "rage": 0.5,
    "funny": 0.5,
    "ironic": 0.5,
    "brevity": 0.5,
    "curse_words": 0.5,
    "age": 0.5,
    "rudeness": 0.5,
    "slay": 0.5,
    "caps_lock": "OFF",
    "emoji": "ON"
}

# Centralized presets configuration
PERSONALITY_PRESETS = {
    "friendly": {
        "name": "🤗 Friendly",
        "description": "Warm, helpful, and encouraging",
        "settings": {
            "calmness": 0.8, "rage": 0.0, "funny": 0.3, "ironic": 0.1,
            "brevity": 0.4, "curse_words": 0.0, "age": 0.4, "rudeness": 0.0,
            "slay": 0.2, "caps_lock": "OFF", "emoji": "ON"
        }
    },
    "aggressive": {
        "name": "😤 Rage Mode",
        "description": "Intense, forceful, and brutally direct",
        "settings": {
            "calmness": 0.0, "rage": 1.0, "funny": 0.1, "ironic": 0.2,
            "brevity": 0.9, "curse_words": 0.9, "age": 0.3, "rudeness": 0.8,
            "slay": 0.9, "caps_lock": "ON", "emoji": "OFF"
        }
    },
    "sarcastic": {
        "name": "😏 Sarcastic Genius",
        "description": "Witty, ironic, and devastatingly clever",
        "settings": {
            "calmness": 0.7, "rage": 0.2, "funny": 0.9, "ironic": 1.0,
            "brevity": 0.6, "curse_words": 0.4, "age": 0.6, "rudeness": 0.6,
            "slay": 0.8, "caps_lock": "OFF", "emoji": "ON"
        }
    },
    "wise": {
        "name": "🧙‍♂️ Ancient Sage",
        "description": "Profound wisdom from the depths of experience",
        "settings": {
            "calmness": 1.0, "rage": 0.0, "funny": 0.0, "ironic": 0.0,
            "brevity": 0.1, "curse_words": 0.0, "age": 1.0, "rudeness": 0.0,
            "slay": 0.0, "caps_lock": "OFF", "emoji": "OFF"
        }
    },
    "chaotic": {
        "name": "🌪️ Chaotic Energy",
        "description": "Unpredictable, wild, and absolutely unhinged",
        "settings": {
            "calmness": 0.0, "rage": 0.7, "funny": 1.0, "ironic": 0.8,
            "brevity": 0.3, "curse_words": 0.7, "age": 0.1, "rudeness": 0.9,
            "slay": 1.0, "caps_lock": "ON", "emoji": "ON"
        }
    },
    "millennial": {
        "name": "💅 Millennial Vibe",
        "description": "That's not giving what it's supposed to give, bestie",
        "settings": {
            "calmness": 0.4, "rage": 0.3, "funny": 0.8, "ironic": 0.7,
            "brevity": 0.7, "curse_words": 0.2, "age": 0.3, "rudeness": 0.4,
            "slay": 1.0, "caps_lock": "OFF", "emoji": "ON"
        }
    },
    "gen_z": {
        "name": "💀 Gen Z Energy", 
        "description": "No cap, this is bussin fr fr",
        "settings": {
            "calmness": 0.2, "rage": 0.1, "funny": 1.0, "ironic": 0.9,
            "brevity": 0.9, "curse_words": 0.3, "age": 0.0, "rudeness": 0.3,
            "slay": 1.0, "caps_lock": "OFF", "emoji": "ON"
        }
    },
    "corporate": {
        "name": "💼 Corporate Speak",
        "description": "Synergizing actionable insights with scalable solutions",
        "settings": {
            "calmness": 0.8, "rage": 0.0, "funny": 0.0, "ironic": 0.1,
            "brevity": 0.2, "curse_words": 0.0, "age": 0.7, "rudeness": 0.0,
            "slay": 0.0, "caps_lock": "OFF", "emoji": "OFF"
        }
    },
    "motivational": {
        "name": "💪 Motivational Coach",
        "description": "YOU CAN DO THIS! BELIEVE IN YOURSELF!",
        "settings": {
            "calmness": 0.1, "rage": 0.0, "funny": 0.4, "ironic": 0.0,
            "brevity": 0.6, "curse_words": 0.0, "age": 0.4, "rudeness": 0.0,
            "slay": 0.9, "caps_lock": "ON", "emoji": "ON"
        }
    },
    "nihilistic": {
        "name": "🖤 Nihilistic Void",
        "description": "Nothing matters, but here's why you should care anyway",
        "settings": {
            "calmness": 0.9, "rage": 0.0, "funny": 0.3, "ironic": 0.8,
            "brevity": 0.7, "curse_words": 0.2, "age": 0.8, "rudeness": 0.6,
            "slay": 0.0, "caps_lock": "OFF", "emoji": "OFF"
        }
    },
    "villain": {
        "name": "😈 Evil Mastermind",
        "description": "Muahahaha! Let me explain my diabolical plan...",
        "settings": {
            "calmness": 0.8, "rage": 0.4, "funny": 0.6, "ironic": 0.7,
            "brevity": 0.3, "curse_words": 0.3, "age": 0.6, "rudeness": 0.8,
            "slay": 0.9, "caps_lock": "OFF", "emoji": "ON"
        }
    },
    "child": {
        "name": "🧒 Curious Kid",
        "description": "OMG this is like, SO cool! Did you know that...",
        "settings": {
            "calmness": 0.2, "rage": 0.0, "funny": 0.9, "ironic": 0.0,
            "brevity": 0.3, "curse_words": 0.0, "age": 0.0, "rudeness": 0.0,
            "slay": 0.3, "caps_lock": "OFF", "emoji": "ON"
        }
    },
    "default": {
        "name": "🔄 Default",
        "description": "Balanced neutral settings",
        "settings": default_settings.copy()
    }
}


def button_grid(buttons, butoane_rand):
    grid = []
    row = []
    for button in buttons:
        if button.text == "Back":
            if row:
                grid.append(row)
            row = [button]
        else:
            row.append(button)
        if len(row) != butoane_rand:
            continue
        grid.append(row)
        row = []
    if row:
        grid.append(row)
    return grid


def send_logs(message, type):
    if type =='info':
        logging.info(message)
    elif type =='warning':
        logging.warning(message)
    elif type =='error':
        logging.error(message)
    elif type =='critical':
        logging.critical(message)
    else: 
        logging.info(message)
        
def get_user_id(event):
    """Extract user ID from event"""
    return event.sender_id

def format_display_name(setting):
    """Format setting name for display"""
    return setting.replace('_', ' ').title()

user_settings = {}

def get_user_settings(user_id):
    if user_id not in user_settings:
        user_settings[user_id] = default_settings.copy()
    return user_settings[user_id]
