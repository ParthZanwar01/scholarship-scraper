"""
Media-to-Text Processor for Social Media Scraping

Handles:
1. Image OCR - Extract text from scholarship flyers/graphics
2. Video Transcription - Transcribe audio from scholarship videos
3. Continuous processing via Celery

Uses:
- pytesseract for image OCR
- OpenAI Whisper API for video transcription (cloud-friendly)
- yt-dlp for video downloads
"""

import os
import re
import tempfile
import requests
from datetime import datetime
from PIL import Image
from io import BytesIO

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class MediaProcessor:
    """Processes images and videos to extract scholarship information."""
    
    def __init__(self, openai_api_key=None):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.temp_dir = tempfile.mkdtemp(prefix="media_")
        
        print("MediaProcessor initialized")
        print(f"  OCR Available: {TESSERACT_AVAILABLE}")
        print(f"  OpenAI Available: {OPENAI_AVAILABLE and bool(self.openai_api_key)}")
    
    def extract_text_from_image(self, image_url: str) -> str:
        """
        Download and OCR an image to extract text.
        
        Args:
            image_url: URL of the image to process
            
        Returns:
            Extracted text from the image
        """
        if not TESSERACT_AVAILABLE:
            print("Tesseract not available for OCR")
            return ""
        
        try:
            print(f"Downloading image: {image_url[:60]}...")
            
            # Download image
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(image_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"Failed to download image: {response.status_code}")
                return ""
            
            # Open image with PIL
            image = Image.open(BytesIO(response.content))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Run OCR
            print("Running OCR...")
            text = pytesseract.image_to_string(image)
            
            # Clean up text
            text = self._clean_ocr_text(text)
            
            print(f"OCR extracted {len(text)} characters")
            return text
            
        except Exception as e:
            print(f"OCR error: {e}")
            return ""
    
    def _clean_ocr_text(self, text: str) -> str:
        """Clean OCR output text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove non-printable characters
        text = ''.join(c for c in text if c.isprintable() or c in '\n\t')
        
        return text.strip()
    
    def transcribe_video(self, video_url: str) -> str:
        """
        Download and transcribe audio from a video.
        
        Uses OpenAI Whisper API (cloud-friendly, no large model download needed).
        
        Args:
            video_url: URL of the video to transcribe
            
        Returns:
            Transcribed text
        """
        if not OPENAI_AVAILABLE or not self.openai_api_key:
            print("OpenAI not available for transcription")
            return self._fallback_transcription(video_url)
        
        try:
            print(f"Downloading video: {video_url[:60]}...")
            
            # Download video using yt-dlp
            import yt_dlp
            
            audio_path = os.path.join(self.temp_dir, "audio.mp3")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': audio_path.replace('.mp3', '.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # Find the audio file
            if os.path.exists(audio_path):
                audio_file = audio_path
            else:
                # Look for any audio file in temp dir
                for f in os.listdir(self.temp_dir):
                    if f.endswith(('.mp3', '.m4a', '.wav')):
                        audio_file = os.path.join(self.temp_dir, f)
                        break
                else:
                    print("No audio file found after download")
                    return ""
            
            # Transcribe using OpenAI Whisper API
            print("Transcribing with OpenAI Whisper API...")
            
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            with open(audio_file, 'rb') as f:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            
            text = transcription.text
            print(f"Transcribed {len(text)} characters")
            
            # Cleanup
            try:
                os.remove(audio_file)
            except:
                pass
            
            return text
            
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
    
    def _fallback_transcription(self, video_url: str) -> str:
        """Fallback when OpenAI is not available - try local Whisper."""
        try:
            import whisper
            print("Using local Whisper model (fallback)...")
            
            # Download video
            import yt_dlp
            
            video_path = os.path.join(self.temp_dir, "video.mp4")
            
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': video_path,
                'quiet': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            if not os.path.exists(video_path):
                return ""
            
            # Transcribe with local Whisper
            model = whisper.load_model("tiny")
            result = model.transcribe(video_path)
            
            # Cleanup
            os.remove(video_path)
            
            return result.get('text', '')
            
        except ImportError:
            print("Neither OpenAI nor local Whisper available")
            return ""
        except Exception as e:
            print(f"Fallback transcription error: {e}")
            return ""
    
    def extract_scholarship_info(self, text: str, source_url: str = "") -> dict:
        """
        Parse extracted text for scholarship information.
        
        Returns dict with extracted fields.
        """
        if not text or len(text) < 20:
            return None
        
        text_lower = text.lower()
        
        # Check if it's about scholarships
        scholarship_keywords = [
            'scholarship', 'grant', 'financial aid', 'tuition',
            'award', 'funding', 'bursary', 'fellowship'
        ]
        
        if not any(kw in text_lower for kw in scholarship_keywords):
            return None
        
        # Extract amount
        amount = None
        amount_patterns = [
            r'\$[\d,]+(?:\.[\d]{2})?',
            r'\d+(?:,\d{3})+\s*(?:dollars?)?',
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group()
                break
        
        # Extract deadline
        deadline = None
        deadline_patterns = [
            r'(?:deadline|due|by|before)[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}',
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                deadline = match.group(1) if match.lastindex else match.group()
                break
        
        # Extract URLs
        urls = re.findall(r'https?://[^\s]+', text)
        
        # Create title from first meaningful line
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        title = lines[0][:100] if lines else "Scholarship from image/video"
        
        return {
            'title': title,
            'description': text[:500],
            'amount': amount,
            'deadline': deadline,
            'source_url': source_url,
            'urls_found': urls[:5],
        }
    
    def process_media_batch(self, media_items: list) -> list:
        """
        Process a batch of media items (images/videos).
        
        Args:
            media_items: List of dicts with 'url' and 'type' ('image' or 'video')
            
        Returns:
            List of extracted scholarship info dicts
        """
        results = []
        
        for item in media_items:
            url = item.get('url', '')
            media_type = item.get('type', 'image')
            
            if media_type == 'video':
                text = self.transcribe_video(url)
            else:
                text = self.extract_text_from_image(url)
            
            if text:
                info = self.extract_scholarship_info(text, url)
                if info:
                    results.append(info)
        
        return results


if __name__ == "__main__":
    # Test with a sample image
    processor = MediaProcessor()
    
    # Test OCR
    test_url = "https://example.com/test_scholarship_flyer.jpg"
    text = processor.extract_text_from_image(test_url)
    print(f"Extracted: {text[:200]}...")
