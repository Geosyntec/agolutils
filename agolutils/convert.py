import sys

from pathlib import Path
from pywintypes import com_error

if sys.platform == "win32":
    import win32com.client


class WordDocument:
    def __init__(self, client, filepath):
        self.client = client
        self.filepath = str(filepath)
        self.doc = None

    def __getattr__(self, item):
        if self.doc:
            return self.doc.__getattr__(item)

    def __getitem__(self, item):
        if self.doc:
            return self.doc.__getitem__(item)

    def __enter__(self):
        self.doc = self.client.Documents.Open(self.filepath)
        return self.doc

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.doc is None:
            return

        self.doc.Close(0)


def get_Word(visible=False):
    app = "Word.Application"
    was_open = False
    word = None
    try:
        word = win32com.client.GetActiveObject(app)
        was_open = True
    except com_error:
        word = win32com.client.gencache.EnsureDispatch(app)
        word.Visible = visible

    if word is None:
        raise Exception("Unable to open MS Word")

    return word, was_open


def windows(paths):
    word, was_open = get_Word(visible=False)
    wdFormatPDF = 17
    try:
        if paths["batch"]:
            for docx_filepath in sorted(Path(paths["input"]).glob("[!~]*.doc*")):
                pdf_filepath = Path(paths["output"]) / (
                    str(docx_filepath.stem) + ".pdf"
                )
                with WordDocument(word, docx_filepath) as doc:
                    doc.SaveAs(str(pdf_filepath), FileFormat=wdFormatPDF)

        else:
            docx_filepath = Path(paths["input"]).resolve()
            pdf_filepath = Path(paths["output"]).resolve()
            with WordDocument(word, docx_filepath) as doc:
                doc.SaveAs(str(pdf_filepath), FileFormat=wdFormatPDF)
    finally:
        if not was_open:
            word.Quit()


def resolve_paths(input_path, output_path):
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve() if output_path else None
    output = {}
    if input_path.is_dir():
        output["batch"] = True
        output["input"] = str(input_path)
        if output_path:
            assert output_path.is_dir()
        else:
            output_path = str(input_path)
        output["output"] = output_path
    else:
        output["batch"] = False
        assert str(input_path).lower().endswith((".docx", ".doc"))
        output["input"] = str(input_path)
        if output_path and output_path.is_dir():
            output_path = str(output_path / (str(input_path.stem) + ".pdf"))
        elif output_path:
            assert str(output_path).endswith(".pdf")
        else:
            output_path = str(input_path.parent / (str(input_path.stem) + ".pdf"))
        output["output"] = output_path
    return output


def convert(input_path, output_path=None):
    paths = resolve_paths(input_path, output_path)
    if sys.platform == "win32":
        return windows(paths)
    else:
        raise NotImplementedError("Not implemented for linux or darwin systems.")
