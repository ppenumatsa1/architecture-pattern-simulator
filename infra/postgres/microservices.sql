CREATE TABLE IF NOT EXISTS microservices.submissions (
  submission_id TEXT PRIMARY KEY CHECK (btrim(submission_id) <> ''),
  submission_version INTEGER NOT NULL DEFAULT 1 CHECK (submission_version > 0),
  status TEXT NOT NULL DEFAULT 'received' CHECK (status IN ('received', 'under_review', 'approved', 'rejected')),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_microservices_submissions_status_received
  ON microservices.submissions (status, received_at DESC);

CREATE TABLE IF NOT EXISTS microservices.risk_results (
  submission_id TEXT PRIMARY KEY,
  risk_score NUMERIC(5,2) NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
  risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
  model_name TEXT NOT NULL CHECK (btrim(model_name) <> ''),
  model_version TEXT,
  factors JSONB NOT NULL DEFAULT '[]'::jsonb,
  evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_microservices_risk_submission
    FOREIGN KEY (submission_id) REFERENCES microservices.submissions (submission_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_microservices_risk_results_level_evaluated
  ON microservices.risk_results (risk_level, evaluated_at DESC);

CREATE TABLE IF NOT EXISTS microservices.timeline_events (
  timeline_event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  submission_id TEXT NOT NULL,
  producer_service TEXT NOT NULL CHECK (producer_service IN ('submissions-service', 'risk-service', 'timeline-service', 'orchestrator-service')),
  event_type TEXT NOT NULL CHECK (event_type IN ('submission_received', 'risk_scored', 'manual_review_requested', 'decision_made')),
  idempotency_key TEXT,
  event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_microservices_timeline_submission
    FOREIGN KEY (submission_id) REFERENCES microservices.submissions (submission_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_microservices_timeline_service_idempotency
  ON microservices.timeline_events (producer_service, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_microservices_timeline_submission_occurred
  ON microservices.timeline_events (submission_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_microservices_timeline_event_type_occurred
  ON microservices.timeline_events (event_type, occurred_at DESC);

CREATE TABLE IF NOT EXISTS microservices.outbox_messages (
  outbox_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  stream_name TEXT NOT NULL CHECK (stream_name IN ('submission_requests', 'risk_results')),
  message_key TEXT NOT NULL CHECK (btrim(message_key) <> ''),
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  published_at TIMESTAMPTZ,
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  max_attempts INTEGER NOT NULL DEFAULT 20 CHECK (max_attempts > 0),
  last_attempt_at TIMESTAMPTZ,
  last_error TEXT,
  CONSTRAINT uq_microservices_outbox_key UNIQUE (stream_name, message_key)
);

CREATE INDEX IF NOT EXISTS idx_microservices_outbox_pending
  ON microservices.outbox_messages (published_at, available_at, outbox_id)
  WHERE published_at IS NULL;
