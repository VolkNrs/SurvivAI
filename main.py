import flet as ft
import sqlite3
import asyncio
import queue
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from aiengine import ask_ai, ensure_model_ready, sanitize_response, set_model_dir


_DB_PATH: str = "survival_data.db"


def set_db_path(path: str) -> None:
    global _DB_PATH
    _DB_PATH = path


def _open_db():
    return sqlite3.connect(_DB_PATH)


def search_database(query: str):
    try:
        conn = _open_db()
        c = conn.cursor()
        term = f"%{query}%"
        c.execute(
            "SELECT title, content FROM guides WHERE title LIKE ? OR tags LIKE ? OR content LIKE ? LIMIT 1",
            (term, term, term),
        )
        result = c.fetchone()
        conn.close()
        return result
    except Exception:
        return None


def db_all_guides() -> dict:
    try:
        conn = _open_db()
        c = conn.cursor()
        c.execute("SELECT id, category, title, tags FROM guides ORDER BY category, title")
        rows = c.fetchall()
        conn.close()
        by_cat: dict = {}
        for gid, cat, title, tags in rows:
            by_cat.setdefault(cat, []).append({"id": gid, "title": title, "tags": tags or ""})
        return by_cat
    except Exception:
        return {}


def db_all_guides_flat() -> list:
    try:
        conn = _open_db()
        c = conn.cursor()
        c.execute("SELECT id, category, title, tags FROM guides ORDER BY category, title")
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "category": r[1], "title": r[2], "tags": r[3] or ""} for r in rows]
    except Exception:
        return []


def db_guide(guide_id: int):
    try:
        conn = _open_db()
        c = conn.cursor()
        c.execute("SELECT title, content FROM guides WHERE id=?", (guide_id,))
        result = c.fetchone()
        conn.close()
        return result
    except Exception:
        return None


QUICK_ACTIONS = [
    ("Severe Bleeding",  "I have severe uncontrolled bleeding. What do I do immediately?"),
    ("CPR",              "Someone is unresponsive and not breathing normally. How do I perform CPR?"),
    ("Fire / Burns",     "There is fire nearby and someone has burns. What do I do right now?"),
    ("Snake Bite",       "Someone was just bitten by a snake. What are the immediate steps?"),
    ("Hypothermia",      "Someone is severely cold, shivering badly and confused. What do I do?"),
    ("Trapped",          "I am trapped under debris or wreckage. What should I do while I wait?"),
    ("No Water",         "I have no water and I am stranded. How do I find or purify water?"),
    ("Need Shelter",     "I am stranded outdoors and need shelter fast. How do I build one?"),
    ("Stroke Signs",     "Someone may be having a stroke. What are the signs and what do I do?"),
    ("Flooding",         "There is flash flooding around me. What do I do right now?"),
    ("Choking",          "Someone is choking and cannot breathe. What do I do immediately?"),
    ("Heat Stroke",      "Someone is overheating, confused and not sweating. What do I do?"),
    ("Fracture",         "I think I have a broken bone. How do I immobilise it with limited supplies?"),
    ("Gas Leak",         "I can smell gas in or around a building. What do I do?"),
    ("Frostbite",        "Someone has frostbitten fingers or toes. What are the steps?"),
]

FOLLOW_UPS = [
    "What supplies do I need for this?",
    "What are the warning signs to watch for?",
    "What if there is no improvement?",
]


