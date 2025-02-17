import os
import base64
import hashlib
import random
import struct
from tkinter import filedialog
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

class Encoder:
    @staticmethod
    def _generate_keystream(key_hash, length):
        """Generate a deterministic keystream using SHA-256 hash expansion"""
        keystream = bytearray()
        hash_len = len(key_hash)
        for i in range(length):
            keystream.append(key_hash[(i * 7) % hash_len] ^ key_hash[(i * 3) % hash_len])
        return bytes(keystream)

    @staticmethod
    def _create_sboxes(key_seed):
        """Create shuffled substitution boxes using cryptographic mixing"""
        random.seed(key_seed)
        sbox = list(range(256))
        for _ in range(8):
            random.shuffle(sbox)
        
        inv_sbox = [0] * 256
        for i, val in enumerate(sbox):
            inv_sbox[val] = i
            
        return sbox, inv_sbox

    @staticmethod
    def encode(data: bytes, key: str) -> bytes:
        """Multi-layer encoding algorithm"""
        key_hash = hashlib.sha256(key.encode()).digest()
        sbox, _ = Encoder._create_sboxes(struct.unpack('>I', key_hash[:4])[0])
        
        # Phase 1: XOR with dynamic keystream
        keystream = Encoder._generate_keystream(key_hash, len(data))
        xored = bytes([b ^ k for b, k in zip(data, keystream)])
        
        # Phase 2: S-Box substitution
        substituted = bytes([sbox[b] for b in xored])
        
        # Phase 3: Bit rotation
        rotated = bytes([((b << 3) | (b >> 5)) & 0xff for b in substituted])
        
        # Phase 4: Reverse entire sequence
        return rotated[::-1]

    @staticmethod
    def decode(data: bytes, key: str) -> bytes:
        """Inverse of the encoding process"""
        key_hash = hashlib.sha256(key.encode()).digest()
        _, inv_sbox = Encoder._create_sboxes(struct.unpack('>I', key_hash[:4])[0])
        
        # Reverse phase 4
        reversed_data = data[::-1]
        
        # Reverse phase 3
        unrotated = bytes([((b >> 3) | (b << 5)) & 0xff for b in reversed_data])
        
        # Reverse phase 2
        unsubstituted = bytes([inv_sbox[b] for b in unrotated])
        
        # Reverse phase 1
        keystream = Encoder._generate_keystream(key_hash, len(unsubstituted))
        return bytes([b ^ k for b, k in zip(unsubstituted, keystream)])

