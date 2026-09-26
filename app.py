from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import pymupdf
from PIL import Image, ImageTk
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(sys._MEIPASS)
    APP_DIR = (
        Path.home() / "Documents" / "AMMDF"
        if sys.platform == "darwin"
        else Path(sys.executable).resolve().parent
    )
else:
    APP_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = APP_DIR
FILES_DIR = APP_DIR / "files"
LOGO_PATH = RESOURCE_DIR / "images" / "logo.jpg"
PAGE_COLUMNS = 2
PAGE_ROWS = 7
LABELS_PER_PAGE = PAGE_COLUMNS * PAGE_ROWS
PAGE_MARGIN = 10 * mm
PDF_FONT_SIZE = 12


def draw_fitted_centered_text(
    pdf: canvas.Canvas,
    text: str,
    left: float,
    y: float,
    width: float,
    font_name: str,
) -> None:
    text_width = pdf.stringWidth(text, font_name, PDF_FONT_SIZE)
    horizontal_scale = min(1, width / text_width) if text_width else 1
    center = left + width / 2
    pdf.saveState()
    pdf.translate(center * (1 - horizontal_scale), 0)
    pdf.scale(horizontal_scale, 1)
    pdf.setFont(font_name, PDF_FONT_SIZE)
    pdf.drawCentredString(center, y, text)
    pdf.restoreState()


def create_sheet_pdf(output_path: Path, labels: list[tuple[str, str]]) -> None:
    page_width, page_height = A4
    cell_width = (page_width - 2 * PAGE_MARGIN) / PAGE_COLUMNS
    cell_height = (page_height - 2 * PAGE_MARGIN) / PAGE_ROWS
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    logo = ImageReader(str(LOGO_PATH)) if LOGO_PATH.is_file() else None

    for index, (lot, emplacement) in enumerate(labels):
        page_index, page_position = divmod(index, LABELS_PER_PAGE)
        if page_index and page_position == 0:
            pdf.showPage()
        row, column = divmod(page_position, PAGE_COLUMNS)
        left = PAGE_MARGIN + column * cell_width
        bottom = page_height - PAGE_MARGIN - (row + 1) * cell_height
        pdf.setLineWidth(0.6)
        pdf.rect(left, bottom, cell_width, cell_height)

        inset = 5
        logo_width = 57
        logo_height = cell_height - inset * 2
        if logo:
            image_width, image_height = logo.getSize()
            scale = min(logo_width / image_width, logo_height / image_height)
            drawn_width = image_width * scale
            drawn_height = image_height * scale
            pdf.drawImage(
                logo,
                left + inset + (logo_width - drawn_width) / 2,
                bottom + (cell_height - drawn_height) / 2,
                width=drawn_width,
                height=drawn_height,
                preserveAspectRatio=True,
                mask="auto",
            )

        text_left = left + inset + logo_width + 5
        text_right = left + cell_width - inset
        text_width = text_right - text_left
        heading_y = bottom + cell_height - 13
        for heading in ("ASSOCIATION", "MOTARDS ET MOTARDS DE FRANCE"):
            draw_fitted_centered_text(pdf, heading, text_left, heading_y, text_width, "Helvetica-Bold")
            heading_y -= 14

        fields = (("VOTRE LOT :", lot), ("EMPLACEMENT :", emplacement))
        field_y = bottom + cell_height * 0.43
        for label, value in fields:
            pdf.setFont("Helvetica-Bold", PDF_FONT_SIZE)
            pdf.drawString(text_left, field_y, label)
            value_left = text_left + pdf.stringWidth(label, "Helvetica-Bold", PDF_FONT_SIZE) + 4
            value_width = max(0, text_right - value_left)
            pdf.saveState()
            pdf.setDash(1, 2)
            pdf.line(value_left, field_y - 1, text_right, field_y - 1)
            pdf.restoreState()
            if value and value_width > 0:
                draw_fitted_centered_text(pdf, value[:100], value_left, field_y + 1, value_width, "Helvetica")
            field_y -= 14

    pdf.save()


