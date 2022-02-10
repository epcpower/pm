import alqtendpy.compileui
import pathlib

# import epyqlib.buildui


def compile_ui():
    print("build epyq from pm (TODO: TEMPORARY!, i dont like this)")
    # todo, both of these are the same.  change it only have one
    alqtendpy.compileui.compile_ui(
        directory_paths=[pathlib.Path(__file__).parent / "sub" / "epyqlib" / "epyqlib"],
    )


#    epyqlib.buildui.compile_ui()