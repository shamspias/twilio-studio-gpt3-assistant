import os
import openai
import requests
from celery import Celery
from twilio.rest import Client
from flask import Flask, request, Response
from dotenv import load_dotenv

load_dotenv()

# Configure Twilio, OpenAI, and Whisper API credentials
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Set up the Celery app
celery_app = Celery("tasks", broker=os.getenv('CELERY_BROKER_URL'), backend=os.getenv('CELERY_RESULT_BACKEND'))

openai.api_key = openai_api_key


@celery_app.task
def process_voice_message(recording_url, to_phone_number):
    """
    Process the voice message and send a response back to the user
    :param recording_url:  The URL of the voice message
    :param to_phone_number:    The phone number to send the response to
    :return:   None
    """
    # Download the voice message
    response = requests.get(recording_url)
    with open("voice_message.wav", "wb") as f:
        f.write(response.content)

    # Convert voice to text using Whisper API
    text = convert_voice_to_text("voice_message.wav")

    # Send the text to GPT-3.5 and get a response
    response = generate_gpt_response(text)

    # Send the response back to the user
    send_response(response, to_phone_number)


def convert_voice_to_text(file_path):
    """
    Convert the voice message to text using the Whisper API
    :param file_path:  The path to the voice message
    :return:   The text from the voice message
    """
    # Implement the Whisper ASR API integration here
    transcript = openai.Audio.transcribe("whisper-1", file_path)
    return transcript["text"].strip()


def generate_gpt_response(text):
    """
    Send the text to GPT-3.5 and get a response
    :param text:  The text to send to GPT-3.5
    :return:  The response from GPT-3.5
    """
    # Implement the OpenAI API integration here
    message_list = [{"role": "user", "content": text}]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
                     {"role": "system",
                      "content": "You are an AI named sonic and you are in a conversation with a human. You can answer "
                                 "questions, provide information, and help with a wide variety of tasks."},
                     {"role": "user", "content": "Who are you?"},
                     {"role": "assistant",
                      "content": "I am the sonic powered by ChatGpt.Contact me sonic@deadlyai.com"},
                 ] + message_list
    )

    return response["choices"][0]["message"]["content"].strip()


def send_response(response, to_phone_number):
    """
    Send the response back to the user using Twilio
    :param response:   The response to send back to the user
    :param to_phone_number:    The phone number to send the response to
    :return:    None
    """
    print(response)
    # # Implement the response sending using Twilio here
    # # https://www.twilio.com/docs/quickstart/python/sms
    # client = Client(twilio_account_sid, twilio_auth_token)
    # message = client.messages.create(
    #     body=response,
    #     from_=twilio_phone_number,
    #     to=to_phone_number
    # )


# Set up the Flask app
app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    This is the webhook that Twilio will call when a voice message is received.
    :return:  Response
    """
    recording_url = request.form.get("RecordingUrl")
    to_phone_number = request.form.get("To")

    if recording_url and to_phone_number:
        process_voice_message.delay(recording_url, to_phone_number)
        return Response(status=200)
    else:
        return Response(status=400)


if __name__ == "__main__":
    app.run()
