class Uut(object):
    def __init__(self):
        pass

    def add_attr(self, name, value):
        """add attr"""
        setattr(self, name, value)

    def del_attr(self, name):
        """Delete attr"""
        if hasattr(self, name):
            delattr(self, name)

    def set_attr(self, name, value):
        """change attr"""
        setattr(self, name, value)

    def check_attr(self, name):
        return hasattr(self, name)

    def list_attrs(self):
        """list attr"""
        return {k: v for k, v in self.__dict__.items()}
