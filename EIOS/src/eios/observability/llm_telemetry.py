"""LLM Gateway Telemetry and Constitution Principle I Auditor Gate Tracking.

Provides per-call token accounting, model-configured USD financial cost tracking,
latency distributions, and Constitution Principle I Auditor Gate verdict telemetry
(PASSED, MASKED, REJECTED) with cryptographic output hashing and citation provenance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
import threading
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class AuditorVerdict(str, Enum):
    """Auditor Gate evaluation decision."""

    PASSED = "PASSED"
    MASKED = "MASKED"
    REJECTED = "REJECTED"


class ModelPricingConfig(BaseModel):
    """Pricing configuration for an LLM model in USD per 1,000,000 tokens."""

    prompt_cost_per_million: float = Field(default=0.0, ge=0.0)
    completion_cost_per_million: float = Field(default=0.0, ge=0.0)
    cached_cost_per_million: float = Field(default=0.0, ge=0.0)

    def calculate_cost(
        self, prompt_tokens: int, completion_tokens: int, cached_tokens: int = 0
    ) -> float:
        """Calculates exact financial cost in USD."""
        cost = (
            (prompt_tokens * self.prompt_cost_per_million)
            + (completion_tokens * self.completion_cost_per_million)
            + (cached_tokens * self.cached_cost_per_million)
        ) / 1_000_000.0
        return max(0.0, cost)


class LLMInvocationTelemetry(BaseModel):
    """Per-call language model telemetry record."""

    call_id: str = Field(..., description="Unique LLM invocation call ID")
    trace_id: str = Field(..., description="Active W3C trace ID")
    correlation_id: str = Field(..., description="Enterprise transaction correlation ID")
    prompt_id: str = Field(..., description="Versioned prompt template ID")
    prompt_version: str = Field(..., description="Semantic version of prompt")
    model_id: str = Field(..., description="LLM model identifier")
    prompt_tokens: int = Field(..., ge=0, description="Input prompt tokens consumed")
    completion_tokens: int = Field(..., ge=0, description="Output tokens generated")
    cached_tokens: int = Field(default=0, ge=0, description="Tokens read from cache")
    duration_ms: float = Field(..., ge=0.0, description="Total call latency in milliseconds")
    cost_usd: float = Field(..., ge=0.0, description="Calculated financial cost in USD")
    timestamp: datetime = Field(..., description="Invocation timestamp in UTC")


class AuditorGateTelemetry(BaseModel):
    """Telemetry record for Constitution Principle I Auditor Gate evaluations."""

    audit_id: str = Field(..., description="Unique auditor verification ID")
    trace_id: str = Field(..., description="Active W3C trace ID")
    correlation_id: str = Field(..., description="Enterprise correlation ID")
    text_hash: str = Field(..., description="SHA-256 hash digest of validated output text")
    total_claims_checked: int = Field(..., ge=0, description="Total numeric claims checked")
    verified_claims_count: int = Field(..., ge=0, description="Claims traced to tool outputs")
    unverified_claims_count: int = Field(..., ge=0, description="Ungrounded claims intercepted")
    verdict: AuditorVerdict = Field(..., description="Auditor Gate decision")
    citation_references: List[str] = Field(default_factory=list, description="Verified metric citation IDs")
    evaluated_at: datetime = Field(..., description="Evaluation timestamp in UTC")


class LLMTelemetryCollector:
    """Collects and aggregates LLM calls and Auditor Gate verdicts."""

    def __init__(self) -> None:
        self._pricing_tables: Dict[str, ModelPricingConfig] = {}
        self._invocations: List[LLMInvocationTelemetry] = []
        self._audits: List[AuditorGateTelemetry] = []
        self._lock = threading.RLock()

    def register_pricing(self, model_id: str, pricing: ModelPricingConfig) -> None:
        """Registers pricing parameters for a given model ID."""
        with self._lock:
            self._pricing_tables[model_id] = pricing

    def record_invocation(
        self,
        trace_id: str,
        correlation_id: str,
        prompt_id: str,
        prompt_version: str,
        model_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: float,
        cached_tokens: int = 0,
        timestamp: Optional[datetime] = None,
    ) -> LLMInvocationTelemetry:
        """Records an LLM invocation with deterministic cost accounting."""
        ts = timestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        with self._lock:
            pricing = self._pricing_tables.get(model_id, ModelPricingConfig())
            cost_usd = pricing.calculate_cost(prompt_tokens, completion_tokens, cached_tokens)

            record = LLMInvocationTelemetry(
                call_id=str(uuid.uuid4()),
                trace_id=trace_id,
                correlation_id=correlation_id,
                prompt_id=prompt_id,
                prompt_version=prompt_version,
                model_id=model_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cached_tokens=cached_tokens,
                duration_ms=round(duration_ms, 2),
                cost_usd=round(cost_usd, 6),
                timestamp=ts,
            )
            self._invocations.append(record)
            return record

    def record_auditor_gate(
        self,
        trace_id: str,
        correlation_id: str,
        text: str,
        total_claims_checked: int,
        verified_claims_count: int,
        unverified_claims_count: int,
        verdict: AuditorVerdict,
        citation_references: Optional[List[str]] = None,
        evaluated_at: Optional[datetime] = None,
    ) -> AuditorGateTelemetry:
        """Records an Auditor Gate verification evaluation."""
        ts = evaluated_at or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        record = AuditorGateTelemetry(
            audit_id=str(uuid.uuid4()),
            trace_id=trace_id,
            correlation_id=correlation_id,
            text_hash=text_hash,
            total_claims_checked=total_claims_checked,
            verified_claims_count=verified_claims_count,
            unverified_claims_count=unverified_claims_count,
            verdict=verdict,
            citation_references=citation_references or [],
            evaluated_at=ts,
        )

        with self._lock:
            self._audits.append(record)
            return record

    def get_correlation_summary(self, correlation_id: str) -> Dict[str, Any]:
        """Calculates token counts, spend, and audit stats for a given correlation ID."""
        with self._lock:
            calls = [inv for inv in self._invocations if inv.correlation_id == correlation_id]
            audits = [aud for aud in self._audits if aud.correlation_id == correlation_id]

            total_cost = sum(c.cost_usd for c in calls)
            total_prompt_tok = sum(c.prompt_tokens for c in calls)
            total_comp_tok = sum(c.completion_tokens for c in calls)
            total_cached_tok = sum(c.cached_tokens for c in calls)

            passed_audits = sum(1 for a in audits if a.verdict == AuditorVerdict.PASSED)
            rejected_audits = sum(1 for a in audits if a.verdict == AuditorVerdict.REJECTED)

            return {
                "correlation_id": correlation_id,
                "total_calls": len(calls),
                "total_cost_usd": round(total_cost, 6),
                "total_prompt_tokens": total_prompt_tok,
                "total_completion_tokens": total_comp_tok,
                "total_cached_tokens": total_cached_tok,
                "total_audits": len(audits),
                "passed_audits": passed_audits,
                "rejected_audits": rejected_audits,
            }

    def clear(self) -> None:
        """Flushes in-memory telemetry records."""
        with self._lock:
            self._invocations.clear()
            self._audits.clear()


def llm_telemetry_to_contract_dict(record: LLMInvocationTelemetry) -> Dict[str, Any]:
    """Converts LLMInvocationTelemetry to dictionary matching schema."""
    return {
        "call_id": record.call_id,
        "trace_id": record.trace_id,
        "correlation_id": record.correlation_id,
        "prompt_id": record.prompt_id,
        "prompt_version": record.prompt_version,
        "model_id": record.model_id,
        "prompt_tokens": record.prompt_tokens,
        "completion_tokens": record.completion_tokens,
        "cached_tokens": record.cached_tokens,
        "duration_ms": record.duration_ms,
        "cost_usd": record.cost_usd,
        "timestamp": record.timestamp.isoformat(),
    }


def auditor_telemetry_to_contract_dict(record: AuditorGateTelemetry) -> Dict[str, Any]:
    """Converts AuditorGateTelemetry to dictionary matching schema."""
    return {
        "audit_id": record.audit_id,
        "trace_id": record.trace_id,
        "correlation_id": record.correlation_id,
        "text_hash": record.text_hash,
        "total_claims_checked": record.total_claims_checked,
        "verified_claims_count": record.verified_claims_count,
        "unverified_claims_count": record.unverified_claims_count,
        "verdict": record.verdict.value,
        "citation_references": record.citation_references,
        "evaluated_at": record.evaluated_at.isoformat(),
    }
