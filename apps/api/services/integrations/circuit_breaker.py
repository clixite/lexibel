"""Circuit Breaker — resilience pattern for external API calls.

Prevents cascading failures when external services (DPA, BCE, Plaud, Ringover)
are unavailable. Implements three states:

- CLOSED: normal operation, requests pass through
- OPEN: service is down, requests fail immediately (fast-fail)
- HALF_OPEN: test with limited requests to see if service recovered

Configurable thresholds per service. Thread-safe via asyncio locks.

References:
- Martin Fowler: https://martinfowler.com/bliki/CircuitBreaker.html
- Microsoft Azure patterns: Circuit Breaker
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker instance."""

    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds before trying half_open
    half_open_max_calls: int = 2
    success_threshold: int = 2  # successes in half_open to close


@dataclass
class CircuitBreakerState:
    """Runtime state for a circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    half_open_calls: int = 0


class CircuitBreaker:
    """Circuit breaker for protecting external API calls.

    Usage:
        breaker = CircuitBreaker("bce_api", config=CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60.0,
        ))

        result = await breaker.call(bce_client.lookup, bce_number="0123.456.789")
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state.state

    @property
    def failure_count(self) -> int:
        return self._state.failure_count

    def get_status(self) -> dict:
        """Get current circuit breaker status for monitoring."""
        return {
            "name": self.name,
            "state": self._state.state.value,
            "failure_count": self._state.failure_count,
            "success_count": self._state.success_count,
            "last_failure": self._state.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
            },
        }

    async def call(
        self,
        func: Callable,
        *args: Any,
        fallback: Callable | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute a function through the circuit breaker.

        Args:
            func: Async callable to execute
            *args: Positional arguments for func
            fallback: Optional fallback function if circuit is open
            **kwargs: Keyword arguments for func

        Returns:
            Result of func() or fallback()

        Raises:
            CircuitBreakerOpenError: If circuit is open and no fallback provided
        """
        async with self._lock:
            self._check_state_transition()

            if self._state.state == CircuitState.OPEN:
                logger.warning("Circuit breaker [%s] is OPEN — fast-failing", self.name)
                if fallback:
                    return (
                        await fallback(*args, **kwargs)
                        if asyncio.iscoroutinefunction(fallback)
                        else fallback(*args, **kwargs)
                    )
                raise CircuitBreakerOpenError(
                    f"Circuit breaker [{self.name}] is open. "
                    f"Service unavailable. Retry after {self.config.recovery_timeout}s."
                )

            if self._state.state == CircuitState.HALF_OPEN:
                if self._state.half_open_calls >= self.config.half_open_max_calls:
                    logger.warning(
                        "Circuit breaker [%s] HALF_OPEN max calls reached", self.name
                    )
                    if fallback:
                        return (
                            await fallback(*args, **kwargs)
                            if asyncio.iscoroutinefunction(fallback)
                            else fallback(*args, **kwargs)
                        )
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker [{self.name}] half-open limit reached."
                    )
                self._state.half_open_calls += 1

        # Execute outside lock
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            await self._on_success()
            return result

        except Exception as e:
            await self._on_failure(e)
            if fallback:
                return (
                    await fallback(*args, **kwargs)
                    if asyncio.iscoroutinefunction(fallback)
                    else fallback(*args, **kwargs)
                )
            raise

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1
                if self._state.success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
            else:
                self._state.failure_count = 0

    async def _on_failure(self, error: Exception) -> None:
        async with self._lock:
            self._state.failure_count += 1
            self._state.last_failure_time = time.monotonic()

            logger.warning(
                "Circuit breaker [%s] failure %d/%d: %s",
                self.name,
                self._state.failure_count,
                self.config.failure_threshold,
                str(error)[:200],
            )

            if self._state.state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
            elif self._state.failure_count >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def _check_state_transition(self) -> None:
        """Check if OPEN → HALF_OPEN transition is due."""
        if self._state.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._state.last_failure_time
            if elapsed >= self.config.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        old_state = self._state.state
        self._state.state = new_state

        if new_state == CircuitState.CLOSED:
            self._state.failure_count = 0
            self._state.success_count = 0
            self._state.half_open_calls = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._state.success_count = 0
            self._state.half_open_calls = 0

        logger.info(
            "Circuit breaker [%s] transition: %s → %s",
            self.name,
            old_state.value,
            new_state.value,
        )

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED."""
        self._state = CircuitBreakerState()
        logger.info("Circuit breaker [%s] manually reset", self.name)


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and no fallback provided."""


# ── Global registry of circuit breakers ──

_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str, config: CircuitBreakerConfig | None = None
) -> CircuitBreaker:
    """Get or create a named circuit breaker (singleton per name)."""
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name, config)
    return _breakers[name]


def get_all_breaker_statuses() -> list[dict]:
    """Get status of all registered circuit breakers."""
    return [breaker.get_status() for breaker in _breakers.values()]
