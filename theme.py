from tkinter import ttk

BG, CARD, ACC, ACC_D, TXT, MUTED, LINE, SEL = "#f3f4f6", "#ffffff", "#2563eb", "#1d4ed8", "#111827", "#6b7280", "#e5e7eb", "#dbeafe"


def apply(root):
    root.configure(bg=BG)
    st = ttk.Style(root)
    st.theme_use("clam")
    st.configure(".", font=("Segoe UI", 10), background=BG, foreground=TXT)
    st.configure("Card.TFrame", background=CARD, borderwidth=1, relief="solid", bordercolor=LINE)
    st.configure("Muted.TLabel", foreground=MUTED)
    st.configure("TEntry", fieldbackground=CARD, padding=8, bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
    st.map("TEntry", bordercolor=[("focus", ACC)], lightcolor=[("focus", ACC)], darkcolor=[("focus", ACC)])
    st.configure("TButton", padding=(14, 7), background=CARD, bordercolor=LINE, lightcolor=CARD, darkcolor=CARD)
    st.map("TButton", background=[("active", "#eef2ff")])
    st.configure("Accent.TButton", background=ACC, foreground="white", bordercolor=ACC, lightcolor=ACC, darkcolor=ACC)
    st.map("Accent.TButton", background=[("active", ACC_D)])
    st.configure("TMenubutton", padding=(14, 7), background=CARD, bordercolor=LINE, arrowcolor=MUTED)
    st.map("TMenubutton", background=[("active", "#eef2ff")])
    st.configure("Accent.Horizontal.TProgressbar", background=ACC, troughcolor=LINE, bordercolor=LINE, lightcolor=ACC, darkcolor=ACC)
    st.configure("Treeview", background=CARD, fieldbackground=CARD, rowheight=28, borderwidth=0)
    st.map("Treeview", background=[("selected", SEL)], foreground=[("selected", TXT)])
    st.configure("Treeview.Heading", font=("Segoe UI Semibold", 10), background=BG, relief="flat", padding=(8, 6))
    st.map("Treeview.Heading", background=[("active", LINE)])
