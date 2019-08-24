def c_to_f(celcius):
    '''Utility method to convert Celcius degrees to Fahrenheit degrees.

    Params:
        celcius (float): Celcius degrees to be converted.
    '''
    return celcius * 9 / 5 + 32

class Message():
    def __init__(self, type, action = None, params = None):
        '''Utility class to represent messages being used in queue communication between thread
        queues.

        Params:
            type (:obj:`str`): String identifier for the type of message.
            action (:obj:`str`, optional): String identifier for the action to be executed. Thought
                as a type subcategory. Defaults to None.
            params (:obj:`dict`, optional): Dictionary of parameters to be used when executing the
                corresponding action. Defaults to None.
        '''
        self.type = type
        self.action = action
        self.params = params
