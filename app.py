import os
import openai
import requests
from celery import Celery
from twilio.rest import Client
from flask import Flask, request, Response
from dotenv import load_dotenv
import speech_recognition as sr
import asyncio
import websockets
import json
import uuid

# Set up the Flask app
app = Flask(__name__)

load_dotenv()

# Configure Twilio, OpenAI, and Whisper API credentials
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize Celery
celery = Celery(app.name, broker=os.getenv('CELERY_BROKER_URL'))
celery.conf.update(result_backend=os.getenv('CELERY_RESULT_BACKEND'), task_serializer='json', result_serializer='json',
                   accept_content=['json'])

openai.api_key = openai_api_key


@celery.task
def process_voice_message(recording_url, to_phone_number):
    """
    Process the voice message and send a response back to the user
    :param recording_url:  The URL of the voice message
    :param to_phone_number:    The phone number to send the response to
    :return:   None
    """
    # Download the voice message
    response = requests.get(recording_url)

    file_id = str(uuid.uuid4())
    wav_file_name = f"voice_message_{file_id}"

    wav_file = wav_file_name + ".wav"

    with open(wav_file, "wb") as f:
        f.write(response.content)

    # Convert voice to text using Whisper API
    text = convert_voice_to_text(wav_file)

    # Send the text to GPT-3.5 and get a response
    response = generate_gpt_response(text)

    os.remove(wav_file)

    # Send the response back to the user
    # send_response(response, to_phone_number)
    return response


def convert_voice_to_text(file_path):
    """
    Convert the voice message to text using the Whisper API
    :param file_path:  The path to the voice message
    :return:   The text from the voice message
    """
    # Implement the Whisper ASR API integration here
    file_name = os.path.basename(file_path)
    r = sr.Recognizer()
    with sr.AudioFile(file_name) as source:
        audio_data = r.record(source)
        text = r.recognize_google(audio_data)

    text = text.lower()

    return text


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


# async def send_data_to_crm_websocket(data):
#     async with websockets.connect("wss://example.com/crm-websocket-url") as websocket:
#         await websocket.send(json.dumps(data))


def send_response(response, to_phone_number):
    """
    Send the response back to the user using Twilio and to the CRM webhook
    :param response:   The response to send back to the user
    :param to_phone_number:    The phone number to send the response to
    :return:    None
    """
    print(response)

    # Send the response using Twilio
    # client = Client(twilio_account_sid, twilio_auth_token)
    # message = client.messages.create(
    #     body=response,
    #     from_=twilio_phone_number,
    #     to=to_phone_number
    # )

    # Send the response to the CRM using WebSocket
    crm_websocket_data = {
        "phone_number": to_phone_number,
        "response": response,
    }
    # Send the data to the CRM WebSocket
    # asyncio.get_event_loop().run_until_complete(send_data_to_crm_websocket(crm_websocket_data))


@app.route("/webhook", methods=["POST"])
def webhook():
    print(request.form)  # Add this line to debug the request parameters

    recording_url = request.form.get("RecordingUrl")
    from_phone_number = "+8801784056345"  # Change this line to get the "From" parameter

    if recording_url and from_phone_number:
        print("Received voice message from Twilio")
        print("Recording URL: ", recording_url)
        task = process_voice_message.apply_async(args=[recording_url, from_phone_number])
        response = task.get()
        print("Response: ", response)

        return Response(status=200)
    else:
        return Response(status=400)


if __name__ == "__main__":
    app.run()
