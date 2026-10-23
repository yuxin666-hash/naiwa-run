"""Win32 分层透明窗口 / 托盘 / 菜单 / 开机自启。全部走 ctypes, 不依赖第三方 GUI 库。"""
import ctypes
import json
import os
import sys
import winreg
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT,
                             wintypes.WPARAM, wintypes.LPARAM)

# ---- 常量 ----
WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000
CS_DBLCLKS = 0x0008
SW_SHOWNOACTIVATE = 4
SW_HIDE = 0

WM_DESTROY = 0x0002
WM_NULL = 0x0000
WM_CLOSE = 0x0010
WM_PAINT = 0x000F
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MOUSEACTIVATE = 0x0021
WM_NCHITTEST = 0x0084
MA_NOACTIVATE = 3
HTCLIENT = 1
HTTRANSPARENT = -1
WM_APP_TRAY = 0x8000 + 17

PM_REMOVE = 0x0001
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
DIB_RGB_COLORS = 0
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 0x1, 0x2, 0x4
TPM_RETURNCMD = 0x0100
TPM_RIGHTBUTTON = 0x0002
MF_STRING = 0x0
MF_SEPARATOR = 0x800
MF_CHECKED = 0x8
MF_POPUP = 0x10
MF_GRAYED = 0x1
SPI_GETWORKAREA = 0x0030
SW_RESTORE = 9


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class RGBQUAD(ctypes.Structure):
    _fields_ = [("rgbBlue", ctypes.c_ubyte), ("rgbGreen", ctypes.c_ubyte),
                ("rgbRed", ctypes.c_ubyte), ("rgbReserved", ctypes.c_ubyte)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", RGBQUAD * 1)]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON), ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH), ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR), ("hIconSm", wintypes.HICON)]


class MSG(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND), ("message", wintypes.UINT),
                ("wParam", wintypes.WPARAM), ("lParam", wintypes.LPARAM),
                ("time", wintypes.DWORD), ("pt", POINT)]


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                ("uID", wintypes.UINT), ("uFlags", wintypes.UINT),
                ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON),
                ("szTip", wintypes.WCHAR * 128), ("dwState", wintypes.DWORD),
                ("dwStateMask", wintypes.DWORD), ("szInfo", wintypes.WCHAR * 256),
                ("uVersion", wintypes.UINT), ("szInfoTitle", wintypes.WCHAR * 64),
                ("dwInfoFlags", wintypes.DWORD), ("guidItem", GUID),
                ("hBalloonIcon", wintypes.HICON)]


user32.DefWindowProcW.restype = LRESULT
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
user32.RegisterClassExW.restype = wintypes.ATOM
user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.UpdateLayeredWindow.restype = wintypes.BOOL
user32.UpdateLayeredWindow.argtypes = [wintypes.HWND, wintypes.HDC, ctypes.POINTER(POINT),
                                       ctypes.POINTER(SIZE), wintypes.HDC, ctypes.POINTER(POINT),
                                       wintypes.DWORD, ctypes.POINTER(BLENDFUNCTION), wintypes.DWORD]
user32.SetWindowPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.ShowWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.PeekMessageW.restype = wintypes.BOOL
user32.PeekMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT,
                                wintypes.UINT, wintypes.UINT]
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.LoadImageW.restype = wintypes.HANDLE
user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                              ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.AppendMenuW.restype = wintypes.BOOL
user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.WPARAM, wintypes.LPCWSTR]
user32.TrackPopupMenu.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, wintypes.HWND, ctypes.POINTER(RECT)]
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.SetCapture.restype = wintypes.HWND
kernel32.CreateMutexW.restype = wintypes.HANDLE


def init_dpi():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def dpi_scale():
    """系统 DPI 缩放(1.0 = 100%)。窗口尺寸按逻辑像素乘它, 保证观感一致。"""
    try:
        d = user32.GetDpiForSystem()
        if d:
            return d / 96.0
    except Exception:
        pass
    try:
        hdc = user32.GetDC(None)
        d = gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSY
        user32.ReleaseDC(None, hdc)
        if d:
            return d / 96.0
    except Exception:
        pass
    return 1.0


def work_area():
    r = RECT()
    if user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(r), 0):
        return r.left, r.top, r.right, r.bottom
    return 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def screen_size():
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


