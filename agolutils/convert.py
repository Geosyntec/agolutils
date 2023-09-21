import logging
import sys
import time
from pathlib import Path
from pywintypes import com_error

if sys.platform == "win32":
    import win32com.client


_DELAY = 0.05  # seconds
_TIMEOUT = 60.0  # seconds


def _com_call_wrapper(f, *args, **kwargs):
    """
    COMWrapper support function.
    Repeats calls when 'Call was rejected by callee.' exception occurs.
    """
    # Unwrap inputs
    args = [arg._wrapped_object if isinstance(arg, ComWrapper) else arg for arg in args]
    kwargs = dict(
        [
            (key, value._wrapped_object)
            if isinstance(value, ComWrapper)
            else (key, value)
            for key, value in dict(kwargs).items()
        ]
    )

    start_time = None
    while True:
        try:
            result = f(*args, **kwargs)
        except com_error as e:
            if e.strerror == "Call was rejected by callee.":
                if start_time is None:
                    start_time = time.time()
                    logging.debug("Call was rejected by callee.")

                elif time.time() - start_time >= _TIMEOUT:
                    raise

                time.sleep(_DELAY)
                continue

            raise

        break

    if isinstance(result, win32com.client.CDispatch) or callable(result):
        return ComWrapper(result)
    return result


class ComWrapper(object):
    """
    Class to wrap COM objects to repeat calls when 'Call was rejected by callee.' exception occurs.
    """

    def __init__(self, wrapped_object):
        assert isinstance(wrapped_object, win32com.client.CDispatch) or callable(
            wrapped_object
        )
        self.__dict__["_wrapped_object"] = wrapped_object

    def __getattr__(self, item):
        return _com_call_wrapper(self._wrapped_object.__getattr__, item)

    def __getitem__(self, item):
        return _com_call_wrapper(self._wrapped_object.__getitem__, item)

    def __setattr__(self, key, value):
        _com_call_wrapper(self._wrapped_object.__setattr__, key, value)

    def __setitem__(self, key, value):
        _com_call_wrapper(self._wrapped_object.__setitem__, key, value)

    def __call__(self, *args, **kwargs):
        return _com_call_wrapper(self._wrapped_object.__call__, *args, **kwargs)

    def __repr__(self):
        return "ComWrapper<{}>".format(repr(self._wrapped_object))


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

    return ComWrapper(word), was_open


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
