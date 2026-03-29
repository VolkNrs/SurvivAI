import flet as ft
import sqlite3
import asyncio
import queue
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
    page.title = "SurvivAI"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    chat_history = []
    model_ready = False
    auto_follow_stream = True
    generation_state = {"is_generating": False, "stop_requested": False}

    header = ft.Text("SurvivAI", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
    subtitle = ft.Text(
        "May be wrong. Not for medical decisions.",
        color=ft.Colors.GREY_500,
        size=11,
    )

    download_status = ft.Text("", color=ft.Colors.GREY_400, size=11, visible=False)
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
        border_radius=22,
        content_padding=ft.padding.symmetric(horizontal=16, vertical=14),
        expand=True,
        on_submit=lambda e: on_search_click(None),
    )

    def append_message(text, is_user):
        # Dynamically set width only if the text is long enough to need wrapping
        needs_wrap = len(text) > 35 or "\n" in text

        if is_user:
            content_control = ft.Text(text, selectable=True)
        else:
            content_control = ft.Text(
                text,
                selectable=True,
                weight=ft.FontWeight.W_500,
            )

        bubble = ft.Container(
            content=content_control,
            bgcolor=ft.Colors.RED_400 if is_user else ft.Colors.BLUE_GREY_800,
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
        status_control = ft.Text("●", selectable=True, weight=ft.FontWeight.W_700)
        status_bubble = ft.Container(
            content=status_control,
            bgcolor=ft.Colors.BLUE_GREY_800,
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

    search_button = ft.ElevatedButton(
        "",
        icon=ft.Icons.SEND,
        on_click=on_search_click,
        width=46,
        height=46,
        style=ft.ButtonStyle(
            shape=ft.CircleBorder(),
            bgcolor=ft.Colors.RED_400,
            color=ft.Colors.WHITE,
        ),
    )

    new_chat_button = ft.OutlinedButton(
        "New Chat",
        on_click=on_new_chat_click,
        style=ft.ButtonStyle(
            color=ft.Colors.RED_300,
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.RED_900),
            side=ft.BorderSide(1, ft.Colors.RED_700),
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        ),
    )

    settings_button = ft.IconButton(
        icon=ft.Icons.SETTINGS,
        icon_size=24,
        icon_color=ft.Colors.RED_300,
        on_click=lambda e: None,
        width=42,
        height=42,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.RED_900),
            side=ft.BorderSide(1, ft.Colors.RED_700),
            shape=ft.CircleBorder(),
        ),
    )

    stop_button = ft.IconButton(
        icon=ft.Icons.STOP_CIRCLE_OUTLINED,
        tooltip="Stop",
        icon_color=ft.Colors.RED_300,
        bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.RED_900),
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

    main_layout = ft.Column(
        controls=[
            header_section,
            ft.Container(
                content=chat_list,
                border=ft.border.all(1, ft.Colors.GREY_800),
                border_radius=12,
                padding=10,
                expand=True,
            ),
            ft.Row([search_bar, stop_button, search_button], alignment=ft.MainAxisAlignment.CENTER),
        ],
        spacing=12,
        expand=True,
    )

    page.add(ft.SafeArea(main_layout, expand=True))

if __name__ == "__main__":
    ft.app(target=main)