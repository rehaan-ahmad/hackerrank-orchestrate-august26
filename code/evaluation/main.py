import os
import sys
import pandas as pd
from dotenv import load_dotenv

code_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

from utils import clean_val
from context_builder import ContextBuilder
from scam_detector import check_scam
from evidence_retriever import find_evidence_message_ids
from router import MessageRouter

def evaluate():
    load_dotenv()
    dataset_dir = "dataset"
    if not os.path.exists(dataset_dir):
        dataset_dir = os.path.join(code_dir, "dataset")

    sample_path = os.path.join(dataset_dir, "sample_messages.csv")
    if not os.path.exists(sample_path):
        print(f"[-] Error: {sample_path} not found.")
        sys.exit(1)

    df_sample = pd.read_csv(sample_path)
    print(f"[+] Evaluating system against {len(df_sample)} benchmark samples from sample_messages.csv...")

    builder = ContextBuilder(dataset_dir)
    api_key = os.environ.get("GOOGLE_API_KEY")
    router = MessageRouter(api_key=api_key) if api_key else None

    action_correct = 0
    type_correct = 0
    total = len(df_sample)
    
    action_matrix = {"notify": {"tp":0, "fp":0, "fn":0}, "digest": {"tp":0, "fp":0, "fn":0}, "mute": {"tp":0, "fp":0, "fn":0}}

    for idx, row in df_sample.iterrows():
        msg_dict = row.to_dict()
        expected_action = clean_val(msg_dict.get("action"))
        expected_type = clean_val(msg_dict.get("message_type"))
        
        context = builder.build_context(msg_dict)
        
        # Scam check
        is_scam, scam_res = check_scam(context.get("message_text"), context.get("business"))
        if is_scam and scam_res:
            pred_action = scam_res["action"]
            pred_type = scam_res["message_type"]
        elif router:
            evidence_ids = find_evidence_message_ids(msg_dict, builder.message_history_df, builder.message_events_df)
            res = router.route_message(context, evidence_ids=evidence_ids)
            pred_action = res["action"]
            pred_type = res["message_type"]
        else:
            pred_action = "digest" if context.get("in_quiet_hours") else "notify"
            pred_type = "personal"

        if pred_action == expected_action:
            action_correct += 1
            if pred_action in action_matrix:
                action_matrix[pred_action]["tp"] += 1
        else:
            if pred_action in action_matrix:
                action_matrix[pred_action]["fp"] += 1
            if expected_action in action_matrix:
                action_matrix[expected_action]["fn"] += 1

        if pred_type == expected_type:
            type_correct += 1

    accuracy = (action_correct / total) * 100
    type_acc = (type_correct / total) * 100

    print("\n" + "="*50)
    print("      EVALUATION METRICS BENCHMARK SUMMARY")
    print("="*50)
    print(f"Action Accuracy      : {accuracy:.2f}% ({action_correct}/{total})")
    print(f"Message Type Accuracy: {type_acc:.2f}% ({type_correct}/{total})")
    
    f1_scores = []
    print("\nPer-Class Metrics:")
    for act, counts in action_matrix.items():
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        f1_scores.append(f1)
        print(f"  - {act.upper():<7}: Precision={prec:.2f}, Recall={rec:.2f}, F1={f1:.2f}")

    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0
    print(f"\nMacro F1 Score: {macro_f1:.4f}")
    print("="*50)

if __name__ == "__main__":
    evaluate()
