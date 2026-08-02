import datetime
import re
import pandas as pd

def clean_val(val):
    """Clean NaN or float/null values safely."""
    if pd.isna(val) or val is None:
        return None
    val_str = str(val).strip()
    if val_str.lower() in ("nan", "none", "null", ""):
        return None
    return val_str

def is_in_quiet_hours(created_at: str, window_str: str) -> bool:
    """
    Check if created_at timestamp falls within user's do_not_disturb_window.
    window_str format: "22:00-07:00" or "00:00-06:00"
    """
    cleaned_window = clean_val(window_str)
    cleaned_time = clean_val(created_at)
    if not cleaned_window or not cleaned_time:
        return False
    
    try:
        if " " in cleaned_time:
            time_part = cleaned_time.split(" ")[1]
        else:
            time_part = cleaned_time
        
        hour, minute = map(int, time_part.split(":")[:2])
        msg_minutes = hour * 60 + minute
        
        start_str, end_str = cleaned_window.split("-")
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))
        
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        
        if start_minutes <= end_minutes:
            return start_minutes <= msg_minutes <= end_minutes
        else:
            return msg_minutes >= start_minutes or msg_minutes <= end_minutes
    except Exception:
        return False

def has_direct_mention(text: str, user_name: str = None) -> bool:
    """Check if message text contains `@` mention or user's name."""
    text_clean = clean_val(text)
    if not text_clean:
        return False
    
    if "@" in text_clean:
        return True
        
    if user_name:
        clean_name = clean_val(user_name)
        if clean_name and len(clean_name) > 2:
            pattern = r'\b' + re.escape(clean_name.lower()) + r'\b'
            if re.search(pattern, text_clean.lower()):
                return True
    return False

def is_high_forward_risk(forwarded_count) -> bool:
    """Check if message has a high forward count (> 5)."""
    try:
        fwd = int(forwarded_count or 0)
        return fwd > 5
    except Exception:
        return False
