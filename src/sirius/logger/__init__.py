import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s || %(levelname)s || %(module)s.%(funcName)s\n%(message)s\n")


class RollbarHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        from sirius import application_performance_monitoring
        from sirius.application_performance_monitoring import MessageLevel

        application_performance_monitoring.send_message(self.format(record), MessageLevel(record.levelname.lower()))


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.addHandler(RollbarHandler())
    return logger
