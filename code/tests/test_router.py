import unittest
import os
import sys

# Add code directory to path
code_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

from utils import is_in_quiet_hours, has_direct_mention, clean_val
from scam_detector import check_scam

class TestNotificationRouterUtils(unittest.TestCase):

    def test_quiet_hours(self):
        # Overnight window 22:00 to 07:00
        self.assertTrue(is_in_quiet_hours("2026-07-30 23:15", "22:00-07:00"))
        self.assertTrue(is_in_quiet_hours("2026-07-30 04:30", "22:00-07:00"))
        self.assertFalse(is_in_quiet_hours("2026-07-30 14:00", "22:00-07:00"))
        
        # Daytime window 09:00 to 17:00
        self.assertTrue(is_in_quiet_hours("2026-07-30 11:00", "09:00-17:00"))
        self.assertFalse(is_in_quiet_hours("2026-07-30 20:00", "09:00-17:00"))

    def test_direct_mention(self):
        self.assertTrue(has_direct_mention("Hey @Rahul check this out"))
        self.assertTrue(has_direct_mention("Hi Rahul, please review this", user_name="Rahul"))
        self.assertFalse(has_direct_mention("General update for team"))

    def test_clean_val(self):
        self.assertIsNone(clean_val("nan"))
        self.assertIsNone(clean_val("None"))
        self.assertEqual(clean_val("  u_001  "), "u_001")

    def test_scam_detection(self):
        # Phishing domain mismatch
        biz_spoof = {
            "official_domain": "amazon.in",
            "domain_used_by_sender": "amazonpay-delivery.in",
            "verified": 0
        }
        is_scam, res = check_scam("Pay fee to release package", biz_info=biz_spoof)
        self.assertTrue(is_scam)
        self.assertEqual(res["action"], "mute")
        self.assertEqual(res["message_type"], "scam")

        # Lottery text scam
        is_scam, res = check_scam("Congratulations you won KBC 25 lakh lottery! Share OTP to claim.")
        self.assertTrue(is_scam)
        self.assertEqual(res["action"], "mute")

        # Legitimate text
        is_scam, res = check_scam("Meeting at 4pm in room B", biz_info=None)
        self.assertFalse(is_scam)

if __name__ == "__main__":
    unittest.main()
