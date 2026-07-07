"""
Ejecuta este script UNA SOLA VEZ para crear el acceso directo en el escritorio.
Desde cmd: python crear_acceso_directo.py
"""
import os
import sys

def crear_acceso_directo():
    try:
        import winshell
        from win32com.client import Dispatch
    except ImportError:
        print("Instalando dependencias para el acceso directo...")
        os.system("pip install winshell pywin32")
        import winshell
        from win32com.client import Dispatch

    escritorio = winshell.desktop()
    ruta_acceso = os.path.join(escritorio, "JARVIS.lnk")
    ruta_python = sys.executable
    ruta_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.py")
    ruta_icono  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.ico")

    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(ruta_acceso)
    shortcut.Targetpath = ruta_python
    shortcut.Arguments  = f'"{ruta_script}"'
    shortcut.WorkingDirectory = os.path.dirname(os.path.abspath(__file__))
    shortcut.Description = "Asistente JARVIS local"
    if os.path.exists(ruta_icono):
        shortcut.IconLocation = ruta_icono
    shortcut.WindowStyle = 1
    shortcut.save()

    print(f"\n✅ Acceso directo creado en: {ruta_acceso}")
    print("Ya puedes hacer doble clic en el icono JARVIS del escritorio.")

if __name__ == "__main__":
    crear_acceso_directo()
