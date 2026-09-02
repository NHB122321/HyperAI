from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

client = OpenAI()


def transcribe_audio(file_path):

    with open(file_path, "rb") as audio_file:

        transcription = (
            client.audio.transcriptions.create(
                model="gpt-transcribe",
                file=audio_file
            )
        )

    return transcription.text