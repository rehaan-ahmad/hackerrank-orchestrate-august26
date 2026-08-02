SYSTEM_PROMPT = """You are an AI-powered Message Notification Router for WhatsApp.
Your task is to analyze an incoming multimodal message along with the user's personal context and decide how to route the message.

Actions:
- "notify": Interrupt the user immediately (for urgent, time-sensitive, safety, critical work, or high-value personalized updates).
- "digest": Batch for later summary (for general group updates, non-urgent news, social events, or routine info).
- "mute": Suppress silently (for low-value promotions, opt-out promotions, spam, scams, or low-engagement/muted group chatter).

Allowed Message Types:
- "urgent", "event", "personal", "business_update", "promotion", "greeting", "forward", "scam", "spam", "unknown"

Key Routing Principles:
1. QUIET HOURS: If the message arrives during the user's Quiet Hours / Do-Not-Disturb window, elevate the threshold for "notify" to only truly critical/urgent items. Otherwise, route non-critical items to "digest" or "mute".
2. GROUP CHATS: If a group is muted by the user, route to "digest" or "mute" unless sent by a group admin containing an urgent/critical update.
3. BUSINESS MESSAGES: If promotions are disabled or opted out by the user, route promotional messages to "mute". Verified critical transactional updates (e.g. order tracking, banking OTP/alerts) should be "notify".
4. SCAMS / SECURITY: Phishing attempts, unverified suspicious senders, domain mismatches, or prize scams MUST be routed to "mute" with message_type "scam".
5. REASONING: Keep the reason clear, concise (1 sentence, under 250 characters), professional, and matching the tone of HackerRank Orchestrate sample outputs.
6. CONFIDENCE: Provide a realistic confidence float between 0.75 and 0.92.

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this schema:
{
  "action": "notify" | "digest" | "mute",
  "message_type": "urgent" | "event" | "personal" | "business_update" | "promotion" | "greeting" | "forward" | "scam" | "spam" | "unknown",
  "reason": "Clear one-sentence explanation.",
  "confidence": 0.85
}
"""

def build_user_prompt(context, evidence_ids="none"):
    """Format rich context into prompt string for Gemini."""
    prompt_lines = [
        "### INCOMING MESSAGE DETAILS",
        f"- Message ID: {context.get('message_id')}",
        f"- Conversation Type: {context.get('conversation_type')}",
        f"- Timestamp: {context.get('created_at')}",
        f"- In Quiet Hours / DND: {'YES' if context.get('in_quiet_hours') else 'NO'}",
        f"- Forwarded Count: {context.get('forwarded_count', 0)}",
    ]
    
    msg_text = context.get("message_text")
    if msg_text:
        prompt_lines.append(f"- Message Text: \"{msg_text}\"")
    else:
        prompt_lines.append("- Message Text: [No text attached]")
        
    # User Profile Context
    user_ctx = context.get("user", {})
    if user_ctx:
        prompt_lines.extend([
            "\n### RECEIVING USER CONTEXT",
            f"- DND Window: {user_ctx.get('do_not_disturb_window', 'None')}",
            f"- Messages Opened (30d): {user_ctx.get('messages_opened_30d', 0)}",
            f"- Messages Replied (30d): {user_ctx.get('messages_replied_30d', 0)}",
            f"- Notifications Dismissed (30d): {user_ctx.get('notifications_dismissed_30d', 0)}"
        ])

    # Group Context
    group_ctx = context.get("group", {})
    if group_ctx:
        prompt_lines.extend([
            "\n### GROUP CONTEXT",
            f"- Group Name: {group_ctx.get('group_name')}",
            f"- Group Type: {group_ctx.get('group_type')}",
            f"- User Role in Group: {group_ctx.get('user_role', 'member')}",
            f"- Group Muted by User: {'YES' if group_ctx.get('is_muted_by_user') else 'NO'}"
        ])
        
    sender_ctx = context.get("sender", {})
    if sender_ctx:
        prompt_lines.append(f"- Sender Role in Group: {sender_ctx.get('group_role', 'member')}")

    # Business Context
    biz_ctx = context.get("business", {})
    if biz_ctx:
        prompt_lines.extend([
            "\n### BUSINESS SENDER CONTEXT",
            f"- Business Name: {biz_ctx.get('display_name') or biz_ctx.get('brand_name')}",
            f"- Category: {biz_ctx.get('category')}",
            f"- Verified Account: {'YES' if biz_ctx.get('verified') == 1 else 'NO'}",
            f"- Official Domain: {biz_ctx.get('official_domain')}",
            f"- Sender Domain: {biz_ctx.get('domain_used_by_sender')}",
            f"- User Allows Promotions: {'YES' if biz_ctx.get('allows_promotions') == 1 else 'NO'}",
            f"- Opted Out Date: {biz_ctx.get('promotions_opted_out_at', 'None')}"
        ])

    # Media Context
    media_ctx = context.get("media")
    if media_ctx:
        media_type = media_ctx.get("media_type")
        if media_type == "image":
            prompt_lines.append("\n### ATTACHMENT: Image file attached inline. Analyze visual content (poster, invoice, promo, personal picture).")
        elif media_type == "voice":
            prompt_lines.append("\n### ATTACHMENT: Audio voice note attached inline. Transcribe the audio, understand the voice content/tone, and use it in your routing decision.")

    prompt_lines.extend([
        f"\n### HISTORICAL EVIDENCE FOUND: {evidence_ids}",
        "\nPlease provide your routing decision in the required JSON format."
    ])
    
    return "\n".join(prompt_lines)
