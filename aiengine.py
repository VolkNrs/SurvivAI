from llama_cpp import Llama
from typing import Any, cast
import re

MODEL_CTX = 4096
MAX_DB_CHARS = 2200
MAX_HISTORY_CHARS = 1200
MAX_OUTPUT_TOKENS = 420

FORBIDDEN_PATTERNS = [
    r"\b(?:sorry|apologize|apologies)\b",
    r"\bi can'?t\b",
    r"\bi cannot\b",
    r"\bdisclaimer\b",
    r"\bcall\s+(?:911|999|112)\b",
    r"\bemergency\s+line\b",
    r"\bcontact\s+(?:authorities|emergency\s+services)\b",
    r"\binternet\s+access\b",
    r"\bmedical\s+attention\b",
    r"\bmedical\s+help\b",
    r"\bprofessional\s+help\b",
    r"\bmedical\s+facility\b",
    r"\bemergency\s+response\s+team\b",
]

REWRITE_PATTERNS = [
    (r"\bseek\s+(?:immediate\s+)?medical\s+attention\b", "start immediate self-care steps and monitor closely"),
    (r"\bseek\s+medical\s+help\b", "continue careful self-monitoring and follow the steps above"),
    (r"\bget\s+professional\s+help\b", "continue careful self-monitoring and reassess symptoms frequently"),
    (r"\breach(?:ing)?\s+out\s+to\s+(?:a\s+nearby\s+)?medical\s+facility\b", "move to a safer position and continue the listed actions"),
    (r"\bemergency\s+services\b", "urgent self-care steps"),
]

TEMPLATE_TOKEN_PATTERNS = [
    r"<\|assistant\|[^>]*>",
    r"<\|user\|[^>]*>",
    r"<\|system\|[^>]*>",
    r"<\|end\|[^>]*>",
]

HIGH_RISK_PATTERNS = [
    r"\b(can'?t\s+breathe|cannot\s+breathe|difficulty\s+breathing|shortness\s+of\s+breath)\b",
    r"\bchest\s+pain\b",
    r"\bsevere\s+bleeding\b",
    r"\bunconscious\b",
    r"\bseizure\b",
]

SURVIVAL_INVENTORY_PATTERNS = [
    r"\btrapped\b",
    r"\bwreckage\b",
    r"\bstranded\b",
    r"\blost\b",
    r"\bburn(?:ed|t)?\b",
    r"\bfire\b",
    r"\bcollapse\b",
    r"\brubble\b",
]


llm = Llama(
    model_path="./models/phi-3-mini-4k-instruct-q4.gguf",
    n_ctx=MODEL_CTX,
    n_threads=4  # Optimized for mobile/laptop CPUs
)


def _clip_text(text, limit):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n[truncated]"


def _sanitize_response(text):
    cleaned = (text or "").strip()

    for pattern, replacement in REWRITE_PATTERNS:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

    for pattern in FORBIDDEN_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    for pattern in TEMPLATE_TOKEN_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"\b(if\s+symptoms\s+persist\s+or\s+worsen,?\s*)?(consider\s+)?(seeking|getting|reaching\s+out\s+for)\s+(medical|professional)\s+(help|attention)\b", "continue the listed actions and reassess every few minutes", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _is_high_risk(user_query):
    query = (user_query or "").lower()
    return any(re.search(pattern, query, flags=re.IGNORECASE) for pattern in HIGH_RISK_PATTERNS)


def _needs_inventory_followup(user_query):
    query = (user_query or "").lower()
    return any(re.search(pattern, query, flags=re.IGNORECASE) for pattern in SURVIVAL_INVENTORY_PATTERNS)


def ask_ai(user_query, context_from_db, chat_history=None):
    history_block = ""
    if chat_history:
        recent_turns = chat_history[-6:]
        history_lines = []
        for turn in recent_turns:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if content:
                history_lines.append(f"{role}: {_clip_text(content, 300)}")
        if history_lines:
            history_block = "\nRecent Conversation:\n" + "\n".join(history_lines)
            history_block = _clip_text(history_block, MAX_HISTORY_CHARS)

    safe_context = _clip_text(context_from_db, MAX_DB_CHARS)
    safe_query = _clip_text(user_query, 500)
    high_risk = _is_high_risk(safe_query)
    inventory_followup = _needs_inventory_followup(safe_query)

    response_mode = """
    7) Default mode for most questions:
       - Give a concise direct answer in normal paragraph or short bullet format.
       - Ask follow-up questions only if needed.
    8) High-risk mode ONLY if user symptoms are severe (e.g., can't breathe, chest pain, severe bleeding, unconsciousness, seizure):
       - Keep the same natural style as normal mode (no forced section headers).
       - Start with the most urgent 2 to 4 immediate actions first.
       - Then ask 2 to 5 short, specific follow-up questions if needed.
       - Add a brief "next steps based on answers" summary in plain language.
    9) Keep wording concise, command-style, and focused on useful actions.
    10) For trapped/stranded/wreckage/hurt scenarios, answer normally first, then end with inventory questions about available resources.
        Ask about items like water, clothing, light source, phone battery, first-aid supplies, tools, shelter, lighter and nearby hazards.
    """

    if high_risk:
        mode_hint = "Current case severity: HIGH-RISK. Use normal style, but prioritize immediate actions and targeted follow-up questions."
    else:
        mode_hint = "Current case severity: ROUTINE. Give a direct answer in normal style."

    if inventory_followup:
        inventory_hint = "Scenario context: RESOURCE-INVENTORY NEEDED. After guidance, end with multiple short questions asking what resources the user has right now."
    else:
        inventory_hint = "Scenario context: INVENTORY FOLLOW-UP OPTIONAL."

    prompt = f"""
    <|system|>
    You are SurvivAI, an offline emergency assistant.
    MANDATORY OUTPUT CONTRACT:
     1) Give direct, practical, step-by-step survival guidance.
     2) Prioritize verified data below; if needed, use general survival knowledge.
     3) Never apologize and never use phrases like "sorry", "I can't", or "I cannot".
     4) Never include disclaimers.
    5) Never mention emergency lines, calling services, contacting authorities, internet access, medical attention, medical help, professional help, or medical facilities.
     6) Ask follow up questions if needed.
    {response_mode}
    If any draft violates a rule, rewrite it before finalizing.
    {mode_hint}
    {inventory_hint}
    
    Verified Data: {safe_context}{history_block}
    <|end|>
    <|user|>
    {safe_query}
    <|end|>
    <|assistant|>
    """

    try:
        prompt_tokens = len(llm.tokenize(prompt.encode("utf-8")))
        max_tokens = max(96, min(MAX_OUTPUT_TOKENS, MODEL_CTX - prompt_tokens - 16))
        response = cast(
            dict[str, Any],
            llm(
                prompt,
                max_tokens=max_tokens,
                stop=["<|end|>", "<|user|>", "<|system|>"],
                echo=False,
                stream=False,
                temperature=0.2,
            ),
        )
        return _sanitize_response(response["choices"][0]["text"])
    except Exception:
        return "I hit a local model limit while generating this answer. Try a shorter follow-up question."