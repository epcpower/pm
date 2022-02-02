import alqtendpy.compileui
import pathlib

# import epyqlib.buildui


def compile_ui():
    print("compile_ui building UI in pm")
    alqtendpy.compileui.compile_ui(
        directory_paths=[pathlib.Path(__file__).parent],
    )

#    epyqlib.buildui.compile_ui()
