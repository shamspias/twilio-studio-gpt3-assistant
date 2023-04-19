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
def process_voice_message(recording_url, to_phone_number, recording_sid):
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

    keywords = generate_gpt_keyword_response(text)

    # Send the response back to the user
    send_response(id_conv=recording_sid, recording_url=recording_url, voicemessage_transcription=wav_file,
                  voicemessage_resume=response, voicemessage_tags=keywords, to_phone_number=to_phone_number)
    os.remove(wav_file)
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
                      "content": "You are an AI that expertise to make resume. you make resume for everyone with "
                                 "proper section and format. You don't need more information to make a resume you can make a resume out of name."}
                 ] + message_list
    )

    return response["choices"][0]["message"]["content"].strip()


def generate_gpt_keyword_response(text):
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
                      "content": "You are an AI that expertise to make keywords based on the topic."}
                 ] + message_list
    )

    return response["choices"][0]["message"]["content"].strip()


# async def send_data_to_crm_websocket(data):
#     async with websockets.connect("wss://example.com/crm-websocket-url") as websocket:
#         await websocket.send(json.dumps(data))


def send_data_to_webhook(payload):
    webhook_url = "https://devis.mutuello.com/api/phoneticket/resume"
    headers = {"Content-Type": "application/json"}

    response = requests.post(webhook_url, json=payload, headers=headers)

    if response.status_code != 200:
        print(f"Error sending data to webhook: {response.status_code}, {response.text}")
    else:
        print("Data sent successfully to webhook")


def send_response(id_conv, recording_url, voicemessage_transcription, voicemessage_resume, voicemessage_tags,
                  to_phone_number):
    """
    Send the response back to the user using Twilio and to the CRM webhook
    :param id_conv: The conversation ID
    :param recording_url: The recording URL
    :param voicemessage_transcription: The text to voice transcription
    :param voicemessage_resume: The voice message resume
    :param voicemessage_tags: The voice message tags
    :param to_phone_number: The phone number to send the response to
    :return: None
    """
    print(voicemessage_resume)

    # Send the response to the CRM using a webhook
    payload = {
        "id_conv": id_conv,
        "recording_url": recording_url,
        "voicemessage_transcription": voicemessage_transcription,
        "voicemessage_resume": voicemessage_resume,
        "voicemessage_tags": voicemessage_tags,
    }

    send_data_to_webhook(payload)


@app.route("/webhook", methods=["POST"])
def webhook():
    print(request.form)  # Add this line to debug the request parameters

    recording_url = request.form.get("RecordingUrl")
    recording_sid = request.form.get("RecordingSid")
    from_phone_number = "+8801784056345"  # Change this line to get the "From" parameter

    if recording_url and from_phone_number:
        print("Received voice message from Twilio")
        print("Recording URL: ", recording_url)
        task = process_voice_message.apply_async(args=[recording_url, from_phone_number, recording_sid])
        response = task.get()
        print("Response: ", response)

        return Response(status=200)
    else:
        return Response(status=400)


if __name__ == "__main__":
    app.run()
