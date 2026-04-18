import hashlib
import tkinter as tk
from tkinter import messagebox
from gui.theme import THEME, get_font

class SecurityManager:
    """
    Manages security context for the application.
    Handles authentication state, locking mechanisms, and credential verification.
    """
    

    _PASSCODE_HASH = "07334386287751ba02a4588c1a0875dbd074a61bd9e6ab7c48d244eacd0c99e0"
    
    def __init__(self):
        self._is_locked = False
        self._is_authenticated = False
    
    @property
    def is_locked(self) -> bool:
        """Return True if the system is locked due to failed auth."""
        return self._is_locked
    
    @property
    def is_authenticated(self) -> bool:
        """Return True if the user has successfully authenticated."""
        return self._is_authenticated
    
    def check_passcode(self, input_code: str) -> bool:
        """
        Verify the input passcode against the stored hash.
        """
        if self._is_locked:
            return False
            
        # calculate hash
        input_hash = hashlib.sha256(input_code.encode()).hexdigest()
        
        if input_hash == self._PASSCODE_HASH:
            self._is_authenticated = True
            return True
        else:
            self._is_locked = True
            return False

    def lock(self):
        """Force lock the system."""
        self._is_locked = True
        self._is_authenticated = False

    def reset_lock_debug(self):
        """Debug method to reset lock (not exposed in production UI)."""
        self._is_locked = False
    
    def verify_developer_access(self, parent) -> bool:
        """
        Verify developer access with password dialog.
        Returns True if authenticated, False otherwise.
        """
        if self._is_authenticated:
            return True
        
        if self._is_locked:
            messagebox.showerror("Access Denied", 
                "⛔ System is locked.\nRestart application to retry.")
            return False
        
        # Show passcode dialog
        result = [False]
        
        def on_success():
            result[0] = True
        
        dialog = PasscodeDialog(parent, self, on_success)
        parent.wait_window(dialog.window)
        
        return result[0]


class PasscodeDialog:
    """
    Secure modal dialog for passcode entry.
    """
    def __init__(self, parent, security_manager: SecurityManager, on_success):
        self.parent = parent
        self.security_manager = security_manager
        self.on_success = on_success
        
        self.window = tk.Toplevel(parent)
        self.window.title("🔒 Security Access")
        self.window.geometry("400x250")
        self.window.configure(bg=THEME.bg_dark)
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center the window
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        self._build_ui()
        
    def _build_ui(self):
        # Header
        tk.Label(self.window, text="🔒 RESTRICTED ACCESS", 
                 font=get_font("lg", "bold"), fg=THEME.red, bg=THEME.bg_dark).pack(pady=(25, 10))
                 
        tk.Label(self.window, text="Enter Developer Passcode", 
                 font=get_font("sm"), fg=THEME.fg, bg=THEME.bg_dark).pack(pady=(0, 20))
        
        # Input
        self.entry = tk.Entry(self.window, show="●", font=get_font("xl", mono=True),
                              width=10, justify='center',
                              bg=THEME.bg_highlight, fg=THEME.white, 
                              insertbackground=THEME.white, relief=tk.FLAT)
        self.entry.pack(ipady=8, pady=(0, 20))
        self.entry.focus_set()
        self.entry.bind('<Return>', lambda e: self._verify())
        
        # Verify Button
        btn_frame = tk.Frame(self.window, bg=THEME.bg_dark)
        btn_frame.pack(fill=tk.X, padx=40)
        
        tk.Button(btn_frame, text="AUTHENTICATE", font=get_font("sm", "bold"),
                  bg=THEME.cyan, fg=THEME.black,
                  activebackground=THEME.green, activeforeground=THEME.black,
                  relief=tk.FLAT, cursor='hand2',
                  command=self._verify).pack(fill=tk.X, ipady=5)

    def _verify(self):
        code = self.entry.get()
        if self.security_manager.check_passcode(code):
            self.window.destroy()
            self.on_success()
        else:
            self.window.destroy()
            messagebox.showerror("Access Denied", "⛔ INVALID PASSCODE\n\nSecurity Lockout Initiated.\nApplication restart required to retry.")
            # The parent UI needs to handle the visual lockout state update
