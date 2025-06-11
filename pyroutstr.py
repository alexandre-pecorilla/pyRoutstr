import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, font
import threading
import queue
from openai import OpenAI
import json
from datetime import datetime
import os
from dotenv import load_dotenv, set_key
import sys

# Load environment variables
load_dotenv()

# Popular models dictionary
POPULAR_MODELS = {
    "OpenAI": [
        "openai/o3",
        "openai/o4-mini",
        "openai/o4-mini-high",
        "openai/gpt-4.5-preview",
        "openai/gpt-4.1"
    ],
    "Anthropic": [
        "anthropic/claude-opus-4",
        "anthropic/claude-sonnet-4",
        "anthropic/claude-3.7-sonnet",
        "anthropic/claude-3.7-sonnet:thinking"
    ],
    "Google": [
        "google/gemini-2.5-pro-preview",
        "google/gemini-2.5-flash-preview-05-20"
    ],
    "Deepseek": [
        "deepseek/deepseek-r1-0528",
        "deepseek/deepseek-prover-v2"
    ],
    "Qwen": [
        "qwen/qwen-max",
        "qwen/qwen3-32b"
    ]
}

class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("pyRoutstr v1.0")

        # Start maximized
        self.root.state('zoomed') if sys.platform == 'win32' else self.root.attributes('-zoomed', True)

        # Variables
        self.api_key = tk.StringVar(value=os.getenv('ROUTSTR_API_KEY', ''))
        self.default_model = tk.StringVar(value=os.getenv('DEFAULT_MODEL', 'openai/gpt-4.5-preview'))
        self.current_model = tk.StringVar()
        self.use_tor = tk.BooleanVar(value=False)
        self.font_size = tk.IntVar(value=11)
        self.theme = tk.StringVar(value='dark')

        # State
        self.client = None
        self.messages = []
        self.total_tokens = 0
        self.conversation_active = False
        self.stream_queue = queue.Queue()

        # Apply initial theme
        self.themes = {
            'dark': {
                'bg': '#1e1e1e',
                'fg': '#e0e0e0',
                'button_bg': '#3a3a3a',
                'button_fg': '#e0e0e0',
                'entry_bg': '#2a2a2a',
                'entry_fg': '#e0e0e0',
                'highlight': '#0078d4',
                'success': '#4caf50',
                'error': '#f44336',
                'warning': '#ff9800',
                'tor': '#9c27b0'
            },
            'light': {
                'bg': '#ffffff',
                'fg': '#000000',
                'button_bg': '#e0e0e0',
                'button_fg': '#000000',
                'entry_bg': '#f5f5f5',
                'entry_fg': '#000000',
                'highlight': '#0078d4',
                'success': '#4caf50',
                'error': '#f44336',
                'warning': '#ff9800',
                'tor': '#9c27b0'
            }
        }

        self.setup_ui()
        self.apply_theme()

        # Check if API key exists
        if not self.api_key.get():
            self.root.after(100, self.show_settings)

    def setup_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Conversation", command=self.new_conversation)
        file_menu.add_command(label="Save Conversation", command=self.save_conversation)
        file_menu.add_separator()
        file_menu.add_command(label="Settings", command=self.show_settings)
        file_menu.add_command(label="Get Credits", command=self.show_get_credits)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="How to Use", command=self.show_how_to_use)
        help_menu.add_command(label="About", command=self.show_about)

        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status bar at top
        self.status_frame = ttk.Frame(main_frame)
        self.status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_label = ttk.Label(self.status_frame, text="Not connected")
        self.status_label.pack(side=tk.LEFT)

        self.token_label = ttk.Label(self.status_frame, text="")
        self.token_label.pack(side=tk.RIGHT)

        # Chat display
        chat_frame = ttk.Frame(main_frame)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=('Consolas', self.font_size.get()),
            padx=10,
            pady=10
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        # Configure tags for formatting (font size will be updated later)
        self.configure_tags()

        # Input area
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.input_text = tk.Text(
            input_frame,
            height=4,
            wrap=tk.WORD,
            font=('Consolas', 11)
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind Enter key to send message (Shift+Enter for new line)
        self.input_text.bind('<Return>', self.handle_return)
        self.input_text.bind('<Shift-Return>', lambda e: None)

        button_frame = ttk.Frame(input_frame)
        button_frame.pack(side=tk.RIGHT, padx=(5, 0))

        self.send_button = ttk.Button(button_frame, text="Send", command=self.send_message)
        self.send_button.pack(pady=(0, 2))

        self.clear_button = ttk.Button(button_frame, text="Clear", command=self.clear_input)
        self.clear_button.pack()

        # Initial state
        self.toggle_input_state(False)

    def set_theme(self, theme_name):
        """Set theme and update button states"""
        self.theme.set(theme_name)
        if hasattr(self, 'dark_btn') and hasattr(self, 'light_btn'):
            self.update_theme_buttons()

    def update_theme_buttons(self):
        """Update theme button appearance to show selection"""
        theme = self.themes[self.theme.get()]

        if self.theme.get() == 'dark':
            # Dark is selected
            self.dark_btn.configure(
                relief=tk.SUNKEN,
                bg=theme['highlight'],
                fg='white',
                activebackground=theme['highlight']
            )
            self.light_btn.configure(
                relief=tk.RAISED,
                bg=theme['button_bg'],
                fg=theme['button_fg'],
                activebackground=theme['button_bg']
            )
        else:
            # Light is selected
            self.light_btn.configure(
                relief=tk.SUNKEN,
                bg=theme['highlight'],
                fg='white',
                activebackground=theme['highlight']
            )
            self.dark_btn.configure(
                relief=tk.RAISED,
                bg=theme['button_bg'],
                fg=theme['button_fg'],
                activebackground=theme['button_bg']
            )

    def configure_tags(self):
        """Configure text tags with current font size"""
        size = self.font_size.get()
        theme = self.themes[self.theme.get()]
        
        # Configure tags with dynamic font size
        self.chat_display.tag_config('user', foreground=theme['highlight'], font=('Consolas', size, 'bold'))
        self.chat_display.tag_config('assistant', foreground=theme['success'], font=('Consolas', size, 'bold'))
        self.chat_display.tag_config('system', foreground=theme['warning'], font=('Consolas', size, 'italic'))
        self.chat_display.tag_config('error', foreground=theme['error'], font=('Consolas', size, 'italic'))
        self.chat_display.tag_config('tor', foreground=theme['tor'], font=('Consolas', size, 'bold'))
        self.chat_display.tag_config('separator', foreground='#666666' if self.theme.get() == 'dark' else '#cccccc', font=('Consolas', size - 2))

    def apply_theme(self):
        theme = self.themes[self.theme.get()]

        # Configure root
        self.root.configure(bg=theme['bg'])

        # Configure text widgets
        self.chat_display.configure(
            bg=theme['entry_bg'],
            fg=theme['fg'],
            insertbackground=theme['fg']
        )
        self.input_text.configure(
            bg=theme['entry_bg'],
            fg=theme['fg'],
            insertbackground=theme['fg']
        )

        # Update tags with theme colors and current font size
        self.configure_tags()

        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TFrame', background=theme['bg'])
        style.configure('TLabel', background=theme['bg'], foreground=theme['fg'])
        style.configure('TButton', background=theme['button_bg'], foreground=theme['button_fg'])
        style.map('TButton',
                  background=[('active', theme['highlight']),
                              ('pressed', theme['highlight'])])

    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("1200x600")
        settings_window.transient(self.root)
        settings_window.grab_set()

        # Apply theme to settings window
        theme = self.themes[self.theme.get()]
        settings_window.configure(bg=theme['bg'])
        
        # Create temporary variables for settings (don't modify the originals until save)
        temp_api_key = tk.StringVar(value=self.api_key.get())
        temp_default_model = tk.StringVar(value=self.default_model.get())

        # API Key section
        api_frame = ttk.LabelFrame(settings_window, text="API Configuration", padding=10)
        api_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(api_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, pady=5)
        api_entry = ttk.Entry(api_frame, textvariable=temp_api_key, show="*", width=40)
        api_entry.grid(row=0, column=1, pady=5, padx=5)
        
        # Check Credits Balance button
        balance_label = ttk.Label(api_frame, text="", font=('Consolas', 11))
        balance_label.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        def check_balance():
            api_key = temp_api_key.get().strip()
            if not api_key:
                messagebox.showerror("Error", "Please enter an API key")
                return
                
            try:
                import httpx
                
                headers = {
                    "Authorization": f"Bearer {api_key}"
                }
                
                balance_label.config(text="Checking...")
                settings_window.update()
                
                with httpx.Client(timeout=30.0) as client:
                    response = client.get("https://api.routstr.com/v1/wallet/info", headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        balance = data.get('balance', 0)
                        sats = balance / 1000
                        balance_label.config(text=f"Balance: {balance:,} credits ({sats:,.3f} SAT)", foreground=theme['success'])
                    else:
                        balance_label.config(text=f"Error: {response.status_code}", foreground=theme['error'])
                        
            except Exception as e:
                balance_label.config(text=f"Error: {str(e)[:50]}...", foreground=theme['error'])
        
        check_btn = ttk.Button(api_frame, text="Check Credits Balance", command=check_balance)
        check_btn.grid(row=1, column=0, sticky=tk.W, pady=5)

        # Default Model section
        model_frame = ttk.LabelFrame(settings_window, text="Default Model", padding=10)
        model_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(model_frame, text="Model:").grid(row=0, column=0, sticky=tk.W, pady=5)
        model_combo = ttk.Combobox(model_frame, textvariable=temp_default_model, width=37)

        # Flatten models for combobox
        all_models = []
        for provider, models in POPULAR_MODELS.items():
            all_models.extend(models)
        model_combo['values'] = all_models
        model_combo.grid(row=0, column=1, pady=5, padx=5)

        # Appearance section
        appearance_frame = ttk.LabelFrame(settings_window, text="Appearance", padding=10)
        appearance_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(appearance_frame, text="Font Size:").grid(row=0, column=0, sticky=tk.W, pady=5)
        font_spinbox = ttk.Spinbox(appearance_frame, from_=8, to=20, textvariable=self.font_size, width=10)
        font_spinbox.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        ttk.Label(appearance_frame, text="Theme:").grid(row=1, column=0, sticky=tk.W, pady=5)
        theme_frame = ttk.Frame(appearance_frame)
        theme_frame.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)

        # Use buttons with visual feedback
        self.dark_btn = tk.Button(theme_frame, text="Dark", width=10,
                                  command=lambda: self.set_theme('dark'),
                                  relief=tk.RAISED, bd=2)
        self.dark_btn.pack(side=tk.LEFT, padx=5)

        self.light_btn = tk.Button(theme_frame, text="Light", width=10,
                                   command=lambda: self.set_theme('light'),
                                   relief=tk.RAISED, bd=2)
        self.light_btn.pack(side=tk.LEFT, padx=5)

        # Update button appearance based on current theme
        self.update_theme_buttons()

        # Buttons
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        def save_settings():
            # Update the actual variables with the temporary values
            self.api_key.set(temp_api_key.get())
            self.default_model.set(temp_default_model.get())
            
            # Save to .env file
            env_path = '.env'
            set_key(env_path, 'ROUTSTR_API_KEY', self.api_key.get())
            set_key(env_path, 'DEFAULT_MODEL', self.default_model.get())

            # Update font for chat display only (not input field)
            new_font = font.Font(family='Consolas', size=self.font_size.get())
            self.chat_display.configure(font=new_font)
            
            # Update tags to use new font size
            self.configure_tags()

            # Update theme
            self.apply_theme()

            settings_window.destroy()

            # Show success message
            self.add_system_message("Settings saved successfully!")

        ttk.Button(button_frame, text="Save", command=save_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.RIGHT)

    def show_get_credits(self):
        """Show dialog for getting credits with cashu token"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Get Credits")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Apply theme
        theme = self.themes[self.theme.get()]
        dialog.configure(bg=theme['bg'])
        
        # Main frame to control padding and sizing
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Variables
        api_key_var = tk.StringVar()
        balance_var = tk.StringVar()
        confirmed_var = tk.BooleanVar(value=False)
        
        # Token entry frame
        token_frame = ttk.LabelFrame(main_frame, text="Enter Cashu Token to get a new Routstr API key", padding=10)
        token_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(token_frame, text="Cashu Token:").pack(anchor=tk.W)
        token_entry = ttk.Entry(token_frame, show="*", width=50)
        token_entry.pack(fill=tk.X, pady=5)
        
        # Result frame (initially hidden)
        result_frame = ttk.LabelFrame(main_frame, text="Result", padding=10)
        
        # API Key display
        api_frame = ttk.Frame(result_frame)
        api_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(api_frame, text="API Key:").pack(side=tk.LEFT)
        api_key_label = ttk.Entry(api_frame, textvariable=api_key_var, state='readonly', show="*", width=40)
        api_key_label.pack(side=tk.LEFT, padx=5)
        
        def copy_api_key():
            # Get the actual API key value
            self.root.clipboard_clear()
            self.root.clipboard_append(api_key_var.get())
            copy_btn.config(text="Copied!")
            self.root.after(2000, lambda: copy_btn.config(text="Copy"))
        
        copy_btn = ttk.Button(api_frame, text="Copy", command=copy_api_key)
        copy_btn.pack(side=tk.LEFT, padx=5)
        
        # Balance display
        balance_label = ttk.Label(result_frame, textvariable=balance_var, font=('Consolas', 11))
        balance_label.pack(pady=5)
        
        # Confirmation checkbox
        confirm_check = ttk.Checkbutton(
            result_frame,
            text="I have copied my API key and saved it securely",
            variable=confirmed_var,
            command=lambda: finish_btn.config(state='normal' if confirmed_var.get() else 'disabled')
        )
        confirm_check.pack(pady=10)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def get_credits():
            token = token_entry.get().strip()
            if not token:
                messagebox.showerror("Error", "Please enter a cashu token")
                return
            
            try:
                import httpx
                
                # Make API call
                headers = {
                    "Authorization": f"Bearer {token}"
                }
                
                with httpx.Client(timeout=30.0) as client:
                    response = client.get("https://api.routstr.com/v1/wallet/info", headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        api_key_var.set(data.get('api_key', ''))
                        balance = data.get('balance', 0)
                        sats = balance / 1000
                        balance_var.set(f"Balance: {balance:,} credits ({sats:,.3f} SAT)")
                        
                        # Show result frame
                        result_frame.pack(fill=tk.X, padx=10, pady=10)
                        
                        # Disable get credits button
                        get_btn.config(state='disabled')
                        token_entry.config(state='disabled')
                    else:
                        messagebox.showerror("Error", f"Failed to get credits: {response.text}")
                    
            except ImportError:
                messagebox.showerror("Error", "httpx is required. Install with: pip install httpx[socks]")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to get credits: {str(e)}")
        
        get_btn = ttk.Button(button_frame, text="Get Credits", command=get_credits)
        get_btn.pack(side=tk.LEFT, padx=5)
        
        finish_btn = ttk.Button(button_frame, text="Finish", command=dialog.destroy, state='disabled')
        finish_btn.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
        
        # Update dialog to fit content
        dialog.update_idletasks()
        dialog.geometry("")  # Let the dialog size itself to fit content
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Set minimum size
        dialog.minsize(600, dialog.winfo_height())

    def new_conversation(self):
        if self.conversation_active and self.messages:
            if messagebox.askyesno("New Conversation", "Do you want to save the current conversation?"):
                self.save_conversation()

        # Reset state
        self.messages = []
        self.total_tokens = 0
        self.conversation_active = False
        self.client = None

        # Clear display
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.configure(state=tk.DISABLED)

        # Update status
        self.status_label.config(text="Not connected")
        self.token_label.config(text="")

        # Show model selection dialog
        self.show_model_selection()

    def show_model_selection(self):
        if not self.api_key.get():
            messagebox.showerror("Error", "Please set your API key in Settings first!")
            self.show_settings()
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("New Conversation")
        dialog.geometry("750x650")
        dialog.transient(self.root)
        dialog.grab_set()

        # Apply theme
        theme = self.themes[self.theme.get()]
        dialog.configure(bg=theme['bg'])

        # Model selection
        model_frame = ttk.LabelFrame(dialog, text="Select Model", padding=10)
        model_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create notebook for provider tabs
        notebook = ttk.Notebook(model_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        model_var = tk.StringVar(value=self.default_model.get())

        # Add tabs for each provider
        for provider, models in POPULAR_MODELS.items():
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=provider)

            for i, model in enumerate(models):
                ttk.Radiobutton(
                    tab,
                    text=model,
                    variable=model_var,
                    value=model
                ).pack(anchor=tk.W, padx=10, pady=2)

        # Custom model entry
        custom_frame = ttk.Frame(model_frame)
        custom_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(custom_frame, text="Or enter custom model:").pack(anchor=tk.W)
        custom_entry = ttk.Entry(custom_frame, width=40)
        custom_entry.pack(fill=tk.X, pady=5)

        # Tor option
        tor_frame = ttk.LabelFrame(dialog, text="Network Options", padding=10)
        tor_frame.pack(fill=tk.X, padx=10, pady=10)

        tor_check = ttk.Checkbutton(
            tor_frame,
            text="Use Tor (requires SOCKS5 proxy on localhost:9050)",
            variable=self.use_tor
        )
        tor_check.pack(anchor=tk.W)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        def start_conversation():
            # Get model (custom or selected)
            model = custom_entry.get().strip() or model_var.get()
            if not model:
                messagebox.showerror("Error", "Please select or enter a model!")
                return

            self.current_model.set(model)
            dialog.destroy()

            # Initialize conversation
            self.initialize_conversation()

        ttk.Button(button_frame, text="Start", command=start_conversation).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)

    def initialize_conversation(self):
        try:
            # Create client
            if self.use_tor.get():
                try:
                    import httpx
                    transport = httpx.HTTPTransport(proxy="socks5://localhost:9050")
                    http_client = httpx.Client(transport=transport, timeout=30.0)

                    self.client = OpenAI(
                        base_url="https://api.routstr.com/v1",
                        api_key=self.api_key.get(),
                        http_client=http_client
                    )

                    status_text = f"Connected to {self.current_model.get()} [TOR]"
                    self.status_label.config(text=status_text, foreground=self.themes[self.theme.get()]['tor'])

                except ImportError:
                    messagebox.showerror("Error", "httpx[socks] is required for Tor support!\nInstall with: pip install httpx[socks]")
                    return
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to connect via Tor: {e}\nEnsure Tor SOCKS5 proxy is running on localhost:9050")
                    return
            else:
                self.client = OpenAI(
                    base_url="https://api.routstr.com/v1",
                    api_key=self.api_key.get()
                )
                status_text = f"Connected to {self.current_model.get()}"
                self.status_label.config(text=status_text, foreground=self.themes[self.theme.get()]['success'])

            # Initialize conversation
            self.messages = [{"role": "system", "content": "You are a helpful AI assistant."}]
            self.total_tokens = 0
            self.conversation_active = True

            # Enable input
            self.toggle_input_state(True)

            # Add welcome message
            self.add_system_message(f"Conversation started with {self.current_model.get()}")
            if self.use_tor.get():
                self.add_system_message("🧅 Traffic is being routed through Tor - Your IP address is now hidden", tag='tor')

        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize conversation: {e}")

    def toggle_input_state(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.input_text.configure(state=state)
        self.send_button.configure(state=state)
        self.clear_button.configure(state=state)

    def handle_return(self, event):
        if not event.state & 0x1:  # Not Shift key
            self.send_message()
            return 'break'

    def send_message(self):
        if not self.conversation_active:
            messagebox.showwarning("Warning", "Please start a new conversation first!")
            return

        message = self.input_text.get(1.0, tk.END).strip()
        if not message:
            return

        # Clear input
        self.clear_input()

        # Add to display
        self.add_message("You", message, 'user')

        # Add to conversation history
        self.messages.append({"role": "user", "content": message})

        # Disable input during processing
        self.toggle_input_state(False)

        # Start streaming in thread
        thread = threading.Thread(target=self.stream_response, daemon=True)
        thread.start()

    def stream_response(self):
        try:
            # Add separator and spacing before assistant message
            self.chat_display.configure(state=tk.NORMAL)
            self.chat_display.insert(tk.END, "\n")
            self.chat_display.insert(tk.END, "─" * 80 + "\n", 'separator')
            self.chat_display.insert(tk.END, "\n")
            self.chat_display.insert(tk.END, "Assistant: ", 'assistant')
            self.chat_display.configure(state=tk.DISABLED)
            self.chat_display.see(tk.END)

            # Create streaming request
            stream = self.client.chat.completions.create(
                model=self.current_model.get(),
                messages=self.messages,
                stream=True,
                stream_options={"include_usage": True}
            )

            # Collect response
            assistant_message = ""
            last_chunk_tokens = 0

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    assistant_message += content

                    # Update display in main thread
                    self.root.after(0, self.append_to_display, content)

                # Get token usage
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    last_chunk_tokens = chunk.usage.total_tokens

            # Add to conversation history
            self.messages.append({"role": "assistant", "content": assistant_message})

            # Update tokens
            self.total_tokens += last_chunk_tokens
            self.root.after(0, self.update_token_display, last_chunk_tokens)
            
            # Add extra line after assistant message
            self.root.after(0, self.append_to_display, "\n")

            # Re-enable input
            self.root.after(0, self.toggle_input_state, True)

        except Exception as e:
            error_msg = f"Error: {e}"
            self.root.after(0, self.add_system_message, error_msg, 'error')
            self.root.after(0, self.toggle_input_state, True)

            # Remove failed user message
            if self.messages and self.messages[-1]['role'] == 'user':
                self.messages.pop()

    def append_to_display(self, content):
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.insert(tk.END, content)
        self.chat_display.configure(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def update_token_display(self, last_tokens):
        self.token_label.config(text=f"Last: {last_tokens} tokens | Total: {self.total_tokens} tokens")

    def add_message(self, sender, message, tag):
        self.chat_display.configure(state=tk.NORMAL)
        
        # Check if this is the first message to avoid separator at the beginning
        if self.chat_display.get("1.0", "end-1c").strip():
            # Add separator and spacing
            self.chat_display.insert(tk.END, "\n")
            self.chat_display.insert(tk.END, "─" * 80 + "\n", 'separator')
            self.chat_display.insert(tk.END, "\n")

        # Add timestamp if tor
        if self.use_tor.get() and sender == "You":
            self.chat_display.insert(tk.END, f"{sender} [TOR]: ", tag)
        else:
            self.chat_display.insert(tk.END, f"{sender}: ", tag)

        self.chat_display.insert(tk.END, message)
        self.chat_display.insert(tk.END, "\n")  # Add extra line after message
        self.chat_display.configure(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def add_system_message(self, message, tag='system'):
        self.chat_display.configure(state=tk.NORMAL)
        
        # Check if this is the first message to avoid separator at the beginning
        if self.chat_display.get("1.0", "end-1c").strip():
            # Add separator and spacing
            self.chat_display.insert(tk.END, "\n")
            self.chat_display.insert(tk.END, "─" * 80 + "\n", 'separator')
            self.chat_display.insert(tk.END, "\n")
        
        self.chat_display.insert(tk.END, f"[{message}]\n", tag)
        self.chat_display.insert(tk.END, "\n")  # Add extra line after message
        self.chat_display.configure(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def clear_input(self):
        self.input_text.delete(1.0, tk.END)

    def show_how_to_use(self):
        howto_window = tk.Toplevel(self.root)
        howto_window.title("How to Use pyRoutstr")
        howto_window.geometry("1400x1200")
        howto_window.transient(self.root)
        howto_window.grab_set()
        howto_window.resizable(False, False)

        # Apply theme
        theme = self.themes[self.theme.get()]
        howto_window.configure(bg=theme['bg'])

        # Main container with padding
        main_frame = tk.Frame(howto_window, bg=theme['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=60, pady=40)

        # Title
        title_label = tk.Label(
            main_frame,
            text="How to Use pyRoutstr",
            font=('Consolas', 28, 'bold'),
            bg=theme['bg'],
            fg=theme['highlight']
        )
        title_label.pack(pady=(0, 40))

        # Steps container
        steps_frame = tk.Frame(main_frame, bg=theme['bg'])
        steps_frame.pack(fill=tk.BOTH, expand=True)

        # Steps
        steps = [
            ("1.", "Sign up on Routstr using Nostr:", "https://chat.routstr.com"),
            ("2.", "Go to Settings > Wallet, and deposit funds via Lightning or Cashu.", None),
            ("3.", "In Settings > API Keys, create a new key and link some funds to it.", None),
            ("4.", "Copy the API key into pyRoutstr's settings.", None),
            ("5.", "Start a conversation by selecting a model from the defaults or from", "https://www.routstr.com/models"),
            ("6.", "Optional: Enable Tor routing to protect your IP (ensure Tor is running on localhost:9050).", None)
        ]

        for step_num, step_text, link_url in steps:
            step_frame = tk.Frame(steps_frame, bg=theme['bg'])
            step_frame.pack(anchor=tk.W, pady=15, fill=tk.X)

            # Step number with circle background
            num_frame = tk.Frame(step_frame, bg=theme['highlight'], width=40, height=40)
            num_frame.pack(side=tk.LEFT, anchor=tk.N, padx=(0, 20))
            num_frame.pack_propagate(False)

            num_label = tk.Label(
                num_frame,
                text=step_num[0],  # Just the number
                font=('Consolas', 16, 'bold'),
                bg=theme['highlight'],
                fg='white'
            )
            num_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

            # Step content frame
            content_frame = tk.Frame(step_frame, bg=theme['bg'])
            content_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # Step text
            text_label = tk.Label(
                content_frame,
                text=step_text,
                font=('Consolas', 14),
                bg=theme['bg'],
                fg=theme['fg'],
                justify=tk.LEFT,
                wraplength=800
            )
            text_label.pack(anchor=tk.W)

            # Add link if provided
            if link_url:
                link_label = tk.Label(
                    content_frame,
                    text=link_url,
                    font=('Consolas', 13, 'underline'),
                    bg=theme['bg'],
                    fg=theme['highlight'],
                    cursor="hand2"
                )
                link_label.pack(anchor=tk.W, pady=(5, 0))
                link_label.bind("<Button-1>", lambda e, url=link_url: self.open_url(url))

        # Close button
        close_btn = tk.Button(
            howto_window,
            text="Got it!",
            font=('Consolas', 12, 'bold'),
            bg=theme['button_bg'],
            fg=theme['button_fg'],
            activebackground=theme['highlight'],
            width=15,
            command=howto_window.destroy
        )
        close_btn.pack(pady=30)

    def show_about(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("About pyRoutstr")
        about_window.geometry("2200x1200")
        about_window.transient(self.root)
        about_window.grab_set()
        about_window.resizable(False, False)

        # Apply theme
        theme = self.themes[self.theme.get()]
        about_window.configure(bg=theme['bg'])

        # Main container with padding
        main_frame = tk.Frame(about_window, bg=theme['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

        # Title
        title_label = tk.Label(
            main_frame,
            text="pyRoutstr",
            font=('Consolas', 32, 'bold'),
            bg=theme['bg'],
            fg=theme['highlight']
        )
        title_label.pack(pady=(0, 5))

        # Version
        version_label = tk.Label(
            main_frame,
            text="v1.0",
            font=('Consolas', 16),
            bg=theme['bg'],
            fg=theme['fg']
        )
        version_label.pack(pady=(0, 20))

        # Tagline
        tagline_label = tk.Label(
            main_frame,
            text="✨ Nothing beats reality ✨",
            font=('Consolas', 14, 'italic'),
            bg=theme['bg'],
            fg=theme['warning']
        )
        tagline_label.pack(pady=(0, 30))

        # Description
        desc_label = tk.Label(
            main_frame,
            text="A GUI client for Routstr\nvibe-coded with Claude Opus 4",
            font=('Consolas', 12),
            bg=theme['bg'],
            fg=theme['fg'],
            justify=tk.CENTER
        )
        desc_label.pack(pady=(0, 30))

        # New description section with frame for better organization
        desc_frame = tk.Frame(main_frame, bg=theme['bg'])
        desc_frame.pack(fill=tk.X, pady=(0, 30))

        # Main description
        main_desc = tk.Label(
            desc_frame,
            text="Access the best proprietary and open-source AI models—no personal info, no monthly subscriptions.\nStarts as low as 500 SATS.",
            font=('Consolas', 12),
            bg=theme['bg'],
            fg=theme['fg'],
            justify=tk.CENTER
        )
        main_desc.pack(pady=(0, 20))

        # Features frame
        features_frame = tk.Frame(desc_frame, bg=theme['bg'])
        features_frame.pack()

        # Features
        features = [
            ("⚡", "Pay-per-use", "Lightning & Cashu, pay only for what you use"),
            ("🔐", "Zero KYC", "Private signup via Nostr, keep your identity hidden"),
            ("🌐", "Decentralized", "Independent providers, no central control"),
            ("🕵️", "Anonymous", "Tor integration masks your IP")
        ]

        for emoji, title, desc in features:
            feature_frame = tk.Frame(features_frame, bg=theme['bg'])
            feature_frame.pack(anchor=tk.W, pady=5)

            # Emoji
            emoji_label = tk.Label(
                feature_frame,
                text=emoji,
                font=('Consolas', 16),
                bg=theme['bg'],
                fg=theme['fg']
            )
            emoji_label.pack(side=tk.LEFT, padx=(0, 10))

            # Title
            title_label = tk.Label(
                feature_frame,
                text=title,
                font=('Consolas', 12, 'bold'),
                bg=theme['bg'],
                fg=theme['highlight']
            )
            title_label.pack(side=tk.LEFT, padx=(0, 10))

            # Bullet point
            bullet_label = tk.Label(
                feature_frame,
                text="•",
                font=('Consolas', 12),
                bg=theme['bg'],
                fg=theme['fg']
            )
            bullet_label.pack(side=tk.LEFT, padx=(0, 10))

            # Description
            desc_label = tk.Label(
                feature_frame,
                text=desc,
                font=('Consolas', 11),
                bg=theme['bg'],
                fg=theme['fg']
            )
            desc_label.pack(side=tk.LEFT)

        # Powered by section
        powered_label = tk.Label(
            desc_frame,
            text="Powered by Bitcoin, Cashu, Nostr and Routstr.",
            font=('Consolas', 12, 'italic'),
            bg=theme['bg'],
            fg=theme['success']
        )
        powered_label.pack(pady=(20, 0))

        # Links frame
        links_frame = tk.Frame(main_frame, bg=theme['bg'])
        links_frame.pack(fill=tk.X, pady=(20, 0))

        # GitHub link
        github_frame = tk.Frame(links_frame, bg=theme['bg'])
        github_frame.pack(anchor=tk.W, pady=5)

        github_label = tk.Label(
            github_frame,
            text="Source:",
            font=('Consolas', 11, 'bold'),
            bg=theme['bg'],
            fg=theme['fg']
        )
        github_label.pack(side=tk.LEFT, padx=(0, 10))

        github_link = tk.Label(
            github_frame,
            text="github.com/alexandre-pecorilla/pyRoutstr",
            font=('Consolas', 11, 'underline'),
            bg=theme['bg'],
            fg=theme['highlight'],
            cursor="hand2"
        )
        github_link.pack(side=tk.LEFT)
        github_link.bind("<Button-1>", lambda e: self.open_url("https://github.com/alexandre-pecorilla/pyRoutstr"))

        # Author
        author_frame = tk.Frame(links_frame, bg=theme['bg'])
        author_frame.pack(anchor=tk.W, pady=5)

        author_label = tk.Label(
            author_frame,
            text="Author:",
            font=('Consolas', 11, 'bold'),
            bg=theme['bg'],
            fg=theme['fg']
        )
        author_label.pack(side=tk.LEFT, padx=(0, 10))

        author_name = tk.Label(
            author_frame,
            text="Alex Pecorilla",
            font=('Consolas', 11),
            bg=theme['bg'],
            fg=theme['fg']
        )
        author_name.pack(side=tk.LEFT)

        # Nostr key (in a frame for better layout)
        nostr_frame = tk.Frame(links_frame, bg=theme['bg'])
        nostr_frame.pack(anchor=tk.W, pady=5)

        nostr_label = tk.Label(
            nostr_frame,
            text="Nostr:",
            font=('Consolas', 11, 'bold'),
            bg=theme['bg'],
            fg=theme['fg']
        )
        nostr_label.pack(side=tk.LEFT, padx=(0, 10))

        # Nostr key in smaller font to fit
        nostr_key = tk.Label(
            nostr_frame,
            text="npub1t9ak286ttdxf0njjf8nmvazhyvxx72xeazx7n2udcg0h5dy7e68sl8dw5g",
            font=('Consolas', 9),
            bg=theme['bg'],
            fg=theme['tor'],
            cursor="hand2"
        )
        nostr_key.pack(side=tk.LEFT)
        nostr_key.bind("<Button-1>", self.copy_nostr_key)

        # Tooltip for nostr key
        self.create_tooltip(nostr_key, "Click to copy")

        # Close button
        close_btn = tk.Button(
            about_window,
            text="Close",
            font=('Consolas', 11),
            bg=theme['button_bg'],
            fg=theme['button_fg'],
            activebackground=theme['highlight'],
            width=10,
            command=about_window.destroy
        )
        close_btn.pack(pady=20)

    def open_url(self, url):
        import webbrowser
        webbrowser.open(url)

    def copy_nostr_key(self, event):
        self.root.clipboard_clear()
        self.root.clipboard_append("npub1t9ak286ttdxf0njjf8nmvazhyvxx72xeazx7n2udcg0h5dy7e68sl8dw5g")
        self.add_system_message("Nostr key copied to clipboard!")

    def create_tooltip(self, widget, text):
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")

            theme = self.themes[self.theme.get()]
            label = tk.Label(
                tooltip,
                text=text,
                font=('Consolas', 9),
                bg=theme['bg'],
                fg=theme['fg'],
                relief=tk.SOLID,
                borderwidth=1
            )
            label.pack()
            widget.tooltip = tooltip

        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def save_conversation(self):
        if not self.messages:
            messagebox.showinfo("Info", "No conversation to save!")
            return

        # Ask for file location
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = f"chat_{self.current_model.get().replace('/', '_')}_{timestamp}.json"

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=default_filename
        )

        if filename:
            try:
                conversation_data = {
                    "model": self.current_model.get(),
                    "timestamp": datetime.now().isoformat(),
                    "messages": self.messages,
                    "total_tokens": self.total_tokens,
                    "used_tor": self.use_tor.get()
                }

                with open(filename, 'w') as f:
                    json.dump(conversation_data, f, indent=2)

                self.add_system_message(f"Conversation saved to {os.path.basename(filename)}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to save conversation: {e}")

def main():
    # Check for httpx if planning to use Tor
    try:
        import httpx
    except ImportError:
        print("Warning: httpx[socks] not installed. Tor support will not be available.")
        print("Install with: pip install httpx[socks]")

    root = tk.Tk()
    app = ChatGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

