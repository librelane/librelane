# Copyright 2023 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import click
import atexit
import logging
from enum import IntEnum
from typing import ClassVar, Iterable, Union

import rich.console
import rich.logging
from rich.text import Text
from rich.style import Style, StyleType


class LogLevels(IntEnum):
    ALL = 0
    DEBUG = 10
    SUBPROCESS = 12
    VERBOSE = 15
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


console = rich.console.Console()
atexit.register(lambda: rich.console.Console().show_cursor())
__event_logger: logging.Logger = logging.getLogger("__librelane__")


class options:
    _condensed_mode: ClassVar[bool] = False
    _show_progress_bar: ClassVar[bool] = True

    @classmethod
    def get_condensed_mode(Self) -> bool:
        return Self._condensed_mode

    @classmethod
    def set_condensed_mode(Self, condensed: bool):
        Self._condensed_mode = condensed

    @classmethod
    def get_show_progress_bar(Self) -> bool:
        return Self._show_progress_bar

    @classmethod
    def set_show_progress_bar(Self, show: bool):
        Self._show_progress_bar = show


class NullFormatter(logging.Formatter):
    def format(self, record):
        return record.getMessage()


class LevelFormatter(logging.Formatter):
    def format(self, record):
        message = record.getMessage()
        if record.levelname == "WARNING":
            message = f"[yellow]{message}"
        elif record.levelname == "ERROR":
            message = f"[red]{message}"
        elif record.levelname == "CRITICAL":
            message = f"[red][bold]{message}"
        else:
            message = f"{message}"
        return message


class RichHandler(rich.logging.RichHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(**kwargs)

    def get_level_text(self, record: logging.LogRecord) -> Text:
        if not options.get_condensed_mode():
            return super().get_level_text(record)
        level_name = record.levelname
        style: StyleType
        if level_name == "WARNING":
            style = Style(color="yellow", bold=True)
        else:
            style = f"logging.level.{level_name.lower()}"
        level_text = Text.styled(
            f"[{level_name[0]}]",
            style,
        )
        return level_text


class KeywordFilter(logging.Filter):
    def __init__(self, matching_values: dict) -> None:
        super().__init__()
        self.matching_values = matching_values.copy()

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in self.matching_values.items():
            if value is None:
                if hasattr(record, key) and getattr(record, key) is not None:
                    return False
            else:
                if not hasattr(record, key) or getattr(record, key) != value:
                    return False
        return True


class LevelFilter(logging.Filter):
    def __init__(self, levels: Iterable[str], invert: bool = False) -> None:
        self.levels = levels
        self.invert = invert

    def filter(self, record: logging.LogRecord) -> bool:
        if options.get_condensed_mode():
            if record.levelname == "SUBPROCESS":
                return False
        if self.invert:
            return record.levelname not in self.levels
        else:
            return record.levelname in self.levels


def initialize_logger():
    global __event_logger, console

    for level in LogLevels:
        logging.addLevelName(level.value, level.name)

    subprocess_handler = RichHandler(
        console=console,
        show_time=False,
        omit_repeated_times=False,
        show_level=False,
        show_path=False,
        enable_link_path=False,
        tracebacks_word_wrap=False,
        keywords=[],
        markup=False,
    )
    subprocess_handler.addFilter(LevelFilter(["SUBPROCESS"]))

    rich_handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        omit_repeated_times=False,
        markup=True,
        tracebacks_suppress=[
            click,
        ],
        show_level=True,
        keywords=[],
    )
    rich_handler.setFormatter(LevelFormatter("%(message)s", datefmt="[%X]"))
    rich_handler.addFilter(LevelFilter(["SUBPROCESS"], invert=True))

    logger = logging.getLogger("__librelane__")
    logger.setLevel(LogLevels.SUBPROCESS)

    logger.handlers.clear()

    logger.addHandler(subprocess_handler)
    logger.addHandler(rich_handler)


initialize_logger()


def register_additional_handler(handler: logging.Handler):
    """
    Adds a new handler to the default LibreLane logger.

    :param handler: The new handler. Must be of type ``logging.Handler``
        or its subclasses.
    """
    __event_logger.addHandler(handler)


def deregister_additional_handler(handler: logging.Handler):
    """
    Removes a registered handler from the default LibreLane logger.

    :param handler: The handler. If not registered, the behavior
        of this function is undefined.
    """
    __event_logger.removeHandler(handler)


def set_log_level(lv: Union[str, int]):
    """
    Sets the log level of the default LibreLane logger.

    :param lv: Either the name or number of the desired log level.
    """
    __event_logger.setLevel(lv)


def reset_log_level():
    """
    Sets the log level of the default LibreLane logger back to the
    default log level.
    """
    set_log_level("SUBPROCESS")


def get_log_level() -> int:
    """
    Obtains the numeric log level of the LibreLane logger.
    """
    return __event_logger.getEffectiveLevel()


def debug(*args, **kwargs):
    """
    Logs to the LibreLane logger with the log level DEBUG.

    :param msg: The message to log
    """
    if kwargs.get("stacklevel") is None:
        kwargs["stacklevel"] = 2
    __event_logger.debug(*args, **kwargs)


def verbose(*args, **kwargs):
    """
    Logs to the LibreLane logger with the log level VERBOSE.
    """
    if kwargs.get("stacklevel") is None:
        kwargs["stacklevel"] = 2
    __event_logger.log(
        LogLevels.VERBOSE,
        *args,
        **kwargs,
    )


def info(msg: object, /, **kwargs):
    """
    Logs to the LibreLane logger with the log level INFO.

    :param msg: The message to log
    """
    if kwargs.get("stacklevel") is None:
        kwargs["stacklevel"] = 2
    __event_logger.info(msg, **kwargs)


def subprocess(msg: object, /, **kwargs):
    """
    Logs to the LibreLane logger with the log level SUBPROCESS.

    :param msg: The message to log
    """
    if kwargs.get("stacklevel") is None:
        kwargs["stacklevel"] = 2
    __event_logger.log(LogLevels.SUBPROCESS, msg, **kwargs)


def rule(title: str = "", /, **kwargs):  # pragma: no cover
    """
    Prints a horizontal line on the terminal enclosing the first argument
    if the log level is <= INFO.

    Kwargs are passed to https://rich.readthedocs.io/en/stable/reference/console.html#rich.console.Console.rule

    :param title: A title string to enclose in the console rule
    """
    console.rule(title)


def success(msg: object, /, **kwargs):
    """
    Logs to the LibreLane logger with the log level INFO.

    :param msg: The message to log
    """
    if kwargs.get("stacklevel") is None:
        kwargs["stacklevel"] = 2
    __event_logger.info(f"{msg}", **kwargs)


def warn(msg: object, /, **kwargs):
    """
    Logs to the LibreLane logger with the log level WARNING.

    :param msg: The message to log
    """
    if kwargs.get("stacklevel") is None:
        kwargs["stacklevel"] = 2
    __event_logger.warning(f"{msg}", **kwargs)


def err(msg: object, /, **kwargs):
    """
    Logs to the LibreLane logger with the log level ERROR.

    :param msg: The message to log
    """
    if kwargs.get("stacklevel") is None:
        kwargs["stacklevel"] = 2
    __event_logger.error(f"{msg}", **kwargs)


if __name__ == "__main__":
    initialize_logger()
    debug("Debug")
    verbose("Verbose")
    subprocess("Subprocess")
    rule("Rule")
    info("Info")
    success("Success")
    warn("Warn")
    err("Err")
    print("\n")
