import flet as ft
import sqlite3
import asyncio
import queue
import json
from pathlib import Path
from aiengine import ask_ai, ensure_model_ready

def search_database(query):
    try:
        conn = sqlite3.connect("survival_data.db")
        cursor = conn.cursor()
        search_term = f"%{query}%"
        cursor.execute("SELECT title, content FROM guides WHERE title LIKE ? OR tags LIKE ? LIMIT 1", (search_term, search_term))
        result = cursor.fetchone()
        conn.close()
        return result
    except Exception as e:
        return ("Error", str(e))

def main(page: ft.Page):
    SETTINGS_PATH = Path("user_settings.json")

    THEMES = {
        "Default": {
            "bg": ft.Colors.BLACK,
            "header": ft.Colors.RED_400,
            "text_subtle": ft.Colors.GREY_500,
            "border": ft.Colors.GREY_800,
            "accent": ft.Colors.RED_400,
            "accent_soft": ft.Colors.RED_300,
            "button_bg": ft.Colors.with_opacity(0.15, ft.Colors.RED_900),
            "input_bg": ft.Colors.with_opacity(0.18, ft.Colors.GREY_900),
            "chat_bg": ft.Colors.with_opacity(0.12, ft.Colors.GREY_900),
            "user_bubble": ft.Colors.with_opacity(0.78, ft.Colors.RED_500),
            "assistant_bubble": ft.Colors.with_opacity(0.36, ft.Colors.BLUE_GREY_800),
        },
        "Default Soft": {
            "bg": ft.Colors.BLACK,
            "header": ft.Colors.RED_300,
            "text_subtle": ft.Colors.GREY_400,
            "border": ft.Colors.GREY_700,
            "accent": ft.Colors.RED_300,
            "accent_soft": ft.Colors.RED_200,
            "button_bg": ft.Colors.with_opacity(0.14, ft.Colors.RED_900),
            "input_bg": ft.Colors.with_opacity(0.16, ft.Colors.GREY_900),
            "chat_bg": ft.Colors.with_opacity(0.10, ft.Colors.GREY_900),
            "user_bubble": ft.Colors.with_opacity(0.68, ft.Colors.RED_400),
            "assistant_bubble": ft.Colors.with_opacity(0.30, ft.Colors.BLUE_GREY_800),
        },
        "Default Carbon": {
            "bg": ft.Colors.BLACK,
            "header": ft.Colors.RED_500,
            "text_subtle": ft.Colors.GREY_500,
            "border": ft.Colors.BLUE_GREY_800,
            "accent": ft.Colors.RED_500,
            "accent_soft": ft.Colors.RED_300,
            "button_bg": ft.Colors.with_opacity(0.12, ft.Colors.RED_900),
            "input_bg": ft.Colors.with_opacity(0.20, ft.Colors.BLUE_GREY_900),
            "chat_bg": ft.Colors.with_opacity(0.10, ft.Colors.BLUE_GREY_900),
            "user_bubble": ft.Colors.with_opacity(0.74, ft.Colors.RED_600),
            "assistant_bubble": ft.Colors.with_opacity(0.34, ft.Colors.BLUE_GREY_900),
        },
        "Default Glow": {
            "bg": ft.Colors.BLACK,
            "header": ft.Colors.RED_300,
            "text_subtle": ft.Colors.with_opacity(0.86, ft.Colors.RED_100),
            "border": ft.Colors.RED_700,
            "accent": ft.Colors.RED_300,
            "accent_soft": ft.Colors.RED_200,
            "button_bg": ft.Colors.with_opacity(0.16, ft.Colors.RED_900),
            "input_bg": ft.Colors.with_opacity(0.20, ft.Colors.RED_900),
            "chat_bg": ft.Colors.with_opacity(0.11, ft.Colors.RED_900),
            "user_bubble": ft.Colors.with_opacity(0.70, ft.Colors.RED_400),
            "assistant_bubble": ft.Colors.with_opacity(0.34, ft.Colors.BLUE_GREY_800),
        },
        "Forest": {
            "bg": ft.Colors.BLACK,
            "header": ft.Colors.GREEN_400,
            "text_subtle": ft.Colors.with_opacity(0.82, ft.Colors.GREEN_200),
            "border": ft.Colors.GREEN_700,
            "accent": ft.Colors.GREEN_400,
            "accent_soft": ft.Colors.GREEN_300,
            "button_bg": ft.Colors.with_opacity(0.15, ft.Colors.GREEN_900),
            "input_bg": ft.Colors.with_opacity(0.18, ft.Colors.GREEN_900),
            "chat_bg": ft.Colors.with_opacity(0.14, ft.Colors.GREEN_900),
            "user_bubble": ft.Colors.with_opacity(0.75, ft.Colors.GREEN_500),
            "assistant_bubble": ft.Colors.with_opacity(0.36, ft.Colors.GREEN_900),
        },
        "Ocean": {
            "bg": ft.Colors.BLUE_GREY_900,
            "header": ft.Colors.CYAN_300,
            "text_subtle": ft.Colors.with_opacity(0.84, ft.Colors.CYAN_100),
            "border": ft.Colors.CYAN_700,
            "accent": ft.Colors.CYAN_400,
            "accent_soft": ft.Colors.CYAN_200,
            "button_bg": ft.Colors.with_opacity(0.14, ft.Colors.CYAN_900),
            "input_bg": ft.Colors.with_opacity(0.18, ft.Colors.CYAN_900),
            "chat_bg": ft.Colors.with_opacity(0.14, ft.Colors.CYAN_900),
            "user_bubble": ft.Colors.with_opacity(0.74, ft.Colors.CYAN_600),
            "assistant_bubble": ft.Colors.with_opacity(0.34, ft.Colors.BLUE_900),
        },
        "Violet": {
            "bg": ft.Colors.BLUE_GREY_900,
            "header": ft.Colors.DEEP_PURPLE_300,
            "text_subtle": ft.Colors.with_opacity(0.82, ft.Colors.DEEP_PURPLE_100),
            "border": ft.Colors.DEEP_PURPLE_700,
            "accent": ft.Colors.DEEP_PURPLE_400,
            "accent_soft": ft.Colors.DEEP_PURPLE_200,
            "button_bg": ft.Colors.with_opacity(0.14, ft.Colors.DEEP_PURPLE_900),
            "input_bg": ft.Colors.with_opacity(0.18, ft.Colors.DEEP_PURPLE_900),
            "chat_bg": ft.Colors.with_opacity(0.14, ft.Colors.DEEP_PURPLE_900),
            "user_bubble": ft.Colors.with_opacity(0.74, ft.Colors.DEEP_PURPLE_500),
            "assistant_bubble": ft.Colors.with_opacity(0.34, ft.Colors.INDIGO_900),
        },
        "Amber": {
            "bg": ft.Colors.BLACK,
            "header": ft.Colors.AMBER_400,
            "text_subtle": ft.Colors.with_opacity(0.82, ft.Colors.AMBER_200),
            "border": ft.Colors.AMBER_700,
            "accent": ft.Colors.AMBER_400,
            "accent_soft": ft.Colors.AMBER_300,
            "button_bg": ft.Colors.with_opacity(0.14, ft.Colors.AMBER_900),
            "input_bg": ft.Colors.with_opacity(0.18, ft.Colors.AMBER_900),
            "chat_bg": ft.Colors.with_opacity(0.13, ft.Colors.AMBER_900),
            "user_bubble": ft.Colors.with_opacity(0.76, ft.Colors.AMBER_600),
            "assistant_bubble": ft.Colors.with_opacity(0.34, ft.Colors.BROWN_800),
        },
        "Mono": {
            "bg": ft.Colors.BLACK,
            "header": ft.Colors.GREY_300,
            "text_subtle": ft.Colors.GREY_500,
            "border": ft.Colors.GREY_700,
            "accent": ft.Colors.BLUE_GREY_300,
            "accent_soft": ft.Colors.GREY_300,
            "button_bg": ft.Colors.with_opacity(0.14, ft.Colors.GREY_900),
            "input_bg": ft.Colors.with_opacity(0.18, ft.Colors.GREY_900),
            "chat_bg": ft.Colors.with_opacity(0.12, ft.Colors.GREY_900),
            "user_bubble": ft.Colors.with_opacity(0.72, ft.Colors.BLUE_GREY_600),
            "assistant_bubble": ft.Colors.with_opacity(0.32, ft.Colors.GREY_800),
        },
    }

    TEXT_SIZES = {
        "Small": 12,
        "Medium": 14,
        "Large": 16,
        "XL": 18,
        "XXL": 30,
    }

    def load_user_settings():
        if not SETTINGS_PATH.exists():
            return {}
        try:
            with SETTINGS_PATH.open("r", encoding="utf-8") as settings_file:
                data = json.load(settings_file)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    loaded_settings = load_user_settings()
    current_theme_name = loaded_settings.get("theme", "Default")
    if current_theme_name not in THEMES:
        current_theme_name = "Default"

    current_text_size_name = loaded_settings.get("text_size", "Large")
    if current_text_size_name not in TEXT_SIZES:
        current_text_size_name = "Large"

    active_theme = THEMES[current_theme_name]
    CHAT_TEXT_SIZE = TEXT_SIZES[current_text_size_name]

    THEME_BG = active_theme["bg"]
    THEME_HEADER = active_theme["header"]
    THEME_TEXT_SUBTLE = active_theme["text_subtle"]
    THEME_BORDER = active_theme["border"]
    THEME_ACCENT = active_theme["accent"]
    THEME_ACCENT_SOFT = active_theme["accent_soft"]
    THEME_BUTTON_BG = active_theme["button_bg"]
    THEME_INPUT_BG = active_theme["input_bg"]
    THEME_CHAT_BG = active_theme["chat_bg"]
    THEME_USER_BUBBLE = active_theme["user_bubble"]
    THEME_ASSISTANT_BUBBLE = active_theme["assistant_bubble"]

    page.title = "SurvivAI"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = THEME_BG
    page.padding = 20
    chat_history = []
    model_ready = False
    auto_follow_stream = True
    generation_state = {"is_generating": False, "stop_requested": False}

    header = ft.Text("SurvivAI", size=32, weight=ft.FontWeight.BOLD, color=THEME_HEADER)
    subtitle = ft.Text(
        "May be wrong. Not for medical decisions.",
        color=THEME_TEXT_SUBTLE,
        size=11,
    )

    download_status = ft.Text("", color=THEME_TEXT_SUBTLE, size=11, visible=False)
    download_progress = ft.ProgressBar(width=280, value=None, visible=False)

    def on_chat_scroll(e: ft.OnScrollEvent):
        nonlocal auto_follow_stream
        try:
            pixels = float(e.pixels)
            max_extent = float(e.max_scroll_extent)
            auto_follow_stream = (max_extent - pixels) <= 40
        except Exception:
            pass

    chat_list = ft.ListView(
        expand=True,
        spacing=14,
        auto_scroll=False,
        on_scroll=on_chat_scroll,
    )

    async def maybe_scroll_to_bottom(duration=90):
        if auto_follow_stream:
            await chat_list.scroll_to(offset=-1, duration=duration)

    search_bar = ft.TextField(
        hint_text="Describe the situation...",
        prefix_icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
        filled=True,
        text_size=CHAT_TEXT_SIZE,
        bgcolor=THEME_INPUT_BG,
        border_color=THEME_BORDER,
        focused_border_color=THEME_ACCENT,
        cursor_color=THEME_ACCENT,
        hint_style=ft.TextStyle(color=THEME_TEXT_SUBTLE, size=max(11, CHAT_TEXT_SIZE - 1)),
        border_radius=22,
        content_padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        expand=True,
        on_submit=lambda e: on_search_click(None),
    )

    def append_message(text, is_user):
        # Dynamically set width only if the text is long enough to need wrapping
        needs_wrap = len(text) > 35 or "\n" in text

        if is_user:
            content_control = ft.Text(text, selectable=True, size=CHAT_TEXT_SIZE)
        else:
            content_control = ft.Text(
                text,
                selectable=True,
                weight=ft.FontWeight.W_500,
                size=CHAT_TEXT_SIZE,
            )

        bubble = ft.Container(
            content=content_control,
            bgcolor=THEME_USER_BUBBLE if is_user else THEME_ASSISTANT_BUBBLE,
            border_radius=12,
            padding=12,
            width=280 if needs_wrap else None, # MAGIC FIX: Auto-shrinks if None
        )
        row = ft.Row(
            controls=[bubble],
            alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START,
            tight=True,
        )
        chat_list.controls.append(row)
        return bubble.content

    # Notice we now pass status_bubble into process_query
    async def process_query(user_query, ai_status_text, status_bubble):
        nonlocal model_ready
        progress_queue = queue.Queue()
        stream_queue = queue.Queue()
        downloading_shown = False
        generation_state["is_generating"] = True
        generation_state["stop_requested"] = False
        stop_button.disabled = False

        def on_model_progress(downloaded, total):
            progress_queue.put((downloaded, total))

        def on_stream_chunk(text_chunk):
            if generation_state["stop_requested"]:
                return False
            stream_queue.put(text_chunk)
            return True

        try:
            db_task = asyncio.create_task(asyncio.to_thread(search_database, user_query))

            if not model_ready:
                model_task = asyncio.create_task(asyncio.to_thread(ensure_model_ready, on_model_progress))

                while not model_task.done():
                    while not progress_queue.empty():
                        downloaded, total = progress_queue.get_nowait()
                        if not downloading_shown:
                            download_status.visible = True
                            download_progress.visible = True
                            downloading_shown = True
                        if total > 0:
                            ratio = min(1.0, downloaded / total)
                            download_progress.value = ratio
                            download_status.value = f"Downloading offline model... {ratio * 100:.0f}%"
                        else:
                            download_progress.value = None
                            download_status.value = "Downloading offline model..."

                    page.update()
                    await asyncio.sleep(0.15)

                await model_task
                model_ready = True

            db_result = await db_task

            ai_status_text.value = "●"
            page.update()

            if db_result:
                ai_task = asyncio.create_task(
                    asyncio.to_thread(ask_ai, user_query, db_result[1], chat_history, on_stream_chunk)
                )
            else:
                ai_task = asyncio.create_task(
                    asyncio.to_thread(
                        ask_ai,
                        user_query,
                        "No specific data found in offline vault.",
                        chat_history,
                        on_stream_chunk,
                    )
                )

            last_dot_update = asyncio.get_running_loop().time()
            while not ai_task.done():
                if generation_state["stop_requested"]:
                    break

                updated = False
                while not stream_queue.empty():
                    text_chunk = stream_queue.get_nowait()
                    if text_chunk:
                        if ai_status_text.value in {"●", "●●", "●●●"}:
                            ai_status_text.value = ""
                        ai_status_text.value += text_chunk
                        
                        # DYNAMIC WIDTH LOCK: Once the stream gets long, lock it to 280px so it wraps
                        if status_bubble.width is None and (len(ai_status_text.value) > 35 or "\n" in ai_status_text.value):
                            status_bubble.width = 280
                            
                        updated = True
                if not updated and ai_status_text.value in {"●", "●●", "●●●"}:
                    now = asyncio.get_running_loop().time()
                    if now - last_dot_update >= 0.30:
                        ai_status_text.value = "●" * ((len(ai_status_text.value) // 1) % 3 + 1)
                        last_dot_update = now
                        updated = True
                if updated:
                    await maybe_scroll_to_bottom(duration=80)
                    page.update()
                await asyncio.sleep(0.04)

            if generation_state["stop_requested"]:
                ai_status_text.value = "STOPPED"
                status_bubble.width = None
                try:
                    await ai_task
                except Exception:
                    pass
                chat_history.append({"role": "user", "content": user_query})
                chat_history.append({"role": "assistant", "content": ai_status_text.value})
                await maybe_scroll_to_bottom(duration=120)
                return

            while not stream_queue.empty():
                text_chunk = stream_queue.get_nowait()
                if text_chunk:
                    ai_status_text.value += text_chunk

            # Final check just in case the stream was instant
            if status_bubble.width is None and (len(ai_status_text.value) > 35 or "\n" in ai_status_text.value):
                status_bubble.width = 280

            ai_response = await ai_task

            ai_status_text.value = ai_response.strip()
            await maybe_scroll_to_bottom(duration=120)
            chat_history.append({"role": "user", "content": user_query})
            chat_history.append({"role": "assistant", "content": ai_status_text.value})
        except Exception:
            ai_status_text.value = "Unable to process right now. Please try again."
        finally:
            if downloading_shown:
                download_progress.visible = False
                download_status.visible = False

            search_button.disabled = False
            new_chat_button.disabled = False
            stop_button.visible = False
            stop_button.disabled = False
            generation_state["is_generating"] = False
            generation_state["stop_requested"] = False
            page.update()

    def on_search_click(e):
        nonlocal auto_follow_stream
        if generation_state["is_generating"]:
            return

        user_query = (search_bar.value or "").strip()
        if not user_query:
            return

        auto_follow_stream = True
        page.run_task(search_button.focus)
        append_message(user_query, is_user=True)
        
        # We start the thinking bubble with width=None so it perfectly hugs the single dot
        status_control = ft.Text("●", selectable=True, weight=ft.FontWeight.W_700, size=max(10, CHAT_TEXT_SIZE - 2))
        status_bubble = ft.Container(
            content=status_control,
            bgcolor=THEME_ASSISTANT_BUBBLE,
            border_radius=12,
            padding=12,
            width=None, # Starts small!
        )
        status_row = ft.Row(
            controls=[status_bubble],
            alignment=ft.MainAxisAlignment.START,
            tight=True,
        )
        chat_list.controls.append(status_row)
        status_text = status_control

        search_bar.value = ""
        search_bar.hint_text = "Give more info or ask..."
        search_button.disabled = True
        new_chat_button.disabled = True
        stop_button.visible = True
        stop_button.disabled = False
        page.update()

        # Pass the bubble object into process_query so it can resize it later
        page.run_task(process_query, user_query, status_text, status_bubble)

    def on_new_chat_click(e):
        nonlocal auto_follow_stream
        chat_history.clear()
        chat_list.controls.clear()
        search_bar.value = ""
        search_bar.hint_text = "Describe the situation..."
        auto_follow_stream = True
        page.update()

    def on_stop_click(e):
        if generation_state["is_generating"]:
            generation_state["stop_requested"] = True
            stop_button.disabled = True
            page.update()

    settings_dialog = ft.AlertDialog(modal=False)
    settings_view = "categories"

    def save_user_settings():
        data = {
            "theme": current_theme_name,
            "text_size": current_text_size_name,
        }
        try:
            with SETTINGS_PATH.open("w", encoding="utf-8") as settings_file:
                json.dump(data, settings_file)
        except Exception:
            pass

    def apply_theme(theme_name):
        nonlocal current_theme_name
        nonlocal THEME_BG
        nonlocal THEME_HEADER
        nonlocal THEME_TEXT_SUBTLE
        nonlocal THEME_BORDER
        nonlocal THEME_ACCENT
        nonlocal THEME_ACCENT_SOFT
        nonlocal THEME_BUTTON_BG
        nonlocal THEME_INPUT_BG
        nonlocal THEME_CHAT_BG
        nonlocal THEME_USER_BUBBLE
        nonlocal THEME_ASSISTANT_BUBBLE

        current_theme_name = theme_name
        selected = THEMES[theme_name]
        THEME_BG = selected["bg"]
        THEME_HEADER = selected["header"]
        THEME_TEXT_SUBTLE = selected["text_subtle"]
        THEME_BORDER = selected["border"]
        THEME_ACCENT = selected["accent"]
        THEME_ACCENT_SOFT = selected["accent_soft"]
        THEME_BUTTON_BG = selected["button_bg"]
        THEME_INPUT_BG = selected["input_bg"]
        THEME_CHAT_BG = selected["chat_bg"]
        THEME_USER_BUBBLE = selected["user_bubble"]
        THEME_ASSISTANT_BUBBLE = selected["assistant_bubble"]
        save_user_settings()

        page.bgcolor = THEME_BG
        header.color = THEME_HEADER
        subtitle.color = THEME_TEXT_SUBTLE
        download_status.color = THEME_TEXT_SUBTLE

        search_bar.bgcolor = THEME_INPUT_BG
        search_bar.border_color = THEME_BORDER
        search_bar.focused_border_color = THEME_ACCENT
        search_bar.cursor_color = THEME_ACCENT
        search_bar.hint_style = ft.TextStyle(color=THEME_TEXT_SUBTLE, size=max(11, CHAT_TEXT_SIZE - 1))

        search_button.style = ft.ButtonStyle(
            shape=ft.CircleBorder(),
            bgcolor=THEME_ACCENT,
            color=ft.Colors.WHITE,
        )
        new_chat_button.style = ft.ButtonStyle(
            color=THEME_ACCENT_SOFT,
            bgcolor=THEME_BUTTON_BG,
            side=ft.BorderSide(1, THEME_BORDER),
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        )
        settings_button.icon_color = THEME_ACCENT_SOFT
        settings_button.style = ft.ButtonStyle(
            bgcolor=THEME_BUTTON_BG,
            side=ft.BorderSide(1, THEME_BORDER),
            shape=ft.CircleBorder(),
        )
        stop_button.icon_color = THEME_ACCENT_SOFT
        stop_button.bgcolor = THEME_BUTTON_BG

        chat_frame.bgcolor = THEME_CHAT_BG
        chat_frame.border = ft.Border.all(1, THEME_BORDER)

        for row in chat_list.controls:
            if isinstance(row, ft.Row) and row.controls:
                bubble = row.controls[0]
                if isinstance(bubble, ft.Container):
                    if row.alignment == ft.MainAxisAlignment.END:
                        bubble.bgcolor = THEME_USER_BUBBLE
                    else:
                        bubble.bgcolor = THEME_ASSISTANT_BUBBLE

        page.update()

    def apply_text_size(size_name):
        nonlocal current_text_size_name
        nonlocal CHAT_TEXT_SIZE

        current_text_size_name = size_name
        CHAT_TEXT_SIZE = TEXT_SIZES[size_name]
        save_user_settings()

        search_bar.text_size = CHAT_TEXT_SIZE
        search_bar.hint_style = ft.TextStyle(color=THEME_TEXT_SUBTLE, size=max(11, CHAT_TEXT_SIZE - 1))

        for row in chat_list.controls:
            if isinstance(row, ft.Row) and row.controls:
                bubble = row.controls[0]
                if isinstance(bubble, ft.Container) and isinstance(bubble.content, ft.Text):
                    bubble.content.size = CHAT_TEXT_SIZE

        page.update()

    def close_settings():
        settings_dialog.open = False
        page.update()

    def on_theme_select(theme_name):
        apply_theme(theme_name)
        close_settings()

    def on_text_size_select(size_name):
        apply_text_size(size_name)
        close_settings()

    def show_settings_categories(e=None):
        nonlocal settings_view
        settings_view = "categories"
        render_settings_dialog()

    def show_settings_themes(e=None):
        nonlocal settings_view
        settings_view = "themes"
        render_settings_dialog()

    def show_settings_text_size(e=None):
        nonlocal settings_view
        settings_view = "text_size"
        render_settings_dialog()

    def render_settings_dialog():
        if settings_view == "categories":
            settings_dialog.title = ft.Text("Settings", color=THEME_HEADER)
            settings_dialog.content = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.OutlinedButton(
                            "Themes",
                            icon=ft.Icons.PALETTE,
                            on_click=show_settings_themes,
                            style=ft.ButtonStyle(
                                color=THEME_ACCENT_SOFT,
                                bgcolor=THEME_BUTTON_BG,
                                side=ft.BorderSide(1, THEME_BORDER),
                            ),
                        ),
                        ft.OutlinedButton(
                            "Text Size",
                            icon=ft.Icons.FORMAT_SIZE,
                            on_click=show_settings_text_size,
                            style=ft.ButtonStyle(
                                color=THEME_ACCENT_SOFT,
                                bgcolor=THEME_BUTTON_BG,
                                side=ft.BorderSide(1, THEME_BORDER),
                            ),
                        ),
                    ],
                    tight=True,
                ),
                width=260,
                height=160,
            )
            settings_dialog.actions = [ft.TextButton("Close", on_click=lambda ev: close_settings())]
        elif settings_view == "themes":
            theme_buttons = []
            for theme_name in THEMES:
                theme_buttons.append(
                    ft.OutlinedButton(
                        theme_name,
                        on_click=lambda ev, name=theme_name: on_theme_select(name),
                        style=ft.ButtonStyle(
                            color=THEME_ACCENT_SOFT,
                            bgcolor=THEME_BUTTON_BG,
                            side=ft.BorderSide(1, THEME_BORDER),
                        ),
                    )
                )

            settings_dialog.title = ft.Text("Themes", color=THEME_HEADER)
            settings_dialog.content = ft.Container(
                content=ft.Column(
                    controls=theme_buttons,
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=260,
                height=320,
            )
            settings_dialog.actions = [
                ft.TextButton("Back", on_click=show_settings_categories),
                ft.TextButton("Close", on_click=lambda ev: close_settings()),
            ]
        else:
            size_buttons = []
            for size_name, size_value in TEXT_SIZES.items():
                label = f"{size_name} ({size_value}px)"
                if size_name == "Large":
                    label += " - Default"
                size_buttons.append(
                    ft.OutlinedButton(
                        label,
                        on_click=lambda ev, name=size_name: on_text_size_select(name),
                        style=ft.ButtonStyle(
                            color=THEME_ACCENT_SOFT,
                            bgcolor=THEME_BUTTON_BG,
                            side=ft.BorderSide(1, THEME_BORDER),
                        ),
                    )
                )

            settings_dialog.title = ft.Text("Text Size", color=THEME_HEADER)
            settings_dialog.content = ft.Container(
                content=ft.Column(
                    controls=size_buttons,
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=260,
                height=220,
            )
            settings_dialog.actions = [
                ft.TextButton("Back", on_click=show_settings_categories),
                ft.TextButton("Close", on_click=lambda ev: close_settings()),
            ]

    def open_settings(e):
        show_settings_categories()

        if settings_dialog not in page.overlay:
            page.overlay.append(settings_dialog)
        settings_dialog.open = True
        page.update()

    search_button = ft.Button(
        "",
        icon=ft.Icons.SEND,
        on_click=on_search_click,
        width=46,
        height=46,
        style=ft.ButtonStyle(
            shape=ft.CircleBorder(),
            bgcolor=THEME_ACCENT,
            color=ft.Colors.WHITE,
        ),
    )

    new_chat_button = ft.OutlinedButton(
        "New Chat",
        on_click=on_new_chat_click,
        style=ft.ButtonStyle(
            color=THEME_ACCENT_SOFT,
            bgcolor=THEME_BUTTON_BG,
            side=ft.BorderSide(1, THEME_BORDER),
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        ),
    )

    settings_button = ft.IconButton(
        icon=ft.Icons.SETTINGS,
        icon_size=24,
        icon_color=THEME_ACCENT_SOFT,
        on_click=open_settings,
        width=42,
        height=42,
        style=ft.ButtonStyle(
            bgcolor=THEME_BUTTON_BG,
            side=ft.BorderSide(1, THEME_BORDER),
            shape=ft.CircleBorder(),
        ),
    )

    stop_button = ft.IconButton(
        icon=ft.Icons.STOP_CIRCLE_OUTLINED,
        tooltip="Stop",
        icon_color=THEME_ACCENT_SOFT,
        bgcolor=THEME_BUTTON_BG,
        on_click=on_stop_click,
        visible=False,
    )

    top_row = ft.Row(
        controls=[
            header,
            ft.Row(
                controls=[settings_button, new_chat_button],
                spacing=8,
                tight=True,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.END,
    )

    header_section = ft.Column(
        controls=[top_row, subtitle, download_status, download_progress],
        spacing=2,
    )

    chat_frame = ft.Container(
        content=chat_list,
        bgcolor=THEME_CHAT_BG,
        border=ft.Border.all(1, THEME_BORDER),
        border_radius=12,
        padding=10,
        expand=True,
    )

    main_layout = ft.Column(
        controls=[
            header_section,
            chat_frame,
            ft.Row([search_bar, stop_button, search_button], alignment=ft.MainAxisAlignment.CENTER),
        ],
        spacing=12,
        expand=True,
    )

    page.add(ft.SafeArea(main_layout, expand=True))

if __name__ == "__main__":
    ft.app(target=main)