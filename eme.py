import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
import os

# PostgreSQL configuration - UPDATE THESE CONNECTION DETAILS
DB_HOST = "localhost"  # or your host
DB_NAME = "tale_keeper"
DB_USER = "shane"
DB_PASSWORD = "xshanex"
DB_PORT = "5432"

BG_MAIN = "#ffccdd"
BG_HEADER = "#a7c7ff"

def get_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

# ---------- streak DB helpers ----------
def init_streak_table():
    """Create streak table if it does not exist and ensure one row."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reading_streak (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_read_date DATE,
            current_streak INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0
        )
    """)
    cur.execute("SELECT COUNT(*) FROM reading_streak")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO reading_streak (id, last_read_date, current_streak, longest_streak) "
            "VALUES (1, NULL, 0, 0)"
        )
    con.commit()
    con.close()

def get_streak():
    """Return (last_read_date, current_streak, longest_streak)."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT last_read_date, current_streak, longest_streak FROM reading_streak WHERE id = 1")
    row = cur.fetchone()
    con.close()
    return row if row else (None, 0, 0)

def update_streak_on_read():
    """Update streak when user reads a story (called by Read Story button)."""
    today = date.today()
    
    last_read_date, current_streak, longest_streak = get_streak()
    
    if last_read_date is None:
        new_streak = 1
    else:
        last = last_read_date  # already date object
        diff = (today - last).days
        if diff == 0:
            messagebox.showinfo("Streak", "Today's read is already counted.")
            return
        elif diff == 1:
            new_streak = current_streak + 1
        else:
            new_streak = 1
    
    new_longest = max(longest_streak, new_streak)
    
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        UPDATE reading_streak
        SET last_read_date = %s, current_streak = %s, longest_streak = %s
        WHERE id = 1
    """, (today, new_streak, new_longest))
    con.commit()
    con.close()
    
    streak_lbl.config(text=f"Current streak: {new_streak} day(s)")
    longest_lbl.config(text=f"Longest streak: {new_longest} day(s)")

# ---------- Story DB helpers ----------
def init_stories_table():
    """Create stories table if it does not exist."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id SERIAL PRIMARY KEY,
            favorite BOOLEAN DEFAULT FALSE,
            title TEXT NOT NULL,
            author TEXT,
            genre TEXT,
            date_started DATE,
            date_completed DATE,
            status TEXT,
            num_chapters INTEGER DEFAULT 0,
            word_count INTEGER DEFAULT 0,
            main_character TEXT,
            last_updated DATE,
            preview TEXT DEFAULT ''
        )
    """)
    con.commit()
    con.close()

def load_stories_to_tree():
    """Load all stories from DB into treeview."""
    for item in tree.get_children():
        tree.delete(item)
    
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT id, favorite, title, author, genre, date_started, date_completed, 
               status, num_chapters, word_count, main_character, last_updated, preview
        FROM stories ORDER BY id
    """)
    rows = cur.fetchall()
    con.close()
    
    for row in rows:
        fav_icon = "★" if row[1] else ""
        tree.insert("", "end", values=(
            row[0], fav_icon, row[2], row[3], row[4],
            row[5] or "", row[6] or "", row[7] or "",
            row[8] or 0, row[9] or 0, row[10] or "",
            row[11] or "", row[12] or ""
        ))

def save_story_to_db():
    """Save current form data as new story."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO stories (favorite, title, author, genre, date_started, date_completed, 
                           status, num_chapters, word_count, main_character, last_updated)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        fav_var.get(),
        story_title.get(),
        author_entry.get(),
        genre_var.get(),
        date_started.get() or None,
        date_completed.get() or None,
        status_var.get(),
        int(num_chaps.get() or 0),
        int(word_count.get() or 0),
        main_char.get(),
        last_upd.get() or None
    ))
    con.commit()
    con.close()
    load_stories_to_tree()
    clear_form()
    messagebox.showinfo("Success", "Story created!")

