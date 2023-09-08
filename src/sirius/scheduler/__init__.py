import threading
import time

import schedule


class ScheduleThread(threading.Thread):
    threading_event: threading.Event | None = None
    instance: "ScheduleThread" = None

    @classmethod
    def run(cls) -> None:
        while not cls.threading_event.is_set():
            schedule.run_pending()
            time.sleep(1)


class Scheduler:
    threading_event: threading.Event | None = None

    @classmethod
    def start_scheduler(cls) -> None:
        cls.threading_event = threading.Event() if cls.threading_event is None else cls.threading_event
        ScheduleThread.threading_event = cls.threading_event if ScheduleThread.threading_event is None else ScheduleThread.threading_event
        ScheduleThread.instance = ScheduleThread() if ScheduleThread.instance is None else ScheduleThread.instance

        if not ScheduleThread.instance.is_alive():
            ScheduleThread.instance.start()
