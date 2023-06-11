import inspect
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s || %(levelname)s || %(module)s.%(funcName)s\n%(message)s\n")


class RollbarHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        from sirius import application_performance_monitoring
        from sirius.application_performance_monitoring import MessageLevel

        application_performance_monitoring.send_message(self.format(record), MessageLevel(record.levelname.lower()))


def get_logger() -> logging.Logger:
    logger = logging.getLogger(get_name_of_calling_module())
    logger.addHandler(RollbarHandler())
    return logger


def get_name_of_calling_module() -> str:
    file_path: str = inspect.getmodule(inspect.stack()[2][0]).__file__
    file_name: str = file_path.split("\\")[-1] if "\\" in file_path else file_path.split("/")[-1]
    return file_name.replace(".py", "")
