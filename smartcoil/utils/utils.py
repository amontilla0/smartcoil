def c_to_f(celcius):
    return celcius * 9 / 5 + 32

class Message():
    def __init__(self, type, action = None, params = None):
        self.type = type
        self.action = action
        self.params = params
