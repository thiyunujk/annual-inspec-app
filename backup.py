import flet as ft
import os
import shutil
import csv
from datetime import datetime, timedelta, date

from db import (
    init_db,
    load_companies,
    add_company,
    update_company,
    delete_company
)

def main(page: ft.Page):
    page.title = "年次点検管理システム | Annual Inspection Tracker"
    page.window_width = 1200
    page.window_height = 900
    page.padding = 30
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.GREY_50
    db_file = "inspection.db"
    if not os.path.exists(db_file):
        dlg = ft.AlertDialog(
            title=ft.Text("Database Missing | データベースが見つかりません"),
            content=ft.Text("inspection.db not found. Please restore it and restart the app. | inspection.db が見つかりません。復元してアプリを再起動してください。"),
            actions=[ft.TextButton("OK", on_click=lambda e: (setattr(dlg, "open", False), page.update()))],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.add(ft.Text("Database not found. Please restore inspection.db and restart the app. | データベースが見つかりません。inspection.db を復元してアプリを再起動してください。", color=ft.Colors.RED))
        page.update()
        return
    init_db()                   # ✔ once
    companies = load_companies() # ✔ safe


    edit_index = None
    search_text = ""
    sort_by = "next"
    sort_reverse = False
    page.session_notified = False

    def backup_database():
        try:
            db_file = "inspection.db"
            backup_dir = "backups"

            if not os.path.exists(db_file):
                dlg = ft.AlertDialog(
                    title=ft.Text("Backup Failed"),
                    content=ft.Text("Database file not found:\ninspection.db"),
                    actions=[ft.TextButton("OK", on_click=lambda e: close_dialog(dlg))],
                )
                page.overlay.append(dlg)
                dlg.open = True
                page.update()
                return

            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{backup_dir}/inspection_backup_{timestamp}.db"

            shutil.copy2(db_file, backup_file)

            dlg = ft.AlertDialog(
                title=ft.Text("バックアップ完了 | Backup Successful"),
                content=ft.Text(f"バックアップを作成しました:\n{backup_file}"),
                actions=[ft.TextButton("OK", on_click=lambda e: close_dialog(dlg))],
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        except Exception as e:
            dlg = ft.AlertDialog(
                title=ft.Text("エラー | Backup Failed"),
                content=ft.Text(str(e)),
                actions=[ft.TextButton("OK", on_click=lambda e: close_dialog(dlg))],
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()
   
    def close_dialog(dlg):
        dlg.open = False
        page.update()

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

    def export_to_csv():
        try:
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = f"{export_dir}/inspection_export_{timestamp}.csv"

            with open(export_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Company", "Last", "Next", "Status"])
                for c in companies:
                    status_text, _, _ = get_status_info(c["next"])
                    writer.writerow([c["name"], c["done"], c["next"], status_text])

            dlg = ft.AlertDialog(
                title=ft.Text("Export Successful"),
                content=ft.Text(f"CSV exported:\n{export_file}"),
                actions=[ft.TextButton("OK", on_click=lambda e: close_dialog(dlg))],
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()
        except Exception as e:
            dlg = ft.AlertDialog(
                title=ft.Text("Export Failed"),
                content=ft.Text(str(e)),
                actions=[ft.TextButton("OK", on_click=lambda e: close_dialog(dlg))],
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

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
                content=ft.Row([ft.Icon(ft.Icons.EDIT, color=ft.Colors.BLUE, size=18), ft.Text("編集 | Edit", size=12)]),
                on_click=lambda e, tid=this_id: edit_company_by_id(tid)
            )
            delete_btn = ft.TextButton(
                content=ft.Row([ft.Icon(ft.Icons.DELETE, color=ft.Colors.RED, size=18), ft.Text("削除 | Delete", size=12)]),
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
                    ft.TextButton(" ✅ 了解 | Got it", on_click=close_dlg),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            page.overlay.append(alert_dlg)
            alert_dlg.open = True
            page.session_notified = True # Set this so it only pops up once per app start
            
        page.update()

    # ── UI Components & Fixed Alignment ───────────────────────────
    base_col_widths = [250, 150, 150, 180, 220]
    min_col_widths = [200, 120, 120, 140, 180]

    def compute_col_widths():
        available = (page.width or page.window_width or 1200) - (page.padding * 2) - 2
        base_total = sum(base_col_widths)
        widths = []
        for base_w, min_w in zip(base_col_widths, min_col_widths):
            w = int(available * base_w / base_total)
            if w < min_w:
                w = min_w
            widths.append(w)
        return widths

    col_widths = compute_col_widths()

    company_name = ft.TextField(label="会社名 | Company Name", expand=True)
    date_picker = ft.DatePicker(first_date=datetime.now() - timedelta(days=365*5), last_date=datetime.now() + timedelta(days=365*5))
    page.overlay.append(date_picker)
    selected_date_display = ft.Text("未選択 | Not selected", color=ft.Colors.GREY_700, size=13, italic=True)
    
    date_picker.on_change = lambda e: (
        setattr(selected_date_display, "value", (date_picker.value + timedelta(hours=12)).date().strftime("%Y-%m-%d")),
        page.update()
    ) if date_picker.value else None

    header_cells = [
        ft.Container(ft.Text("🏭 会社名 | Company", weight="bold"), width=col_widths[0]),
        ft.Container(ft.Text("🪧 最終点検日 | Last", weight="bold"), width=col_widths[1]),
        ft.Container(ft.Text("📅 次回予定日 | Next", weight="bold"), width=col_widths[2]),
        ft.Container(ft.Text("🚦 状況 | Status", weight="bold"), width=col_widths[3]),
        ft.Container(ft.Text("🛠️ 操作 | Actions", weight="bold"), width=col_widths[4]),
    ]

    header_table = ft.DataTable(
        heading_row_color=ft.Colors.BLUE_GREY_50,
        column_spacing=25,
        columns=[ft.DataColumn(c) for c in header_cells],
    )

    data_col_spacers = [ft.Container(width=w) for w in col_widths]
    data_table = ft.DataTable(
        heading_row_height=0,
        column_spacing=25,
        columns=[ft.DataColumn(c) for c in data_col_spacers]
    )

    def apply_col_widths(widths):
        for i, w in enumerate(widths):
            col_widths[i] = w
            header_cells[i].width = w
            data_col_spacers[i].width = w

    def on_resize(e):
        apply_col_widths(compute_col_widths())
        update_table()
        page.update()

    page.on_resize = on_resize

    main_table_container = ft.Container(
        content=ft.Column(
            [
                header_table,
                ft.Container(
                    content=ft.Column([data_table], scroll=ft.ScrollMode.AUTO),
                    expand=True,
                    bgcolor=ft.Colors.WHITE,
                ),
            ],
            expand=True,
            spacing=0,
        ),
        expand=True,
        bgcolor=ft.Colors.WHITE,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=12,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )

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

    def calculate_next_date(done_date):
        # Rule: next date = same calendar day next year, minus one day.
        try:
            same_day_next_year = done_date.replace(year=done_date.year + 1)
        except ValueError:
            # Handle Feb 29 -> Feb 28 for non-leap years.
            same_day_next_year = done_date.replace(year=done_date.year + 1, day=28)
        return same_day_next_year - timedelta(days=1)

    def add_or_update():
        nonlocal edit_index, companies

        if not company_name.value or not date_picker.value:
            return

        adj = date_picker.value + timedelta(hours=12)
        done_s = adj.date().strftime("%Y-%m-%d")
        next_s = calculate_next_date(adj.date()).strftime("%Y-%m-%d")

        if edit_index is not None:
            cid = companies[edit_index]["id"]
            update_company(cid, company_name.value, done_s, next_s)
            edit_index = None
            add_button.text = "リストに追加 | Add to List"
        else:
            add_company(company_name.value, done_s, next_s)

        company_name.value = ""
        date_picker.value = None
        selected_date_display.value = "未選択 | Not selected"

        companies = load_companies()
        update_table()


    def confirm_delete(tid, nm):
        def on_delete(e):
            nonlocal companies
            delete_company(tid)
            companies = load_companies()
            update_table()
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(" 🚨 削除確認 | Delete Confirmation"),
            content=ft.Text(f"{nm} を削除しますか？ | Delete {nm}?"),
            actions=[
                ft.TextButton(
                    "❌ キャンセル | Cancel",
                    on_click=lambda _: (setattr(dlg, "open", False), page.update())
                ),
                ft.TextButton(
                    "🗑️ 削除 | Delete",
                    on_click=on_delete,
                    style=ft.ButtonStyle(color=ft.Colors.RED),
                ),
            ],
        )        

        page.overlay.append(dlg)
        dlg.open = True
        page.update()


    def edit_company_by_id(tid):
        nonlocal edit_index
        for idx, c in enumerate(companies):
            if c.get("id") == tid:
                edit_index = idx
                company_name.value = c["name"]
                date_picker.value = datetime.strptime(c["done"], "%Y-%m-%d")
                selected_date_display.value = c["done"]
                add_button.text = " 🔄 更新する | Update"
                page.update(); break

    add_button = ft.FilledButton("💾 リストに追加 | Add to List", icon=ft.Icons.ADD, on_click=lambda _: add_or_update())
    export_button = ft.OutlinedButton("Export CSV", icon=ft.Icons.FILE_DOWNLOAD, on_click=lambda _: export_to_csv())
    search_field = ft.TextField(label="検索 | Search", prefix_icon=ft.Icons.SEARCH, expand=True, on_change=lambda e: on_search(e.control.value))
    

    # ── Final Layout (Fine-Tuned) ──────────────────────────────
    # ── Final Layout (Compact & Full Width) ──────────────────────
    page.add(
        ft.Column([
            # 1. Header
            ft.Text(" 🪪 年次点検管理システム | Annual Inspection Management System", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            
            # 2. Input Section
            ft.Container(
                content=ft.Column([
                    # Row 1: Company Name
                    company_name, 
                    
                    # Row 2: Date Picker, Date Display, and Add Button (ALL TOGETHER)
                    ft.Row([
                        ft.OutlinedButton(
                            " 点検日を選択 | Select Date", 
                            icon=ft.Icons.CALENDAR_MONTH, 
                            on_click=lambda _: (setattr(date_picker, "open", True), page.update())
                        ),
                        selected_date_display,
                        add_button,
                        ft.Container(expand=True),
                        export_button,
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
                ft.FilledButton(
                    " 📦 バックアップ | Backup",
                    icon=ft.Icons.BACKUP,
                    on_click=lambda _: backup_database(),
                ),
            ], alignment=ft.MainAxisAlignment.START),
            


            # 4. Main Dashboard (Fills Horizontal and Vertical Space)
            ft.Container(
                content=main_table_container,
                expand=True,
            ),
        ], expand=True, spacing=15)
    )

    update_table()

if __name__ == "__main__":
    ft.run(main)
