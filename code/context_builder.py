import pandas as pd
from utils import clean_val, is_in_quiet_hours
from media_processor import resolve_media_info

class ContextBuilder:
    def __init__(self, dataset_dir):
        self.dataset_dir = dataset_dir
        self.users_df = self._load_csv("users.csv")
        self.groups_df = self._load_csv("groups.csv")
        self.group_members_df = self._load_csv("group_members.csv")
        self.business_accounts_df = self._load_csv("business_accounts.csv")
        self.user_business_history_df = self._load_csv("user_business_history.csv")
        self.message_history_df = self._load_csv("message_history.csv")
        self.message_events_df = self._load_csv("message_events.csv")
        self.images_df = self._load_csv("images.csv")
        self.voice_notes_df = self._load_csv("voice_notes.csv")

    def _load_csv(self, filename):
        import os
        path = os.path.join(self.dataset_dir, filename)
        if os.path.exists(path):
            try:
                return pd.read_csv(path)
            except Exception:
                return pd.DataFrame()
        return pd.DataFrame()

    def build_context(self, msg):
        """
        Build rich context dict for an incoming message row.
        """
        user_id = clean_val(msg.get("user_id"))
        created_at = clean_val(msg.get("created_at"))
        conv_type = clean_val(msg.get("conversation_type"))
        group_id = clean_val(msg.get("group_id"))
        business_id = clean_val(msg.get("business_id"))
        sender_user_id = clean_val(msg.get("sender_user_id"))
        media_type = clean_val(msg.get("media_type"))
        media_id = clean_val(msg.get("media_id"))

        context = {
            "message_id": clean_val(msg.get("message_id")),
            "user_id": user_id,
            "created_at": created_at,
            "conversation_type": conv_type,
            "message_text": clean_val(msg.get("message_text")),
            "forwarded_count": msg.get("forwarded_count", 0),
            "user": {},
            "group": {},
            "business": {},
            "sender": {},
            "media": None,
            "in_quiet_hours": False
        }

        # 1. User Context & Quiet Hours
        if not self.users_df.empty and "user_id" in self.users_df.columns and user_id:
            u_match = self.users_df[self.users_df["user_id"] == user_id]
            if not u_match.empty:
                u_row = u_match.iloc[0].to_dict()
                dnd_win = u_row.get("do_not_disturb_window")
                context["user"] = {
                    "do_not_disturb_window": clean_val(dnd_win),
                    "messages_opened_30d": u_row.get("messages_opened_30d", 0),
                    "messages_replied_30d": u_row.get("messages_replied_30d", 0),
                    "notifications_dismissed_30d": u_row.get("notifications_dismissed_30d", 0),
                    "messages_reported_30d": u_row.get("messages_reported_30d", 0)
                }
                context["in_quiet_hours"] = is_in_quiet_hours(created_at, dnd_win)

        # 2. Group Context
        if conv_type == "group" and group_id:
            if not self.groups_df.empty and "group_id" in self.groups_df.columns:
                g_match = self.groups_df[self.groups_df["group_id"] == group_id]
                if not g_match.empty:
                    g_row = g_match.iloc[0].to_dict()
                    context["group"] = {
                        "group_id": group_id,
                        "group_name": clean_val(g_row.get("group_name")),
                        "group_type": clean_val(g_row.get("group_type")),
                        "member_count": g_row.get("member_count", 0),
                        "admin_count": g_row.get("admin_count", 0)
                    }
            
            # Check user membership in group
            if not self.group_members_df.empty and "group_id" in self.group_members_df.columns and "user_id" in self.group_members_df.columns:
                gm_match = self.group_members_df[(self.group_members_df["group_id"] == group_id) & (self.group_members_df["user_id"] == user_id)]
                if not gm_match.empty:
                    gm_row = gm_match.iloc[0].to_dict()
                    context["group"]["user_role"] = clean_val(gm_row.get("role"))
                    context["group"]["is_muted_by_user"] = bool(gm_row.get("group_muted_by_user", 0))

            # Check sender role in group
            if sender_user_id and not self.group_members_df.empty:
                sm_match = self.group_members_df[(self.group_members_df["group_id"] == group_id) & (self.group_members_df["user_id"] == sender_user_id)]
                if not sm_match.empty:
                    sm_row = sm_match.iloc[0].to_dict()
                    context["sender"]["group_role"] = clean_val(sm_row.get("role"))

        # 3. Business Context
        if conv_type == "business" and business_id:
            if not self.business_accounts_df.empty and "business_id" in self.business_accounts_df.columns:
                b_match = self.business_accounts_df[self.business_accounts_df["business_id"] == business_id]
                if not b_match.empty:
                    b_row = b_match.iloc[0].to_dict()
                    context["business"] = {
                        "business_id": business_id,
                        "display_name": clean_val(b_row.get("display_name")),
                        "brand_name": clean_val(b_row.get("brand_name")),
                        "category": clean_val(b_row.get("category")),
                        "verified": int(b_row.get("verified", 0)),
                        "official_domain": clean_val(b_row.get("official_domain")),
                        "domain_used_by_sender": clean_val(b_row.get("domain_used_by_sender")),
                        "user_reports_30d": b_row.get("user_reports_30d", 0)
                    }

            # Check User Business History
            if not self.user_business_history_df.empty and "user_id" in self.user_business_history_df.columns and "business_id" in self.user_business_history_df.columns:
                ubh_match = self.user_business_history_df[(self.user_business_history_df["user_id"] == user_id) & (self.user_business_history_df["business_id"] == business_id)]
                if not ubh_match.empty:
                    ubh_row = ubh_match.iloc[0].to_dict()
                    context["business"]["why_user_knows_account"] = clean_val(ubh_row.get("why_user_knows_account"))
                    context["business"]["allows_promotions"] = int(ubh_row.get("allows_promotions", 1))
                    context["business"]["promotions_opted_out_at"] = clean_val(ubh_row.get("promotions_opted_out_at"))
                    context["business"]["messages_replied_30d"] = ubh_row.get("messages_replied_30d", 0)

        # 4. Media Processing
        if media_id:
            media_info = resolve_media_info(media_id, media_type, self.images_df, self.voice_notes_df, self.dataset_dir)
            context["media"] = media_info

        return context