async def main(page: ft.Page):

    try:
        _app_dir_str = await page.storage_paths.get_application_support_directory()
        _app_dir = Path(_app_dir_str)
    except Exception:
        _app_dir = Path.home() / ".survivai"
    _app_dir.mkdir(parents=True, exist_ok=True)

    SETTINGS_PATH = _app_dir / "user_settings.json"
    SESSION_PATH  = _app_dir / "chat_session.json"

    _db_dest = _app_dir / "survival_data.db"
    if not _db_dest.exists():
        for _src in [
            Path("survival_data.db"),
            Path("assets/survival_data.db"),
            Path(getattr(sys, "_MEIPASS", ".")) / "survival_data.db",
        ]:
            if _src.exists():
                shutil.copy2(_src, _db_dest)
                break
    set_db_path(str(_db_dest))

    _local_model_dir  = Path("models")
    _local_model_file = _local_model_dir / "phi-3-mini-4k-instruct-q4.gguf"
    if _local_model_file.exists():
        set_model_dir(str(_local_model_dir))
    else:
        set_model_dir(str(_app_dir / "models"))


    THEMES: dict[str, dict] = {
        "Default": {
            "bg": ft.Colors.BLACK, "surface": "#141414",
            "header": ft.Colors.RED_400, "text_subtle": ft.Colors.GREY_500,
            "border": ft.Colors.GREY_800, "accent": ft.Colors.RED_400,
            "accent_soft": ft.Colors.RED_300,
            "button_bg": ft.Colors.with_opacity(0.15, ft.Colors.RED_900),
            "input_bg":  ft.Colors.with_opacity(0.18, ft.Colors.GREY_900),
            "chat_bg":   ft.Colors.with_opacity(0.12, ft.Colors.GREY_900),
            "user_bubble":      ft.Colors.with_opacity(0.78, ft.Colors.RED_500),
            "assistant_bubble": ft.Colors.with_opacity(0.36, ft.Colors.BLUE_GREY_800),
        },
        "Default Soft": {
            "bg": ft.Colors.BLACK, "surface": "#141414",
            "header": ft.Colors.RED_300, "text_subtle": ft.Colors.GREY_400,
            "border": ft.Colors.GREY_700, "accent": ft.Colors.RED_300,
            "accent_soft": ft.Colors.RED_200,
            "button_bg": ft.Colors.with_opacity(0.14, ft.Colors.RED_900),
            "input_bg":  ft.Colors.with_opacity(0.16, ft.Colors.GREY_900),
            "chat_bg":   ft.Colors.with_opacity(0.10, ft.Colors.GREY_900),
            "user_bubble":      ft.Colors.with_opacity(0.68, ft.Colors.RED_400),
            "assistant_bubble": ft.Colors.with_opacity(0.30, ft.Colors.BLUE_GREY_800),
        },
        "Default Carbon": {
            "bg": ft.Colors.BLACK, "surface": "#141820",
            "header": ft.Colors.RED_500, "text_subtle": ft.Colors.GREY_500,
            "border": ft.Colors.BLUE_GREY_800, "accent": ft.Colors.RED_500,
            "accent_soft": ft.Colors.RED_300,
            "button_bg": ft.Colors.with_opacity(0.12, ft.Colors.RED_900),
            "input_bg":  ft.Colors.with_opacity(0.20, ft.Colors.BLUE_GREY_900),
            "chat_bg":   ft.Colors.with_opacity(0.10, ft.Colors.BLUE_GREY_900),
            "user_bubble":      ft.Colors.with_opacity(0.74, ft.Colors.RED_600),
            "assistant_bubble": ft.Colors.with_opacity(0.34, ft.Colors.BLUE_GREY_900),
        },
        "Default Glow": {
            "bg": ft.Colors.BLACK, "surface": "#1A0A0A",
            "header": ft.Colors.RED_300,
            "text_subtle": ft.Colors.with_opacity(0.86, ft.Colors.RED_100),
            "border": ft.Colors.RED_700, "accent": ft.Colors.RED_300,
            "accent_soft": ft.Colors.RED_200,
            "button_bg": ft.Colors.with_opacity(0.16, ft.Colors.RED_900),
            "input_bg":  ft.Colors.with_opacity(0.20, ft.Colors.RED_900),
            "chat_bg":   ft.Colors.with_opacity(0.11, ft.Colors.RED_900),
            "user_bubble":      ft.Colors.with_opacity(0.70, ft.Colors.RED_400),
            "assistant_bubble": ft.Colors.with_opacity(0.34, ft.Colors.BLUE_GREY_800),
        },
        "Forest": {
            "bg": ft.Colors.BLACK, "surface": "#0D1A0D",
            "header": ft.Colors.GREEN_400,
            "text_subtle": ft.Colors.with_opacity(0.82, ft.Colors.GREEN_200),
            "border": ft.Colors.GREEN_700, "accent": ft.Colors.GREEN_400,
            "accent_soft": ft.Colors.GREEN_300,
            "button_bg": ft.Colors.with_opacity(0.15, ft.Colors.GREEN_900),
            "input_bg":  ft.Colors.with_opacity(0.18, ft.Colors.GREEN_900),
            "chat_bg":   ft.Colors.with_opacity(0.14, ft.Colors.GREEN_900),
            "user_bubble":      ft.Colors.with_opacity(0.75, ft.Colors.GREEN_500),
            "assistant_bubble": ft.Colors.with_opacity(0.36, ft.Colors.GREEN_900),
        },
        "Ocean": {
            "bg": ft.Colors.BLUE_GREY_900, "surface": "#0E1820",
            "header": ft.Colors.CYAN_300,
            "text_subtle": ft.Colors.with_opacity(0.84, ft.Colors.CYAN_100),
            "border": ft.Colors.CYAN_700, "accent": ft.Colors.CYAN_400,
            "accent_soft": ft.Colors.CYAN_200,
            "button_bg": ft.Colors.with_opacity(0.14, ft.Colors.CYAN_900),
            "input_bg":  ft.Colors.with_opacity(0.18, ft.Colors.CYAN_900),
            "chat_bg":   ft.Colors.with_opacity(0.14, ft.Colors.CYAN_900),
            "user_bubble":      ft.Colors.with_opacity(0.74, ft.Colors.CYAN_600),
            "assistant_bubble": ft.Colors.with_opacity(0.34, ft.Colors.BLUE_900),
        },
        "Violet": {
            "bg": ft.Colors.BLUE_GREY_900, "surface": "#160D2A",
            "header": ft.Colors.DEEP_PURPLE_300,
            "text_subtle": ft.Colors.with_opacity(0.82, ft.Colors.DEEP_PURPLE_100),
            "border": ft.Colors.DEEP_PURPLE_700, "accent": ft.Colors.DEEP_PURPLE_400,
            "accent_soft": ft.Colors.DEEP_PURPLE_200,
            "button_bg": ft.Colors.with_opacity(0.14, ft.Colors.DEEP_PURPLE_900),
            "input_bg":  ft.Colors.with_opacity(0.18, ft.Colors.DEEP_PURPLE_900),
            "chat_bg":   ft.Colors.with_opacity(0.14, ft.Colors.DEEP_PURPLE_900),
            "user_bubble":      ft.Colors.with_opacity(0.74, ft.Colors.DEEP_PURPLE_500),
            "assistant_bubble": ft.Colors.with_opacity(0.34, ft.Colors.INDIGO_900),
        },
        "Amber": {
            "bg": ft.Colors.BLACK, "surface": "#1A1200",
            "header": ft.Colors.AMBER_400,
            "text_subtle": ft.Colors.with_opacity(0.82, ft.Colors.AMBER_200),
            "border": ft.Colors.AMBER_700, "accent": ft.Colors.AMBER_400,
            "accent_soft": ft.Colors.AMBER_300,
            "button_bg": ft.Colors.with_opacity(0.14, ft.Colors.AMBER_900),
            "input_bg":  ft.Colors.with_opacity(0.18, ft.Colors.AMBER_900),
            "chat_bg":   ft.Colors.with_opacity(0.13, ft.Colors.AMBER_900),
            "user_bubble":      ft.Colors.with_opacity(0.76, ft.Colors.AMBER_600),
            "assistant_bubble": ft.Colors.with_opacity(0.34, ft.Colors.BROWN_800),
        },
        "Mono": {
            "bg": ft.Colors.BLACK, "surface": "#141414",
            "header": ft.Colors.GREY_300, "text_subtle": ft.Colors.GREY_500,
            "border": ft.Colors.GREY_700, "accent": ft.Colors.BLUE_GREY_300,
            "accent_soft": ft.Colors.GREY_300,
            "button_bg": ft.Colors.with_opacity(0.14, ft.Colors.GREY_900),
            "input_bg":  ft.Colors.with_opacity(0.18, ft.Colors.GREY_900),
            "chat_bg":   ft.Colors.with_opacity(0.12, ft.Colors.GREY_900),
            "user_bubble":      ft.Colors.with_opacity(0.72, ft.Colors.BLUE_GREY_600),
            "assistant_bubble": ft.Colors.with_opacity(0.32, ft.Colors.GREY_800),
        },
    }

    TEXT_SIZES: dict[str, int] = {
        "Small": 13, "Medium": 15, "Large": 16, "XL": 18, "XXL": 22,
    }


    def _load_settings() -> dict:
        if not SETTINGS_PATH.exists():
            return {}
        try:
            with SETTINGS_PATH.open("r", encoding="utf-8") as f:
                d = json.load(f)
                return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    _s = _load_settings()
    current_theme_name: str = _s.get("theme", "Default")
    if current_theme_name not in THEMES:
        current_theme_name = "Default"
    current_text_size_name: str = _s.get("text_size", "Large")
    if current_text_size_name not in TEXT_SIZES:
        current_text_size_name = "Large"

    _t = THEMES[current_theme_name]
    CHAT_TEXT_SIZE: int = TEXT_SIZES[current_text_size_name]

    THEME_BG              = _t["bg"]
    THEME_SURFACE         = _t["surface"]
    THEME_HEADER          = _t["header"]
    THEME_TEXT_SUBTLE     = _t["text_subtle"]
    THEME_BORDER          = _t["border"]
    THEME_ACCENT          = _t["accent"]
    THEME_ACCENT_SOFT     = _t["accent_soft"]
    THEME_BUTTON_BG       = _t["button_bg"]
    THEME_INPUT_BG        = _t["input_bg"]
    THEME_CHAT_BG         = _t["chat_bg"]
    THEME_USER_BUBBLE     = _t["user_bubble"]
    THEME_ASSISTANT_BUBBLE= _t["assistant_bubble"]

    def save_settings() -> None:
        try:
            with SETTINGS_PATH.open("w", encoding="utf-8") as f:
                json.dump({"theme": current_theme_name, "text_size": current_text_size_name}, f)
        except Exception:
            pass


    page.title       = "SurvivAI"
    page.theme_mode  = ft.ThemeMode.DARK
    page.bgcolor     = THEME_BG
    page.padding     = 0
    page.spacing     = 0
    page.theme       = ft.Theme(font_family="Roboto")

    chat_history: list[dict]  = []
    model_ready               = False
    auto_follow_stream        = True
    generation_state: dict    = {"is_generating": False, "stop_requested": False}
    active_tab: dict          = {"tab": "chat"}
    _last_fu_ref: dict        = {"row": None}


    def show_snack(msg: str, ms: int = 2500) -> None:
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.GREY_900),
            duration=ms,
        )
        page.snack_bar.open = True
        page.update()

    def bubble_width() -> int:
        w = page.width or 400
        return max(220, min(int(w * 0.78), 380))


    _status_dot  = ft.Container(width=8, height=8, bgcolor=ft.Colors.GREY_700, border_radius=4)
    _status_text = ft.Text("Works offline", size=10, color=ft.Colors.GREY_600)
    status_badge = ft.Row(controls=[_status_dot, _status_text], spacing=5, tight=True)

    def update_status(state: str) -> None:
        if state == "loading_model":
            _status_dot.bgcolor  = ft.Colors.AMBER_400
            _status_text.value   = "Loading model..."
            _status_text.color   = ft.Colors.AMBER_400
        elif state == "downloading":
            _status_dot.bgcolor  = ft.Colors.LIGHT_BLUE_300
            _status_text.value   = "Downloading model..."
            _status_text.color   = ft.Colors.LIGHT_BLUE_300
        elif state == "ready":
            _status_dot.bgcolor  = ft.Colors.GREEN_400
            _status_text.value   = "OFFLINE  ·  READY"
            _status_text.color   = ft.Colors.GREEN_400
        elif state == "thinking":
            _status_dot.bgcolor  = ft.Colors.LIGHT_BLUE_400
            _status_text.value   = "Generating..."
            _status_text.color   = ft.Colors.LIGHT_BLUE_400
        else:
            _status_dot.bgcolor  = ft.Colors.GREY_700
            _status_text.value   = "Works offline"
            _status_text.color   = ft.Colors.GREY_600


    def save_session() -> None:
        try:
            with SESSION_PATH.open("w", encoding="utf-8") as f:
                json.dump({"messages": chat_history[-40:]}, f)
        except Exception:
            pass

    def restore_session() -> None:
        if not SESSION_PATH.exists():
            return
        try:
            with SESSION_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
            for msg in data.get("messages", []):
                role    = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                    chat_history.append({"role": role, "content": content})
                    _append_bubble(content, is_user=(role == "user"))
            if chat_history:
                _update_empty_state()
                page.update()
        except Exception:
            pass


    def on_chat_scroll(e: ft.OnScrollEvent) -> None:
        nonlocal auto_follow_stream
        try:
            auto_follow_stream = (float(e.max_scroll_extent) - float(e.pixels)) <= 60
        except Exception:
            pass

    chat_list = ft.ListView(
        expand=True, spacing=10, auto_scroll=False,
        on_scroll=on_chat_scroll,
        padding=ft.Padding.symmetric(horizontal=6, vertical=6),
    )

    async def _scroll_bottom(ms: int = 90) -> None:
        if auto_follow_stream:
            await chat_list.scroll_to(offset=-1, duration=ms)


    _empty_state = ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(ft.Icons.EMERGENCY, color=ft.Colors.with_opacity(0.25, ft.Colors.RED_400), size=54),
                ft.Container(height=8),
                ft.Text(
                    "SurvivAI",
                    size=22, weight=ft.FontWeight.BOLD,
                    color=ft.Colors.with_opacity(0.35, ft.Colors.WHITE),
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Offline emergency guidance.\nDescribe your situation or tap a quick action.",
                    size=14, color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=4,
            tight=True,
        ),
        alignment=ft.Alignment(0, 0),
        expand=True,
        visible=True,
    )

    def _update_empty_state() -> None:
        _empty_state.visible = len(chat_history) == 0


    def _copy_message(text: str) -> None:
        try:
            page.set_clipboard(text)
            show_snack("Copied to clipboard")
        except Exception:
            show_snack("Copy failed")

    def _remove_followup_chips() -> None:
        ref = _last_fu_ref["row"]
        if ref is not None and ref in chat_list.controls:
            chat_list.controls.remove(ref)
        _last_fu_ref["row"] = None

    def _add_followup_chips() -> None:
        chips = []
        for txt in FOLLOW_UPS:
            chips.append(
                ft.Container(
                    content=ft.Text(txt, size=12, color=THEME_TEXT_SUBTLE, max_lines=1),
                    on_click=lambda e, q=txt: _quick_action_send(q),
                    bgcolor=THEME_BUTTON_BG,
                    border_radius=16,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                    border=ft.Border.all(1, THEME_BORDER),
                )
            )
        row_ctrl = ft.Container(
            content=ft.Row(controls=chips, spacing=6, scroll=ft.ScrollMode.AUTO),
            padding=ft.Padding.only(left=4, top=2, bottom=6),
        )
        chat_list.controls.append(
            ft.Row(controls=[row_ctrl], alignment=ft.MainAxisAlignment.START, tight=True)
        )
        _last_fu_ref["row"] = chat_list.controls[-1]

    def _append_bubble(text: str, is_user: bool) -> ft.Text:
        max_line = max((len(ln) for ln in text.split("\n")), default=0)
        needs_wrap = max_line > 50
        text_ctrl = ft.Text(
            text, selectable=True, size=CHAT_TEXT_SIZE,
            weight=ft.FontWeight.W_400 if is_user else ft.FontWeight.W_500,
            color=ft.Colors.WHITE,
        )
        bubble = ft.Container(
            content=text_ctrl,
            bgcolor=THEME_USER_BUBBLE if is_user else THEME_ASSISTANT_BUBBLE,
            border_radius=ft.BorderRadius(
                top_left=16, top_right=4 if is_user else 16,
                bottom_left=16, bottom_right=16 if is_user else 4,
            ),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            width=bubble_width() if needs_wrap else None,
            on_click=(lambda e, t=text: _copy_message(t)) if not is_user else None,
            tooltip="Tap to copy" if not is_user else None,
        )
        chat_list.controls.append(
            ft.Row(
                controls=[bubble],
                alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START,
                tight=True,
            )
        )
        return text_ctrl


    async def _process_query(user_query: str, ai_text: ft.Text, ai_bubble: ft.Container) -> None:
        nonlocal model_ready
        pq: queue.Queue = queue.Queue()
        sq: queue.Queue = queue.Queue()
        dl_shown = False
        generation_state["is_generating"]  = True
        generation_state["stop_requested"] = False
        stop_button.disabled = False

        def on_model_progress(dl: int, total: int) -> None:
            pq.put((dl, total))

        def on_stream_chunk(chunk: str) -> bool:
            if generation_state["stop_requested"]:
                return False
            sq.put(chunk)
            return True

        try:
            db_task = asyncio.create_task(asyncio.to_thread(search_database, user_query))

            if not model_ready:
                update_status("loading_model")
                page.update()
                mtask = asyncio.create_task(asyncio.to_thread(ensure_model_ready, on_model_progress))
                while not mtask.done():
                    while not pq.empty():
                        dl, total = pq.get_nowait()
                        if not dl_shown:
                            download_status.visible  = True
                            download_progress.visible= True
                            update_status("downloading")
                            dl_shown = True
                        if total > 0:
                            r = min(1.0, dl / total)
                            download_progress.value = r
                            mb_dl = dl / (1024 * 1024)
                            mb_tot = total / (1024 * 1024)
                            download_status.value = (
                                f"Downloading model  {mb_dl:.0f} / {mb_tot:.0f} MB  ({r*100:.0f}%)"
                            )
                        else:
                            download_progress.value = None
                            download_status.value   = "Downloading model..."
                    page.update()
                    await asyncio.sleep(0.15)
                await mtask
                model_ready = True
                update_status("ready")
                if dl_shown:
                    download_status.value   = "Model ready."
                    page.update()
                    await asyncio.sleep(1.2)
                    download_status.visible  = False
                    download_progress.visible= False
                page.update()

            db_result = await db_task
            update_status("thinking")
            ai_text.value = "●"
            page.update()

            context = db_result[1] if db_result else "No specific data found in offline vault."
            ai_task = asyncio.create_task(
                asyncio.to_thread(ask_ai, user_query, context, chat_history, on_stream_chunk)
            )

            raw_parts: list[str] = []
            last_dot  = asyncio.get_running_loop().time()
            while not ai_task.done():
                if generation_state["stop_requested"]:
                    break
                updated = False
                while not sq.empty():
                    chunk = sq.get_nowait()
                    if chunk:
                        raw_parts.append(chunk)
                        clean = sanitize_response("".join(raw_parts))
                        ai_text.value = clean if clean else "●"
                        if ai_bubble.width is None and len(ai_text.value) > 55:
                            ai_bubble.width = bubble_width()
                        updated = True
                if not updated and ai_text.value in {"●", "●●", "●●●"}:
                    now = asyncio.get_running_loop().time()
                    if now - last_dot >= 0.30:
                        ai_text.value = "●" * (len(ai_text.value) % 3 + 1)
                        last_dot = now
                        updated  = True
                if updated:
                    await _scroll_bottom(80)
                    page.update()
                await asyncio.sleep(0.04)

            if generation_state["stop_requested"]:
                ai_text.value   = "STOPPED"
                ai_bubble.width = None
                try:
                    await ai_task
                except Exception:
                    pass
                chat_history.append({"role": "user",      "content": user_query})
                chat_history.append({"role": "assistant", "content": ai_text.value})
                await _scroll_bottom(120)
                save_session()
                return

            while not sq.empty():
                chunk = sq.get_nowait()
                if chunk:
                    raw_parts.append(chunk)

            raw_joined = "".join(raw_parts)
            if ai_bubble.width is None and len(raw_joined) > 55:
                ai_bubble.width = bubble_width()

            final = await ai_task
            ai_text.value = final.strip()
            chat_history.append({"role": "user",      "content": user_query})
            chat_history.append({"role": "assistant", "content": ai_text.value})
            save_session()
            _add_followup_chips()
            await _scroll_bottom(120)
        except Exception:
            ai_text.value = "Unable to process right now. Please try again."
        finally:
            if dl_shown:
                download_progress.visible = False
                download_status.visible   = False
            update_status("ready" if model_ready else "idle")
            search_button.disabled    = False
            new_chat_button.disabled  = False
            stop_button.visible       = False
            stop_button.disabled      = False
            generation_state["is_generating"]  = False
            generation_state["stop_requested"] = False
            page.update()

    def on_search_click(e) -> None:
        nonlocal auto_follow_stream
        if generation_state["is_generating"]:
            return
        user_query = (search_bar.value or "").strip()
        if not user_query:
            return

        auto_follow_stream = True
        _remove_followup_chips()
        _empty_state.visible = False
        _append_bubble(user_query, is_user=True)

        ai_text_ctrl = ft.Text(
            "●", selectable=True,
            weight=ft.FontWeight.W_700, size=max(12, CHAT_TEXT_SIZE - 2),
            color=ft.Colors.WHITE,
        )
        ai_bubble = ft.Container(
            content=ai_text_ctrl,
            bgcolor=THEME_ASSISTANT_BUBBLE,
            border_radius=ft.BorderRadius(top_left=16, top_right=16, bottom_left=4, bottom_right=16),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            width=None,
        )
        chat_list.controls.append(
            ft.Row(controls=[ai_bubble], alignment=ft.MainAxisAlignment.START, tight=True)
        )

        search_bar.value          = ""
        search_bar.hint_text      = "Give more info or ask..."
        char_counter.value        = "0 / 500"
        search_button.disabled    = True
        new_chat_button.disabled  = True
        stop_button.visible       = True
        stop_button.disabled      = False
        page.update()

        page.run_task(_process_query, user_query, ai_text_ctrl, ai_bubble)

    def _quick_action_send(query: str) -> None:
        if generation_state["is_generating"]:
            return
        if active_tab["tab"] != "chat":
            switch_tab("chat")
        search_bar.value = query
        on_search_click(None)

    def on_new_chat_click(e) -> None:
        nonlocal auto_follow_stream
        chat_history.clear()
        chat_list.controls.clear()
        _last_fu_ref["row"] = None
        search_bar.value     = ""
        search_bar.hint_text = "Describe the situation..."
        char_counter.value   = "0 / 500"
        auto_follow_stream   = True
        _update_empty_state()
        try:
            SESSION_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        page.update()

    def on_stop_click(e) -> None:
        if generation_state["is_generating"]:
            generation_state["stop_requested"] = True
            stop_button.disabled = True
            page.update()


    header = ft.Text("SurvivAI", size=28, weight=ft.FontWeight.BOLD, color=THEME_HEADER)
    download_status   = ft.Text("", color=THEME_TEXT_SUBTLE, size=11, visible=False)
    download_progress = ft.ProgressBar(value=None, visible=False, color=THEME_ACCENT, height=3)

    char_counter = ft.Text("0 / 500", size=10, color=THEME_TEXT_SUBTLE)

    search_bar = ft.TextField(
        hint_text="Describe the situation...",
        prefix_icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
        filled=True, text_size=CHAT_TEXT_SIZE,
        bgcolor=THEME_INPUT_BG, border_color=THEME_BORDER,
        focused_border_color=THEME_ACCENT, cursor_color=THEME_ACCENT,
        hint_style=ft.TextStyle(color=THEME_TEXT_SUBTLE, size=max(12, CHAT_TEXT_SIZE - 1)),
        border_radius=24,
        content_padding=ft.Padding.symmetric(horizontal=18, vertical=14),
        expand=True,
        on_submit=lambda e: on_search_click(None),
        on_change=lambda e: _on_input_change(),
        multiline=True,
        min_lines=1,
        max_lines=4,
        shift_enter=True,
    )

    def _on_input_change() -> None:
        count = len(search_bar.value or "")
        char_counter.value = f"{count} / 500"
        char_counter.color = ft.Colors.RED_400 if count >= 460 else THEME_TEXT_SUBTLE
        page.update()

    search_button = ft.IconButton(
        icon=ft.Icons.SEND_ROUNDED, icon_color=ft.Colors.WHITE, icon_size=20,
        on_click=on_search_click, width=48, height=48,
        style=ft.ButtonStyle(
            shape=ft.CircleBorder(), bgcolor=THEME_ACCENT,
            overlay_color=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
        ),
    )
    new_chat_button = ft.OutlinedButton(
        "New Chat", icon=ft.Icons.ADD_COMMENT_OUTLINED,
        on_click=on_new_chat_click,
        style=ft.ButtonStyle(
            color=THEME_ACCENT_SOFT, bgcolor=THEME_BUTTON_BG,
            side=ft.BorderSide(1, THEME_BORDER),
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        ),
    )
    settings_button = ft.IconButton(
        icon=ft.Icons.TUNE, icon_size=22, icon_color=THEME_ACCENT_SOFT,
        on_click=lambda e: open_settings(), width=44, height=44,
        style=ft.ButtonStyle(
            bgcolor=THEME_BUTTON_BG, side=ft.BorderSide(1, THEME_BORDER),
            shape=ft.CircleBorder(),
            overlay_color=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        ),
    )
    stop_button = ft.IconButton(
        icon=ft.Icons.STOP_CIRCLE_OUTLINED, tooltip="Stop generating",
        icon_color=THEME_ACCENT_SOFT, bgcolor=THEME_BUTTON_BG, icon_size=22,
        on_click=on_stop_click, width=44, height=44, visible=False,
    )


    _qa_chips: list[ft.Container] = []
    for _label, _query in QUICK_ACTIONS:
        _chip = ft.Container(
            content=ft.Text(_label, size=12, color=ft.Colors.WHITE,
                            max_lines=1, weight=ft.FontWeight.W_500),
            on_click=lambda e, q=_query: _quick_action_send(q),
            bgcolor=THEME_BUTTON_BG, border_radius=20,
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            border=ft.Border.all(1, THEME_BORDER),
        )
        _qa_chips.append(_chip)

    quick_actions_strip = ft.Container(
        content=ft.Row(controls=_qa_chips, scroll=ft.ScrollMode.AUTO, spacing=8),
        padding=ft.Padding.symmetric(horizontal=16, vertical=6),
    )


    chat_frame = ft.Container(
        content=ft.Stack(
            controls=[_empty_state, chat_list],
            expand=True,
        ),
        bgcolor=THEME_CHAT_BG,
        border=ft.Border.all(1, THEME_BORDER),
        border_radius=14,
        expand=True,
        margin=ft.Margin(16, 6, 16, 0),
    )

    chat_view = ft.Column(
        controls=[chat_frame, quick_actions_strip],
        spacing=0, expand=True, visible=True,
    )


    _all_guides    = db_all_guides()
    _all_guides_flat = db_all_guides_flat()
    _guide_state   = {"guide_id": None}

    _CAT_ICONS = {
        "Trauma & First Aid":                           ft.Icons.LOCAL_HOSPITAL,
        "Natural Disasters & Environmental Threats":    ft.Icons.THUNDERSTORM,
        "Resource Scarcity & Wilderness Survival":      ft.Icons.FOREST,
        "Urban Emergencies & Grid Failures":            ft.Icons.LOCATION_CITY,
    }

    guides_back_btn = ft.IconButton(
        icon=ft.Icons.ARROW_BACK_IOS_NEW, icon_color=THEME_ACCENT_SOFT,
        icon_size=18, on_click=lambda e: _show_guides_list(), visible=False,
    )
    guides_title   = ft.Text(
        "Guides", size=18, weight=ft.FontWeight.BOLD, color=THEME_HEADER,
        expand=True, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1,
    )
    guides_ask_btn = ft.OutlinedButton(
        "Ask AI", icon=ft.Icons.CHAT_BUBBLE_OUTLINE, visible=False,
        style=ft.ButtonStyle(
            color=THEME_ACCENT_SOFT, bgcolor=THEME_BUTTON_BG,
            side=ft.BorderSide(1, THEME_BORDER),
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        ),
    )
    guides_body = ft.ListView(expand=True, spacing=0)

    guides_search = ft.TextField(
        hint_text="Search guides...",
        prefix_icon=ft.Icons.SEARCH,
        filled=True, text_size=14,
        bgcolor=THEME_INPUT_BG, border_color=THEME_BORDER,
        focused_border_color=THEME_ACCENT, cursor_color=THEME_ACCENT,
        hint_style=ft.TextStyle(color=THEME_TEXT_SUBTLE, size=13),
        border_radius=20,
        content_padding=ft.Padding.symmetric(horizontal=16, vertical=10),
        on_change=lambda e: _on_guides_search_change(),
        visible=True,
    )

    def _on_guides_search_change() -> None:
        if _guide_state["guide_id"] is not None:
            return
        term = (guides_search.value or "").strip().lower()
        if not term:
            guides_body.controls = _build_guides_list_controls(_all_guides)
        else:
            matched = [
                g for g in _all_guides_flat
                if term in g["title"].lower() or term in g["tags"].lower()
                   or term in g["category"].lower()
            ]
            guides_body.controls = _build_flat_guide_results(matched)
        page.update()

    def _build_flat_guide_results(guides: list) -> list:
        if not guides:
            return [
                ft.Container(
                    content=ft.Text("No guides found.", size=14, color=THEME_TEXT_SUBTLE),
                    padding=ft.Padding.symmetric(horizontal=16, vertical=20),
                )
            ]
        items = []
        for g in guides:
            gid = g["id"]
            items.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ARTICLE_OUTLINED, color=THEME_TEXT_SUBTLE, size=16),
                            ft.Column(
                                controls=[
                                    ft.Text(g["title"], size=14, color=ft.Colors.WHITE,
                                            expand=True, max_lines=2),
                                    ft.Text(g["category"], size=11, color=THEME_TEXT_SUBTLE),
                                ],
                                spacing=1, tight=True, expand=True,
                            ),
                            ft.Icon(ft.Icons.CHEVRON_RIGHT, color=THEME_TEXT_SUBTLE, size=18),
                        ],
                        spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    on_click=lambda e, i=gid: _open_guide(i),
                    padding=ft.Padding(left=16, top=10, right=16, bottom=10),
                    border=ft.Border(bottom=ft.BorderSide(1, THEME_BORDER)),
                    ink=True,
                )
            )
        return items

    def _build_guides_list_controls(cat_dict: dict) -> list:
        items = []
        for cat, gs in cat_dict.items():
            icon = _CAT_ICONS.get(cat, ft.Icons.MENU_BOOK)
            items.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(icon, color=THEME_ACCENT, size=18),
                            ft.Text(cat, size=13, weight=ft.FontWeight.BOLD,
                                    color=THEME_ACCENT, expand=True),
                            ft.Text(str(len(gs)), size=12, color=THEME_TEXT_SUBTLE),
                        ],
                        spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding(left=16, top=14, right=16, bottom=6),
                )
            )
            for g in gs:
                gid = g["id"]
                items.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.ARTICLE_OUTLINED, color=THEME_TEXT_SUBTLE, size=16),
                                ft.Text(g["title"], size=14, color=ft.Colors.WHITE,
                                        expand=True, max_lines=2),
                                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=THEME_TEXT_SUBTLE, size=18),
                            ],
                            spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        on_click=lambda e, i=gid: _open_guide(i),
                        padding=ft.Padding(left=22, top=10, right=16, bottom=10),
                        border=ft.Border(bottom=ft.BorderSide(1, THEME_BORDER)),
                        ink=True,
                    )
                )
        return items

    def _show_guides_list() -> None:
        guides_body.controls = _build_guides_list_controls(_all_guides)
        guides_title.value       = "Guides"
        guides_back_btn.visible  = False
        guides_ask_btn.visible   = False
        guides_search.visible    = True
        guides_search.value      = ""
        _guide_state["guide_id"] = None
        page.update()

    def _open_guide(guide_id: int) -> None:
        result = db_guide(guide_id)
        if not result:
            return
        title, content = result
        _guide_state["guide_id"] = guide_id
        guides_title.value       = title
        guides_back_btn.visible  = True
        guides_ask_btn.visible   = True
        guides_ask_btn.on_click  = lambda e: _ask_ai_about(title)
        guides_search.visible    = False
        guides_body.controls = [
            ft.Container(
                content=ft.Text(content, size=CHAT_TEXT_SIZE, color=ft.Colors.WHITE,
                                selectable=True),
                padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            )
        ]
        page.update()

    def _ask_ai_about(title: str) -> None:
        switch_tab("chat")
        search_bar.value = f"Key survival steps for: {title}"
        on_search_click(None)

    guides_body.controls = _build_guides_list_controls(_all_guides)

    guides_view = ft.Column(
        controls=[
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Row(
                            controls=[guides_back_btn, guides_title],
                            spacing=4, expand=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        guides_ask_btn,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding(left=16, top=10, right=16, bottom=6),
            ),
            ft.Container(
                content=guides_search,
                padding=ft.Padding.symmetric(horizontal=12, vertical=4),
            ),
            ft.Divider(color=THEME_BORDER, height=1, thickness=1),
            guides_body,
        ],
        spacing=0, expand=True, visible=False,
    )


    _stab: dict = {"tab": "themes"}

    _settings_tab_body = ft.ListView(controls=[], spacing=6, height=300, expand=False)

    _stab_themes = ft.Container(
        content=ft.Text("Themes", size=14, weight=ft.FontWeight.W_600, color=THEME_ACCENT),
        padding=ft.Padding.symmetric(horizontal=6, vertical=8),
        border=ft.Border(bottom=ft.BorderSide(2, THEME_ACCENT)),
        on_click=lambda e: _switch_stab("themes"),
    )
    _stab_sizes = ft.Container(
        content=ft.Text("Text Size", size=14, weight=ft.FontWeight.W_500, color=THEME_TEXT_SUBTLE),
        padding=ft.Padding.symmetric(horizontal=6, vertical=8),
        border=ft.Border(bottom=ft.BorderSide(0, ft.Colors.TRANSPARENT)),
        on_click=lambda e: _switch_stab("text_size"),
    )
    _stab_about = ft.Container(
        content=ft.Text("About", size=14, weight=ft.FontWeight.W_500, color=THEME_TEXT_SUBTLE),
        padding=ft.Padding.symmetric(horizontal=6, vertical=8),
        border=ft.Border(bottom=ft.BorderSide(0, ft.Colors.TRANSPARENT)),
        on_click=lambda e: _switch_stab("about"),
    )

    def _make_theme_items() -> list:
        out = []
        for name, t in THEMES.items():
            active = name == current_theme_name
            out.append(ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Container(width=22, height=22, bgcolor=t["accent"], border_radius=11),
                        ft.Text(name, size=15, expand=True,
                                color=THEME_ACCENT if active else ft.Colors.WHITE,
                                weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400),
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=THEME_ACCENT, size=18)
                        if active else ft.Container(width=18),
                    ],
                    spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                on_click=lambda e, n=name: on_theme_select(n),
                padding=ft.Padding.symmetric(horizontal=12, vertical=11),
                border_radius=10,
                border=ft.Border.all(1.5 if active else 1,
                                     THEME_ACCENT if active else THEME_BORDER),
                bgcolor=THEME_BUTTON_BG,
            ))
        return out

    def _make_size_items() -> list:
        out = []
        for name, val in TEXT_SIZES.items():
            active = name == current_text_size_name
            out.append(ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text("Aa", size=val, color=THEME_ACCENT if active else THEME_TEXT_SUBTLE,
                                weight=ft.FontWeight.W_600),
                        ft.Text(f"{name}  ·  {val}px", size=15, expand=True,
                                color=THEME_ACCENT if active else ft.Colors.WHITE,
                                weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400),
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=THEME_ACCENT, size=18)
                        if active else ft.Container(width=18),
                    ],
                    spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                on_click=lambda e, n=name: on_size_select(n),
                padding=ft.Padding.symmetric(horizontal=12, vertical=11),
                border_radius=10,
                border=ft.Border.all(1.5 if active else 1,
                                     THEME_ACCENT if active else THEME_BORDER),
                bgcolor=THEME_BUTTON_BG,
            ))
        return out

    def _make_about_items() -> list:
        def _export_chat(e) -> None:
            if not chat_history:
                show_snack("No conversation to export.")
                return
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = _app_dir / f"SurvivAI_chat_{ts}.txt"
            try:
                lines = ["SurvivAI – Emergency Chat Export",
                         f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                         "=" * 48, ""]
                for m in chat_history:
                    role = "You" if m["role"] == "user" else "SurvivAI"
                    lines += [f"{role}:", m["content"], ""]
                path.write_text("\n".join(lines), encoding="utf-8")
                show_snack(f"Saved: {path.name}")
            except Exception as ex:
                show_snack(f"Export failed: {ex}")

        def _clear_session(e) -> None:
            on_new_chat_click(None)
            show_snack("Session cleared.")

        return [
            ft.Container(
                content=ft.Column([
                    ft.Text("SurvivAI", size=18, weight=ft.FontWeight.BOLD, color=THEME_HEADER),
                    ft.Text("Version 1.1  ·  Offline Emergency AI",
                            size=13, color=ft.Colors.WHITE),
                    ft.Text("Model: Phi-3 Mini 4K Instruct (Q4, ~2.4 GB)",
                            size=13, color=THEME_TEXT_SUBTLE),
                    ft.Text("Data: curated survival guides  ·  4 categories",
                            size=13, color=THEME_TEXT_SUBTLE),
                    ft.Container(height=6),
                    ft.Text(
                        "Not a substitute for professional medical advice.\n"
                        "Use only when professional help is unavailable.",
                        size=12, color=ft.Colors.AMBER_300,
                    ),
                    ft.Container(height=10),
                    ft.Row([
                        ft.ElevatedButton(
                            "Export Chat", icon=ft.Icons.DOWNLOAD,
                            on_click=_export_chat,
                            style=ft.ButtonStyle(
                                bgcolor=THEME_BUTTON_BG, color=THEME_ACCENT_SOFT,
                                side=ft.BorderSide(1, THEME_BORDER),
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                        ),
                        ft.ElevatedButton(
                            "Clear Session", icon=ft.Icons.DELETE_OUTLINE,
                            on_click=_clear_session,
                            style=ft.ButtonStyle(
                                bgcolor=THEME_BUTTON_BG, color=ft.Colors.RED_300,
                                side=ft.BorderSide(1, THEME_BORDER),
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                        ),
                    ], spacing=10, wrap=True),
                ], spacing=6, tight=True),
                padding=ft.Padding.symmetric(horizontal=4, vertical=4),
            )
        ]

    def _apply_stab_state(tab_name: str) -> None:
        _stab["tab"] = tab_name
        for btn, name in [(_stab_themes, "themes"), (_stab_sizes, "text_size"), (_stab_about, "about")]:
            active = name == tab_name
            label  = {"themes": "Themes", "text_size": "Text Size", "about": "About"}[name]
            btn.content = ft.Text(label, size=14,
                                  weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_500,
                                  color=THEME_ACCENT if active else THEME_TEXT_SUBTLE)
            btn.border  = ft.Border(bottom=ft.BorderSide(2 if active else 0,
                                    THEME_ACCENT if active else ft.Colors.TRANSPARENT))
        if tab_name == "themes":
            _settings_tab_body.controls = _make_theme_items()
        elif tab_name == "text_size":
            _settings_tab_body.controls = _make_size_items()
        else:
            _settings_tab_body.controls = _make_about_items()

    def _switch_stab(tab_name: str) -> None:
        _apply_stab_state(tab_name)
        page.update()

    _settings_sheet = ft.Container(
        bgcolor=THEME_SURFACE,
        border_radius=ft.BorderRadius(top_left=20, top_right=20, bottom_left=0, bottom_right=0),
        padding=ft.Padding.only(left=20, right=20, top=12, bottom=36),
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(width=38, height=4, bgcolor=THEME_BORDER, border_radius=2)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=10),
                ft.Row(
                    controls=[
                        ft.Text("Settings", size=18, weight=ft.FontWeight.BOLD, color=THEME_HEADER),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE, icon_color=THEME_TEXT_SUBTLE, icon_size=20,
                            on_click=lambda e: close_settings(),
                            style=ft.ButtonStyle(
                                overlay_color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
                                padding=ft.Padding.all(4),
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(controls=[_stab_themes, _stab_sizes, _stab_about], spacing=4),
                ft.Divider(color=THEME_BORDER, height=1, thickness=1),
                _settings_tab_body,
            ],
            spacing=8, tight=True,
        ),
    )

    settings_overlay = ft.Container(
        visible=False, expand=True,
        bgcolor=ft.Colors.with_opacity(0.55, ft.Colors.BLACK),
        padding=0,
        content=ft.Column(
            controls=[
                ft.Container(expand=True, on_click=lambda e: close_settings()),
                _settings_sheet,
            ],
            spacing=0, expand=True,
        ),
    )

    def open_settings() -> None:
        _apply_stab_state(_stab.get("tab", "themes"))
        _settings_sheet.bgcolor = THEME_SURFACE
        settings_overlay.visible = True
        page.update()

    def close_settings() -> None:
        settings_overlay.visible = False
        page.update()

    def on_theme_select(name: str) -> None:
        close_settings()
        apply_theme(name)

    def on_size_select(name: str) -> None:
        close_settings()
        apply_text_size(name)


    def apply_theme(theme_name: str) -> None:
        nonlocal current_theme_name
        nonlocal THEME_BG, THEME_SURFACE, THEME_HEADER, THEME_TEXT_SUBTLE, THEME_BORDER
        nonlocal THEME_ACCENT, THEME_ACCENT_SOFT, THEME_BUTTON_BG, THEME_INPUT_BG
        nonlocal THEME_CHAT_BG, THEME_USER_BUBBLE, THEME_ASSISTANT_BUBBLE

        current_theme_name = theme_name
        t = THEMES[theme_name]
        THEME_BG               = t["bg"]
        THEME_SURFACE          = t["surface"]
        THEME_HEADER           = t["header"]
        THEME_TEXT_SUBTLE      = t["text_subtle"]
        THEME_BORDER           = t["border"]
        THEME_ACCENT           = t["accent"]
        THEME_ACCENT_SOFT      = t["accent_soft"]
        THEME_BUTTON_BG        = t["button_bg"]
        THEME_INPUT_BG         = t["input_bg"]
        THEME_CHAT_BG          = t["chat_bg"]
        THEME_USER_BUBBLE      = t["user_bubble"]
        THEME_ASSISTANT_BUBBLE = t["assistant_bubble"]
        save_settings()

        page.bgcolor             = THEME_BG
        header.color             = THEME_HEADER
        download_status.color    = THEME_TEXT_SUBTLE
        download_progress.color  = THEME_ACCENT
        char_counter.color       = THEME_TEXT_SUBTLE

        search_bar.bgcolor              = THEME_INPUT_BG
        search_bar.border_color         = THEME_BORDER
        search_bar.focused_border_color = THEME_ACCENT
        search_bar.cursor_color         = THEME_ACCENT
        search_bar.hint_style = ft.TextStyle(color=THEME_TEXT_SUBTLE,
                                             size=max(12, CHAT_TEXT_SIZE - 1))

        search_button.style = ft.ButtonStyle(
            shape=ft.CircleBorder(), bgcolor=THEME_ACCENT,
            overlay_color=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
        )
        new_chat_button.style = ft.ButtonStyle(
            color=THEME_ACCENT_SOFT, bgcolor=THEME_BUTTON_BG,
            side=ft.BorderSide(1, THEME_BORDER),
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        )
        settings_button.icon_color = THEME_ACCENT_SOFT
        settings_button.style = ft.ButtonStyle(
            bgcolor=THEME_BUTTON_BG, side=ft.BorderSide(1, THEME_BORDER),
            shape=ft.CircleBorder(),
            overlay_color=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        )
        stop_button.icon_color = THEME_ACCENT_SOFT
        stop_button.bgcolor    = THEME_BUTTON_BG

        chat_frame.bgcolor = THEME_CHAT_BG
        chat_frame.border  = ft.Border.all(1, THEME_BORDER)

        for row in chat_list.controls:
            if isinstance(row, ft.Row) and row.controls:
                bub = row.controls[0]
                if isinstance(bub, ft.Container) and isinstance(bub.content, ft.Text):
                    bub.bgcolor = (THEME_USER_BUBBLE
                                   if row.alignment == ft.MainAxisAlignment.END
                                   else THEME_ASSISTANT_BUBBLE)

        for chip in _qa_chips:
            chip.bgcolor = THEME_BUTTON_BG
            chip.border  = ft.Border.all(1, THEME_BORDER)

        guides_back_btn.icon_color = THEME_ACCENT_SOFT
        guides_title.color         = THEME_HEADER
        guides_ask_btn.style = ft.ButtonStyle(
            color=THEME_ACCENT_SOFT, bgcolor=THEME_BUTTON_BG,
            side=ft.BorderSide(1, THEME_BORDER),
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        )
        guides_search.bgcolor              = THEME_INPUT_BG
        guides_search.border_color         = THEME_BORDER
        guides_search.focused_border_color = THEME_ACCENT
        guides_search.cursor_color         = THEME_ACCENT
        guides_search.hint_style           = ft.TextStyle(color=THEME_TEXT_SUBTLE, size=13)
        guides_body.controls = (
            _build_guides_list_controls(_all_guides)
            if _guide_state["guide_id"] is None
            else guides_body.controls
        )

        bottom_nav.bgcolor = THEME_BG
        bottom_nav.border  = ft.Border(top=ft.BorderSide(1, THEME_BORDER))
        _update_nav()

        page.update()

    def apply_text_size(size_name: str) -> None:
        nonlocal current_text_size_name, CHAT_TEXT_SIZE
        current_text_size_name = size_name
        CHAT_TEXT_SIZE = TEXT_SIZES[size_name]
        save_settings()
        search_bar.text_size  = CHAT_TEXT_SIZE
        search_bar.hint_style = ft.TextStyle(color=THEME_TEXT_SUBTLE,
                                             size=max(12, CHAT_TEXT_SIZE - 1))
        for row in chat_list.controls:
            if isinstance(row, ft.Row) and row.controls:
                bub = row.controls[0]
                if isinstance(bub, ft.Container) and isinstance(bub.content, ft.Text):
                    bub.content.size = CHAT_TEXT_SIZE
        page.update()


    _nav_chat_icon   = ft.Icon(ft.Icons.CHAT_BUBBLE,  color=THEME_ACCENT,      size=22)
    _nav_chat_label  = ft.Text("Chat",   size=11,     color=THEME_ACCENT)
    _nav_guides_icon = ft.Icon(ft.Icons.MENU_BOOK,    color=THEME_TEXT_SUBTLE, size=22)
    _nav_guides_label= ft.Text("Guides", size=11,     color=THEME_TEXT_SUBTLE)

    def _update_nav() -> None:
        is_chat = active_tab["tab"] == "chat"
        _nav_chat_icon.color    = THEME_ACCENT      if is_chat  else THEME_TEXT_SUBTLE
        _nav_chat_label.color   = THEME_ACCENT      if is_chat  else THEME_TEXT_SUBTLE
        _nav_guides_icon.color  = THEME_ACCENT      if not is_chat else THEME_TEXT_SUBTLE
        _nav_guides_label.color = THEME_ACCENT      if not is_chat else THEME_TEXT_SUBTLE

    def switch_tab(tab_name: str) -> None:
        active_tab["tab"]    = tab_name
        is_chat              = tab_name == "chat"
        chat_view.visible    = is_chat
        guides_view.visible  = not is_chat
        input_row.visible    = is_chat
        _update_nav()
        page.update()

    _nav_chat_btn = ft.Container(
        content=ft.Column(
            controls=[_nav_chat_icon, _nav_chat_label],
            spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True,
        ),
        expand=True, on_click=lambda e: switch_tab("chat"),
        padding=ft.Padding.symmetric(vertical=10),
    )
    _nav_guides_btn = ft.Container(
        content=ft.Column(
            controls=[_nav_guides_icon, _nav_guides_label],
            spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True,
        ),
        expand=True, on_click=lambda e: switch_tab("guides"),
        padding=ft.Padding.symmetric(vertical=10),
    )
    bottom_nav = ft.Container(
        content=ft.Row(controls=[_nav_chat_btn, _nav_guides_btn], spacing=0),
        bgcolor=THEME_BG,
        border=ft.Border(top=ft.BorderSide(1, THEME_BORDER)),
    )


    input_row = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[search_bar, stop_button, search_button],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
                ft.Row(controls=[char_counter],
                       alignment=ft.MainAxisAlignment.END),
            ],
            spacing=2, tight=True,
        ),
        padding=ft.Padding.only(left=16, right=16, top=8, bottom=6),
        visible=True,
    )


    header_section = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Column(
                            controls=[header, status_badge],
                            spacing=3, tight=True,
                        ),
                        ft.Row(
                            controls=[settings_button, new_chat_button],
                            spacing=8, tight=True,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                download_status,
                download_progress,
            ],
            spacing=4, tight=True,
        ),
        padding=ft.Padding.only(left=16, right=16, top=14, bottom=4),
    )


    main_layout = ft.Column(
        controls=[
            header_section,
            chat_view,
            guides_view,
            input_row,
            bottom_nav,
        ],
        spacing=0, expand=True,
    )

    page.add(
        ft.Stack(
            controls=[
                ft.SafeArea(main_layout, expand=True),
                settings_overlay,
            ],
            expand=True,
        )
    )


    def on_resize(e) -> None:
        w = bubble_width()
        for row in chat_list.controls:
            if isinstance(row, ft.Row) and row.controls:
                bub = row.controls[0]
                if isinstance(bub, ft.Container) and isinstance(bub.content, ft.Text):
                    if bub.width is not None:
                        bub.width = w
        page.update()

    page.on_resize = on_resize


    def on_keyboard(e: ft.KeyboardEvent) -> None:
        if e.key in ("GoBack", "Escape", "Browser Back"):
            if settings_overlay.visible:
                close_settings()
            elif active_tab["tab"] == "guides" and _guide_state["guide_id"] is not None:
                _show_guides_list()
            elif active_tab["tab"] == "guides":
                switch_tab("chat")

    page.on_keyboard_event = on_keyboard


    restore_session()


if __name__ == "__main__":
    ft.run(main)
