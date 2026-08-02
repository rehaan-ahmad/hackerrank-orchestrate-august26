import os
from utils import clean_val

MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp3": "audio/mp3",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".opus": "audio/opus",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
}

def resolve_media_info(media_id, media_type, images_df, voice_df, dataset_dir):
    """
    Look up media_id in images_df or voice_df, resolve full local path and MIME type.
    """
    media_id = clean_val(media_id)
    media_type = clean_val(media_type)
    
    if not media_id:
        return None
    
    relative_path = None
    
    # Try image lookup
    if media_type == "image" or not media_type:
        if images_df is not None and not images_df.empty and "image_id" in images_df.columns:
            match = images_df[images_df["image_id"] == media_id]
            if not match.empty:
                relative_path = match.iloc[0]["file_path"]
                media_type = "image"
    
    # Try voice lookup if not found
    if not relative_path and (media_type == "voice" or not media_type):
        if voice_df is not None and not voice_df.empty and "voice_note_id" in voice_df.columns:
            match = voice_df[voice_df["voice_note_id"] == media_id]
            if not match.empty:
                relative_path = match.iloc[0]["file_path"]
                media_type = "voice"
    
    if not relative_path:
        return None
    
    relative_path = str(relative_path).strip()
    
    # Resolve full path safely without double-prefixing
    if relative_path.startswith(dataset_dir):
        full_path = relative_path
    elif relative_path.startswith("dataset/"):
        full_path = os.path.join(os.path.dirname(dataset_dir), relative_path)
    else:
        full_path = os.path.join(dataset_dir, relative_path)
    
    if not os.path.exists(full_path):
        return None
    
    ext = os.path.splitext(full_path)[1].lower()
    mime_type = MIME_MAP.get(ext)
    
    if not mime_type:
        mime_type = "image/jpeg" if media_type == "image" else "audio/mp3"
        
    return {
        "media_id": media_id,
        "media_type": media_type,
        "full_path": full_path,
        "mime_type": mime_type,
        "file_size": os.path.getsize(full_path)
    }
