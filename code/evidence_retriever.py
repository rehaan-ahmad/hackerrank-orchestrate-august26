import pandas as pd
from utils import clean_val

def find_evidence_message_ids(msg, message_history_df, message_events_df=None):
    """
    Find relevant historical evidence message IDs for the incoming message.
    Returns: string comma-separated evidence IDs (e.g. "message_0001") or "none"
    """
    if message_history_df is None or message_history_df.empty:
        return "none"
        
    user_id = clean_val(msg.get("user_id"))
    conversation_type = clean_val(msg.get("conversation_type"))
    group_id = clean_val(msg.get("group_id"))
    business_id = clean_val(msg.get("business_id"))
    sender_user_id = clean_val(msg.get("sender_user_id"))
    msg_text = clean_val(msg.get("message_text")) or ""
    
    candidates = message_history_df.copy()
    
    # Filter by user if user_id column exists
    if "user_id" in candidates.columns and user_id:
        user_matches = candidates[candidates["user_id"] == user_id]
        if not user_matches.empty:
            candidates = user_matches
            
    matched_ids = []
    
    # Strategy 1: Group conversation match
    if conversation_type == "group" and group_id and "group_id" in candidates.columns:
        group_history = candidates[candidates["group_id"] == group_id]
        if not group_history.empty:
            # If sender match exists
            if sender_user_id and "sender_user_id" in group_history.columns:
                sender_hist = group_history[group_history["sender_user_id"] == sender_user_id]
                if not sender_hist.empty:
                    matched_ids.append(str(sender_hist.iloc[-1]["message_id"]))
            if not matched_ids:
                matched_ids.append(str(group_history.iloc[-1]["message_id"]))

    # Strategy 2: Business conversation match
    elif conversation_type == "business" and business_id and "business_id" in candidates.columns:
        biz_history = candidates[candidates["business_id"] == business_id]
        if not biz_history.empty:
            matched_ids.append(str(biz_history.iloc[-1]["message_id"]))
            
    # Strategy 3: Personal conversation match
    elif conversation_type == "personal" and sender_user_id and "sender_user_id" in candidates.columns:
        personal_history = candidates[candidates["sender_user_id"] == sender_user_id]
        if not personal_history.empty:
            matched_ids.append(str(personal_history.iloc[-1]["message_id"]))

    # Deduplicate & format
    unique_ids = []
    for mid in matched_ids:
        mid_clean = clean_val(mid)
        if mid_clean and mid_clean not in unique_ids and mid_clean != "none":
            unique_ids.append(mid_clean)
            
    if unique_ids:
        return ",".join(unique_ids[:2])
    return "none"
