"""Criterios puros de aceptación; sin llamadas a GKE ni inferencia."""
import re


def require(condition, message):
    if not condition:
        raise ValueError(message)


def complete_choice(choice):
    text = choice.get("message", {}).get("content") or ""
    reason = choice.get("finish_reason")
    require(bool(text.strip()), "Respuesta vacía")
    require(reason == "stop", f"Respuesta no terminada naturalmente: finish_reason={reason!r}")
    return text.strip()


def final_answer(text, reasoning=False):
    if reasoning:
        require("</think>" in text, "Razonamiento sin marcador de respuesta final </think>")
        text = text.rsplit("</think>", 1)[1]
    require(bool(text.strip()), "Respuesta final vacía")
    return text.strip()


def quality(text, case):
    text = text.strip()
    if "exact" in case:
        require(text == case["exact"], f"Se esperaba {case['exact']!r}; se obtuvo {text!r}")
    for pattern in case.get("required", []):
        require(re.search(pattern, text), f"Falta contenido requerido: {pattern}")
    for pattern in case.get("forbidden", []):
        require(not re.search(pattern, text), f"Contenido incorrecto: {pattern}")
    if case.get("one_sentence"):
        sentences = [s for s in re.split(r"[.!?]+(?:\s|$)", text) if s.strip()]
        require(len(sentences) == 1 and "\n\n" not in text,
                f"Se requiere una oración; se observaron {len(sentences)}")
    return text


def complete_stream(events):
    require(any(e["data"] == "[DONE]" for e in events), "SSE sin [DONE]")
    import json
    parts, reason = [], None
    for event in events:
        if event["data"] == "[DONE]":
            continue
        for choice in json.loads(event["data"]).get("choices", []):
            parts.append(choice.get("delta", {}).get("content") or "")
            reason = choice.get("finish_reason") or reason
    text = "".join(parts).strip()
    require(bool(text), "Streaming vacío")
    require(reason == "stop", f"Streaming truncado/incompleto: finish_reason={reason!r}")
    return text
