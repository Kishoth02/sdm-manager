import json5
import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "sdm-intent"

SYSTEM_PROMPT = (
    "You are an SDM intent detection model. Analyze the user message and return only a JSON response "
    "with intent, target, group, question, linked_operations, validation, confidence, fallback, "
    "next_action, and message fields."
)

def _resolve_option_intent(result, group_str, is_replace=False):
    return {
        "type": "add",
        "target": "option",
        "questionNum": result.get("questionNum"),
        "newValue": result.get("newValue") or result.get("newOptionText", ""),
        "optionKey": (result.get("optionKey") or "").upper(),
        "is_replace": is_replace,
        "group": {"name": group_str} if group_str else None,
    }

def _parse_raw(raw: str) -> dict:
    """Clean and parse raw model output into a dict."""
    cleaned = raw.strip().rstrip('.').strip()
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    try:
        return json5.loads(cleaned)
    except Exception:
        return json.loads(cleaned)

def get_intent(message: str) -> dict:
    msg_lower = message.lower().strip()

    # ── Keyword overrides BEFORE model call ───────────────────────────────
    SHOW_KEYWORDS = ("show all", "show questions", "list all", "list questions",
                     "how many", "all questions", "display questions", "show topics",
                     "list topics", "all topics", "show files", "list files",
                     "list out", "show all questions")
    if any(kw in msg_lower for kw in SHOW_KEYWORDS):
        if "topic" in msg_lower:
            return {"type": "topics", "target": "topics", "group": None}
        if "file" in msg_lower:
            return {"type": "show", "target": "files", "group": None}
        if "how many" in msg_lower:
            return {"type": "show", "target": "stats", "group": None}
        return {"type": "show", "target": "questions", "group": None}

    if "convert" in msg_lower:
        return {"type": "convert", "target": "file"}
    # ─────────────────────────────────────────────────────────────────────

    # ── TEMPORARY: Ollama disabled for Azure deployment ───────────────────
    # When ready, remove this block and uncomment the Ollama section below
    return {
        "type": "unknown",
        "message": "AI model not connected yet. Coming soon!"
    }
    # ─────────────────────────────────────────────────────────────────────

    # ── OLLAMA CALL (disabled for now) ────────────────────────────────────
    # payload = {
    #     "model": MODEL_NAME,
    #     "stream": False,
    #     "messages": [
    #         {"role": "system", "content": SYSTEM_PROMPT},
    #         {"role": "user", "content": message},
    #     ],
    # }
    # response = requests.post(OLLAMA_URL, json=payload)
    # response.raise_for_status()
    # raw = response.json()["message"]["content"].strip()
    # print(f"DEBUG RAW OUTPUT: {raw}")
    # try:
    #     result = _parse_raw(raw)
    # except Exception:
    #     return {"type": "unknown", "raw": raw}
    # print(f"DEBUG PARSED: {result}")
    # ─────────────────────────────────────────────────────────────────────

    intent = result.get("intent", "").lower().replace("-", "_")
    group_info = result.get("group") or {}
    group_str = group_info.get("name", "") if isinstance(group_info, dict) else str(group_info)
    question_info = result.get("question") or {}
    question_oid = (
        question_info.get("num") if isinstance(question_info, dict)
        else result.get("questionNum") or result.get("question_id")
    )

    # ── ADD OPTION ────────────────────────────────────────────────────────
    if intent == "add_option":
        return {
            "type": "add",
            "target": "option",
            "questionNum": question_oid or result.get("questionNum"),
            "newValue": result.get("newValue") or result.get("newOptionText", ""),
            "optionKey": (result.get("optionKey") or "").upper(),
            "is_replace": False,
            "group": {"name": group_str} if group_str else None,
        }

    # ── EDIT OPTION ───────────────────────────────────────────────────────
    if intent == "edit_option":
        return _resolve_option_intent(result, group_str, is_replace=True)

    # ── EDIT QUESTION ─────────────────────────────────────────────────────
    if intent == "edit_question":
        opt_key = (result.get("optionKey") or "").upper()
        new_val = result.get("newValue") or result.get("newOptionText", "")

        if opt_key and new_val:
            return _resolve_option_intent(result, group_str, is_replace=True)

        qnum = result.get("questionNum") or question_oid
        text_val = result.get("text") or result.get("questionText")

        if text_val and qnum:
            return {
                "type": "edit",
                "target": "question",
                "questionNum": qnum,
                "newValue": text_val,
                "group": {"name": group_str} if group_str else None,
            }

        return {
            "type": "edit",
            "target": "question",
            "questionNum": qnum,
            "group": {"name": group_str} if group_str else None,
        }

    # ── ADD ───────────────────────────────────────────────────────────────
    if intent == "add":
        target = result.get("target", "question")

        if target == "option":
            return _resolve_option_intent(result, group_str, is_replace=False)

        return {
            "type": "add",
            "target": "question",
            "questionText": result.get("questionText") or result.get("question") or "",
            "topic": group_str,
            "group": {"name": group_str} if group_str else None,
            "afterQuestion": result.get("afterQuestion"),
        }

    # ── ADD QUESTION ──────────────────────────────────────────────────────
    if intent == "add_question":
        return {
            "type": "add",
            "target": "question",
            "questionText": result.get("questionText") or "",
            "questionNum": result.get("questionNum"),
            "position": result.get("position"),
            "topic": group_str,
            "group": {"name": group_str} if group_str else None,
        }

    # ── EDIT ──────────────────────────────────────────────────────────────
    if intent == "edit":
        target = result.get("target", "question")
        opt_key = (result.get("optionKey") or "").upper()
        new_val = result.get("newValue") or result.get("newOptionText", "")

        if target == "option" and opt_key and new_val:
            return _resolve_option_intent(result, group_str, is_replace=True)

        qnum = result.get("questionNum") or question_oid
        return {
            "type": "edit",
            "target": target,
            "questionNum": qnum,
            "group": {"name": group_str} if group_str else None,
        }

    # ── DELETE OPTION ─────────────────────────────────────────────────────
    if intent == "delete_option":
        return {
            "type": "delete",
            "target": "option",
            "questionNum": question_oid or result.get("questionNum"),
            "optionKey": (result.get("optionKey") or "").upper(),
            "group": {"name": group_str} if group_str else None,
        }

    # ── DELETE QUESTION ───────────────────────────────────────────────────
    if intent in ("delete_question", "delete"):
        target = result.get("target", "question")

        if target == "option":
            return {
                "type": "delete",
                "target": "option",
                "questionNum": question_oid or result.get("questionNum"),
                "optionKey": (result.get("optionKey") or "").upper(),
                "group": {"name": group_str} if group_str else None,
            }

        return {
            "type": "delete",
            "target": "question",
            "questionNum": result.get("questionNum") or question_oid,
            "group": {"name": group_str} if group_str else None,
        }

    # ── DELETE GROUP ──────────────────────────────────────────────────────
    if intent == "delete_group":
        return {
            "type": "delete",
            "target": "group",
            "group": {"name": group_str} if group_str else None,
        }

    # ── EDIT GROUP ────────────────────────────────────────────────────────
    if intent == "edit_group":
        return {
            "type": "edit",
            "target": "group",
            "group": {"name": group_str} if group_str else None,
            "newName": result.get("newName"),
        }

    # ── CONVERT ───────────────────────────────────────────────────────────
    if "convert" in msg_lower:
        return {"type": "convert", "target": "file"}

    # ── SHOW / LIST ───────────────────────────────────────────────────────
    if intent in ("show", "list", "show_questions", "list_questions"):
        return {
            "type": "show",
            "target": result.get("target", "questions"),
            "group": {"name": group_str} if group_str else None,
        }

    if intent == "show_groups":
        return {
            "type": "show",
            "target": "groups",
            "group": None,
        }

    # ── TOPICS ───────────────────────────────────────────────────────────
    if intent == "topics":
        return {"type": "topics", "target": "topics", "group": None}

    # ── FALLBACK ──────────────────────────────────────────────────────────
    return {
        "type": "unknown",
        "raw_intent": intent,
        "result": result,
    }

# Alias for backward compatibility
detect_intent = get_intent