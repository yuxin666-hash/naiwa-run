"""用 ctypes 直接调 COM 生成 .lnk 快捷方式(不依赖 pywin32)。"""
import ctypes
import os
import sys
from ctypes import wintypes

ole32 = ctypes.WinDLL("ole32")
CLSCTX_INPROC_SERVER = 1


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]


def guid(s):
    g = GUID()
    ole32.CLSIDFromString(ctypes.c_wchar_p(s), ctypes.byref(g))
    return g


CLSID_ShellLink = guid("{00021401-0000-0000-C000-000000000046}")
IID_IShellLinkW = guid("{000214F9-0000-0000-C000-000000000046}")
IID_IPersistFile = guid("{0000010B-0000-0000-C000-000000000046}")


def vt(punk, index, restype, argtypes):
    table = ctypes.cast(punk, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(table[index])


def make_shortcut(lnk_path, target, args, workdir, icon, desc, show_cmd=7):
    ole32.CoInitialize(None)
    psl = ctypes.c_void_p()
    ole32.CoCreateInstance(ctypes.byref(CLSID_ShellLink), None, CLSCTX_INPROC_SERVER,
                           ctypes.byref(IID_IShellLinkW), ctypes.byref(psl))
    if not psl:
        raise OSError("CoCreateInstance failed")
    hr = vt(psl, 20, ctypes.HRESULT, [wintypes.LPCWSTR])(psl, target)          # SetPath
    vt(psl, 11, ctypes.HRESULT, [wintypes.LPCWSTR])(psl, args)                 # SetArguments
    vt(psl, 9, ctypes.HRESULT, [wintypes.LPCWSTR])(psl, workdir)               # SetWorkingDirectory
    vt(psl, 7, ctypes.HRESULT, [wintypes.LPCWSTR])(psl, desc)                  # SetDescription
    vt(psl, 17, ctypes.HRESULT, [wintypes.LPCWSTR, ctypes.c_int])(psl, icon, 0)  # SetIconLocation
    vt(psl, 15, ctypes.HRESULT, [ctypes.c_int])(psl, show_cmd)                 # SetShowCmd
    ppf = ctypes.c_void_p()
    vt(psl, 0, ctypes.HRESULT, [ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)])(
        psl, ctypes.byref(IID_IPersistFile), ctypes.byref(ppf))
    if not ppf:
        raise OSError("QueryInterface IPersistFile failed")
    vt(ppf, 6, ctypes.HRESULT, [wintypes.LPCWSTR, wintypes.BOOL])(ppf, lnk_path, True)  # Save
    vt(ppf, 2, ctypes.c_ulong, [])(ppf)
    vt(psl, 2, ctypes.c_ulong, [])(psl)
    ole32.CoUninitialize()


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    lnk = os.path.join(root, "奶蛙快跑.lnk")
    make_shortcut(lnk, pyw, f'"{os.path.join(root, "app", "main.py")}"', root,
                  os.path.join(root, "assets", "tray.ico"), "奶蛙快跑", 7)
    print("ok", os.path.exists(lnk), lnk)
