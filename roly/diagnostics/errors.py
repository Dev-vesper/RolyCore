class RolyError(Exception):
    pass


def _io_reason(error):
    if isinstance(error, UnicodeDecodeError):
        return "the file is not valid UTF-8 text"
    text = error.strerror or str(error)
    return text[:1].lower() + text[1:]
