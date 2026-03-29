import flet as ft
import sqlite3

# --- 1. Database Function ---
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

    # --- UI Elements ---
    header = ft.Text("SurvivAI", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
    result_title = ft.Text("Search for an emergency", size=20, weight=ft.FontWeight.W_600)
    
    # We use a Column inside the container to allow for long scrolling text if needed
    result_content = ft.Text("Ready to answer", color=ft.Colors.GREY_400)

    # --- Search Logic ---
    def on_search_click(e):
        if not search_bar.value: return
        db_result = search_database(search_bar.value)
        if db_result:
            result_title.value = db_result[0]
            result_content.value = db_result[1]
        else:
            result_title.value = "No Results"
            result_content.value = "No offline data found."
        page.update()

    search_bar = ft.TextField(
        hint_text="e.g. Snake, Water, Earthquake",
        prefix_icon=ft.Icons.SEARCH,
        on_submit=on_search_click,
        filled=True,
        expand=True, 
    )

    # --- Assembly ---
    main_layout = ft.Column(
        controls=[
            # TOP SECTION
            ft.Column([
                header,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                result_title,
                ft.Container(
                    content=ft.Column([result_content], scroll=ft.ScrollMode.AUTO),
                    padding=15,
                    border=ft.border.all(1, ft.Colors.GREY_800),
                    border_radius=10,
                    width=float("inf"),
                ),
            ],
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ), # Allow the top section to grow and stretch controls across width
            
            # BOTTOM SECTION
            ft.Column([
                ft.Row([search_bar]),
                ft.ElevatedButton(
                    "Search",
                    on_click=on_search_click,
                    width=page.width, # Uses the full width of the phone
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        bgcolor=ft.Colors.RED_900,
                        color=ft.Colors.WHITE
                    )
                )
            ])
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        expand=True
    )

    # Wrap in SafeArea to avoid Dynamic Island/Home Indicator
    page.add(ft.SafeArea(main_layout, expand=True))

if __name__ == "__main__":
    ft.app(target=main)