import sys
import time
from pathlib import Path

if sys.platform == "win32":
    import win32com.client
    from pywintypes import com_error


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

        retry_delay_seconds = 0.25
        retry_n_times = int(60 / retry_delay_seconds)
        for _ in range(retry_n_times):
            try:
                self.doc.Close(0)
            except com_error as e:
                if "rejected by callee" in e.strerror.lower():  # type: ignore
                    time.sleep(retry_delay_seconds)
                    continue
                raise

            break


def get_Word():
    app = "Word.Application"

    word = win32com.client.DispatchEx(app)
    word.Visible = False

    return word


def update_fields(input_paths: list[Path], word=None):
    got_our_own_word = False
    if word is None:
        word = get_Word()
        got_our_own_word = True

    try:
        for docx_inp in input_paths:
            with WordDocument(word, docx_inp) as doc:
                retry_delay_seconds = 0.25
                retry_n_times = int(60 / retry_delay_seconds)
                for _ in range(retry_n_times):
                    try:
                        doc.Fields.Update()
                        doc.Save()
                    except com_error as e:
                        if "rejected by callee" in e.strerror.lower():  # type: ignore
                            time.sleep(retry_delay_seconds)
                            continue
                        raise
                    break
    finally:
        if got_our_own_word:
            word.Quit()

    return input_paths


def save_as_pdf(
    input_paths: list[Path], output_paths: list[Path], word=None
) -> list[Path]:
    got_our_own_word = False
    if word is None:
        word = get_Word()
        got_our_own_word = True
    wdFormatPDF = 17

    try:
        for docx_inp, pdf_out in zip(input_paths, output_paths, strict=False):
            with WordDocument(word, docx_inp) as doc:
                retry_delay_seconds = 0.25
                retry_n_times = int(60 / retry_delay_seconds)
                for _ in range(retry_n_times):
                    try:
                        doc.SaveAs(str(pdf_out), FileFormat=wdFormatPDF)
                    except com_error as e:
                        if "rejected by callee" in e.strerror.lower():  # type: ignore
                            time.sleep(retry_delay_seconds)
                            continue
                        raise

                    break

    finally:
        if got_our_own_word:
            word.Quit()

    return output_paths
