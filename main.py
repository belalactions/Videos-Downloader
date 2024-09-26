import flet as ft
import yt_dlp
import os
import asyncio
import sqlite3
import webbrowser

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect("theme_settings.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            theme_mode TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL,
            filename TEXT NOT NULL,
            filetype TEXT NOT NULL
        )
    ''')
    # Insert default theme mode if none exists
    cursor.execute('SELECT COUNT(*) FROM settings')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO settings (theme_mode) VALUES ('system')")
    conn.commit()
    conn.close()

# Function to get the current theme mode from the database
def get_theme_settings():
    conn = sqlite3.connect("theme_settings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT theme_mode FROM settings WHERE id = 1")
    settings = cursor.fetchone()
    conn.close()
    return settings[0] if settings else "system"

# Function to set the theme mode in the database
def set_theme_settings(mode):
    conn = sqlite3.connect("theme_settings.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET theme_mode = ? WHERE id = 1", (mode,))
    conn.commit()
    conn.close()

# Function to apply theme based on mode
def apply_theme(page, theme_mode):
    page.theme_mode = {
        "light": ft.ThemeMode.LIGHT,
        "dark": ft.ThemeMode.DARK,
        "system": ft.ThemeMode.SYSTEM
    }.get(theme_mode, ft.ThemeMode.SYSTEM)
    
    page.update()

# Function to handle radio button selection for theme mode
def on_theme_change(e, page):
    theme_mode = e.control.value
    set_theme_settings(theme_mode)  # Save the selected theme mode to the database
    apply_theme(page, theme_mode)

# Function to handle navigation clicks
def on_nav_click(e, page):
    if e.control.selected_index == 0:
        page.go("/")  # Go to home view
    elif e.control.selected_index == 1:
        page.go("/downloads")  # Go to downloads view
    elif e.control.selected_index == 2:
        page.go("/settings")  # Go to settings view
    page.update()

# Function to handle back button click
def on_back_click(e, page):
    page.go("/")  # Go back to home view
    page.update()

# Function to add download info to the database
def add_download_to_db(url, filename, filetype):
    conn = sqlite3.connect("theme_settings.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO downloads (url, filename, filetype) VALUES (?, ?, ?)", (url, filename, filetype))
    conn.commit()
    conn.close()

# Function to retrieve all downloads from the database
def get_all_downloads():
    conn = sqlite3.connect("theme_settings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, url, filename, filetype FROM downloads ORDER BY id DESC")
    downloads = cursor.fetchall()
    conn.close()
    return downloads

# Function to delete a download from the database
def delete_download_from_db(download_id, page):
    conn = sqlite3.connect("theme_settings.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
    conn.commit()
    conn.close()
    page.update()
    page.go("/")
    page.go("/downloads")

# Function to open the downloaded file
def open_file(filename):
    file_path = os.path.join(os.path.expanduser("~"), "Downloads", filename)
    if os.path.exists(file_path):
        webbrowser.open(f"file://{file_path}")  # Open the file using the default system application

# Function to handle video downloading with proper resolution format
def download_video(url, resolution, page, progress_bar, status_label):
    if resolution == "Best Available":
        ydl_format = "best"
    else:
        ydl_format = f"bestvideo[height={resolution}]+bestaudio/best"

    ydl_opts = {
        'format': ydl_format,
        'outtmpl': os.path.join(os.path.expanduser("~"), "Downloads", '%(title)s.%(ext)s'),
        'progress_hooks': [lambda d: asyncio.run(update_progress(d, page, progress_bar, status_label))],
    }

    try:
        status_label.value = "Downloading... 0%"
        page.update()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            add_download_to_db(url, filename, "video")  # Store download in DB
        status_label.value = "Download Completed 100%"
        progress_bar.value = 1.0
        page.update()
    except Exception as e:
        status_label.value = f"Error: {str(e)}"
        page.update()

# Function to update progress during download
async def update_progress(d, page, progress_bar, status_label):
    if d['status'] == 'downloading':
        percent = int(float(d.get('downloaded_bytes', 0)) / float(d.get('total_bytes', 1)) * 100)
        progress_bar.value = float(d.get('downloaded_bytes', 0)) / float(d.get('total_bytes', 1))
        status_label.value = f"Downloading... {percent}%"
    elif d['status'] == 'finished':
        progress_bar.value = 1.0
        status_label.value = "Download Completed 100%"
    page.update()
# Function to handle audio-only downloading
def download_audio(url, page, progress_bar, status_label):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(os.path.expanduser("~"), "Downloads", '%(title)s.%(ext)s'),
        'progress_hooks': [lambda d: asyncio.run(update_progress(d, page, progress_bar, status_label))],
    }

    try:
        status_label.value = "Downloading Audio... 0%"
        page.update()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            add_download_to_db(url, filename, "audio")  # Store download in DB
        status_label.value = "Download Completed 100%"
        progress_bar.value = 1.0
        page.update()
    except Exception as e:
        status_label.value = f"Error: {str(e)}"
        page.update()


# Function to handle download button click
def on_download_click(e, page, progress_bar, status_label, resolution_dropdown, url_input):
    url = url_input.value
    resolution = resolution_dropdown.value
    if url and resolution:
        download_video(url, resolution, page, progress_bar, status_label)

def on_download_audio_click(e, page, progress_bar, status_label, url_input):
    url = url_input.value
    if url:
        download_audio(url, page, progress_bar, status_label)

# Home page layout
def home_page(page, progress_bar, status_label, resolution_dropdown, url_input, download_button, download_audio_button):
    return ft.Column(
        controls=[
            ft.Container(
                content=ft.Text(
                    value="Enter Video URL",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.ON_BACKGROUND,
                    text_align=ft.TextAlign.CENTER,
                    selectable=True
                ),
                padding=ft.Padding(10, 0, 0, 0),
                alignment=ft.alignment.center
            ),
            ft.Container(
                content=url_input,
                padding=ft.Padding(10, 0, 0, 0),
                alignment=ft.alignment.center
            ),
            ft.Container(
                content=ft.Text(
                    value="Select Resolution",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.ON_BACKGROUND,
                    text_align=ft.TextAlign.CENTER,
                    selectable=True
                ),
                padding=ft.Padding(10, 0, 0, 0),
                alignment=ft.alignment.center
            ),
            ft.Container(
                content=resolution_dropdown,
                padding=ft.Padding(0, 0, 20, 0),
                alignment=ft.alignment.center
            ),
            ft.Container(
                content=download_button,
                alignment=ft.alignment.center
            ),
            ft.Container(
                content=download_audio_button,
                alignment=ft.alignment.center
            ),
            ft.Container(
                content=status_label,
                padding=ft.Padding(20, 0, 0, 0),
                alignment=ft.alignment.center
            ),
            ft.Container(
                content=progress_bar,
                padding=ft.Padding(10, 0, 20, 0),
                alignment=ft.alignment.center
            ),
        ],
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

# Downloads page layout with delete and open buttons
def downloads_page(page):
    downloads = get_all_downloads()
    
    if len(downloads) == 0:
        return ft.Column(
            controls=[
                ft.Text(
                    value="Your downloads will appear here",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.ON_BACKGROUND,
                    text_align=ft.TextAlign.CENTER,
                    selectable=True
                )
            ],
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    
    download_cards = []
    for download_id, url, filename, filetype in downloads:
        download_cards.append(
            ft.Card(
                content=ft.Column(
                    [
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.DOWNLOAD),
                            title=ft.Text(f"{filetype.capitalize()} - {filename}"),
                            subtitle=ft.Text(url),
                        ),
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    text="Open",
                                    on_click=lambda e, fn=filename: open_file(fn),
                                    style=ft.ButtonStyle(
                                        color=ft.colors.WHITE,
                                        bgcolor=ft.colors.GREEN_600
                                    )
                                ),
                                ft.ElevatedButton(
                                    text="Delete",
                                    on_click=lambda e, d_id=download_id: delete_download_from_db(d_id, page),
                                    style=ft.ButtonStyle(
                                        color=ft.colors.WHITE,
                                        bgcolor=ft.colors.RED_600
                                    )
                                )
                            ],
                            alignment=ft.MainAxisAlignment.CENTER
                        )
                    ]
                )
            )
        )
    
    return ft.Column(
        controls=download_cards,
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

# Settings page layout with theme mode
def settings_page(page):
    current_theme_mode = get_theme_settings()
    page.session.set("theme_mode", current_theme_mode)

    theme_label = ft.Text(
        value="Select Theme Mode:",
        size=18,
        weight=ft.FontWeight.BOLD,
        color=ft.colors.ON_BACKGROUND,
        text_align=ft.TextAlign.CENTER
    )

    theme_radio_group = ft.RadioGroup(
        content=ft.Column(
            [
                ft.Radio(
                    value="light",
                    label="Light Theme",
                    fill_color=ft.colors.ON_BACKGROUND,
                ),
                ft.Radio(
                    value="dark",
                    label="Dark Theme",
                    fill_color=ft.colors.ON_BACKGROUND,
                ),
                ft.Radio(
                    value="system",
                    label="Follow System",
                    fill_color=ft.colors.ON_BACKGROUND,
                ),
            ]
        ),
        value=current_theme_mode,
        on_change=lambda e: on_theme_change(e, page)
    )

    return ft.Column(
        controls=[
            theme_label,
            theme_radio_group,
        ],
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

# Main function to initialize the app
def main(page: ft.Page):
    global progress_bar, status_label, resolution_dropdown, url_input, download_button, download_audio_button

    # Initialize the database
    init_db()

    page.title = "Videos Downloader"
    page.window.width = 375
    page.window.height = 667
    page.bgcolor = ft.colors.GREY_50

    # Set the theme based on the value from the database
    theme_mode = get_theme_settings()
    apply_theme(page, theme_mode)

    # Create resolution dropdown
    resolution_dropdown = ft.Dropdown(
        options=[
            ft.dropdown.Option("Best Available"),
            ft.dropdown.Option("360"),
            ft.dropdown.Option("480"),
            ft.dropdown.Option("720"),
            ft.dropdown.Option("1080")
        ],
        value="Best Available",
        width=300,
        border_color=ft.colors.TEAL_300,
        focused_border_color=ft.colors.TEAL_500,
        bgcolor=ft.colors.BACKGROUND,
        text_size=14,
        icon=ft.icons.ARROW_DOWNWARD
    )

    # Create URL input field
    url_input = ft.TextField(
        label="Video URL",
        width=300,
        border_color=ft.colors.TEAL_300,
        focused_border_color=ft.colors.TEAL_500,
        color=ft.colors.ON_BACKGROUND,
        text_align=ft.TextAlign.LEFT,
        bgcolor=ft.colors.BACKGROUND,
        text_size=14,
        icon=ft.icons.LINK
    )

    # Create download button
    download_button = ft.ElevatedButton(
        text="Download Video",
        icon=ft.icons.DOWNLOAD,
        on_click=lambda e: on_download_click(e, page, progress_bar, status_label, resolution_dropdown, url_input),
        style=ft.ButtonStyle(
            color=ft.colors.WHITE,
            bgcolor=ft.colors.GREEN_600,
            shape=ft.RoundedRectangleBorder(radius=12),
            elevation=4,
            padding=ft.Padding(16, 16, 16, 16)
        )
    )

    # Create download audio button
    download_audio_button = ft.ElevatedButton(
        text="Download Audio",
        icon=ft.icons.AUDIO_FILE,
        on_click=lambda e: on_download_audio_click(e, page, progress_bar, status_label, url_input),
        style=ft.ButtonStyle(
            color=ft.colors.WHITE,
            bgcolor=ft.colors.RED_600,
            shape=ft.RoundedRectangleBorder(radius=12),
            elevation=4,
            padding=ft.Padding(16, 16, 16, 16)
        )
    )

    # Status label to show download status
    status_label = ft.Text(
        value="Status: Ready",
        size=14,
        color=ft.colors.ON_BACKGROUND,
        selectable=True
    )

    # Progress bar to show download progress
    progress_bar = ft.ProgressBar(
        width=300,
        bgcolor=ft.colors.GREY_200,
        color=ft.colors.TEAL_500,
        value=0.0
    )

    # Back button for navigation
    back_button = ft.IconButton(
        icon=ft.icons.ARROW_BACK,
        on_click=lambda e: on_back_click(e, page),
        visible=False  # Initially hidden
    )

    # Menu button for the home page
    menu_button = ft.IconButton(
        icon=ft.icons.MENU,
        on_click=lambda e: print("Menu button clicked")
    )

    # App Bar setup
    page.appbar = ft.AppBar(
        title=ft.Text("Videos Downloader App"),
        center_title=True,
        bgcolor=ft.colors.TEAL_500,
        leading=menu_button,  # Set the menu button initially
    )

    # Navigation Bar setup
    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.icons.EXPLORE, label="Home"),
            ft.NavigationBarDestination(icon=ft.icons.DOWNLOAD, label="Downloads"),
            ft.NavigationBarDestination(
                icon=ft.icons.SETTINGS,
                label="Settings",
            ),
        ],
        on_change=lambda e: on_nav_click(e, page),
    )

    # Set initial home page view
    page.views.append(
        ft.View(
            "/",
            controls=[home_page(page, progress_bar, status_label, resolution_dropdown, url_input, download_button, download_audio_button)],
            appbar=page.appbar,
            navigation_bar=page.navigation_bar,
            scroll=ft.ScrollMode.AUTO  # Enable smoother scrolling for home page
        )
    )

    # Handle route-based navigation
    def route_change(e):
        if page.route == "/downloads":
            page.views.clear()
            page.views.append(
                ft.View(
                    "/downloads",
                    controls=[downloads_page(page)],
                    appbar=page.appbar,
                    navigation_bar=page.navigation_bar,
                    scroll=ft.ScrollMode.AUTO
                )
            )
            page.appbar.leading = back_button  # Replace menu button with back button
            back_button.visible = True
            page.navigation_bar.selected_index = 1

        elif page.route == "/settings":
            page.views.clear()
            page.views.append(
                ft.View(
                    "/settings",
                    controls=[settings_page(page)],
                    appbar=page.appbar,
                    navigation_bar=page.navigation_bar,
                    scroll=ft.ScrollMode.AUTO
                )
            )
            page.appbar.leading = back_button  # Replace menu button with back button
            back_button.visible = True
            page.navigation_bar.selected_index = 2

        else:  # Home page
            page.views.clear()
            page.views.append(
                ft.View(
                    "/",
                    controls=[home_page(page, progress_bar, status_label, resolution_dropdown, url_input, download_button, download_audio_button)],
                    appbar=page.appbar,
                    navigation_bar=page.navigation_bar,
                    scroll=ft.ScrollMode.AUTO
                )
            )
            page.appbar.leading = menu_button  # Set the menu button for home page
            back_button.visible = False  # Hide back button
            page.navigation_bar.selected_index = 0
        page.update()

    page.on_route_change = route_change
    page.go(page.route)

ft.app(target=main)
