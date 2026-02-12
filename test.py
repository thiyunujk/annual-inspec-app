import flet as ft
import json
import os
from datetime import datetime, timedelta, date

def main(page: ft.Page):
    page.title = "年次点検管理システム | Annual Inspection Tracker"
    page.window_width = 1200
    page.window_height = 900
    page.padding = 30
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.GREY_50

    # State
    companies = []
    edit_index = None
    next_id = 0
    search_text = ""
    sort_by = "next"
    sort_reverse = False
    DB_PATH = "database.json"
    page.session_notified = False

    # ── Persistence ───────────────────────────────────────────────
    def load_data():
        nonlocal companies, next_id
        if os.path.exists(DB_PATH):
            try:
                with open(DB_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    companies = loaded.get("data", [])
                    next_id = loaded.get("next_id", 0)
            except:
                companies = []
        else:
            companies = []

    def save_data():
        nonlocal next_id
        data_to_save = {"data": companies, "next_id": next_id}
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)

    load_data()

    # ── Status Logic (Calendar Month Based) ───────────────────────
    def get_warning_start_date(next_date_obj):
        year = next_date_obj.year
        month = next_date_obj.month - 2
        if month <= 0:
            month += 12
            year -= 1
        return date(year, month, 1)

    def get_status_info(next_str: str):
        today = datetime.now().date()
        next_dt = datetime.strptime(next_str, "%Y-%m-%d").date()
        warning_start = get_warning_start_date(next_dt)

        if today > next_dt:
            return "🚨 期限切れ | Expired", ft.Colors.RED_700, ft.Colors.RED_50
        elif today >= warning_start:
            return "⚠️ 期限間近 | Due Soon", ft.Colors.ORANGE_700, ft.Colors.ORANGE_50
        else:
            return "✅ 正常 | OK", ft.Colors.GREEN_700, ft.Colors.GREEN_50

    # ── Table update ──────────────────────────────────────────────
    def update_table():
        data_table.rows.clear()
        
        # Filtering
        visible_list = [c for c in companies if search_text.lower() in c["name"].lower()]
        
        # Sorting
        if sort_by == "next":
            visible_list.sort(key=lambda c: c["next"], reverse=sort_reverse)
        else:
            visible_list.sort(key=lambda c: c["name"].lower(), reverse=sort_reverse)

        urgent_names = []
        today = datetime.now().date()

        for c in visible_list:
            status_text, status_color, row_bg = get_status_info(c["next"])
            
            # Notification Check
            next_dt = datetime.strptime(c["next"], "%Y-%m-%d").date()
            if today >= get_warning_start_date(next_dt) and today <= next_dt:
                urgent_names.append(c["name"])

            this_id = c.get("id")
            this_name = c.get("name")

            edit_btn = ft.TextButton(
                content=ft.Row([ft.Icon(ft.Icons.EDIT, color=ft.Colors.BLUE, size=18), ft.Text("編集", size=12)]),
                on_click=lambda e, tid=this_id: edit_company_by_id(tid)
            )
            delete_btn = ft.TextButton(
                content=ft.Row([ft.Icon(ft.Icons.DELETE, color=ft.Colors.RED, size=18), ft.Text("削除", size=12)]),
                on_click=lambda e, tid=this_id, nm=this_name: confirm_delete(tid, nm)
            )

            data_table.rows.append(
                ft.DataRow(
                    color=row_bg,
                    cells=[
                        ft.DataCell(ft.Container(ft.Text(c["name"], weight=ft.FontWeight.W_500), width=col_widths[0])),
                        ft.DataCell(ft.Container(ft.Text(c["done"]), width=col_widths[1])),
                        ft.DataCell(ft.Container(ft.Text(c["next"]), width=col_widths[2])),
                        ft.DataCell(ft.Container(ft.Text(status_text, color=status_color, weight=ft.FontWeight.BOLD), width=col_widths[3])),
                        ft.DataCell(ft.Container(ft.Row([edit_btn, delete_btn], spacing=8), width=col_widths[4])),
                    ]
                )
            )

        # ── Trigger Notification ──
        # ── Trigger Notification using Alert Dialog ──
        if urgent_names and not page.session_notified:
            def close_dlg(e):
                alert_dlg.open = False
                page.update()

            alert_dlg = ft.AlertDialog(
                modal=False,
                title=ft.Text("⚠️ 点検リマインダー | Inspection Reminder"),
                content=ft.Text(
                    f"以下の会社の点検期限が2ヶ月以内に迫っています：\n\n"
                    f"{', '.join(urgent_names)}\n\n"
                    "スケジュールを確認してください。"
                ),
                actions=[
                    ft.TextButton("了解 | Got it", on_click=close_dlg),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            page.overlay.append(alert_dlg)
            alert_dlg.open = True
            page.session_notified = True # Set this so it only pops up once per app start
            
        page.update()

    # ── UI Components & Fixed Alignment ───────────────────────────
    col_widths = [250, 150, 150, 180, 220]

    company_name = ft.TextField(label="会社名 | Company Name", expand=True)
    date_picker = ft.DatePicker(first_date=datetime.now() - timedelta(days=365*5), last_date=datetime.now() + timedelta(days=365*5))
    page.overlay.append(date_picker)
    selected_date_display = ft.Text("未選択 | Not selected", color=ft.Colors.GREY_700, size=13, italic=True)
    
    date_picker.on_change = lambda e: (
        setattr(selected_date_display, "value", (date_picker.value + timedelta(hours=12)).date().strftime("%Y-%m-%d")),
        page.update()
    ) if date_picker.value else None

    header_table = ft.DataTable(
        heading_row_color=ft.Colors.BLUE_GREY_50,
        column_spacing=25,
        columns=[
            ft.DataColumn(ft.Container(ft.Text("会社名 | Company", weight="bold"), width=col_widths[0])),
            ft.DataColumn(ft.Container(ft.Text("最終点検日 | Last", weight="bold"), width=col_widths[1])),
            ft.DataColumn(ft.Container(ft.Text("次回予定日 | Next", weight="bold"), width=col_widths[2])),
            ft.DataColumn(ft.Container(ft.Text("状況 | Status", weight="bold"), width=col_widths[3])),
            ft.DataColumn(ft.Container(ft.Text("操作 | Actions", weight="bold"), width=col_widths[4])),
        ],
    )

    data_table = ft.DataTable(
        heading_row_height=0,
        column_spacing=25,
        columns=[ft.DataColumn(ft.Container(width=w)) for w in col_widths]
    )

    main_table_container = ft.Column([
        header_table,
        ft.Container(
            content=ft.Column([data_table], scroll=ft.ScrollMode.AUTO),
            expand=True, border=ft.border.all(1, ft.Colors.GREY_300), bgcolor=ft.Colors.WHITE,
        )
    ], expand=True, spacing=0)

    # ── Logic Actions ─────────────────────────────────────────────
    def on_search(val):
        nonlocal search_text
        search_text = val
        update_table()

    def toggle_sort(key):
        nonlocal sort_by, sort_reverse
        if sort_by == key:
            sort_reverse = not sort_reverse
        else:
            sort_by = key
            sort_reverse = False
        update_table()

    def add_or_update():
        nonlocal edit_index, next_id
        if not company_name.value or not date_picker.value: return
        adj = date_picker.value + timedelta(hours=12)
        done_s = adj.date().strftime("%Y-%m-%d")
        next_s = (adj.date() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        if edit_index is not None:
            companies[edit_index].update({"name": company_name.value, "done": done_s, "next": next_s})
            edit_index = None
            add_button.text = "リストに追加 | Add to List"
        else:
            companies.append({"id": next_id, "name": company_name.value, "done": done_s, "next": next_s})
            next_id += 1
        
        company_name.value = ""
        date_picker.value = None
        selected_date_display.value = "未選択 | Not selected"
        save_data(); update_table()

    def confirm_delete(tid, nm):
        def on_delete(e):
            nonlocal companies
            companies = [c for c in companies if c.get("id") != tid]
            save_data(); update_table(); dlg.open = False; page.update()
        dlg = ft.AlertDialog(
            title=ft.Text("削除確認 | Delete Confirmation"), 
            content=ft.Text(f"{nm} を削除しますか？ | Delete {nm}?"),
            actions=[ft.TextButton("キャンセル | Cancel", on_click=lambda _: (setattr(dlg, "open", False), page.update())),
                     ft.TextButton("削除 | Delete", on_click=on_delete, style=ft.ButtonStyle(color=ft.Colors.RED))]
        )
        page.overlay.append(dlg); dlg.open = True; page.update()

    def edit_company_by_id(tid):
        nonlocal edit_index
        for idx, c in enumerate(companies):
            if c.get("id") == tid:
                edit_index = idx
                company_name.value = c["name"]
                date_picker.value = datetime.strptime(c["done"], "%Y-%m-%d")
                selected_date_display.value = c["done"]
                add_button.text = "更新する | Update"
                page.update(); break

    add_button = ft.FilledButton("リストに追加 | Add to List", icon=ft.Icons.ADD, on_click=lambda _: add_or_update())
    search_field = ft.TextField(label="検索 | Search", prefix_icon=ft.Icons.SEARCH, expand=True, on_change=lambda e: on_search(e.control.value))

    # ── Final Layout (Fine-Tuned) ──────────────────────────────
    # ── Final Layout (Compact & Full Width) ──────────────────────
    page.add(
        ft.Column([
            # 1. Header
            ft.Text("年次点検管理システム | Annual Inspection Management System", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            
            # 2. Input Section
            ft.Container(
                content=ft.Column([
                    # Row 1: Company Name
                    company_name, 
                    
                    # Row 2: Date Picker, Date Display, and Add Button (ALL TOGETHER)
                    ft.Row([
                        ft.OutlinedButton(
                            "点検日を選択", 
                            icon=ft.Icons.CALENDAR_MONTH, 
                            on_click=lambda _: (setattr(date_picker, "open", True), page.update())
                        ),
                        selected_date_display,
                        ft.VerticalDivider(width=10, color=ft.Colors.TRANSPARENT), # Small gap
                        add_button, # Now sitting right next to the date text
                    ], alignment=ft.MainAxisAlignment.START), # Aligns everything to the left
                ], spacing=10),
                padding=ft.padding.only(bottom=10)
            ),
            
            ft.Divider(height=1, color=ft.Colors.GREY_300),
            
            # 3. Search & Sort Controls
            ft.Row([
                search_field,
                ft.TextButton("日付順 | Date Sort", icon=ft.Icons.SORT, on_click=lambda _: toggle_sort("next")),
                ft.TextButton("名前順 | Name Sort", icon=ft.Icons.SORT_BY_ALPHA, on_click=lambda _: toggle_sort("name")),
            ], alignment=ft.MainAxisAlignment.START),
            
            # 4. Main Dashboard (Fills Horizontal and Vertical Space)
            ft.Container(
                content=main_table_container,
                expand=True,
                # Force the container to take the full width of the page
                width=page.window_width 
            ),
        ], expand=True, spacing=15)
    )

    update_table()

if __name__ == "__main__":
    ft.run(main)