class CryptographicApp:
    def __init__(self):
        self.root = tb.Window(title="Crypticoder", themename="superhero")
        self.root.geometry("1000x750")
        self._setup_ui()

    def _setup_ui(self):
        """Create and arrange GUI components"""
        main_frame = tb.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        # Key Entry
        key_frame = tb.Frame(main_frame)
        tb.Label(key_frame, text="Cryptographic Key:").pack(side=LEFT)
        self.key_entry = tb.Entry(key_frame, show="●", width=50)
        self.key_entry.pack(side=LEFT, padx=10)
        key_frame.pack(fill=X, pady=10)

        # Mode Notebook
        self.notebook = tb.Notebook(main_frame)
        self._setup_text_tab()
        self._setup_file_tab()
        self.notebook.pack(fill=BOTH, expand=True)

        # Status Bar
        self.status_bar = tb.Label(main_frame, bootstyle="inverse-primary")
        self.status_bar.pack(fill=X, pady=10)

    def _setup_text_tab(self):
        """Create text encoding tab"""
        text_tab = tb.Frame(self.notebook)
        
        # Input
        input_frame = tb.Frame(text_tab)
        tb.Label(input_frame, text="Input Text:").pack(anchor=W)
        self.input_text = tb.ScrolledText(input_frame, height=10)
        self.input_text.pack(fill=BOTH, expand=True)
        input_frame.pack(fill=BOTH, expand=True, pady=5)

        # Controls
        btn_frame = tb.Frame(text_tab)
        tb.Button(btn_frame, text="Encode", command=self._encode_text,
                 bootstyle="success").pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Decode", command=self._decode_text,
                 bootstyle="warning").pack(side=LEFT, padx=5)
        btn_frame.pack(pady=10)

        # Output
        output_frame = tb.Frame(text_tab)
        tb.Label(output_frame, text="Result:").pack(anchor=W)
        self.output_text = tb.ScrolledText(output_frame, height=10)
        self.output_text.pack(fill=BOTH, expand=True)
        output_frame.pack(fill=BOTH, expand=True, pady=5)

        self.notebook.add(text_tab, text="Text Encoding")

    def _setup_file_tab(self):
        """Create file encoding tab"""
        file_tab = tb.Frame(self.notebook)
        
        # File Selection
        file_sel_frame = tb.Frame(file_tab)
        tb.Label(file_sel_frame, text="Select File:").pack(side=LEFT)
        self.file_entry = tb.Entry(file_sel_frame, width=60)
        self.file_entry.pack(side=LEFT, padx=10)
        tb.Button(file_sel_frame, text="Browse", command=self._browse_file,
                 bootstyle="secondary").pack(side=LEFT)
        file_sel_frame.pack(fill=X, pady=10)

        # Progress
        self.progress = tb.Progressbar(file_tab, bootstyle="striped")
        self.progress.pack(fill=X, pady=5)

        # Controls
        btn_frame = tb.Frame(file_tab)
        tb.Button(btn_frame, text="Encode File", command=self._encode_file,
                 bootstyle="success").pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Decode File", command=self._decode_file,
                 bootstyle="warning").pack(side=LEFT, padx=5)
        btn_frame.pack(pady=10)

        self.notebook.add(file_tab, text="File Encoding")

    def _update_status(self, message, success=True):
        """Update status bar with message"""
        self.status_bar.config(text=message)
        self.root.update_idletasks()

    def _browse_file(self):
        """Handle file selection dialog"""
        path = filedialog.askopenfilename()
        if path:
            self.file_entry.delete(0, END)
            self.file_entry.insert(0, path)

    def _validate_key(self):
        """Validate encryption key input"""
        key = self.key_entry.get()
        if not key:
            messagebox.showerror("Error", "Encryption key is required")
            return False
        return True

    def _encode_text(self):
        """Handle text encoding"""
        if not self._validate_key():
            return
            
        try:
            input_data = self.input_text.get("1.0", "end-1c")
            encoded = Encoder.encode(input_data.encode(), self.key_entry.get())
            b64_encoded = base64.b64encode(encoded).decode()
            self.output_text.config(state="normal")
            self.output_text.delete("1.0", END)
            self.output_text.insert("1.0", b64_encoded)
            self._update_status("Text encoded successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Encoding failed: {str(e)}")

    def _decode_text(self):
        """Handle text decoding"""
        if not self._validate_key():
            return
            
        try:
            b64_data = self.output_text.get("1.0", "end-1c")
            decoded = Encoder.decode(base64.b64decode(b64_data), self.key_entry.get())
            self.input_text.delete("1.0", END)
            self.input_text.insert("1.0", decoded.decode())
            self._update_status("Text decoded successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Decoding failed: {str(e)}")

    def _process_file(self, mode):
        """Common file processing logic"""
        if not self._validate_key():
            return
            
        path = self.file_entry.get()
        if not path:
            messagebox.showerror("Error", "No file selected")
            return
            
        try:
            with open(path, "rb") as f:
                data = f.read()
                
            self.progress["value"] = 33
            result = Encoder.encode(data, self.key_entry.get()) if mode == "encode" \
                    else Encoder.decode(data, self.key_entry.get())
            self.progress["value"] = 66
            
            ext = ".enc" if mode == "encode" else ".dec"
            output_path = f"{os.path.splitext(path)[0]}{ext}"
            with open(output_path, "wb") as f:
                f.write(result)
                
            self.progress["value"] = 100
            self._update_status(f"File {mode}d successfully: {output_path}")
            messagebox.showinfo("Success", f"File {mode}d successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"File processing failed: {str(e)}")
        finally:
            self.progress["value"] = 0

    def _encode_file(self):
        self._process_file("encode")

    def _decode_file(self):
        self._process_file("decode")

if __name__ == "__main__":
    app = CryptographicApp()
    app.root.mainloop()