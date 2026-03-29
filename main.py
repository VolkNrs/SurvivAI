import flet as ft
import sqlite3
import asyncio
from aiengine import ask_ai

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

    header = ft.Text("SurvivAI", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
    subtitle = ft.Text(
        "May be wrong. Not for medical decisions.",
        color=ft.Colors.GREY_500,
        size=11,
    )

    chat_list = ft.ListView(expand=True, spacing=10, auto_scroll=True)

    search_bar = ft.TextField(
        hint_text="Ask a survival question...",
        prefix_icon=ft.Icons.SEARCH,
        filled=True,
        expand=True,
    )

    def append_message(text, is_user):
        bubble = ft.Container(
            content=ft.Text(text, selectable=True),
            bgcolor=ft.Colors.RED_400 if is_user else ft.Colors.BLUE_GREY_800,
            border_radius=12,
            padding=12,
            width=340,
        )
        row = ft.Row(
            controls=[bubble],
            alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START,
        )
        chat_list.controls.append(row)
        return bubble.content

    async def process_query(user_query, ai_status_text):
        db_result = await asyncio.to_thread(search_database, user_query)

        if db_result:
            ai_response = await asyncio.to_thread(ask_ai, user_query, db_result[1], chat_history)
        else:
            ai_response = await asyncio.to_thread(
                ask_ai,
                user_query,
                "No specific data found in offline vault.",
                chat_history,
            )

        ai_status_text.value = ai_response.strip()
        chat_history.append({"role": "user", "content": user_query})
        chat_history.append({"role": "assistant", "content": ai_status_text.value})
        search_button.disabled = False
        new_chat_button.disabled = False
        page.update()

    def on_search_click(e):
        user_query = (search_bar.value or "").strip()
        if not user_query:
            return

        page.run_task(search_button.focus)
        append_message(user_query, is_user=True)
        status_text = append_message("SurvivAI is thinking...", is_user=False)

        search_bar.value = ""
        search_bar.hint_text = "Give more info or ask"
        search_button.disabled = True
        new_chat_button.disabled = True
        page.update()

        page.run_task(process_query, user_query, status_text)

    def on_new_chat_click(e):
        chat_history.clear()
        chat_list.controls.clear()
        search_bar.value = ""
        search_bar.hint_text = "Ask a survival question..."
        page.update()

    search_button = ft.ElevatedButton(
        "Send",
        on_click=on_search_click,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            bgcolor=ft.Colors.RED_900,
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

    top_row = ft.Row(
        controls=[header, new_chat_button],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.END,
    )

    header_section = ft.Column(
        controls=[top_row, subtitle],
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
            ft.Row([search_bar, search_button], alignment=ft.MainAxisAlignment.CENTER),
        ],
        spacing=12,
        expand=True,
    )

    page.add(ft.SafeArea(main_layout, expand=True))

if __name__ == "__main__":
    ft.app(target=main)