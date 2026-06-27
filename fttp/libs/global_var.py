import threading

_global_dict = dict()
_cell_dict = dict()
_thread_local = threading.local()
_dict_lock = threading.Lock()


def _init():
    global _global_dict, _cell_dict
    _global_dict = {}
    _cell_dict = {}


def reset_cell():
    cell_id = get_current_cell_id()
    with _dict_lock:
        _cell_dict[cell_id] = {}


def set_current_cell_id(cell_name):
    _thread_local.cell_name = cell_name


def get_current_cell_id():
    return getattr(_thread_local, "cell_name", None)


def set_value(name, value):
    with _dict_lock:
        cell_id = get_current_cell_id()
        if cell_id is not None:
            if cell_id not in _cell_dict:
                _cell_dict[cell_id] = {}
            _cell_dict[cell_id][name] = value
        else:
            _global_dict[name] = value


def get_value(name, defValue=None):
    with _dict_lock:
        cell_id = get_current_cell_id()
        if cell_id is not None:
            try:
                value = _cell_dict[cell_id][name]
                return value
            except KeyError:
                return defValue
        else:
            try:
                return _global_dict[name]
            except KeyError:
                return defValue


def set_cell_value(cell_id, name, value):
    if cell_id not in _cell_dict:
        _cell_dict[cell_id] = {}
    _cell_dict[cell_id][name] = value


def get_cell_value(cell_id, name, defValue=None):
    try:
        value = _cell_dict[cell_id][name]
        return value
    except KeyError:
        return defValue
