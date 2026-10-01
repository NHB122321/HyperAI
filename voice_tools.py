from config import TRANSCRIPTION_MODEL
from openai import OpenAI


client = OpenAI()


def transcribe_audio(file_path):

    with open(file_path, "rb") as audio_file:

        transcription = (
            client.audio.transcriptions.create(
                model=TRANSCRIPTION_MODEL,
                file=audio_file
            )
        )

    return transcription.text


