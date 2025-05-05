
from datetime import datetime


class Logger():

    LOGEVEL_LOG = 'log'
    LOGEVEL_WARNING = 'warning'
    LOGEVEL_INFO = 'info'
    LOGEVEL_ERROR = 'error'
    LOGEVEL_DEBUG = 'debug'
    
    is_debug = False
    is_console_enabled  = True
    enable_cache = True

    def __init__(self, handler):
        return
        
    def init_provider(self, log_db_provider):
        self.print(log_db_provider)

    @staticmethod    
    def print(*values):
        if Logger.is_console_enabled:
            s = Logger.get_print_string(values)
            print(Logger.get_current_date(), s)

    @staticmethod
    def get_print_string(values):
         v = [str(itm) + " " for itm in values]
         s = "".join(v)
         s = s.strip()
         return s

    @staticmethod    
    def debug(*values):
        if Logger.is_console_enabled and Logger.is_debug:
            s = Logger.get_print_string(values)
            print(Logger.get_current_date(), s)

    @staticmethod
    def get_current_date():
        # datetime object containing current date and time
        now = datetime.now()
        # dd/mm/YY H:M:S
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        return dt_string
    
    @staticmethod
    def debugbreak(*values):           
        if Logger.is_console_enabled and Logger.is_debug:
            s = Logger.get_print_string(values)
            print(Logger.get_current_date(), s)
        exit()