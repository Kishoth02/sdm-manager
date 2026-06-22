import json5
import json
import re
import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

client = ChatCompletionsClient(
    endpoint=os.environ.get("AZURE_AI_ENDPOINT"),
    credential=AzureKeyCredential(os.environ.get("AZURE_AI_KEY"))
)
MODEL_NAME = "Phi-4-mini-instruct"  # match the deployment name you used in AI Foundry

def _resolve_group_by_index(group_str: str, available_groups: list) -> str:
    if not group_str or not available_groups:
        return group_str
    match = re.match(r'^group\s*(\d+)$', group_str.strip().lower())
    if match:
        idx = int(match.group(1)) - 1
        if 0 <= idx < len(available_groups):
            return available_groups[idx]
    return group_str

SYSTEM_PROMPT = """You are an SDM intent detection model. Analyze the user message and return ONLY a JSON response with these fields: intent, target, group, question, linked_operations, validation, confidence, fallback, next_action, and message.

Intent types you must detect:
- show_questions: user wants to see/list/get questions
- add_question: user wants to add a new question
- edit_question: user wants to edit/update/fix a question
- delete_question: user wants to delete/remove a question
- add_option: user wants to add an option to a question
- edit_option: user wants to edit an option
- delete_option: user wants to delete an option
- edit_group: user wants to edit/rename a group
- delete_group: user wants to delete a group
- show_groups: user wants to see groups
- topics: user wants to see topics
- upload: user wants to upload a file
- convert: user wants to convert a file
- unknown: cannot determine intent

Examples:
Input: "show questions in Group 4"
Output: {"intent": "show_questions", "target": "question", "group": {"name": "Group 4"}, "question": null, "questionNum": null, "linked_operations": [], "validation": {}, "confidence": 0.95, "fallback": false, "next_action": "show_questions", "message": "Here are the questions in Group 4."}

Input: "delete Q7 from Group 3"
Output: {"intent": "delete_question", "target": "question", "group": {"name": "Group 3"}, "question": "Q7", "questionNum": 7, "linked_operations": [], "validation": {}, "confidence": 0.95, "fallback": false, "next_action": "delete_question", "message": "Deleting Q7 from Group 3."}

Input: "add option B as Steel to Q5 in Group 2"
Output: {"intent": "add_option", "target": "option", "group": {"name": "Group 2"}, "question": {"num": 5}, "questionNum": 5, "newValue": "Steel", "optionKey": "B", "linked_operations": [], "validation": {}, "confidence": 0.95, "fallback": false, "next_action": "save_add_option", "message": "Adding Steel as option B to Q5 in Group 2."}

Return ONLY the JSON object. No explanation, no markdown, no extra text."""


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
    cleaned = raw.strip().rstrip('.').strip()
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    try:
        return json5.loads(cleaned)
    except Exception:
        return json.loads(cleaned)


def get_intent(message: str, available_groups: list = None) -> dict:
    msg_lower = message.lower().strip()

    # ── Keyword overrides BEFORE model call ──────────────────────────────
    SHOW_KEYWORDS = ("show all", "show questions", "list all", "list questions",
                     "how many", "all questions", "display questions", "show topics",
                     "list topics", "all topics", "show files", "list files",
                     "list out", "show all questions")

    # Skip keyword override if message mentions a specific group number or group name
    has_group_ref = bool(re.search(r'group\s*\d+', msg_lower)) or \
                    any(g.lower() in msg_lower for g in (available_groups or []))

    if any(kw in msg_lower for kw in SHOW_KEYWORDS) and not has_group_ref:
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

    # ── AZURE AI FOUNDRY (PHI-3) API CALL ─────────────────────────────────
    try:
        response = client.complete(
            model=MODEL_NAME,
            messages=[
                SystemMessage(content=SYSTEM_PROMPT),
                UserMessage(content=message),
            ],
            temperature=0.1,
            max_tokens=500,
        )
        raw = response.choices[0].message.content.strip()
        print(f"DEBUG RAW OUTPUT: {raw}")
    except Exception as e:
        print(f"Phi-3 API error: {e}")
        return {"type": "unknown", "message": f"Phi-3 error: {str(e)}"}
    # ─────────────────────────────────────────────────────────────────────

    try:
        result = _parse_raw(raw)
    except Exception:
        return {"type": "unknown", "raw": raw}

    print(f"DEBUG PARSED: {result}")

    intent = result.get("intent", "").lower().replace("-", "_")
    group_info = result.get("group") or {}
    group_str = group_info.get("name", "") if isinstance(group_info, dict) else str(group_info)
    print(f"DEBUG BEFORE RESOLVE: group_str={group_str}, available_groups={available_groups}")
    group_str = _resolve_group_by_index(group_str, available_groups or [])
    print(f"DEBUG AFTER RESOLVE: {group_str}")
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
        return {"type": "show", "target": "groups", "group": None}

    # ── TOPICS ────────────────────────────────────────────────────────────
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