# utils.py
import os
import cv2
import speech_recognition as sr
from deep_translator import GoogleTranslator
from pydub import AudioSegment

def extract_audio(video_path, audio_output_path):
    """
    Extract audio from video file and save it as a .wav file.
    This uses OpenCV and pydub.
    """
    try:
        # Using pydub to convert video to audio
        print(f"Extracting audio from video: {video_path}...")
        audio = AudioSegment.from_file(video_path, format="mp4")  # You can change this to your video format
        audio.export(audio_output_path, format="wav")  # Saving as .wav file
        print(f"Audio extracted and saved as: {audio_output_path}")
        return audio_output_path
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return None

def transcribe_audio(audio_path):
    """
    Transcribe the audio using Google's Speech Recognition API.
    """
    recognizer = sr.Recognizer()
    transcription = None

    try:
        # Open the audio file
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)

        # Recognizing speech using Google's API
        transcription = recognizer.recognize_google(audio)
        print(f"Transcription successful: {transcription}")
    except sr.UnknownValueError:
        print("Audio not recognized.")
    except sr.RequestError:
        print("Could not request results from Google Web Speech API.")
    
    return transcription

def translate_text(text, target_language="es"):
    """
    Translate the text into the specified target language using Google Translate API.
    Default is Spanish (es).
    """
    try:
        translation = GoogleTranslator(source='auto', target=target_language).translate(text)
        print(f"Translation successful: {translation}")
        return translation
    except Exception as e:
        print(f"Error translating text: {e}")
        return None
