import os
import sys
import argparse
import time
import pandas as pd
from dotenv import load_dotenv

# Ensure code directory is in sys.path
code_dir = os.path.dirname(os.path.abspath(__file__))
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

from utils import clean_val
from scam_detector import check_scam
from context_builder import ContextBuilder
from evidence_retriever import find_evidence_message_ids
from router import MessageRouter

def main():
    parser = argparse.ArgumentParser(description="HackerRank Orchestrate Message Notification Router")
    parser.add_argument("--dataset_dir", default="dataset", help="Directory containing dataset CSV files")
    parser.add_argument("--output_file", default="output.csv", help="Path to output predictions CSV")
    parser.add_argument("--sleep_sec", type=float, default=None, help="Delay between API calls in seconds")
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    
    dataset_dir = args.dataset_dir
    if not os.path.exists(dataset_dir):
        # Fallback to code/dataset if dataset doesn't exist at root
        code_dataset = os.path.join(code_dir, "dataset")
        if os.path.exists(code_dataset):
            dataset_dir = code_dataset

    print(f"[+] Using dataset directory: {os.path.abspath(dataset_dir)}")
    messages_path = os.path.join(dataset_dir, "messages.csv")
    if not os.path.exists(messages_path):
        print(f"[-] Error: {messages_path} not found.")
        sys.exit(1)

    messages_df = pd.read_csv(messages_path)
    print(f"[+] Loaded {len(messages_df)} messages to route.")

    # Initialize ContextBuilder
    builder = ContextBuilder(dataset_dir)
    
    # Initialize Router (if API key available)
    api_key = os.environ.get("GOOGLE_API_KEY")
    router = None
    if api_key:
        try:
            router = MessageRouter(api_key=api_key)
            print("[+] Gemini Router initialized successfully.")
        except Exception as e:
            print(f"[!] Warning initializing Gemini Router: {e}. Falling back to rule-based engine.")
    else:
        print("[!] GOOGLE_API_KEY not set. Operating in offline rule-based mode.")

    sleep_sec = args.sleep_sec
    if sleep_sec is None:
        sleep_sec = float(os.environ.get("SLEEP_SEC", "0.2"))

    results = []
    scam_count = 0
    llm_count = 0

    for idx, row in messages_df.iterrows():
        msg_dict = row.to_dict()
        msg_id = clean_val(msg_dict.get("message_id"))

        # Build Context
        context = builder.build_context(msg_dict)
        
        # 1. Fast-Path Scam Check
        is_scam, scam_result = check_scam(context.get("message_text"), context.get("business"))
        if is_scam and scam_result:
            scam_result["message_id"] = msg_id
            results.append(scam_result)
            scam_count += 1
            continue

        # 2. Evidence Retrieval
        evidence_ids = find_evidence_message_ids(msg_dict, builder.message_history_df, builder.message_events_df)
        
        # 3. LLM / Rule Router
        if router:
            result = router.route_message(context, evidence_ids=evidence_ids)
            llm_count += 1
            if sleep_sec > 0:
                time.sleep(sleep_sec)
        else:
            result = builder_rule_fallback(context, evidence_ids)
            
        result["message_id"] = msg_id
        results.append(result)

        if (idx + 1) % 20 == 0 or (idx + 1) == len(messages_df):
            print(f"  Processed {idx + 1}/{len(messages_df)} messages... (Scams: {scam_count}, LLM: {llm_count})")

    # Output DataFrame
    output_df = pd.DataFrame(results)[["message_id", "action", "message_type", "reason", "confidence", "evidence_message_ids"]]
    
    # Save output to dataset/output.csv and root output.csv
    output_df.to_csv(args.output_file, index=False)
    print(f"[+] Successfully wrote {len(output_df)} predictions to {args.output_file}")
    
    if os.path.exists(os.path.join(dataset_dir, "output.csv")):
        output_df.to_csv(os.path.join(dataset_dir, "output.csv"), index=False)
        print(f"[+] Updated {os.path.join(dataset_dir, 'output.csv')}")

    print("\n=== ROUTING ACTION DISTRIBUTION ===")
    print(output_df["action"].value_counts().to_string())

def builder_rule_fallback(context, evidence_ids):
    conv_type = context.get("conversation_type")
    in_quiet = context.get("in_quiet_hours", False)
    
    if in_quiet:
        action = "digest"
        reason = "Message arrived during user quiet hours, batched into digest."
    elif conv_type == "business":
        if context.get("business", {}).get("allows_promotions") == 0:
            action = "mute"
            reason = "Promotional messages from business accounts muted by user preference."
        else:
            action = "digest"
            reason = "Routine business notification queued for digest."
    elif conv_type == "group":
        if context.get("group", {}).get("is_muted_by_user"):
            action = "mute"
            reason = "Message received from a group chat muted by the user."
        else:
            action = "digest"
            reason = "General group discussion batched for digest."
    else:
        action = "notify"
        reason = "Personal direct message routed for immediate user notification."

    return {
        "action": action,
        "message_type": "personal" if conv_type == "personal" else "business_update" if conv_type == "business" else "event",
        "reason": reason,
        "confidence": 0.82,
        "evidence_message_ids": evidence_ids
    }

if __name__ == "__main__":
    main()
