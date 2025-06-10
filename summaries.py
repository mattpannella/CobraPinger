import os
import tempfile
import whisper
import gc
import torch
from yt_dlp import YoutubeDL

class WhisperTranscriber:
    def __init__(self, model_size="tiny"):
        # Clear CUDA cache if using GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        self.model = None
        try:
            self.model = whisper.load_model(model_size)
        except Exception as e:
            print(f"Model loading error: {str(e)}")
    
    def __del__(self):
        if hasattr(self, 'model'):
            del self.model
        gc.collect()

    def download_audio(self, video_id, output_dir):
        """Download audio and return path to the audio file."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        output_path = os.path.join(output_dir, "%(title)s.%(ext)s")
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title')
            audio_path = os.path.join(output_dir, f"{title}.mp3")
            return audio_path

    def transcribe_youtube(self, url):
        """Download audio from YouTube and return the transcript as a string."""
        if not self.model:
            return None
            
        audio_path = None
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path = self.download_audio(url, tmpdir)
                if not audio_path or not os.path.exists(audio_path):
                    return None
                
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
                gc.collect()
                
                result = self.model.transcribe(
                    audio_path,
                    device="cpu",
                    fp16=False,
                    beam_size=1,
                    best_of=1,
                    temperature=0,
                    language="en"
                )
                
                return result.get("text", "")
        except Exception as e:
            print(f"Transcription error: {str(e)}")
            return None
