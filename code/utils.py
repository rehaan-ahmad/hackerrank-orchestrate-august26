import datetime
import pandas as pd

def clean_val(val):
    """Clean NaN or float/null values safely."""
    if pd.isna(val) or val is None:
        return None
    val_str = str(val).strip()
    if val_str.lower() in ("nan", "none", "null", ""):
        return None
    return val

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
        # Parse timestamp hour and minute
        if " " in cleaned_time:
            time_part = cleaned_time.split(" ")[1]
        else:
            time_part = cleaned_time
        
        hour, minute = map(int, time_part.split(":")[:2])
        msg_minutes = hour * 60 + minute
        
        # Parse window
        start_str, end_str = cleaned_window.split("-")
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))
        
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        
        if start_minutes <= end_minutes:
            # Daytime window e.g. 09:00-17:00
            return start_minutes <= msg_minutes <= end_minutes
        else:
            # Overnight window e.g. 22:00-07:00
            return msg_minutes >= start_minutes or msg_minutes <= end_minutes
    except Exception:
        return False
