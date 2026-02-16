"""LXB-029: Tests for SSE — connection, event delivery, tenant isolation."""

import asyncio
import uuid

import pytest

from apps.api.services.sse_service import SSEManager, _format_sse


# ── SSE format tests ──


def test_format_sse_message():
    msg = _format_sse("test_event", {"key": "value"})
    assert msg.startswith("event: test_event\n")
    assert '"key": "value"' in msg
    assert msg.endswith("\n\n")


def test_format_sse_with_uuid():
    """UUIDs should be serialized to string."""
    uid = uuid.uuid4()
    msg = _format_sse("test", {"id": uid})
    assert str(uid) in msg


# ── SSEManager tests ──


@pytest.mark.asyncio
async def test_sse_manager_subscribe_and_publish():
    manager = SSEManager()
    tenant_id = uuid.uuid4()
    received = []

    async def collector():
        async for event in manager.subscribe(tenant_id):
            received.append(event)
            if len(received) >= 2:  # connection event + 1 published
                break

    # Start subscriber in background
    task = asyncio.create_task(collector())

    # Give subscriber time to connect
    await asyncio.sleep(0.05)

    # Publish an event
    count = await manager.publish(
        tenant_id,
        "new_inbox_item",
        {
            "id": str(uuid.uuid4()),
            "source": "RINGOVER",
        },
    )

    # Wait for collector to finish
    await asyncio.wait_for(task, timeout=2.0)

    assert count == 1
    assert len(received) == 2
    # First message is the connection event
    assert "connected" in received[0]
    # Second message is our published event
    assert "new_inbox_item" in received[1]
    assert "RINGOVER" in received[1]


@pytest.mark.asyncio
async def test_sse_tenant_isolation():
    """Events for tenant A should not be seen by tenant B."""
    manager = SSEManager()
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    received_a = []
    received_b = []

    async def collect_a():
        async for event in manager.subscribe(tenant_a):
            received_a.append(event)
            if len(received_a) >= 2:
                break

    async def collect_b():
        count = 0
        async for event in manager.subscribe(tenant_b):
            received_b.append(event)
            count += 1
            if count >= 1:  # Only connection event
                break

    task_a = asyncio.create_task(collect_a())
    task_b = asyncio.create_task(collect_b())

    await asyncio.sleep(0.05)

    # Publish to tenant A only
    await manager.publish(tenant_a, "case_updated", {"case_id": "123"})

    await asyncio.wait_for(task_a, timeout=2.0)
    # Cancel B since it won't get more events
    task_b.cancel()
    try:
        await task_b
    except asyncio.CancelledError:
        pass

    # A got connection + published event
    assert len(received_a) == 2
    assert "case_updated" in received_a[1]

    # B only got connection event
    assert len(received_b) == 1
    assert "connected" in received_b[0]


@pytest.mark.asyncio
async def test_sse_subscriber_count():
    manager = SSEManager()
    tenant_id = uuid.uuid4()

    assert manager.subscriber_count(tenant_id) == 0

    # Create a subscriber that collects 2 events (connected + published)
    received = []

    async def collector():
        async for event in manager.subscribe(tenant_id):
            received.append(event)
            if len(received) >= 2:
                break

    task = asyncio.create_task(collector())
    # Wait for generator to start and register the queue
    await asyncio.sleep(0.1)

    # The subscriber should be registered by now (connected event was yielded)
    assert manager.subscriber_count(tenant_id) == 1
    assert manager.total_subscribers() >= 1

    # Publish to let the collector finish
    await manager.publish(tenant_id, "test", {"data": "cleanup"})
    await asyncio.wait_for(task, timeout=2.0)

    # After task completes, subscriber is cleaned up
    await asyncio.sleep(0.05)
    assert manager.subscriber_count(tenant_id) == 0


@pytest.mark.asyncio
async def test_sse_publish_no_subscribers():
    """Publishing to a tenant with no subscribers returns 0."""
    manager = SSEManager()
    count = await manager.publish(uuid.uuid4(), "test", {"data": "hello"})
    assert count == 0


@pytest.mark.asyncio
async def test_sse_multiple_subscribers():
    """Multiple subscribers for the same tenant all receive the event."""
    manager = SSEManager()
    tenant_id = uuid.uuid4()
    received_1 = []
    received_2 = []

    async def collect(store):
        async for event in manager.subscribe(tenant_id):
            store.append(event)
            if len(store) >= 2:
                break

    task_1 = asyncio.create_task(collect(received_1))
    task_2 = asyncio.create_task(collect(received_2))
    await asyncio.sleep(0.05)

    assert manager.subscriber_count(tenant_id) == 2

    count = await manager.publish(tenant_id, "time_entry_created", {"id": "te-1"})
    assert count == 2

    await asyncio.wait_for(task_1, timeout=2.0)
    await asyncio.wait_for(task_2, timeout=2.0)

    assert len(received_1) == 2
    assert len(received_2) == 2
    assert "time_entry_created" in received_1[1]
    assert "time_entry_created" in received_2[1]