def update_story_in_db():
    """Update selected story with form data."""
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("Update", "Please select a story to update.")
        return
    
    story_id = tree.item(sel[0], "values")[0]
    
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        UPDATE stories 
        SET favorite = %s, title = %s, author = %s, genre = %s, 
            date_started = %s, date_completed = %s, status = %s,
            num_chapters = %s, word_count = %s, main_character = %s, last_updated = %s
        WHERE id = %s
    """, (
        fav_var.get(),
        story_title.get(),
        author_entry.get(),
        genre_var.get(),
        date_started.get() or None,
        date_completed.get() or None,
        status_var.get(),
        int(num_chaps.get() or 0),
        int(word_count.get() or 0),
        main_char.get(),
        last_upd.get() or None,
        story_id
    ))
    con.commit()
    con.close()
    load_stories_to_tree()
    messagebox.showinfo("Success", "Story updated!")

def delete_story_from_db():
    """Delete selected story."""
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("Delete", "Please select a story to delete.")
        return
    
    if not messagebox.askyesno("Confirm Delete", "Delete this story?"):
        return
    
    story_id = tree.item(sel[0], "values")[0]
    
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM stories WHERE id = %s", (story_id,))
    con.commit()
    con.close()
    load_stories_to_tree()
    clear_form()

def search_stories():
    """Search stories by title or author."""
    search_term = story_title.get().lower()
    if not search_term:
        load_stories_to_tree()
        return
    
    for item in tree.get_children():
        tree.delete(item)
    
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT id, favorite, title, author, genre, date_started, date_completed, 
               status, num_chapters, word_count, main_character, last_updated, preview
        FROM stories 
        WHERE LOWER(title) LIKE %s OR LOWER(author) LIKE %s
        ORDER BY id
    """, (f'%{search_term}%', f'%{search_term}%'))
    rows = cur.fetchall()
    con.close()
    
    for row in rows:
        fav_icon = "★" if row[1] else ""
        tree.insert("", "end", values=(
            row[0], fav_icon, row[2], row[3], row[4],
            row[5] or "", row[6] or "", row[7] or "",
            row[8] or 0, row[9] or 0, row[10] or "",
            row[11] or "", row[12] or ""
        ))

# ---------- global library list (in‑memory for now) ----------
library_stories = []

# ---------- main window ----------
root = tk.Tk()
root.title("Writers Haven - Story Shelf Record System (PostgreSQL)")
root.geometry("1100x600")
root.configure(bg=BG_MAIN)

# Title label
title_lbl = tk.Label(root, text="Writers Haven",
                     font=("Monotype Corsiva", 24, "bold"),
                     bg=BG_HEADER)
title_lbl.pack(fill="x")

# ---------- Top row: form (left) + right panel ----------
top_row = tk.Frame(root, bg=BG_MAIN)
top_row.pack(fill="x", padx=10, pady=5)

form_frame = tk.Frame(top_row, bg=BG_MAIN)
form_frame.pack(side="left", fill="x", expand=True)

def add_row(row, col, text, width=20):
    """Create label + entry in form_frame and return the entry widget."""
    lbl = tk.Label(form_frame, text=text, bg=BG_MAIN,
                   font=("Monotype Corsiva", 11))
    lbl.grid(row=row, column=col, sticky="w", padx=3, pady=2)
    ent = tk.Entry(form_frame, width=width)
    ent.grid(row=row, column=col+1, padx=3, pady=2)
    return ent

# form input fields
story_title  = add_row(0, 0, "Story Title:")
author_entry = add_row(0, 2, "Author:")

genre_combo_lbl = tk.Label(form_frame, text="Genre:", bg=BG_MAIN,
                           font=("Monotype Corsiva", 11))
genre_combo_lbl.grid(row=0, column=4, sticky="w", padx=3, pady=2)
genre_var = tk.StringVar()
genre_combo = ttk.Combobox(
    form_frame, textvariable=genre_var,
    values=["Romance", "Drama", "Fantasy", "Mystery", "Horror",
            "Adventure", "Comedy", "Sci-Fi", "Historical", "Others"],
    width=18, state="readonly"
)
genre_combo.grid(row=0, column=5, padx=3, pady=2)

date_started   = add_row(1, 0, "Date Started:")
date_completed = add_row(1, 2, "Date Completed:")

status_lbl = tk.Label(form_frame, text="Story Status:", bg=BG_MAIN,
                      font=("Monotype Corsiva", 11))
status_lbl.grid(row=1, column=4, sticky="w", padx=3, pady=2)
status_var = tk.StringVar()
status_combo = ttk.Combobox(form_frame, textvariable=status_var,
                            values=["Ongoing", "Completed", "Hiatus"],
                            width=18, state="readonly")
status_combo.grid(row=1, column=5, padx=3, pady=2)

num_chaps  = add_row(2, 0, "Num Chapters:")
word_count = add_row(2, 2, "Word Count:")
main_char  = add_row(3, 0, "Main Character:")
last_upd   = add_row(3, 2, "Last Updated:")

# ---------- right panel (favorite, streak, progress) ----------
right_frame = tk.Frame(top_row, bg=BG_MAIN, bd=2, relief="groove")
right_frame.pack(side="right", fill="y", padx=(10, 0))

# favorite section
fav_frame = tk.LabelFrame(right_frame, text="Favorite Story",
                          bg=BG_MAIN, font=("Monotype Corsiva", 11, "italic"))
fav_frame.pack(fill="x", padx=5, pady=5)