class LayeredWindow:
    """真正逐像素 alpha 的分层窗口; 透明处鼠标可穿透。"""

    _class_atom = None

    def __init__(self, w, h, x, y, on_message, title="奶蛙快跑"):
        self.on_message = on_message
        self._proc = WNDPROC(self._wndproc)
        self.w, self.h = int(w), int(h)
        hinst = kernel32.GetModuleHandleW(None)
        if LayeredWindow._class_atom is None:
            cls = WNDCLASSEXW()
            cls.cbSize = ctypes.sizeof(WNDCLASSEXW)
            cls.style = CS_DBLCLKS
            cls.lpfnWndProc = self._proc
            cls.hInstance = hinst
            cls.hCursor = user32.LoadCursorW(None, 32512)  # IDC_ARROW
            cls.lpszClassName = "NaiwaPetWindow"
            LayeredWindow._class_atom = user32.RegisterClassExW(ctypes.byref(cls))
        ex = WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
        self.hwnd = user32.CreateWindowExW(ex, "NaiwaPetWindow", title, WS_POPUP,
                                           int(x), int(y), self.w, self.h,
                                           None, None, hinst, None)
        if not self.hwnd:
            raise OSError("CreateWindowExW failed: %s" % ctypes.get_last_error())
        self.x, self.y = int(x), int(y)
        self._make_surface()
        self._blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)

    # -- 绘制表面 --
    def _make_surface(self):
        screen = user32.GetDC(None)
        self.memdc = gdi32.CreateCompatibleDC(screen)
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = self.w
        bmi.bmiHeader.biHeight = -self.h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0
        self._bits = ctypes.c_void_p()
        self.hbmp = gdi32.CreateDIBSection(screen, ctypes.byref(bmi), DIB_RGB_COLORS,
                                           ctypes.byref(self._bits), None, 0)
        gdi32.SelectObject(self.memdc, self.hbmp)
        user32.ReleaseDC(None, screen)

    def resize(self, w, h):
        if (w, h) == (self.w, self.h):
            return
        gdi32.DeleteObject(self.hbmp)
        self.w, self.h = int(w), int(h)
        self._make_surface()
        user32.SetWindowPos(self.hwnd, None, self.x, self.y, self.w, self.h,
                            SWP_NOZORDER | SWP_NOACTIVATE)

    def draw(self, bgra_bytes):
        """bgra_bytes: 预乘 alpha 的 BGRA, 长度 = w*h*4"""
        ctypes.memmove(self._bits, bgra_bytes, min(len(bgra_bytes), self.w * self.h * 4))
        screen = user32.GetDC(None)
        pt_dst = POINT(self.x, self.y)
        size = SIZE(self.w, self.h)
        pt_src = POINT(0, 0)
        ok = user32.UpdateLayeredWindow(self.hwnd, screen, ctypes.byref(pt_dst),
                                        ctypes.byref(size), self.memdc, ctypes.byref(pt_src),
                                        0, ctypes.byref(self._blend), ULW_ALPHA)
        user32.ReleaseDC(None, screen)
        return ok

    def move(self, x, y):
        x, y = int(x), int(y)
        if (x, y) == (self.x, self.y):
            return
        self.x, self.y = x, y
        user32.SetWindowPos(self.hwnd, None, x, y, 0, 0,
                            SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)

    def set_topmost(self, on):
        user32.SetWindowPos(self.hwnd, HWND_TOPMOST if on else HWND_NOTOPMOST,
                            0, 0, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE)

    def show(self, visible=True):
        user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE if visible else SW_HIDE)
        self.visible = visible

    # -- 消息 --
    def _wndproc(self, hwnd, msg, wparam, lparam):
        try:
            return self.on_message(hwnd, msg, wparam, lparam)
        except Exception as e:  # 绝不让 Python 异常穿进消息循环
            print("wndproc error:", e, flush=True)
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


class Tray:
    def __init__(self, hwnd, icon_path, tip="奶蛙快跑"):
        self.hwnd = hwnd
        self.nid = NOTIFYICONDATAW()
        self.nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self.nid.hWnd = hwnd
        self.nid.uID = 1
        self.nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self.nid.uCallbackMessage = WM_APP_TRAY
        self.nid.szTip = tip
        self.hicon = user32.LoadImageW(None, icon_path, IMAGE_ICON, 0, 0,
                                       LR_LOADFROMFILE | LR_DEFAULTSIZE)
        self.nid.hIcon = self.hicon
        self.ok = bool(shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.nid)))
        if self.ok:
            self.nid.uVersion = 4
            shell32.Shell_NotifyIconW(4, ctypes.byref(self.nid))  # NIM_SETVERSION

    def remove(self):
        if self.ok:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.nid))


def popup_menu(hwnd, items, x=None, y=None):
    """items: [(id, label) | ('-', None) | ('sub', (label, [(id,label)...], 勾选中的id集合))]
    返回被点中的 id, 取消返回 0"""
    menu = user32.CreatePopupMenu()
    subs = []
    for it in items:
        if it[0] == "-":
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        elif it[0] == "sub":
            label, children, checked = it[1]
            sub = user32.CreatePopupMenu()
            subs.append(sub)
            for cid, clabel in children:
                flags = MF_STRING | (MF_CHECKED if cid in checked else 0)
                user32.AppendMenuW(sub, flags, cid, clabel)
            user32.AppendMenuW(menu, MF_POPUP, sub, label)
        else:
            mid, label = it[0], it[1]
            flags = MF_STRING
            if len(it) > 2 and it[2]:
                flags |= MF_CHECKED
            if len(it) > 3 and it[3]:
                flags |= MF_GRAYED
            user32.AppendMenuW(menu, flags, mid, label)
    if x is None or y is None:
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        x, y = pt.x, pt.y
    user32.SetForegroundWindow(hwnd)
    cmd = user32.TrackPopupMenu(menu, TPM_RETURNCMD | TPM_RIGHTBUTTON, int(x), int(y), 0,
                                hwnd, None)
    user32.PostMessageW(hwnd, WM_NULL, 0, 0)
    user32.DestroyMenu(menu)
    return int(cmd)


# ---------- 配置 / 自启 ----------
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "NaiwaPet")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "NaiwaDeskPet"


def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("save config failed:", e, flush=True)


def autostart_command():
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    exe = sys.executable
    cand = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(cand):
        exe = cand
    return f'"{exe}" "{script}"'


def autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            v, _ = winreg.QueryValueEx(k, RUN_NAME)
            return bool(v)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_autostart(on):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(k, RUN_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError as e:
        print("autostart failed:", e, flush=True)
        return False
