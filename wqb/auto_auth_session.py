import logging
import time
from collections.abc import Callable
from typing import Optional
from requests import Response, Session
from . import RETRY_AFTER
from . import RETRY_AFTER

__all__ = ['AutoAuthSession']


class AutoAuthSession(Session):

    def __init__(
        self,
        method: str,
        url: str,
        *,
        auth_expected: Callable[[Response], bool] = lambda _: True,
        auth_max_tries: int = 3,
        auth_delay_unexpected: float = 2.0,
        expected: Callable[[Response], bool] = lambda _: True,
        max_tries: int = 3,
        delay_unexpected: float = 2.0,
        logger: logging.Logger = logging.root,
        **kwargs,
    ) -> None:
        super().__init__()
        self.method = method
        self.url = url
        self.kwargs = kwargs
        self.auth_expected = auth_expected
        self.auth_max_tries = auth_max_tries
        self.auth_delay_unexpected = auth_delay_unexpected
        self.expected = expected
        self.max_tries = max(1, max_tries)
        self.delay_unexpected = max(0.0, delay_unexpected)
        self.logger = logger

    def __repr__(
        self,
    ) -> str:
        """
        Returns a string representation of the `AutoAuthSession` object.

        Returns
        -------
        str
            A string representation of the `AutoAuthSession` object.
        """
        return f"<AutoAuthSession []>"

    def auth_request(
        self,
        method: Optional[str] = None,
        url: Optional[str] = None,
        *args,
        expected: Optional[Callable[[Response], bool]] = None,
        max_tries: Optional[int] = None,
        delay_unexpected: Optional[float] = None,
        log: Optional[str] = None,
        **kwargs,
    ) -> Response:
        if method is None:
            method = self.method
        if url is None:
            url = self.url
        # Use a Python 3.8+ compatible dict merge
        kwargs = {**self.kwargs, **kwargs}
        if expected is None:
            expected = self.auth_expected
        if max_tries is None:
            max_tries = self.auth_max_tries
        if delay_unexpected is None:
            delay_unexpected = self.auth_delay_unexpected
        max_tries = max(1, max_tries)
        delay_unexpected = max(0.0, delay_unexpected)
        tries = 0
        resp = Response()
        for tries in range(1, 1 + max_tries):
            resp = super().request(method, url, *args, **kwargs)
            if expected(resp):
                break
            # Respect server rate limiting if provided
            if resp.status_code == 429:
                retry_after = resp.headers.get(RETRY_AFTER)
                try:
                    if retry_after is not None:
                        time.sleep(float(retry_after))
                    else:
                        time.sleep(delay_unexpected)
                except ValueError:
                    time.sleep(delay_unexpected)
            else:
                time.sleep(delay_unexpected)
        else:
            self.logger.warning(
                '\n'.join(
                    (
                        f"{self}.auth_request(...) [max {tries} tries ran out]",
                        f"super().request(method, url, *args, **kwargs):",
                        f"    method: {method}",
                        f"    url: {url}",
                        f"    args: {args}",
                        f"    kwargs: {kwargs}",
                        f"{resp}:",
                        f"    status_code: {resp.status_code}",
                        f"    reason: {resp.reason}",
                        f"    url: {resp.url}",
                        f"    elapsed: {resp.elapsed}",
                        f"    headers: {resp.headers}",
                        f"    text: {resp.text}",
                    )
                )
            )
        if log is not None:
            self.logger.info(f"{self}.auth_request(...) [{tries} tries]: {log}")
        return resp

    def request(
        self,
        method: str,
        url: str,
        *args,
        expected: Optional[Callable[[Response], bool]] = None,
        max_tries: Optional[int] = None,
        delay_unexpected: Optional[float] = None,
        log: Optional[str] = None,
        **kwargs,
    ) -> Response:
        if expected is None:
            expected = self.expected
        if max_tries is None:
            max_tries = self.max_tries
        if delay_unexpected is None:
            delay_unexpected = self.delay_unexpected
        max_tries = max(1, max_tries)
        delay_unexpected = max(0.0, delay_unexpected)
        tries = 0
        resp = Response()
        for tries in range(1, 1 + max_tries):
            resp = super().request(method, url, *args, **kwargs)
            if expected(resp):
                break
            # Handle specific unexpected statuses
            if resp.status_code == 401:
                # Only re-authenticate on unauthorized
                self.auth_request()
                time.sleep(delay_unexpected)
            elif resp.status_code == 429:
                # Honor rate limiting
                retry_after = resp.headers.get(RETRY_AFTER)
                try:
                    if retry_after is not None:
                        time.sleep(float(retry_after))
                    else:
                        time.sleep(delay_unexpected)
                except ValueError:
                    time.sleep(delay_unexpected)
            else:
                time.sleep(delay_unexpected)
        else:
            self.logger.warning(
                '\n'.join(
                    (
                        f"{self}.request(...) [max {tries} tries ran out]",
                        f"super().request(method, url, *args, **kwargs):",
                        f"    method: {method}",
                        f"    url: {url}",
                        f"    args: {args}",
                        f"    kwargs: {kwargs}",
                        f"{resp}:",
                        f"    status_code: {resp.status_code}",
                        f"    reason: {resp.reason}",
                        f"    url: {resp.url}",
                        f"    elapsed: {resp.elapsed}",
                        f"    headers: {resp.headers}",
                        f"    text: {resp.text}",
                    )
                )
            )
        if log is not None:
            self.logger.info(f"{self}.request(...) [{tries} tries]: {log}")
        return resp
