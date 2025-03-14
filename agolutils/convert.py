import sys
import time
from pathlib import Path
from typing import List, Tuple

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


def windows(input_paths: List[Path], output_paths: List[Path], word=None) -> List[Path]:
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


def resolve_paths(input_path, output_path) -> Tuple[List[Path], List[Path]]:
    _inp = input_path
    _out = output_path

    # prep input
    if isinstance(input_path, (str, Path)):
        input_path = Path(input_path)
        if input_path.is_dir():
            input_path = sorted(input_path.glob("[!~]*.doc*"))
        else:
            input_path = [input_path]
    if isinstance(input_path, list):
        input_path = [
            Path(p).resolve() for p in input_path if Path(p).suffix in [".docx", ".doc"]
        ]
        assert len(input_path) > 0, (_inp, input_path)
    else:
        raise ValueError(f"unexpected input for `input_path`:{_inp}")

    # prep output
    if output_path is None:
        output_path = [
            input_path[0].parent / (str(inp.stem) + ".pdf") for inp in input_path
        ]

    if isinstance(output_path, (str, Path)):
        output_path = Path(output_path)
        if output_path.is_dir():
            output_path = [output_path / (str(inp.stem) + ".pdf") for inp in input_path]

    if isinstance(output_path, list):
        output_path = [
            Path(p).resolve() for p in output_path if Path(p).suffix in [".pdf"]
        ]
        assert len(output_path) == len(input_path), (_out, output_path)
    else:
        raise ValueError(f"unexpected input for `output_path`:{_out}")

    return input_path, output_path


def convert(input_path, output_path=None, word=None):
    inps, outs = resolve_paths(input_path, output_path)
    if sys.platform == "win32":
        return windows(inps, outs, word=word)
    else:
        raise NotImplementedError("Not implemented for linux or darwin systems.")
