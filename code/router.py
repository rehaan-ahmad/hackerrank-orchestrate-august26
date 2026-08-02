import os
import re
import json
import time
from PIL import Image
import google.generativeai as genai
from prompts import SYSTEM_PROMPT, build_user_prompt
from utils import clean_val

class MessageRouter:
    def __init__(self, api_key=None, model_name="gemini-2.0-flash"):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not set in environment or passed to MessageRouter.")
            
        genai.configure(api_key=self.api_key)
        self.model_name = model_name
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=512,
            )
        )

    def route_message(self, context, evidence_ids="none", max_retries=3):
        """
        Route an incoming message context to (action, message_type, reason, confidence, evidence_ids).
        """
        prompt_text = build_user_prompt(context, evidence_ids)
        contents = []

        media_ctx = context.get("media")
        if media_ctx and media_ctx.get("full_path") and os.path.exists(media_ctx["full_path"]):
            full_path = media_ctx["full_path"]
            mime_type = media_ctx.get("mime_type", "")
            
            try:
                if media_ctx.get("media_type") == "image" or mime_type.startswith("image/"):
                    img = Image.open(full_path)
                    contents.append(img)
                elif media_ctx.get("media_type") == "voice" or mime_type.startswith("audio/"):
                    audio_data = open(full_path, "rb").read()
                    audio_part = genai.protos.Part(
                        inline_data=genai.protos.Blob(
                            mime_type=mime_type,
                            data=audio_data
                        )
                    )
                    contents.append(audio_part)
            except Exception:
                pass

        contents.append(prompt_text)

        response_text = None
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(contents)
                if response and hasattr(response, "text") and response.text:
                    response_text = response.text
                    break
                elif hasattr(response, "prompt_feedback") and response.prompt_feedback:
                    return self._fallback_blocked_response(context, evidence_ids)
            except Exception as err:
                err_str = str(err)
                if "429" in err_str or "ResourceExhausted" in err_str or "quota" in err_str.lower():
                    sleep_time = (2 ** attempt) * 3
                    time.sleep(sleep_time)
                else:
                    time.sleep(2)

        if not response_text:
            return self._fallback_rule_response(context, evidence_ids)

        return self._parse_response(response_text, context, evidence_ids)

    def _parse_response(self, text, context, evidence_ids):
        """Parse JSON output from Gemini response string."""
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
            else:
                data = json.loads(text)
                
            action = clean_val(data.get("action")) or "digest"
            message_type = clean_val(data.get("message_type")) or "unknown"
            reason = clean_val(data.get("reason")) or "Message processed based on content and user preferences."
            confidence = float(data.get("confidence", 0.84))
            
            if action not in ("notify", "digest", "mute"):
                action = "digest"
                
            if len(reason) > 280:
                reason = reason[:277] + "..."
                
            calibrated_conf = self.calibrate_confidence(confidence, context)
                
            return {
                "action": action,
                "message_type": message_type,
                "reason": reason,
                "confidence": round(calibrated_conf, 2),
                "evidence_message_ids": evidence_ids
            }
        except Exception:
            return self._fallback_rule_response(context, evidence_ids)

    def calibrate_confidence(self, confidence: float, context: dict) -> float:
        """Calibrate confidence based on richness of available context."""
        user_ctx = context.get("user", {})
        group_ctx = context.get("group", {})
        biz_ctx = context.get("business", {})
        
        # If very minimal context available, slightly temper confidence
        if not user_ctx and not group_ctx and not biz_ctx:
            confidence = min(confidence, 0.72)
        return max(0.60, min(0.95, confidence))

    def _fallback_blocked_response(self, context, evidence_ids):
        return {
            "action": "mute",
            "message_type": "scam",
            "reason": "Message suppressed due to potential safety policy or security violation.",
            "confidence": 0.90,
            "evidence_message_ids": evidence_ids
        }

    def _fallback_rule_response(self, context, evidence_ids):
        conv_type = context.get("conversation_type")
        in_quiet = context.get("in_quiet_hours", False)
        
        if in_quiet:
            action = "digest"
        elif conv_type == "business":
            action = "mute" if context.get("business", {}).get("allows_promotions") == 0 else "digest"
        elif conv_type == "group":
            action = "mute" if context.get("group", {}).get("is_muted_by_user") else "digest"
        else:
            action = "notify"
            
        return {
            "action": action,
            "message_type": "unknown",
            "reason": "Default routing applied based on conversation type and user preferences.",
            "confidence": 0.78,
            "evidence_message_ids": evidence_ids
        }