def toggle_favorite():
    """When checkbox is clicked, update Fav column for selected row."""
    sel = tree.selection()
    if not sel:
        return
    story_id = tree.item(sel[0], "values")[0]
    
    con = get_connection()
    cur = con.cursor()
    cur.execute("UPDATE stories SET favorite = %s WHERE id = %s", 
                (fav_var.get(), story_id))
    con.commit()
    con.close()
    
    load_stories_to_tree()

fav_var = tk.BooleanVar()
fav_check = tk.Checkbutton(
    fav_frame,
    text="★ Mark as Favorite",
    variable=fav_var,
    bg=BG_MAIN,
    command=toggle_favorite
)
fav_check.pack(anchor="w")

# streak section
streak_frame = tk.LabelFrame(right_frame, text="Writing Streak",
                             bg=BG_MAIN, font=("Monotype Corsiva", 11, "italic"))
streak_frame.pack(fill="x", padx=5, pady=5)
streak_lbl = tk.Label(streak_frame, text="Current streak: 0 day(s)",
                      bg=BG_MAIN, font=("Monotype Corsiva", 10))
streak_lbl.pack(anchor="w")
longest_lbl = tk.Label(streak_frame, text="Longest streak: 0 day(s)",
                       bg=BG_MAIN, font=("Monotype Corsiva", 10))
longest_lbl.pack(anchor="w")

# progress section (placeholder)
progress_frame = tk.LabelFrame(right_frame, text="Progress",
                               bg=BG_MAIN, font=("Monotype Corsiva", 11, "italic"))
progress_frame.pack(fill="x", padx=5, pady=5)
progress_lbl = tk.Label(progress_frame, text="Words written: 0",
                        bg=BG_MAIN, font=("Monotype Corsiva", 10))
progress_lbl.pack(anchor="w")

# ---------- Buttons under form (CRUD) ----------
btn_frame = tk.Frame(root, bg=BG_MAIN)
btn_frame.pack(fill="x", padx=10, pady=5)

def clear_form():
    """Clear all input fields and reset combo boxes / favorite."""
    for e in (story_title, author_entry, date_started, date_completed,
              num_chaps, word_count, main_char, last_upd):
        e.delete(0, tk.END)
    genre_var.set("")
    status_var.set("")
    fav_var.set(False)

tk.Button(
    btn_frame,
    text="Create Story",
    width=15,
    command=save_story_to_db,
    bg=BG_MAIN,
    font=("Monotype Corsiva", 10)
).pack(side="left", padx=3)

tk.Button(
    btn_frame,
    text="Update Record",
    width=15,
    command=update_story_in_db,
    bg=BG_MAIN,
    font=("Monotype Corsiva", 10)
).pack(side="left", padx=3)

tk.Button(
    btn_frame,
    text="Search Story",
    width=15,
    command=search_stories,
    bg=BG_MAIN,
    font=("Monotype Corsiva", 10)
).pack(side="left", padx=3)

tk.Button(
    btn_frame,
    text="Clear Record",
    width=15,
    command=clear_form,
    bg=BG_MAIN,
    font=("Monotype Corsiva", 10)
).pack(side="left", padx=3)

tk.Button(
    btn_frame,
    text="Delete Record",
    width=15,
    command=delete_story_from_db,
    bg="#ff9999",
    font=("Monotype Corsiva", 10)
).pack(side="left", padx=3)

# ---------- Table ----------
table_frame = tk.Frame(root, bg=BG_MAIN)
table_frame.pack(fill="both", expand=True, padx=10, pady=5)

columns = ("ID", "Fav", "Title", "Author", "Genre", "Start Date",
           "End Date", "Status", "Chaps", "Words", "Main Char",
           "Updated", "Preview")

style = ttk.Style()
style.configure(
    "Treeview.Heading",
    font=("Monotype Corsiva", 11, "bold")
)
style.configure(
    "Treeview",
    font=("Monotype Corsiva", 10)
)

tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=80, anchor="center")
tree.column("Title", width=180, anchor="w")
tree.column("Main Char", width=120, anchor="w")

vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=vsb.set)

tree.pack(side="left", fill="both", expand=True)
vsb.pack(side="right", fill="y")

# ---------- when a row is selected, show its data in the form ----------
def on_row_select(event):
    """Fill the input fields with the selected row so it can be edited."""
    sel = tree.selection()
    if not sel:
        return
    values = tree.item(sel[0], "values")
    
    # unpack values back into form fields
    clear_form()
    story_title.insert(0, values[2])
    author_entry.insert(0, values[3])
    genre_var.set(values[4] or "")
    date_started.insert(0, values[5])
    date_completed.insert(0, values[6])
    status_var.set(values[7] or "")
    num_chaps.insert(0, str(values[8] or ""))
    word_count.insert(0, str(values[9] or ""))
    main_char.insert(0, values[10] or "")
    last_upd.insert(0, values[11] or "")
    fav_var.set(values[1] == "★")

