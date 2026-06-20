"""
routes/api.py  — complete fixed version with persistent chat history
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from services import file_manager as fm
import io
import os
import json

router = APIRouter()

# ── Chat history storage on disk ──────────────────────────────────────────────

CHATS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chats")
os.makedirs(CHATS_DIR, exist_ok=True)


def _chats_path(username: str) -> str:
    safe = "".join(c for c in username if c.isalnum() or c in "-_")
    return os.path.join(CHATS_DIR, f"{safe}.json")


# ── File management ──────────────────────────────────────────────

@router.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        result = fm.ingest(file.filename, content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/active")
async def get_active_file():
    active = fm.get_active()
    return {"filename": active, "active": active}


@router.get("/files/stats")
async def get_stats():
    return fm.stats()


@router.post("/files/switch/{filename:path}")
async def switch_file(filename: str):
    try:
        result = fm.switch(filename)
        return {"filename": result, "active": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files")
async def list_files():
    return fm.list_files()


@router.delete("/files/{filename:path}")
async def delete_file(filename: str):
    try:
        return {"filename": fm.remove(filename)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── MCQs ─────────────────────────────────────────────────────────

@router.get("/mcqs")
async def get_mcqs(filename: str = None, topic: str = None, difficulty: str = None):
    try:
        results = fm.query(filename=filename, topic=topic, difficulty=difficulty, limit=500)
        return {"mcqs": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcqs/add")
async def add_mcq(payload: dict):
    try:
        position = payload.pop("position", None)
        payload.pop("insert_after_topic", None)
        mcq = fm.add_mcq(payload, position=position)
        return {"mcq": mcq}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/mcqs/{mcq_id}")
async def update_mcq(mcq_id: str, payload: dict):
    try:
        updates = payload.get("updates", payload)
        result = fm.edit_mcq(mcq_id, updates)
        if result is None:
            raise HTTPException(status_code=404, detail="MCQ not found")
        return {"mcq": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/mcqs/{mcq_id}")
async def delete_mcq(mcq_id: str):
    try:
        ok = fm.delete_mcq(mcq_id)
        if not ok:
            raise HTTPException(status_code=404, detail="MCQ not found")
        return {"deleted": mcq_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Export ────────────────────────────────────────────────────────

@router.get("/export")
async def export_mcqs(fmt: str = "json", topic: str = None, filename: str = None):
    try:
        if topic:
            results = fm.query(filename=filename, topic=topic, limit=1000)
            result = fm.export_from_data(results, fmt)
        else:
            result = fm.export(filename=filename, fmt=fmt)
        content = result["content"]
        if isinstance(content, str):
            content = content.encode("utf-8")
        return StreamingResponse(
            io.BytesIO(content), media_type=result["mime"],
            headers={"Content-Disposition": f"attachment; filename=mcq_questions.{result['ext']}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/custom")
async def export_custom(payload: dict, fmt: str = "json"):
    try:
        questions = payload.get("questions", [])
        result = fm.export_from_data(questions, fmt)
        content = result["content"]
        if isinstance(content, str):
            content = content.encode("utf-8")
        return StreamingResponse(
            io.BytesIO(content), media_type=result["mime"],
            headers={"Content-Disposition": f"attachment; filename=selected_questions.{result['ext']}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Intent / AI ───────────────────────────────────────────────────

@router.post("/intent")
async def get_intent(payload: dict):
    try:
        from services.ai_service import get_intent as ai_get_intent
        message = payload.get("message", "")
        filename = payload.get("filename")

        print(f"DEBUG FILENAME RECEIVED: {filename}")

        available_groups = []
        try:
            mcqs = fm.query(filename=filename, limit=500)
            # If filename gave nothing, try without filename (uses active file)
            if not mcqs:
                mcqs = fm.query(limit=500)
            seen = []
            for q in mcqs:
                t = q.get("topic") or q.get("group", "")
                if t and t not in seen:
                    seen.append(t)
            available_groups = seen
        except Exception as e:
            print(f"DEBUG GROUPS ERROR: {e}")
            pass

        print(f"DEBUG GROUPS: {available_groups}")
        result = ai_get_intent(message, available_groups=available_groups)
        return result
    except Exception as e:
        print(f"Intent error: {e}")
        return {"type": "chat"}


# ── SDM Responses ─────────────────────────────────────────────────

@router.post("/sdm/response")
async def save_sdm_response(payload: dict):
    try:
        return fm.save_sdm_response(
            payload.get("filename"), payload.get("item_oid"), payload.get("value")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sdm/responses")
async def get_sdm_responses(filename: str = None):
    try:
        return fm.get_sdm_responses(filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sdm/response")
async def delete_sdm_response(filename: str, item_oid: str):
    try:
        return fm.delete_sdm_response(filename, item_oid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Chat history (persistent — saved to disk) ─────────────────────────────────

@router.get("/chats")
async def get_chats(username: str = "guest"):
    path = _chats_path(username)
    if not os.path.exists(path):
        return {"chats": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return {"chats": json.load(f)}
    except Exception:
        return {"chats": []}


@router.post("/chats")
async def save_chats(payload: dict):
    username = payload.get("username", "guest")
    chats = payload.get("chats", [])
    path = _chats_path(username)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(chats, f, indent=2, ensure_ascii=False)
        return {"saved": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Convert CSV → SDM ─────────────────────────────────────────────

@router.post("/convert/csv-to-sdm")
async def convert_csv_to_sdm(file: UploadFile = File(...)):
    try:
        content = await file.read()
        import pandas as pd, io as _io, json, math

        df = pd.read_csv(_io.BytesIO(content))
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        def is_empty(val):
            if val is None: return True
            if isinstance(val, float) and math.isnan(val): return True
            if str(val).strip() in ('', 'nan', 'NaN', 'None'): return True
            return False

        # ── Build CodeList rows (rows with no question but have options) ──────
        extra_codelists = {}
        for _, row in df.iterrows():
            cl_oid = str(row.get('condition_oid', '') or '').strip()
            q = str(row.get('question', '') or '').strip()
            if cl_oid and not q and not is_empty(row.get('option_a')):
                opts = []
                for i, key in enumerate(['option_a','option_b','option_c','option_d'], 1):
                    val = str(row.get(key, '') or '').strip()
                    if val and not is_empty(val):
                        opts.append({
                            "CodedValue": str(i),
                            "IsEnabled": "Yes",
                            "Decode": {"TranslatedText": {"lang": "en", "text": val}}
                        })
                if opts:
                    extra_codelists[cl_oid] = opts

        # ── Build ConditionDef map from condition rows ─────────────────────────
        condition_defs = {}
        for _, row in df.iterrows():
            c_oid = str(row.get('condition_oid', '') or '').strip()
            c_expr = str(row.get('condition_expression', '') or '').strip()
            q = str(row.get('question', '') or '').strip()
            if c_oid and c_expr and not is_empty(c_expr):
                condition_defs[c_oid] = c_expr

        # ── Process question rows ─────────────────────────────────────────────
        groups: dict = {}
        group_order = []

        for _, row in df.iterrows():
            topic = str(row.get('topic', '') or '').strip()
            question = str(row.get('question', '') or '').strip()
            item_oid = str(row.get('item_oid', '') or '').strip()

            if not topic or not question or not item_oid or is_empty(topic):
                continue

            if topic not in groups:
                groups[topic] = []
                group_order.append(topic)

            groups[topic].append(row)

        # ── Build SDM structure ───────────────────────────────────────────────
        item_defs   = []
        item_groups = []
        code_lists  = []
        cond_defs   = []

        for c_oid, c_expr in condition_defs.items():
            cond_defs.append({
                "OID": c_oid,
                "Name": c_oid,
                "FormalExpression": {"Context": "OpenClinica", "text": c_expr}
            })

        for cl_oid, opts in extra_codelists.items():
            code_lists.append({
                "OID": cl_oid,
                "Name": cl_oid,
                "DataType": "text",
                "CodeListItem": opts
            })

        ig_counter = 1
        for topic in group_order:
            rows = groups[topic]
            group_oid = f"IG.{ig_counter}"
            ig_counter += 1
            item_refs = []

            for row in rows:
                item_oid  = str(row.get('item_oid', '') or '').strip()
                data_type = str(row.get('data_type', 'text') or 'text').strip()
                question  = str(row.get('question', '') or '').strip()
                mandatory = str(row.get('mandatory', 'No') or 'No').strip()
                cond_oid  = str(row.get('condition_oid', '') or '').strip()

                if not item_oid or not question:
                    continue

                opts = []
                for i, key in enumerate(['option_a','option_b','option_c','option_d'], 1):
                    val = str(row.get(key, '') or '').strip()
                    if val and not is_empty(val):
                        opts.append({
                            "CodedValue": str(i),
                            "IsEnabled": "Yes",
                            "Decode": {"TranslatedText": {"lang": "en", "text": val}}
                        })

                cl_ref = {}
                if opts:
                    cl_oid_new = f"CL.{item_oid.replace('I.', '')}"
                    code_lists.append({
                        "OID": cl_oid_new,
                        "Name": cl_oid_new,
                        "DataType": "text",
                        "CodeListItem": opts
                    })
                    cl_ref = {"CodeListOID": cl_oid_new}

                item_def = {
                    "OID": item_oid,
                    "Name": item_oid,
                    "DataType": data_type,
                    "Question": {"TranslatedText": {"lang": "en", "text": question}},
                    "CodeListRef": cl_ref
                }
                item_defs.append(item_def)

                item_ref = {"ItemOID": item_oid, "Mandatory": mandatory}
                if cond_oid and not is_empty(cond_oid):
                    item_ref["CollectionExceptionConditionOID"] = cond_oid
                item_refs.append(item_ref)

            item_groups.append({
                "OID": group_oid,
                "Name": topic,
                "Repeating": "No",
                "Description": {"TranslatedText": {"lang": "en", "text": topic}},
                "ItemRef": item_refs
            })

        sdm = {
            "SDM": {
                "Building": {
                    "TemplateVersion": [{
                        "ItemGroupDef": item_groups,
                        "ItemDef":      item_defs,
                        "CodeList":     code_lists,
                        "ConditionDef": cond_defs
                    }]
                }
            }
        }

        out_filename = file.filename.replace(".csv", "") + "_sdm.json"
        total_q = sum(len(v) for v in groups.values())

        return {
            "sdm":       sdm,
            "filename":  out_filename,
            "groups":    len(groups),
            "questions": total_q
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Convert History (persistent — saved to disk) ──────────────────────────────

CONVERT_HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "convert_history")
os.makedirs(CONVERT_HISTORY_DIR, exist_ok=True)

def _convert_history_path(username: str) -> str:
    safe = "".join(c for c in username if c.isalnum() or c in "-_")
    return os.path.join(CONVERT_HISTORY_DIR, f"{safe}_convert.json")

@router.get("/convert/history")
async def get_convert_history(username: str = "guest"):
    path = _convert_history_path(username)
    if not os.path.exists(path):
        return {"history": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return {"history": json.load(f)}
    except Exception:
        return {"history": []}

@router.post("/convert/history")
async def save_convert_history(payload: dict):
    username = payload.get("username", "guest")
    history = payload.get("history", [])
    path = _convert_history_path(username)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return {"saved": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sdm/responses/clear")
async def clear_sdm_responses(filename: str):
    try:
        return fm.clear_sdm_responses(filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))