def print_pdf_to_printer(pdf_path: Path, printer_name: str, copies: int = 1) -> None:
    if sys.platform == "darwin":
        try:
            subprocess.run(
                [
                    "lp",
                    "-d",
                    printer_name,
                    "-n",
                    str(copies),
                    "-o",
                    "media=A4",
                    "-o",
                    "fit-to-page",
                    str(pdf_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as error:
            detail = error.stderr.strip() or error.stdout.strip() or str(error)
            raise RuntimeError(f"CUPS n’a pas pu imprimer le document : {detail}") from error
        return

    if sys.platform != "win32":
        raise OSError("L'impression directe est disponible uniquement sous Windows et macOS.")

    import win32con
    import win32ui
    from PIL import ImageWin

    document = pymupdf.open(str(pdf_path))
    printer_dc = win32ui.CreateDC()
    try:
        printer_dc.CreatePrinterDC(printer_name)
        printable_width = printer_dc.GetDeviceCaps(win32con.HORZRES)
        printable_height = printer_dc.GetDeviceCaps(win32con.VERTRES)
        for copy_number in range(copies):
            printer_dc.StartDoc(f"{pdf_path.stem} ({copy_number + 1}/{copies})")
            try:
                for page_index in range(len(document)):
                    page = document.load_page(page_index)
                    page_rect = page.rect
                    fit_scale = min(printable_width / page_rect.width, printable_height / page_rect.height)
                    render_scale = min(fit_scale, 300 / 72)
                    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(render_scale, render_scale), alpha=False)
                    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                    dib = ImageWin.Dib(image)
                    target_width = round(page_rect.width * fit_scale)
                    target_height = round(page_rect.height * fit_scale)
                    left = (printable_width - target_width) // 2
                    top = (printable_height - target_height) // 2

                    printer_dc.StartPage()
                    dib.draw(
                        printer_dc.GetHandleOutput(),
                        (left, top, left + target_width, top + target_height),
                    )
                    printer_dc.EndPage()
                    del page
                    pixmap = None
                    dib = None
                    image.close()
            except Exception:
                printer_dc.AbortDoc()
                raise
            else:
                printer_dc.EndDoc()
    finally:
        printer_dc.DeleteDC()
        document.close()


def get_available_printers() -> tuple[list[str], str]:
    if sys.platform == "win32":
        import win32print

        printer_flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        names = sorted(item["pPrinterName"] for item in win32print.EnumPrinters(printer_flags, None, 2))
        try:
            default_name = win32print.GetDefaultPrinter()
        except win32print.error:
            default_name = ""
        if default_name and default_name not in names:
            names.insert(0, default_name)
        return names, default_name

    if sys.platform == "darwin":
        printers = subprocess.run(["lpstat", "-p"], capture_output=True, text=True, check=True)
        names = sorted(
            line[len("printer "):].partition(" is ")[0]
            for line in printers.stdout.splitlines()
            if line.startswith("printer ") and " is " in line
        )
        default = subprocess.run(["lpstat", "-d"], capture_output=True, text=True, check=False)
        default_name = default.stdout.partition(":")[2].strip()
        if default_name not in names:
            default_name = names[0] if names else ""
        return names, default_name

    raise OSError("Les imprimantes sont prises en charge uniquement sous Windows et macOS.")


def center_window(window: tk.Toplevel) -> None:
    window.update_idletasks()
    x = max(0, (window.winfo_screenwidth() - window.winfo_width()) // 2)
    y = max(0, (window.winfo_screenheight() - window.winfo_height()) // 2)
    window.geometry(f"+{x}+{y}")


class PrintPreviewWindow:
    def __init__(self, parent: tk.Tk, pdf_path: Path, print_callback, close_callback) -> None:
        self.pdf_path = pdf_path
        self.print_callback = print_callback
        self.close_callback = close_callback
        self.document = pymupdf.open(str(pdf_path))
        self.page_index = 0
        self.preview_image: ImageTk.PhotoImage | None = None
        self.render_job: str | None = None

        self.window = tk.Toplevel(parent)
        self.window.title("Aperçu avant impression · AMMDF")
        self.window.geometry("1120x820")
        self.window.minsize(760, 600)
        self.window.configure(background="#edf2f0")

        content = ttk.Frame(self.window, style="App.TFrame", padding=(22, 18))
        content.pack(fill="both", expand=True)
        header = ttk.Frame(content, style="App.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Aperçu avant impression", style="Header.TLabel").pack(side="left")
        self.page_status = ttk.Label(header, style="Status.TLabel")
        self.page_status.pack(side="right")

        self.canvas = tk.Canvas(content, background="#d8e0dd", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=(14, 12))
        self.canvas.bind("<Configure>", self._schedule_render)

        footer = ttk.Frame(content, style="App.TFrame")
        footer.pack(fill="x")
        self.previous_button = ttk.Button(footer, text="← Précédente", command=self.previous_page)
        self.previous_button.pack(side="left")
        self.next_button = ttk.Button(footer, text="Suivante →", command=self.next_page)
        self.next_button.pack(side="left", padx=(8, 0))
        ttk.Label(footer, text="A4 · échelle adaptée à la fenêtre", style="Subheader.TLabel").pack(
            side="left", padx=16
        )
        ttk.Button(footer, text="Fermer", command=self.close).pack(side="right")
        ttk.Button(
            footer,
            text="Choisir une imprimante…",
            style="Primary.TButton",
            command=self.print_current_document,
        ).pack(side="right", padx=(0, 8))

        self.window.bind("<Left>", self.previous_page)
        self.window.bind("<Right>", self.next_page)
        self.window.bind("<Escape>", lambda _event: self.close())
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.after_idle(self.render_page)
        self._update_page_controls()
        center_window(self.window)

    def _schedule_render(self, _event: tk.Event) -> None:
        if self.render_job is not None:
            self.window.after_cancel(self.render_job)
        self.render_job = self.window.after(100, self.render_page)

    def render_page(self) -> None:
        self.render_job = None
        if not self.window.winfo_exists():
            return
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            self.render_job = self.window.after(100, self.render_page)
            return

        page = self.document.load_page(self.page_index)
        scale = min(
            max(1, canvas_width - 48) / page.rect.width,
            max(1, canvas_height - 48) / page.rect.height,
        )
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        self.preview_image = ImageTk.PhotoImage(image)
        image.close()

        self.canvas.delete("all")
        center_x = canvas_width / 2
        center_y = canvas_height / 2
        left = center_x - pixmap.width / 2
        top = center_y - pixmap.height / 2
        self.canvas.create_rectangle(
            left + 5,
            top + 5,
            left + pixmap.width + 5,
            top + pixmap.height + 5,
            fill="#aebbb6",
            outline="",
        )
        self.canvas.create_image(center_x, center_y, image=self.preview_image, anchor="center")

    def _update_page_controls(self) -> None:
        page_count = len(self.document)
        self.page_status.configure(text=f"Page {self.page_index + 1} sur {page_count}")
        self.previous_button.configure(state="normal" if self.page_index > 0 else "disabled")
        self.next_button.configure(state="normal" if self.page_index + 1 < page_count else "disabled")

    def previous_page(self, _event: tk.Event | None = None) -> str:
        if self.page_index > 0:
            self.page_index -= 1
            self._update_page_controls()
            self.render_page()
        return "break"

    def next_page(self, _event: tk.Event | None = None) -> str:
        if self.page_index + 1 < len(self.document):
            self.page_index += 1
            self._update_page_controls()
            self.render_page()
        return "break"

    def print_current_document(self) -> None:
        self.print_callback(self.pdf_path, self.window)

    def close(self) -> None:
        if self.render_job is not None:
            self.window.after_cancel(self.render_job)
            self.render_job = None
        self.document.close()
        self.window.destroy()
        self.close_callback(self)


class PrinterManagerWindow:
    def __init__(self, parent: tk.Toplevel, pdf_path: Path) -> None:
        self.pdf_path = pdf_path
        self.window = tk.Toplevel(parent)
        self.window.title("Gestionnaire d’imprimante")
        self.window.geometry("560x390")
        self.window.minsize(500, 360)
        self.window.transient(parent)
        self.window.configure(background="#edf2f0")
        self.printing = False
        self.results: queue.Queue[Exception | None] = queue.Queue()

        content = ttk.Frame(self.window, style="App.TFrame", padding=(24, 20))
        content.pack(fill="both", expand=True)
        ttk.Label(content, text="Gestionnaire d’imprimante", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            content,
            text="Sélectionnez le périphérique et le nombre d’exemplaires.",
            style="Subheader.TLabel",
        ).pack(anchor="w", pady=(4, 18))

        settings = ttk.Frame(content, style="Surface.TFrame", padding=16)
        settings.pack(fill="x")
        ttk.Label(settings, text="IMPRIMANTE", style="Field.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        try:
            self.printer_names, default_printer = get_available_printers()
        except Exception as error:
            self.printer_names = []
            default_printer = ""
            printer_error = str(error)
        else:
            printer_error = "Aucune imprimante n’a été détectée."
        if default_printer and default_printer not in self.printer_names:
            self.printer_names.insert(0, default_printer)
        self.printer_name = tk.StringVar(value=default_printer or (self.printer_names[0] if self.printer_names else ""))
        self.printer_combo = ttk.Combobox(
            settings,
            textvariable=self.printer_name,
            values=self.printer_names,
            state="readonly",
            width=48,
        )
        self.printer_combo.grid(row=1, column=0, sticky="ew", pady=(0, 16))

        ttk.Label(settings, text="EXEMPLAIRES", style="Field.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 6))
        self.copy_count = tk.StringVar(value="1")
        ttk.Spinbox(settings, from_=1, to=99, textvariable=self.copy_count, width=8).grid(
            row=3, column=0, sticky="w"
        )
        settings.columnconfigure(0, weight=1)

        self.status = ttk.Label(content, text="Format A4 · ajusté à la zone imprimable", style="Subheader.TLabel")
        self.status.pack(anchor="w", pady=(14, 8))
        self.progress = ttk.Progressbar(content, mode="indeterminate", style="Horizontal.TProgressbar")
        self.progress.pack(fill="x")

        actions = ttk.Frame(content, style="App.TFrame")
        actions.pack(fill="x", pady=(18, 0))
        self.cancel_button = ttk.Button(actions, text="Annuler", command=self.close)
        self.cancel_button.pack(side="right", padx=(8, 0))
        self.print_button = ttk.Button(
            actions,
            text="Imprimer",
            style="Primary.TButton",
            command=self.start_print,
            state="normal" if self.printer_names else "disabled",
        )
        self.print_button.pack(side="right")

        if not self.printer_names:
            self.status.configure(text=printer_error)
        self.window.bind("<Return>", lambda _event: self.start_print())
        self.window.bind("<Escape>", lambda _event: self.close())
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        center_window(self.window)
        self.window.grab_set()

    def start_print(self) -> None:
        if self.printing:
            return
        try:
            copies = int(self.copy_count.get())
        except ValueError:
            messagebox.showwarning("Nombre invalide", "Le nombre d’exemplaires doit être un entier.", parent=self.window)
            return
        if not 1 <= copies <= 99:
            messagebox.showwarning("Nombre invalide", "Choisissez entre 1 et 99 exemplaires.", parent=self.window)
            return

        self.printing = True
        self.print_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")
        self.printer_combo.configure(state="disabled")
        self.status.configure(text=f"Envoi vers {self.printer_name.get()}…")
        self.progress.start(12)
        threading.Thread(
            target=self._print_worker,
            args=(self.printer_name.get(), copies),
            daemon=True,
        ).start()
        self.window.after(100, self._check_print_result)

    def _print_worker(self, printer_name: str, copies: int) -> None:
        try:
            print_pdf_to_printer(self.pdf_path, printer_name, copies)
            self.results.put(None)
        except Exception as error:
            self.results.put(error)

    def _check_print_result(self) -> None:
        try:
            result = self.results.get_nowait()
        except queue.Empty:
            self.window.after(100, self._check_print_result)
            return

        self.progress.stop()
        if result is not None:
            self.printing = False
            self.print_button.configure(state="normal")
            self.cancel_button.configure(state="normal")
            self.printer_combo.configure(state="readonly")
            self.status.configure(text="L’impression a échoué.")
            messagebox.showerror("Impression impossible", str(result), parent=self.window)
            return

        messagebox.showinfo(
            "Impression envoyée",
            f"{self.copy_count.get()} exemplaire(s) envoyé(s) vers :\n{self.printer_name.get()}",
            parent=self.window,
        )
        self.window.grab_release()
        self.window.destroy()

    def close(self) -> None:
        if self.printing:
            return
        self.window.grab_release()
        self.window.destroy()


class LabelApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.labels: list[tuple[str, str]] = []
        self.preview_window: PrintPreviewWindow | None = None
        self.printer_manager: PrinterManagerWindow | None = None
        root.title("Planche d'étiquettes AMMDF")
        root.geometry("960x700")
        root.minsize(760, 600)
        root.configure(background="#edf2f0")

        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("App.TFrame", background="#edf2f0")
        style.configure("Surface.TFrame", background="#ffffff")
        style.configure("Header.TLabel", background="#edf2f0", foreground="#1d2d32", font=("Segoe UI", 21, "bold"))
        style.configure("Subheader.TLabel", background="#edf2f0", foreground="#687875", font=("Segoe UI", 10))
        style.configure("Eyebrow.TLabel", background="#edf2f0", foreground="#087f76", font=("Segoe UI", 9, "bold"))
        style.configure("Badge.TLabel", background="#e1eeeb", foreground="#12665f", font=("Segoe UI", 10, "bold"))
        style.configure("Status.TLabel", background="#edf2f0", foreground="#25383c", font=("Segoe UI", 10, "bold"))
        style.configure("EmptyTitle.TLabel", background="#ffffff", foreground="#26383c", font=("Segoe UI", 15, "bold"))
        style.configure("EmptyBody.TLabel", background="#ffffff", foreground="#72807c", font=("Segoe UI", 10))
        style.configure("Field.TLabel", background="#ffffff", foreground="#354744", font=("Segoe UI", 10, "bold"))
        style.configure("InlineTitle.TLabel", background="#ffffff", foreground="#26383c", font=("Segoe UI", 13, "bold"))
        style.configure("InlineBody.TLabel", background="#ffffff", foreground="#72807c", font=("Segoe UI", 9))
        style.configure("DialogTitle.TLabel", background="#ffffff", foreground="#26383c", font=("Segoe UI", 16, "bold"))
        style.configure("DialogBody.TLabel", background="#ffffff", foreground="#72807c", font=("Segoe UI", 10))
        style.configure("Treeview", rowheight=36, font=("Segoe UI", 10), background="#ffffff", fieldbackground="#ffffff", borderwidth=0)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#e6eeeb", foreground="#435550", padding=(9, 9))
        style.map("Treeview", background=[("selected", "#cce9e3")], foreground=[("selected", "#173c36")])
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8))
        style.configure("Primary.TButton", background="#087f76", foreground="#ffffff", font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("pressed", "#075f58"), ("active", "#0a7069")])
        style.configure("Horizontal.TProgressbar", troughcolor="#dce6e2", background="#087f76", bordercolor="#dce6e2", lightcolor="#087f76", darkcolor="#087f76")
        style.configure("TEntry", padding=(8, 7))

        self._build_menu()

        main = ttk.Frame(root, style="App.TFrame", padding=(28, 22))
        main.pack(fill="both", expand=True)
        header = ttk.Frame(main, style="App.TFrame")
        header.pack(fill="x", pady=(0, 18))
        self.logo_photo = None
        if LOGO_PATH.is_file():
            logo_image = Image.open(LOGO_PATH)
            logo_image.thumbnail((58, 100), Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_image)
            ttk.Label(header, image=self.logo_photo, style="App.TLabel").pack(side="left", padx=(0, 16))

        heading = ttk.Frame(header, style="App.TFrame")
        heading.pack(side="left", fill="x", expand=True, pady=8)
        ttk.Label(heading, text="AMMDF  /  ÉTIQUETTES", style="Eyebrow.TLabel").pack(anchor="w", pady=(0, 5))
        ttk.Label(heading, text="Planche d’étiquettes", style="Header.TLabel").pack(anchor="w")
        ttk.Label(heading, text="Association Motards et Motards de France", style="Subheader.TLabel").pack(
            anchor="w", pady=(4, 0)
        )
        badge = ttk.Frame(header, style="Surface.TFrame", padding=(14, 10))
        badge.pack(side="right", anchor="center", padx=(12, 0))
        ttk.Label(badge, text="FORMAT", style="Eyebrow.TLabel").pack(anchor="e")
        ttk.Label(badge, text="A4  ·  2 × 7", style="Badge.TLabel").pack(anchor="e", pady=(3, 0))

        ttk.Separator(main).pack(fill="x", pady=(0, 16))

        self.form_visible = False
        self.entry_form = ttk.Frame(main, style="Surface.TFrame", padding=(16, 13))
        self.entry_form.columnconfigure((0, 1, 2), weight=1, uniform="entry-fields")
        ttk.Label(self.entry_form, text="Ajouter une étiquette", style="InlineTitle.TLabel").grid(
            row=0, column=0, sticky="w", columnspan=3, pady=(0, 2)
        )
        ttk.Label(
            self.entry_form,
            text="Renseignez les champs; la quantité répète la même étiquette sans être imprimée dessus.",
            style="InlineBody.TLabel",
        ).grid(row=1, column=0, sticky="w", columnspan=3, pady=(0, 10))
        ttk.Label(self.entry_form, text="VOTRE LOT", style="Field.TLabel").grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=(0, 4)
        )
        ttk.Label(self.entry_form, text="EMPLACEMENT", style="Field.TLabel").grid(
            row=2, column=1, sticky="w", padx=(10, 0), pady=(0, 4)
        )
        ttk.Label(self.entry_form, text="QUANTITÉ", style="Field.TLabel").grid(
            row=2, column=2, sticky="w", padx=(10, 0), pady=(0, 4)
        )
        self.lot_entry = ttk.Entry(self.entry_form, width=22)
        self.lot_entry.grid(row=3, column=0, sticky="ew", padx=(0, 10))
        self.location_entry = ttk.Entry(self.entry_form, width=22)
        self.location_entry.grid(row=3, column=1, sticky="ew", padx=(10, 12))
        self.quantity_value = tk.StringVar(value="1")
        self.quantity_entry = ttk.Entry(self.entry_form, textvariable=self.quantity_value, width=8)
        self.quantity_entry.grid(row=3, column=2, sticky="w", padx=(10, 12))
        self.lot_entry.bind("<Return>", self._focus_location)
        self.location_entry.bind("<Return>", self._focus_quantity)
        self.quantity_entry.bind("<Return>", lambda _event: self.save_current_label())
        form_actions = ttk.Frame(self.entry_form, style="Surface.TFrame")
        form_actions.grid(row=4, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(
            form_actions,
            text="Ajouter",
            style="Primary.TButton",
            command=self.save_current_label,
        ).pack(side="left")

        table = ttk.Frame(main, style="Surface.TFrame", padding=10)
        table.pack(fill="both", expand=True)
        self.table_panel = table
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        self.listbox = ttk.Treeview(
            table,
            columns=("number", "lot", "location"),
            show="headings",
            selectmode="browse",
            height=14,
        )
        self.listbox.heading("number", text="#")
        self.listbox.heading("lot", text="Votre lot")
        self.listbox.heading("location", text="Emplacement")
        self.listbox.column("number", width=55, anchor="center", stretch=False)
        self.listbox.column("lot", width=250)
        self.listbox.column("location", width=250)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.listbox.tag_configure("stripe", background="#f7faf8")
        vertical_scroll = ttk.Scrollbar(table, orient="vertical", command=self.listbox.yview)
        vertical_scroll.grid(row=0, column=1, sticky="ns")
        horizontal_scroll = ttk.Scrollbar(table, orient="horizontal", command=self.listbox.xview)
        horizontal_scroll.grid(row=1, column=0, sticky="ew")
        self.listbox.configure(yscrollcommand=vertical_scroll.set, xscrollcommand=horizontal_scroll.set)

        self.empty_state = ttk.Frame(table, style="Surface.TFrame")
        ttk.Label(self.empty_state, text="Aucune étiquette pour le moment", style="EmptyTitle.TLabel").pack()
        ttk.Label(
            self.empty_state,
            text="Ajoutez un lot et son emplacement pour commencer la planche.",
            style="EmptyBody.TLabel",
        ).pack(pady=(6, 14))
        ttk.Button(
            self.empty_state,
            text="Ajouter une étiquette",
            style="Primary.TButton",
            command=self.show_add_form,
        ).pack()
        self.empty_state.place(relx=0.5, rely=0.5, anchor="center")

        status = ttk.Frame(main, style="App.TFrame")
        status.pack(fill="x", pady=(14, 7))
        self.count_label = ttk.Label(status, text="0 / 14 étiquettes", style="Status.TLabel")
        self.count_label.pack(side="left")
        self.progress = ttk.Progressbar(status, maximum=LABELS_PER_PAGE, length=180, mode="determinate")
        self.progress.pack(side="right")

        actions = ttk.Frame(main, style="App.TFrame")
        actions.pack(fill="x", pady=(4, 0))
        self.delete_button = ttk.Button(actions, text="Supprimer", command=self.delete_label, state="disabled")
        self.delete_button.pack(side="left")
        self.clear_button = ttk.Button(actions, text="Vider la liste", command=self.clear_list, state="disabled")
        self.clear_button.pack(side="left", padx=(8, 0))
        self.add_button = ttk.Button(actions, text="Ajouter", style="Primary.TButton", command=self.show_add_form)
        self.add_button.pack(side="right", padx=(8, 0))
        self.print_button = ttk.Button(
            actions, text="Aperçu / imprimer", command=self.print_sheet, state="disabled"
        )
        self.print_button.pack(side="right")
        self.save_button = ttk.Button(actions, text="Enregistrer PDF", command=self.save_pdf, state="disabled")
        self.save_button.pack(side="right", padx=8)
        ttk.Label(
            main,
            text="Ctrl+N Ajouter   ·   Delete Supprimer   ·   Ctrl+Suppr Vider la liste   ·   Ctrl+S Enregistrer   ·   Ctrl+P Imprimer",
            style="Subheader.TLabel",
        ).pack(anchor="e", pady=(10, 0))

        self.listbox.bind("<<TreeviewSelect>>", lambda _event: self.update_controls())
        root.bind("<Control-n>", lambda _event: self.show_add_form())
        root.bind("<Delete>", lambda _event: self.delete_label())
        root.bind("<Control-Delete>", lambda _event: self.clear_list())
        root.bind("<Control-s>", lambda _event: self.save_pdf())
        root.bind("<Control-p>", lambda _event: self.print_sheet())
        self.update_controls()
        self.show_add_form()
        root.after_idle(self.lot_entry.focus_set)

    def _build_menu(self) -> None:
        menu_font = ("Segoe UI", 10)
        menu_bar = tk.Menu(self.root, font=menu_font)
        file_menu = tk.Menu(menu_bar, tearoff=False, font=menu_font)
        file_menu.add_command(label="Enregistrer en PDF", accelerator="Ctrl+S", command=self.save_pdf)
        file_menu.add_command(label="Aperçu / imprimer", accelerator="Ctrl+P", command=self.print_sheet)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.root.destroy)
        menu_bar.add_cascade(label="Fichier", menu=file_menu)

        labels_menu = tk.Menu(menu_bar, tearoff=False, font=menu_font)
        labels_menu.add_command(label="Ajouter une étiquette", accelerator="Ctrl+N", command=self.show_add_form)
        labels_menu.add_command(label="Supprimer la sélection", accelerator="Delete", command=self.delete_label)
        labels_menu.add_command(label="Vider la liste", accelerator="Ctrl+Suppr", command=self.clear_list)
        menu_bar.add_cascade(label="Étiquettes", menu=labels_menu)
        self.root.configure(menu=menu_bar)

    def get_labels(self) -> list[tuple[str, str]]:
        return list(self.labels)

    def show_add_form(self) -> None:
        if not self.form_visible:
            self.entry_form.pack(fill="x", before=self.table_panel, pady=(0, 12))
            self.form_visible = True
        self.update_controls()
        self.lot_entry.focus_set()

    def _focus_location(self, _event: tk.Event) -> str:
        self.location_entry.focus_set()
        return "break"

    def _focus_quantity(self, _event: tk.Event) -> str:
        self.quantity_entry.focus_set()
        return "break"

    def save_current_label(self) -> None:
        lot = self.lot_entry.get().strip()
        location = self.location_entry.get().strip()
        try:
            quantity = int(self.quantity_value.get())
        except ValueError:
            quantity = 0
        if not lot and not location:
            messagebox.showwarning("Étiquette vide", "Saisissez un lot ou un emplacement.", parent=self.root)
            self.lot_entry.focus_set()
            return
        if quantity < 1:
            messagebox.showwarning(
                "Quantité invalide",
                "Saisissez un entier positif pour la quantité.",
                parent=self.root,
            )
            self.quantity_entry.focus_set()
            return

        items = []
        for _ in range(quantity):
            self.labels.append((lot, location))
            row_tag = ("stripe",) if len(self.labels) % 2 == 0 else ()
            items.append(
                self.listbox.insert(
                    "",
                    "end",
                    values=(len(self.labels), lot, location),
                    tags=row_tag,
                )
            )
        self.lot_entry.delete(0, "end")
        self.location_entry.delete(0, "end")
        self.quantity_value.set("1")
        self.update_controls()
        self.listbox.selection_set(items[-1])
        self.listbox.focus(items[-1])
        self.listbox.see(items[-1])
        self.lot_entry.focus_set()

    def delete_label(self) -> None:
        selection = self.listbox.selection()
        if not selection:
            return
        index = self.listbox.index(selection[0])
        self.labels.pop(index)
        self.listbox.delete(selection[0])
        for row_index, item in enumerate(self.listbox.get_children(), start=1):
            values = self.listbox.item(item, "values")
            row_tag = ("stripe",) if row_index % 2 == 0 else ()
            self.listbox.item(item, values=(row_index, values[1], values[2]), tags=row_tag)
        self.update_controls()

    def clear_list(self) -> None:
        if not self.labels:
            return
        if not messagebox.askyesno(
            "Vider la liste",
            f"Supprimer les {len(self.labels)} étiquettes de la liste ?",
            parent=self.root,
        ):
            return
        self.labels.clear()
        self.listbox.delete(*self.listbox.get_children())
        self.update_controls()

    def update_controls(self) -> None:
        count = len(self.labels)
        pages = (count + LABELS_PER_PAGE - 1) // LABELS_PER_PAGE
        label_word = "étiquette" if count == 1 else "étiquettes"
        page_word = "page" if pages == 1 else "pages"
        self.count_label.configure(text=f"{count} {label_word} · {pages} {page_word}")
        current_page_count = count % LABELS_PER_PAGE or (LABELS_PER_PAGE if count else 0)
        self.progress.configure(value=current_page_count)
        if count or self.form_visible:
            self.empty_state.place_forget()
        else:
            self.empty_state.place(relx=0.5, rely=0.5, anchor="center")
        self.print_button.configure(state="normal" if count else "disabled")
        self.save_button.configure(state="normal" if count else "disabled")
        self.delete_button.configure(state="normal" if self.listbox.selection() else "disabled")
        self.clear_button.configure(state="normal" if count else "disabled")

    def save_pdf(self) -> None:
        if not self.labels:
            return
        try:
            output = self.create_pdf()
            messagebox.showinfo("PDF créé", f"La planche a été enregistrée ici :\n{output}")
        except Exception as error:
            messagebox.showerror("Création du PDF impossible", str(error))

    def print_sheet(self) -> None:
        if not self.labels:
            return
        try:
            if self.preview_window is not None and self.preview_window.window.winfo_exists():
                self.preview_window.close()
            output = self.create_pdf()
            self.preview_window = PrintPreviewWindow(
                self.root,
                output,
                self.open_printer_manager,
                self._close_preview,
            )
        except Exception as error:
            messagebox.showerror("Aperçu impossible", str(error), parent=self.root)

    def open_printer_manager(self, pdf_path: Path, parent: tk.Toplevel) -> None:
        if sys.platform not in ("win32", "darwin"):
            messagebox.showerror(
                "Impression directe indisponible",
                "Le gestionnaire d’imprimante intégré est disponible sous Windows et macOS. Le PDF reste enregistré.",
                parent=parent,
            )
            return
        try:
            if self.printer_manager is not None and self.printer_manager.window.winfo_exists():
                self.printer_manager.window.lift()
                return
            self.printer_manager = PrinterManagerWindow(parent, pdf_path)
        except Exception as error:
            messagebox.showerror("Gestionnaire d’imprimante indisponible", str(error), parent=parent)

    def _close_preview(self, preview: PrintPreviewWindow) -> None:
        if self.preview_window is preview:
            self.preview_window = None

    def create_pdf(self) -> Path:
        FILES_DIR.mkdir(parents=True, exist_ok=True)
        output = FILES_DIR / "planche_ammf.pdf"
        create_sheet_pdf(output, self.get_labels())
        return output


def main() -> None:
    root = tk.Tk()
    LabelApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()