tree.bind("<<TreeviewSelect>>", on_row_select)

# ---------- Bottom buttons (Read, Library, New Chapter) ----------
bottom_frame = tk.Frame(root, bg=BG_MAIN)
bottom_frame.pack(fill="x", padx=10, pady=5)

def read_story():
    """Open a new window to 'read' the selected story and update streak."""
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("Read Story", "Please select a story first.")
        return
    
    values = tree.item(sel[0], "values")
    
    # update streak
    update_streak_on_read()
    
    # create read window
    win = tk.Toplevel(root)
    win.title(f"Read: {values[2]}")
    win.geometry("500x400")
    
    tk.Label(win, text=values[2], font=("Monotype Corsiva", 18, "bold")).pack(pady=5)
    tk.Label(win, text=f"by {values[3]}", font=("Monotype Corsiva", 12)).pack(pady=2)
    
    # placeholder story text
    text = tk.Text(win, wrap="word")
    text.pack(fill="both", expand=True, padx=10, pady=10)
    text.insert("1.0", "Story content goes here...\n\n(Connect to your real chapters later.)")
    text.config(state="disabled")

def add_to_library():
    """Add the selected story to the in‑memory library list."""
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("Library", "Please select a story to add.")
        return
    values = tree.item(sel[0], "values")
    library_stories.append(values)
    messagebox.showinfo("Library", f"'{values[2]}' added to your library.")

def open_library():
    """Open a window showing all stories stored in library_stories."""
    if not library_stories:
        messagebox.showinfo("Library", "Your library is empty.")
        return
    
    win = tk.Toplevel(root)
    win.title("My Library")
    win.geometry("700x300")
    
    cols = ("ID", "Fav", "Title", "Author", "Genre", "Status")
    lib_tree = ttk.Treeview(win, columns=cols, show="headings")
    for c in cols:
        lib_tree.heading(c, text=c)
        lib_tree.column(c, width=100, anchor="center")
    lib_tree.column("Title", width=200, anchor="w")
    
    for row in library_stories:
        lib_tree.insert("", "end", values=(row[0], row[1], row[2], row[3], row[4], row[7]))
    
    lib_tree.pack(fill="both", expand=True, padx=10, pady=10)

def add_new_chapter():
    """Open a simple window where the user can write another chapter."""
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("New Chapter", "Please select a story first.")
        return
    
    values = tree.item(sel[0], "values")
    
    win = tk.Toplevel(root)
    win.title(f"New Chapter for: {values[2]}")
    win.geometry("500x400")
    
    tk.Label(win, text=f"New Chapter - {values[2]}",
             font=("Monotype Corsiva", 16, "bold")).pack(pady=5)
    
    chapter_text = tk.Text(win, wrap="word")
    chapter_text.pack(fill="both", expand=True, padx=10, pady=10)
    
    def save_chapter():
        content = chapter_text.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("New Chapter", "Chapter is empty.")
            return
        messagebox.showinfo("New Chapter", "Chapter saved (placeholder).")
        win.destroy()
    
    tk.Button(win, text="Save Chapter", command=save_chapter).pack(pady=5)

read_btn = tk.Button(
    bottom_frame,
    text="Read Story",
    width=12,
    command=read_story,
    bg=BG_MAIN,
    font=("Monotype Corsiva", 10)
)
read_btn.pack(side="left", padx=3)

add_lib_btn = tk.Button(
    bottom_frame,
    text="Add to Library",
    width=12,
    command=add_to_library,
    bg=BG_MAIN,
    font=("Monotype Corsiva", 10)
)
add_lib_btn.pack(side="left", padx=3)

my_lib_btn = tk.Button(
    bottom_frame,
    text="My Library",
    width=12,
    command=open_library,
    bg=BG_MAIN,
    font=("Monotype Corsiva", 10)
)
my_lib_btn.pack(side="left", padx=3)

new_ch_btn = tk.Button(
    bottom_frame,
    text="New Chapter",
    width=12,
    command=add_new_chapter,
    bg=BG_MAIN,
    font=("Monotype Corsiva", 10)
)
new_ch_btn.pack(side="left", padx=3)

# ---------- Initialize database and load data ----------
try:
    init_streak_table()
    init_stories_table()
    load_stories_to_tree()
    
    # Load initial streak
    last_date, cur_s, long_s = get_streak()
    streak_lbl.config(text=f"Current streak: {cur_s} day(s)")
    longest_lbl.config(text=f"Longest streak: {long_s} day(s)")
except Exception as e:
    messagebox.showerror("Database Error", 
                        f"Failed to connect to PostgreSQL:\n{str(e)}\n\n"
                        "Please check your connection settings at the top of the file.")

root.mainloop()
