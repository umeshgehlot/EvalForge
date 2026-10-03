"""OpenTelemetry setup for the RAG demo app.

Uses an InMemorySpanExporter so span data can be returned in the /ask response
and saved to the eval DB by the worker. In production you'd use an OTLP exporter
with proper W3C trace-context propagation across service boundaries.
"""
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

_exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
otel_trace.set_tracer_provider(_provider)

tracer = otel_trace.get_tracer("evalforge.rag", "1.0.0")


def start_trace() -> None:
    """Clear any spans left from a prior request before starting a new one."""
    _exporter.clear()


def flush_spans() -> list[dict]:
    """Return finished spans as plain dicts and clear the buffer."""
    spans = _exporter.get_finished_spans()
    _exporter.clear()
    result = []
    for sp in spans:
        result.append(
            {
                "span_name": sp.name,
                # OTel IDs are 64-bit ints; hex-encode for JSON transport
                "otel_span_id": format(sp.context.span_id, "016x"),
                "otel_parent_id": (
                    format(sp.parent.span_id, "016x")
                    if sp.parent is not None
                    else None
                ),
                # OTel timestamps are nanoseconds; convert to milliseconds
                "start_ms": sp.start_time // 1_000_000,
                "end_ms": sp.end_time // 1_000_000,
                "metadata": dict(sp.attributes or {}),
            }
        )
    return result
