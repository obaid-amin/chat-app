import socket
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import struct
import os
import requests
from io import BytesIO
import sounddevice as sd
import soundfile as sf
import tempfile
import pygame
import time
import uuid

# --- Theme ---
BG_COLOR = "#0f0f1c"
FG_COLOR = "#e0e0e0"
BTN_COLOR = "#5c7cfa"
BTN_HOVER_COLOR = "#3b5bdb"
ENTRY_BG = "#1f1f2e"
SCROLLBAR_COLOR = "#44475a"
FONT = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 13, "bold")

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 12345
GIPHY_API_KEY = "1UeCNeCh8uUsFT2wdcVSopVF8LD0LGob"

MSG_TYPE_TEXT = 1
MSG_TYPE_FILE = 2
MSG_TYPE_GIF = 3
MSG_TYPE_USERLIST = 4
MSG_TYPE_VOICE = 5
MAX_FILE_SIZE = 5 * 1024 * 1024

# Initialize pygame mixer once (for voice playback)
pygame.mixer.init()

class ChatClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Login")
        self.master.configure(bg=BG_COLOR)
        self.socket = None

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Vertical.TScrollbar", background=SCROLLBAR_COLOR, arrowcolor=FG_COLOR)

        self.login_frame = tk.Frame(master, bg=BG_COLOR)
        self.login_frame.pack(padx=20, pady=40)

        tk.Label(self.login_frame, text="Username", fg=FG_COLOR, bg=BG_COLOR, font=FONT_BOLD).pack(anchor="w")
        self.username_entry = tk.Entry(self.login_frame, font=FONT, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR, relief="flat", highlightthickness=1, highlightbackground=SCROLLBAR_COLOR)
        self.username_entry.pack(fill="x", pady=8)

        tk.Label(self.login_frame, text="Password", fg=FG_COLOR, bg=BG_COLOR, font=FONT_BOLD).pack(anchor="w")
        self.password_entry = tk.Entry(self.login_frame, show="*", font=FONT, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR, relief="flat", highlightthickness=1, highlightbackground=SCROLLBAR_COLOR)
        self.password_entry.pack(fill="x", pady=8)

        btn_style = {"font": FONT_BOLD, "bg": BTN_COLOR, "fg": "white", "relief": "flat", "activebackground": BTN_HOVER_COLOR, "bd": 0}
        tk.Button(self.login_frame, text="Login", command=self.login, **btn_style).pack(fill="x", pady=(10, 5))
        tk.Button(self.login_frame, text="Register", command=self.register, **btn_style).pack(fill="x")

    def connect(self):
        if not self.socket:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((SERVER_HOST, SERVER_PORT))

    def login(self):
        self.connect()
        user = self.username_entry.get()
        pw = self.password_entry.get()
        self.socket.sendall(f"LOGIN:{user}:{pw}".encode())
        res = self.socket.recv(1024).decode()
        if res == "OK":
            self.start_chat_ui()
        else:
            messagebox.showerror("Login Failed", res)

    def register(self):
        self.connect()
        user = self.username_entry.get()
        pw = self.password_entry.get()
        self.socket.sendall(f"REGISTER:{user}:{pw}".encode())
        res = self.socket.recv(1024).decode()
        if res == "OK":
            messagebox.showinfo("Registered", "Registration successful. Please login.")
        else:
            messagebox.showerror("Error", res)

    def start_chat_ui(self):
        self.login_frame.destroy()
        self.master.title("Chat")

        self.chat_frame = tk.PanedWindow(self.master, orient=tk.HORIZONTAL, bg=BG_COLOR, sashwidth=5, sashrelief='raised')
        self.chat_frame.pack(fill="both", expand=True)

        left_panel = tk.Frame(self.chat_frame, bg=BG_COLOR, padx=10, pady=10)
        self.chat_frame.add(left_panel, stretch='always')

        right_panel = tk.Frame(self.chat_frame, bg=ENTRY_BG, padx=5)
        self.chat_frame.add(right_panel)

        header = tk.Label(left_panel, text="Chat Room", font=FONT_BOLD, bg=BTN_COLOR, fg="white", pady=10)
        header.pack(fill="x", pady=(0, 10))

        text_frame = tk.PanedWindow(left_panel, orient=tk.HORIZONTAL)
        text_frame.pack(fill="both", expand=True)

        self.text_area = tk.Text(text_frame, state="disabled", wrap="word", font=FONT, bg=ENTRY_BG, fg=FG_COLOR, relief="flat")
        text_frame.add(self.text_area)

        scroll = ttk.Scrollbar(text_frame, command=self.text_area.yview)
        scroll.pack(side="right", fill="y")
        self.text_area.config(yscrollcommand=scroll.set)

        userlist_label = tk.Label(right_panel, text="Online Users", font=FONT_BOLD, fg=FG_COLOR, bg=ENTRY_BG)
        userlist_label.pack(pady=(0, 5))

        self.user_listbox = tk.Listbox(right_panel, height=25, width=20, font=FONT, bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0, borderwidth=0, selectbackground=BTN_COLOR)
        self.user_listbox.pack(fill="y", expand=True)

        input_frame = tk.Frame(left_panel, bg=BG_COLOR)
        input_frame.pack(fill="x", pady=10)

        self.entry = tk.Entry(input_frame, font=FONT, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR, relief="flat")
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=6)

        btn_cfg = {"font": FONT_BOLD, "bg": BTN_COLOR, "fg": "white", "relief": "flat", "activebackground": BTN_HOVER_COLOR, "width": 8, "bd": 0}
        tk.Button(input_frame, text="Send", command=self.send_text, **btn_cfg).pack(side="left", padx=2)
        tk.Button(input_frame, text="File", command=self.send_file, **btn_cfg).pack(side="left", padx=2)
        tk.Button(input_frame, text="GIF", command=self.open_gif_search, **btn_cfg).pack(side="left", padx=2)
        tk.Button(input_frame, text="Voice", command=self.send_voice_note, **btn_cfg).pack(side="left", padx=2)

        threading.Thread(target=self.receive_messages, daemon=True).start()
        self.gif_refs = {}

    def send_text(self):
        msg = self.entry.get().strip()
        if msg:
            data = bytes([MSG_TYPE_TEXT]) + struct.pack(">I", len(msg)) + msg.encode()
            self.socket.sendall(data)
            self.append_message("You: " + msg)
            self.entry.delete(0, tk.END)

    def send_file(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        if os.path.getsize(path) > MAX_FILE_SIZE:
            messagebox.showwarning("Too large", "File exceeds 5 MB.")
            return
        try:
            with open(path, "rb") as f:
                content = f.read()
            fname = os.path.basename(path).encode()
            data = bytes([MSG_TYPE_FILE]) + struct.pack(">I", len(fname)) + struct.pack(">I", len(content)) + fname + content
            self.socket.sendall(data)
            self.append_message(f"You sent file: {fname.decode()}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_gif_search(self):
        self.gif_search_win = tk.Toplevel(self.master)
        self.gif_search_win.title("Search GIF")
        self.gif_search_win.geometry("600x400")
        self.gif_search_win.configure(bg=BG_COLOR)

        tk.Label(self.gif_search_win, text="Search GIFs:", font=FONT_BOLD, bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)

        search_frame = tk.Frame(self.gif_search_win, bg=BG_COLOR)
        search_frame.pack(pady=5, fill="x", padx=10)

        self.gif_search_entry = tk.Entry(search_frame, font=FONT, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR, relief="flat")
        self.gif_search_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 10))
        self.gif_search_entry.bind("<Return>", lambda e: self.search_gifs())

        btn_cfg = {"font": FONT_BOLD, "bg": BTN_COLOR, "fg": "white", "relief": "flat", "activebackground": "#305a9c", "width": 10}
        tk.Button(search_frame, text="Search", command=self.search_gifs, **btn_cfg).pack(side="left")

        # Canvas + scrollbar for GIF thumbnails grid
        self.gif_canvas = tk.Canvas(self.gif_search_win, bg=BG_COLOR, highlightthickness=0)
        self.gif_scrollbar = ttk.Scrollbar(self.gif_search_win, orient="vertical", command=self.gif_canvas.yview)
        self.gif_scrollable_frame = tk.Frame(self.gif_canvas, bg=BG_COLOR)

        self.gif_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.gif_canvas.configure(scrollregion=self.gif_canvas.bbox("all"))
        )
        self.gif_canvas.create_window((0, 0), window=self.gif_scrollable_frame, anchor="nw")
        self.gif_canvas.configure(yscrollcommand=self.gif_scrollbar.set)

        self.gif_canvas.pack(side="left", fill="both", expand=True, padx=(10,0), pady=10)
        self.gif_scrollbar.pack(side="right", fill="y", pady=10)

        self.gif_thumbs = []

    def search_gifs(self):
        query = self.gif_search_entry.get().strip()
        if not query:
            return
        url = f"https://api.giphy.com/v1/gifs/search?api_key={GIPHY_API_KEY}&q={query}&limit=20&rating=g"
        try:
            resp = requests.get(url).json()
            gifs = resp.get("data", [])
            for widget in self.gif_scrollable_frame.winfo_children():
                widget.destroy()
            self.gif_thumbs.clear()
            for idx, gif in enumerate(gifs):
                thumb_url = gif["images"]["fixed_width_small_still"]["url"]
                full_url = gif["images"]["original"]["url"]
                response = requests.get(thumb_url)
                pil_img = Image.open(BytesIO(response.content))
                photo = ImageTk.PhotoImage(pil_img)
                lbl = tk.Label(self.gif_scrollable_frame, image=photo, bg=BG_COLOR, cursor="hand2")
                lbl.photo = photo
                lbl.grid(row=idx//5, column=idx%5, padx=5, pady=5)

                def on_click(event, url=full_url):
                    self.send_gif(url)
                lbl.bind("<Button-1>", on_click)
                self.gif_thumbs.append(lbl)
        except Exception as e:
            messagebox.showerror("Error", "Failed to search GIFs.")

    def send_gif(self, url):
        url_bytes = url.encode()
        gif_data = bytes([MSG_TYPE_GIF]) + struct.pack(">I", len(url_bytes)) + url_bytes
        self.socket.sendall(gif_data)
        self.append_message("You sent a GIF")
        self.display_gif_in_text_area(url)
        self.open_gif_popup(url)
        self.gif_search_win.destroy()

    def display_gif_in_text_area(self, url):
        try:
            response = requests.get(url)
            pil_img = Image.open(BytesIO(response.content))
            pil_img.thumbnail((120, 120))
            photo = ImageTk.PhotoImage(pil_img)

            self.text_area.config(state="normal")

            # Insert image and attach a tag for click binding
            insert_index = self.text_area.index(tk.END)
            self.text_area.image_create(insert_index, image=photo)
            tag_name = f"gif_{len(self.gif_refs)}"
            # Tag the image position (single character after image)
            self.text_area.insert(tk.END, " ")  # Add a space after the image
            start_index = insert_index
            end_index = self.text_area.index(f"{insert_index} +1c")
            self.text_area.tag_add(tag_name, start_index, end_index)

            def on_click(event, url=url):
                self.open_gif_popup(url)

            self.text_area.tag_bind(tag_name, "<Button-1>", on_click)
            self.text_area.insert(tk.END, "\n")
            self.text_area.config(state="disabled")

            self.gif_refs[url] = photo  # Keep reference alive
        except Exception:
            self.append_message("Failed to load GIF.")

    def open_gif_popup(self, url):
        try:
            popup = tk.Toplevel(self.master)
            popup.title("GIF Preview")
            popup.configure(bg=BG_COLOR)

            response = requests.get(url)
            gif_bytes = BytesIO(response.content)
            pil_img = Image.open(gif_bytes)

            frames = []
            try:
                while True:
                    frame = pil_img.copy().convert("RGBA")
                    frames.append(ImageTk.PhotoImage(frame))
                    pil_img.seek(pil_img.tell() + 1)
            except EOFError:
                pass

            lbl = tk.Label(popup, bg=BG_COLOR)
            lbl.pack()

            def animate(idx=0):
                frame = frames[idx]
                lbl.config(image=frame)
                idx = (idx + 1) % len(frames)
                popup.after(100, animate, idx)

            animate()
        except Exception as e:
            messagebox.showerror("GIF Error", f"Could not open GIF:\n{e}")

    def send_voice_note(self):
        duration = 5
        fs = 44100  # Sample rate
        try:
            messagebox.showinfo("Recording", f"Recording voice note for {duration} seconds. Speak now.")
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)  # Mono recording
            sd.wait()  # Wait until recording is finished
            temp_path = tempfile.mktemp(suffix=".wav")
            sf.write(temp_path, recording, fs, format='WAV')  # Save as WAV file
            with open(temp_path, "rb") as f:
                content = f.read()
            # Save a local copy for playback
            local_filename = f"sent_voice_note_{int(time.time())}_{uuid.uuid4().hex[:6]}.wav"
            with open(local_filename, "wb") as f:
                f.write(content)
            os.remove(temp_path)

            # Send voice data
            data = bytes([MSG_TYPE_VOICE]) + struct.pack(">I", len(content)) + content
            self.socket.sendall(data)
            self.append_message(f"You sent a voice note.", voice_file=local_filename)
        except Exception as e:
            messagebox.showerror("Voice Note Error", str(e))

    def append_message(self, msg, voice_file=None):
        self.text_area.config(state="normal")

        if voice_file:
            start = self.text_area.index(tk.END + "-1c")
            self.text_area.insert(tk.END, msg + "\n")
            end = self.text_area.index(tk.END + "-1c")
            tag = f"voice_{start.replace('.', '_')}"
            self.text_area.tag_add(tag, start, end)
            self.text_area.tag_config(tag, foreground="#61afef", underline=True, font=FONT_BOLD)

            def play_voice(event, file=voice_file):
                threading.Thread(target=self.play_voice_file, args=(file,), daemon=True).start()

            self.text_area.tag_bind(tag, "<Button-1>", play_voice)
        else:
            self.text_area.insert(tk.END, msg + "\n")

        self.text_area.see(tk.END)
        self.text_area.config(state="disabled")

    def play_voice_file(self, filename):
        try:
            if not os.path.exists(filename):
                messagebox.showinfo("No voice note", "Voice note file not found.")
                return
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
        except Exception as e:
            messagebox.showerror("Playback Error", f"Could not play voice note:\n{e}")

    def receive_messages(self):
        while True:
            try:
                msg_type = self.socket.recv(1)
                if not msg_type:
                    break
                msg_type = msg_type[0]

                if msg_type == MSG_TYPE_TEXT:
                    length_bytes = self.recvall(4)
                    length = struct.unpack(">I", length_bytes)[0]
                    msg_bytes = self.recvall(length)
                    msg = msg_bytes.decode()
                    self.append_message("Friend: " + msg)

                elif msg_type == MSG_TYPE_FILE:
                    fname_len = struct.unpack(">I", self.recvall(4))[0]
                    file_len = struct.unpack(">I", self.recvall(4))[0]
                    fname = self.recvall(fname_len).decode()
                    file_data = self.recvall(file_len)
                    with open(f"received_{fname}", "wb") as f:
                        f.write(file_data)
                    self.append_message(f"Received file: {fname}")

                elif msg_type == MSG_TYPE_GIF:
                    length = struct.unpack(">I", self.recvall(4))[0]
                    url = self.recvall(length).decode()
                    self.append_message("Friend sent a GIF")
                    self.display_gif_in_text_area(url)

                elif msg_type == MSG_TYPE_USERLIST:
                    length = struct.unpack(">I", self.recvall(4))[0]
                    userlist_str = self.recvall(length).decode()
                    users = userlist_str.split(",")
                    self.user_listbox.delete(0, tk.END)
                    for u in users:
                        self.user_listbox.insert(tk.END, u)

                elif msg_type == MSG_TYPE_VOICE:
                    length = struct.unpack(">I", self.recvall(4))[0]
                    voice_data = self.recvall(length)
                    filename = f"received_voice_note_{int(time.time())}_{uuid.uuid4().hex[:6]}.wav"
                    with open(filename, "wb") as f:
                        f.write(voice_data)
                    self.append_message("Voice note received.", voice_file=filename)

            except Exception:
                break
        self.socket.close()

    def recvall(self, n):
        data = b""
        while len(data) < n:
            packet = self.socket.recv(n - len(data))
            if not packet:
                return data
            data += packet
        return data

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClient(root)
    root.mainloop()
