"""
VideoNotes Celery Tasks for Video Processing
"""
import os
import uuid
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

import whisper
from celery import shared_task
from sqlalchemy import update

from .celery_app import celery_app
from .config import settings


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def transcribe_video(self, video_id: str, file_path: str, language: str = "en"):
    """
    Transcribe video/audio file using OpenAI Whisper.
    
    Args:
        video_id: UUID of the video record
        file_path: Path to the uploaded file (MinIO path or local)
        language: Language code ('en' or 'ru')
    """
    from .database import SessionLocal, Video, Transcription
    
    db = SessionLocal()
    audio_path = None
    
    try:
        # Update status to processing
        db.execute(
            update(Video).where(Video.id == video_id).values(status="processing")
        )
        db.commit()
        
        # Create temp directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            local_file = os.path.join(temp_dir, "input_file")
            
            # Download file from MinIO if needed
            if file_path.startswith("minio://"):
                from minio import Minio
                minio_client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_SECURE
                )
                bucket, object_name = file_path.replace("minio://", "").split("/", 1)
                minio_client.fget_object(bucket, object_name, local_file)
            else:
                local_file = file_path
            
            # Extract audio if video file
            audio_path = os.path.join(temp_dir, "audio.wav")
            file_ext = Path(local_file).suffix.lower()
            
            if file_ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
                # Extract audio using FFmpeg
                result = subprocess.run([
                    'ffmpeg', '-i', local_file,
                    '-vn', '-acodec', 'pcm_s16le',
                    '-ar', '16000', '-ac', '1',
                    '-y', audio_path
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    raise Exception(f"FFmpeg error: {result.stderr}")
            else:
                # Audio file - convert to wav if needed
                if file_ext in ['.wav']:
                    audio_path = local_file
                else:
                    subprocess.run([
                        'ffmpeg', '-i', local_file,
                        '-acodec', 'pcm_s16le',
                        '-ar', '16000', '-ac', '1',
                        '-y', audio_path
                    ], check=True)
            
            # Load Whisper model
            model = whisper.load_model(settings.WHISPER_MODEL)
            
            # Transcribe
            self.update_state(state='TRANSCRIBING', meta={'progress': 50})
            
            result = model.transcribe(
                audio_path,
                language=language if language != "auto" else None,
                task="transcribe",
                verbose=False
            )
            
            # Get transcription text and segments
            transcription_text = result["text"].strip()
            segments = result.get("segments", [])
            detected_language = result.get("language", language)
            
            # Calculate duration from segments
            duration_seconds = 0
            if segments:
                duration_seconds = int(segments[-1].get("end", 0))
            
            # Format segments with timestamps
            formatted_segments = []
            for seg in segments:
                formatted_segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip()
                })
            
            # Create transcription record
            transcription = Transcription(
                id=uuid.uuid4(),
                video_id=video_id,
                language=detected_language,
                text=transcription_text,
                segments=formatted_segments,
                status="completed",
                processing_time_seconds=0,  # TODO: Calculate actual time
                created_at=datetime.utcnow()
            )
            
            db.add(transcription)
            
            # Update video status
            db.execute(
                update(Video).where(Video.id == video_id).values(
                    status="completed",
                    duration_seconds=duration_seconds
                )
            )
            
            db.commit()
            
            return {
                "status": "success",
                "video_id": str(video_id),
                "transcription_id": str(transcription.id),
                "text_length": len(transcription_text),
                "duration_seconds": duration_seconds
            }
            
    except Exception as e:
        # Update status to error
        db.execute(
            update(Video).where(Video.id == video_id).values(
                status="error",
                error_message=str(e)
            )
        )
        db.commit()
        
        # Retry on failure
        raise self.retry(exc=e)
        
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def generate_summary(self, transcription_id: str, text: str, language: str = "en"):
    """
    Generate AI summary from transcription text.
    This is a placeholder - in production, you'd use OpenAI GPT or similar.
    
    Args:
        transcription_id: UUID of the transcription
        text: Full transcription text
        language: Language for summary
    """
    from .database import SessionLocal, Transcription
    
    db = SessionLocal()
    
    try:
        # Simple extractive summary (placeholder)
        # In production, use OpenAI GPT-4 or similar
        sentences = text.replace('!', '.').replace('?', '.').split('.')
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # Take first 5 sentences as summary
        summary = '. '.join(sentences[:5]) + '.' if sentences else text[:500]
        
        # Extract key points (simple extraction)
        key_points = sentences[:10] if len(sentences) > 10 else sentences
        
        # Update transcription
        db.execute(
            update(Transcription).where(Transcription.id == transcription_id).values(
                summary=summary,
                key_points=key_points
            )
        )
        db.commit()
        
        return {
            "status": "success",
            "transcription_id": transcription_id,
            "summary_length": len(summary)
        }
        
    except Exception as e:
        raise self.retry(exc=e)
        
    finally:
        db.close()


@celery_app.task
def cleanup_temp_files():
    """
    Clean up temporary files older than 24 hours.
    """
    import shutil
    from datetime import timedelta
    
    temp_dir = Path("/tmp/videonotes")
    if not temp_dir.exists():
        return {"status": "no temp directory"}
    
    cutoff = datetime.utcnow() - timedelta(hours=24)
    cleaned = 0
    
    for item in temp_dir.iterdir():
        try:
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            if mtime < cutoff:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                cleaned += 1
        except Exception as e:
            print(f"Error cleaning {item}: {e}")
    
    return {"status": "success", "cleaned_files": cleaned}


@celery_app.task
def send_transcription_email(user_email: str, video_title: str, transcription_id: str):
    """
    Send email notification when transcription is complete.
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        return {"status": "email not configured"}
    
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_FROM
        msg['To'] = user_email
        msg['Subject'] = f'Your transcription is ready: {video_title}'
        
        body = f"""
Hello!

Your video "{video_title}" has been transcribed successfully.

View your transcription:
{settings.FRONTEND_URL}/transcriptions/{transcription_id}

Best regards,
VideoNotes Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        return {"status": "sent", "email": user_email}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
