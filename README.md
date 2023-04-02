# Twilio studio GPT-3 assistant
Twilio Studio Voice Message Processor with GPT-3.5 and OpenAI Whisper is a Flask application that receives voice messages recorded through Twilio or Twilio Studio, transcribes them using OpenAI's Whisper ASR, generates responses with GPT-3.5, and sends the replies as SMS using Twilio.

## Technology
- Flask
- Celery
- OpenAI Whisper ASR
- OpenAI GPT-3.5
- Twilio API
- Redis

## Features
- Record voice messages via Twilio or Twilio Studio
- Transcribe voice messages using OpenAI's Whisper ASR
- Generate responses with OpenAI's GPT-3.5
- Send responses as SMS using Twilio

## Future Scope
- Support for multiple languages
- Real-time voice conversation
- Integration with more AI models
- Customizable response generation

## Installation

- Clone the repository:
  ```bash
  git clone https://github.com/shamspias/twilio-voice-message-processor.git
  ```
- Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
- Set up environment variables:

  Create a .env file with the required credentials:

    ```bash
    TWILIO_ACCOUNT_SID=your_twilio_account_sid
    TWILIO_AUTH_TOKEN=your_twilio_auth_token
    TWILIO_PHONE_NUMBER=your_twilio_phone_number
    OPENAI_API_KEY=your_openai_api_key
    REDIS_URL=redis://localhost:6379/0
    ```
- Run the Flask application:
    ```bash
    python app.py
    ```
- Run Celery worker:
    ```bash
    celery -A app.celery_app worker --loglevel=info
    ```
## API Endpoints
- `/webhook` (POST): Receives a webhook from Twilio with voice message details and processes the message.

## Usage
1. Configure your Twilio Studio flow or TwiML Bin to use the webhook URL for your deployed Flask app (e.g., `https://yourdomain.com/webhook`).

2. Call your Twilio phone number and record a voice message.

3. Upon completion, the webhook will be triggered, and the Flask app will process the voice message using Whisper ASR and GPT-3.5.

4. The generated response will be sent back as an SMS to the caller's phone number.

5. Check your phone for an SMS containing the response from GPT-3.5.