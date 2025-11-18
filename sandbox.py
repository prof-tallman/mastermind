
from multiprocessing import Process, Pipe
from multiprocessing.connection import Connection
import importlib
import traceback
from typing import Any, Optional

DEFAULT_START_TIMEOUT = 2.0
DEFAULT_STOP_TIMEOUT = 1.0
DEFAULT_CALL_TIMEOUT = 0.5

class BotError(Exception):
    """ Raised for any error during import, startup, or calls. """
    pass

class BotTimeout(Exception):
    """ Raised when the bot takes too long to start or respond. """
    pass

class BotProcess:
    """
    Persistent worker process that loads a bot class once and serves requests.

    Public API:
        - start()
        - call(method_name: str, *args, timeout: float | None)
        - stop()
    """

    def __init__(
        self,
        module_name: str,
        settings: dict[str, object],
        class_name: str = "Bot",
        start_timeout: float = DEFAULT_START_TIMEOUT,
    ) -> None:

        self.module_name = module_name
        self.class_name = class_name
        self.settings = settings

        # Connections to the bot
        self._parent_pipe = None
        self._bot_process = None

        # Detect if the bot is unresponsive
        self._start_timeout = start_timeout

        # Keeps track of whether the bot has been properly loaded
        self.alive = False

    def __del__(self) -> None:
        """ Best-effort cleanup during sandbox shutdown. """
        try:
            self.stop()
        except Exception:
            pass

    def start(self) -> None:
        """ Start the bot process and wait for it to report readiness. """
        if self.alive:
            return

        # Pipe is an IPC technique for sending messages back/forth to the bot
        parent_conn, child_conn = Pipe()
        self._parent_pipe = parent_conn

        # Start the bot in a new process to avoid damaging the game engine
        self._bot_process = Process(
            target=_bot_worker_main,
            args=(child_conn, self.module_name, self.class_name, self.settings),
            daemon=True,
        )
        self._bot_process.start()

        # Wait for bot to send either a ready or an error message
        if not parent_conn.poll(self._start_timeout):
            self._kill()
            raise BotTimeout(f"Bot '{self.module_name}' failed to start in time")

        msg = parent_conn.recv()
        if not msg.get("ok", False):
            err = msg.get("error", "unknown error")
            self._kill()
            raise BotError(f"Bot '{self.module_name}' failed to start:\n{err}")

        # Bot has responded with a ready message
        self.alive = True

    def call(
        self,
        method_name: str,
        *args: Any,
        timeout: float = DEFAULT_CALL_TIMEOUT,
    ) -> Any:
        """ Calls a bot method running in the worker process. """
        if not self.alive or self._parent_pipe is None:
            raise BotError("Bot process not started")

        # Send the call message to the bot
        self._parent_pipe.send(
            {"op": "call", "method": method_name, "args": args}
        )

        # Wait an appropriate time for the bot to respond
        if not self._parent_pipe.poll(timeout):
            self._kill()
            raise BotTimeout(
                f"Bot '{self.module_name}' timed out calling {method_name}()"
            )

        # Receive the bot's response and return it
        msg = self._parent_pipe.recv()
        if not msg.get("ok", False):
            err = msg.get("error", "Unknown error")
            raise BotError(
                f"Bot '{self.module_name}' error in {method_name}():\n{err}"
            )
        return msg.get("result", None)

    def stop(self) -> None:
        """ Ask the worker process to stop and clean up resources. """
        if not self.alive or self._parent_pipe is None:
            return

        # Alert the bot that it is finishing so it can clean up open resources
        try:
            self._parent_pipe.send({"op": "stop"})
            if self._bot_process is not None:
                self._bot_process.join(timeout=DEFAULT_STOP_TIMEOUT)
        except Exception:
            pass
        finally:
            self._kill()

    def _kill(self) -> None:
        """ Internal helper to forcibly terminate the worker process. """
        try:
            if self._bot_process is not None and self._bot_process.is_alive():
                self._bot_process.terminate()
                self._bot_process.join(timeout=DEFAULT_STOP_TIMEOUT)
        finally:
            self._bot_process = None
            self._parent_pipe = None
            self.alive = False


def _bot_worker_main(
    conn: Connection,
    module_name: str,
    class_name: str,
    settings: dict[str, object],
) -> None:
    """
    Worker entry point executed inside the child process.

    Loads the bot module/class, instantiates it, and responds to method calls.
    """

    # Import bot module
    try:
        module = importlib.import_module(module_name)
    except Exception:
        full_error = traceback.format_exc()
        conn.send({"ok": False, "error": "Import failed:\n" + full_error})
        return

    # Look up bot class
    try:
        BotClass = getattr(module, class_name)
    except AttributeError:
        conn.send({
            "ok": False,
            "error": f"Class '{class_name}' not found in module '{module_name}'"
        })
        return

    # Instantiate bot
    try:
        bot_instance = BotClass(settings)
    except Exception:
        full_error = traceback.format_exc()
        conn.send({"ok": False, "error": "Instantiation failed:\n" + full_error})
        return

    # Optional bot_info() check
    try:
        info_fn = getattr(bot_instance, "bot_info", None)
        if callable(info_fn):
            _ = info_fn()
        conn.send({"ok": True, "ready": True})
    except Exception:
        full_error = traceback.format_exc()
        conn.send({"ok": False, "error": "bot_info() failed:\n" + full_error})
        return

    # Enter an loop to respond to all calls; quit if call is to 'stop'
    # If this loop ever exits, the bot process finishes
    while True:

        # Receive the call message from the pipe
        try:
            msg = conn.recv()
        except EOFError:
            break

        # Verify that message has the right basic format
        if not isinstance(msg, dict):
            conn.send({"ok": False, "error": "Protocol error: expected dict"})
            continue

        # Get the operation type and then handle each call accordingly
        op = msg.get("op")

        # Bot should quit
        if op == "stop":
            break

        # Bot should execute a function
        if op == "call":
            method_name = msg.get("method")
            args = msg.get("args", ())

            # Get a reference to the desired function
            try:
                method = getattr(bot_instance, method_name)
            except AttributeError:
                conn.send({"ok": False, "error": f"No such method: {method_name}"})
                continue

            # Call the desired function and return the results
            try:
                result = method(*args)
                conn.send({"ok": True, "result": result})
            except Exception:
                full_error = traceback.format_exc()
                conn.send({"ok": False, "error": full_error})

            continue

        # Recieved a call message for an invalid operation
        conn.send({"ok": False, "error": f"Unknown call: {op}"})
