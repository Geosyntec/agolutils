import sys
import time

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
