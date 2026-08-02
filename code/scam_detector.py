import re
from utils import clean_val

SCAM_TEXT_PATTERNS = [
    (r'\b(won|winner|congratulations).{0,30}(lottery|prize|reward|cash|crore|lakh)\b', 'Lottery/prize scam pattern detected.'),
    (r'\b(send|share|tell|enter)\s+(your\s+)?(otp|pin|password|cvv|bank details)\b', 'Request for sensitive credential/OTP.'),
    (r'\b(account|card|wallet|bank)\s+(blocked|suspended|deactivated|locked)\b', 'Fake urgency regarding account block/suspension.'),
    (r'\b(pay\s+small|reattempt\s+fee|release\s+package|delivery\s+failed)\b', 'Package delivery fee scam.'),
    (r'\b(free\s+iphone|free\s+gift|free\s+laptop|claim\s+your\s+cash)\b', 'Promotional scam reward claim.'),
    (r'\b(kbc|kaun\ banega\ crorepati)\b', 'KBC lottery scam.'),
]

def check_scam(message_text, biz_info=None):
    """
    Check if a message is a high-confidence scam or phishing attempt.
    Returns: (is_scam, dict_result) or (False, None)
    """
    text = clean_val(message_text) or ""
    text_lower = text.lower()
    
    # 1. Check Business domain mismatch (phishing)
    if biz_info:
        official = clean_val(biz_info.get("official_domain"))
        sender_dom = clean_val(biz_info.get("domain_used_by_sender"))
        verified = biz_info.get("verified", 1)
        
        if official and sender_dom and official.lower() != sender_dom.lower():
            # Domain spoofing!
            return True, {
                "action": "mute",
                "message_type": "scam",
                "reason": f"Suspicious domain mismatch: sender domain '{sender_dom}' does not match official domain '{official}'.",
                "confidence": 0.93,
                "evidence_message_ids": "none"
            }
        
        if verified == 0 and biz_info.get("user_reports_30d", 0) > 10:
            return True, {
                "action": "mute",
                "message_type": "scam",
                "reason": "Unverified business sender with high user scam report history.",
                "confidence": 0.90,
                "evidence_message_ids": "none"
            }
            
    # 2. Check Scam Regex Patterns
    for pattern, description in SCAM_TEXT_PATTERNS:
        if re.search(pattern, text_lower):
            return True, {
                "action": "mute",
                "message_type": "scam",
                "reason": description,
                "confidence": 0.91,
                "evidence_message_ids": "none"
            }
            
    return False, None
