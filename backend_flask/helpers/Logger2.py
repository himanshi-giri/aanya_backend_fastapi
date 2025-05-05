import os
from datetime import datetime

class Logger:
    # Log levels
    LEVELS = {
        'debug': 1,
        'info': 2,
        'warning': 3,
        'error': 4,
        'critical': 5
    }

    # Default log level (can be configured)
    log_level = 'debug'  # Set default log level to 'debug'
    log_file = None
    log_to_console = True  # Whether to print logs to console

    def __init__(self, log_file=None, log_level='debug', log_to_console=True):
        """
        Initialize the logger with configuration options.
        
        :param log_file: Log file path where logs will be saved (optional)
        :param log_level: The log level to control the verbosity of logs (optional)
        :param log_to_console: Whether to log to console (optional)
        """
        self.log_file = log_file
        self.log_level = log_level
        self.log_to_console = log_to_console

    def log(self, message, level='info'):
        """
        Log a message with a specified level.
        
        :param message: Message to be logged
        :param level: Level of logging (debug, info, warning, error, critical)
        """
        # Check if the message level is enabled based on the current log level
        if SimpleLogger.LEVELS[level] >= SimpleLogger.LEVELS[self.log_level]:
            timestamp = self.get_current_time()
            log_message = f"{timestamp} [{level.upper()}] {message}"

            # Log to console
            if self.log_to_console:
                print(log_message)

            # Log to file if log_file is provided
            if self.log_file:
                self.log_to_file(log_message)

    def log_to_file(self, message):
        """Write the log message to a log file."""
        try:
            with open(self.log_file, 'a') as file:
                file.write(message + '\n')
        except Exception as e:
            print(f"Error writing to log file: {e}")

    @staticmethod
    def get_current_time():
        """Return the current time formatted as 'YYYY-MM-DD HH:MM:SS'."""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def debug(self, message):
        """Log a debug message."""
        self.log(message, level='debug')

    def info(self, message):
        """Log an info message."""
        self.log(message, level='info')

    def warning(self, message):
        """Log a warning message."""
        self.log(message, level='warning')

    def error(self, message):
        """Log an error message."""
        self.log(message, level='error')

    def critical(self, message):
        """Log a critical message."""
        self.log(message, level='critical')
