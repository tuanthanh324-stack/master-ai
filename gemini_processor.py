# ============================================
# GEMINI PROCESSOR - Text Normalization AI
# ============================================
import json
import time
import urllib.request
from typing import Tuple, Optional, Dict, Any

from config import Config
from config_manager import get_gemini_key
from logger import logger

# Gemini models - ưu tiên nhanh nhất
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash-lite",
]

# Prompt templates
PROMPTS = {
    "verbatim": (
        "Bạn là chuyên gia biên tập lời thoại video. "
        "Hãy chỉnh sửa và định dạng đoạn văn bản:\n"
        "1. Bảo toàn 100% lời nói gốc - không tóm tắt\n"
        "2. Sửa lỗi chính tả, thêm dấu câu\n"
        "3. Ngắt đoạn rõ ràng\n\n"
        "Nội dung:\n{text}"
    ),
    "summary": (
        "Tóm tắt đoạn văn sau thành các ý chính ngắn gọn, dễ hiểu:\n\n{text}"
    ),
    "social": (
        "Viết lại đoạn văn thành bài viết mạng xã hội hấp dẫn, "
        "có tiêu đề, icon, kêu gọi tương tác:\n\n{text}"
    ),
    "lecture": (
        "Tạo đề cương bài học từ nội dung: gồm ý chính, thuật ngữ, các bước:\n\n{text}"
    ),
    "emotion": (
        "Phân tích kịch bản và chèn hướng dẫn lồng tiếng cảm xúc:\n\n{text}"
    )
}

# Language names
LANG_NAMES = {
    "Vietnamese": "tiếng Việt",
    "English": "English",
    "Spanish": "Español",
    "French": "Français",
    "German": "Deutsch"
}


def clean_output(text: str) -> str:
    """Làm sạch output từ Gemini."""
    if not text:
        return ""

    text = text.strip()

    # Remove markdown code blocks
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

    # Remove common prefixes
    for prefix in ["Dưới đây", "Here is", "Đây là"]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()

    return text


def fallback_normalize(text: str) -> str:
    """Fallback: Chuẩn hóa text cơ bản nếu không có API."""
    if not text:
        return ""

    lines = text.strip().split("\n")
    cleaned = []
    seen = set()

    for line in lines:
        line = line.strip()
        if not line or line in seen:
            continue

        seen.add(line)

        # Viết hoa đầu câu
        if line and len(line) > 1:
            line = line[0].upper() + line[1:]

        # Thêm dấu câu
        if line and not line[-1] in ".!?…:;":
            line += "."

        cleaned.append(line)

    return "\n".join(cleaned)


import os

def try_deepseek_api(prompt: str, api_key: str) -> Optional[str]:
    """Fallback 1: DeepSeek API (OpenAI compatible endpoint)."""
    if not api_key:
        return None
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            response = json.loads(resp.read().decode("utf-8"))
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        logger.debug(f"DeepSeek API failed: {e}")
        return None

def try_groq_api(prompt: str, api_key: str) -> Optional[str]:
    """Fallback 2: Groq Cloud Llama-3.3-70B API (Ultra-fast 300+ tokens/s)."""
    if not api_key:
        return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            response = json.loads(resp.read().decode("utf-8"))
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        logger.debug(f"Groq API failed: {e}")
        return None

def process(text: str, language: str = "Vietnamese",
            mode: str = "verbatim",
            custom_prompt: str = "") -> Tuple[str, str]:
    """
    Xử lý text với Multi-LLM AI Chain (Gemini -> DeepSeek -> Groq -> Local Rule Engine).
    """
    if not text:
        return "", "ERROR: Không có nội dung"

    start_time = time.time()
    api_key = get_gemini_key()
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    target_lang = LANG_NAMES.get(language, "tiếng Việt")

    # Build prompt
    if custom_prompt:
        prompt = f"{custom_prompt}\n\nNội dung:\n{text}"
    else:
        prompt_template = PROMPTS.get(mode, PROMPTS["verbatim"])
        prompt = prompt_template.replace("{text}", text)
        prompt = prompt.replace("{lang}", target_lang)

    # 1. Primary Provider: Google Gemini APIs
    if api_key:
        for model in GEMINI_MODELS:
            try:
                logger.debug(f"Trying Gemini model: {model}")
                data = {"contents": [{"parts": [{"text": prompt}]}]}
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

                req = urllib.request.Request(
                    url,
                    data=json.dumps(data).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=Config.GEMINI_TIMEOUT) as resp:
                    response = json.loads(resp.read().decode("utf-8"))

                output = response["candidates"][0]["content"]["parts"][0]["text"]
                output = clean_output(output)
                elapsed = time.time() - start_time
                word_count = len(output.split())
                logger.info(f"Gemini done in {elapsed:.1f}s: {word_count} words")
                return output, f"Thành công ({model}) | {word_count} từ"
            except Exception as e:
                logger.debug(f"Model {model} failed: {e}")
                continue

    # 2. Fallback Provider 1: DeepSeek AI
    if deepseek_key:
        ds_out = try_deepseek_api(prompt, deepseek_key)
        if ds_out:
            ds_out = clean_output(ds_out)
            elapsed = time.time() - start_time
            word_count = len(ds_out.split())
            logger.info(f"DeepSeek done in {elapsed:.1f}s: {word_count} words")
            return ds_out, f"Thành công (DeepSeek-V3) | {word_count} từ"

    # 3. Fallback Provider 2: Groq Cloud (Llama 3.3 70B)
    if groq_key:
        groq_out = try_groq_api(prompt, groq_key)
        if groq_out:
            groq_out = clean_output(groq_out)
            elapsed = time.time() - start_time
            word_count = len(groq_out.split())
            logger.info(f"Groq done in {elapsed:.1f}s: {word_count} words")
            return groq_out, f"Thành công (Groq Llama-3.3) | {word_count} từ"

    # 4. Fallback Provider 3: Local Rule Normalization Engine
    logger.warning("All LLM Providers unavailable, using local rule-based normalization engine")
    result = fallback_normalize(text)
    word_count = len(result.split())
    elapsed = time.time() - start_time
    return result, f"Thành công (Chuẩn hóa tự động) | {word_count} từ | {elapsed:.1f}s"


def quick_normalize(text: str) -> str:
    """Wrapper đơn giản - chỉ trả về text."""
    result, _ = process(text)
    return result
