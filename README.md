# AI Explanation Bot

This project is a Telegram bot powered by the DeepSeek AI model. It's designed to receive text or PDF documents and provide an explanation of their importance, tailored to a user-configurable personality. The bot's responses are streamed in real-time for a more interactive experience.

## Features

- **Dynamic Personality:** Adjust the bot's tone and style using a variety of settings like `calmness`, `rage`, `humor`, and more.
- **Personality Presets:** Quickly switch between pre-configured personalities like "Friendly," "Sarcastic Genius," or "Evil Mastermind" using the `/presets` command.
- **PDF Document Analysis:** Upload a PDF document, and the bot will extract the text and provide an explanation based on your current settings.
- **Streaming Responses:** Get real-time feedback as the AI generates its response, character by character.
- **Dockerized:** Comes with a `Dockerfile` and `docker-compose.yml` for easy setup and deployment.

## Technologies Used

- **Python**: The core programming language.
- **Telethon**: A Python library to interact with the Telegram API.
- **DeepSeek API (via OpenRouter)**: The large language model used for generating explanations.
- **PyPDF2**: A library for extracting text from PDF files.
- **Docker & Docker Compose**: For containerization and easy deployment.

## Setup and Usage

### 1. Prerequisites

- Python 3.9+
- Docker and Docker Compose (for containerized deployment)
- A Telegram Bot Token from BotFather.
- An OpenRouter API Key (for DeepSeek access).

### 2. Configuration

1.  Clone this repository.
2.  Rename `config_template.ini` to `config.ini`.
3.  Open `config.ini` and fill in your credentials:
    ```ini
    [default]
    ; Get from my.telegram.org
    api_id = YOUR_API_ID
    api_hash = YOUR_API_HASH

    ; Get from BotFather on Telegram
    BOT_TOKEN = YOUR_TELEGRAM_BOT_TOKEN

    ; Get from https://openrouter.ai/
    DEEPSEEK_API_KEY = sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    ```

### 3. Running the Bot

#### Using Docker (Recommended)

The easiest way to run the bot is with Docker Compose.

1.  **Build the image:**
    ```bash
    docker build --tag dockerbot .
    ```
2.  **Run the services:**
    ```bash
    docker-compose up
    ```
    This will start the bot and conncet to OpenRouter API

#### Running Locally

1.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the script:**
    ```bash
    python script.py
    ```

### How to Interact with the Bot

1.  **Start a chat:** Find your bot on Telegram and send the `/start` command.
2.  **Configure Personality (Optional):**
    - Use `/settings` to fine-tune individual personality traits.
    - Use `/presets` to select a pre-made personality.
3.  **Get Explanations:**
    - Send any text message.
    - Upload a PDF file.

The bot will analyze the content and respond with an explanation tailored to the configured personality.

## Bot Commands

- `/start`: Initializes the bot and shows a welcome message.
- `/settings`: Opens a menu to adjust the AI's personality traits.
- `/presets`: Allows you to choose from a list of pre-defined personalities.
- `/help`: Displays a detailed help message explaining all features.
