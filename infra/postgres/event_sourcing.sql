CREATE TABLE IF NOT EXISTS event_sourcing.event_store (
  event_id UUID PRIMARY KEY,
  aggregate_id UUID NOT NULL,
  aggregate_type TEXT NOT NULL CHECK (btrim(aggregate_type) <> ''),
  event_type TEXT NOT NULL CHECK (btrim(event_type) <> ''),
  event_version INTEGER NOT NULL CHECK (event_version > 0),
  event_data JSONB NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  sequence_number BIGINT GENERATED ALWAYS AS IDENTITY,
  correlation_id UUID,
  causation_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_event_store_sequence UNIQUE (sequence_number),
  CONSTRAINT uq_event_store_aggregate_version UNIQUE (aggregate_type, aggregate_id, event_version)
);

CREATE INDEX IF NOT EXISTS idx_event_store_aggregate_sequence
  ON event_sourcing.event_store (aggregate_type, aggregate_id, sequence_number);

CREATE INDEX IF NOT EXISTS idx_event_store_correlation
  ON event_sourcing.event_store (correlation_id)
  WHERE correlation_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_event_store_created_at
  ON event_sourcing.event_store (created_at);

CREATE TABLE IF NOT EXISTS event_sourcing.submission_read_model (
  aggregate_id UUID PRIMARY KEY,
  submission_status TEXT NOT NULL CHECK (submission_status IN ('received', 'under_review', 'approved', 'rejected')),
  applicant_id TEXT NOT NULL CHECK (btrim(applicant_id) <> ''),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  last_event_version INTEGER NOT NULL CHECK (last_event_version > 0),
  submitted_at TIMESTAMPTZ NOT NULL,
  projection_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submission_read_model_status_submitted
  ON event_sourcing.submission_read_model (submission_status, submitted_at DESC);

CREATE TABLE IF NOT EXISTS event_sourcing.risk_summary_read_model (
  aggregate_id UUID PRIMARY KEY,
  risk_score NUMERIC(5,2) CHECK (risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)),
  risk_level TEXT CHECK (risk_level IS NULL OR risk_level IN ('low', 'medium', 'high', 'critical')),
  factors JSONB NOT NULL DEFAULT '[]'::jsonb,
  evaluated_at TIMESTAMPTZ,
  last_event_version INTEGER NOT NULL CHECK (last_event_version > 0),
  projection_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_risk_summary_submission
    FOREIGN KEY (aggregate_id) REFERENCES event_sourcing.submission_read_model (aggregate_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_risk_summary_level_evaluated
  ON event_sourcing.risk_summary_read_model (risk_level, evaluated_at DESC);

CREATE TABLE IF NOT EXISTS event_sourcing.timeline_events (
  timeline_event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  aggregate_id UUID NOT NULL,
  event_id UUID NOT NULL,
  event_type TEXT NOT NULL CHECK (btrim(event_type) <> ''),
  event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  occurred_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_timeline_event_event_id UNIQUE (event_id),
  CONSTRAINT fk_timeline_event_submission
    FOREIGN KEY (aggregate_id) REFERENCES event_sourcing.submission_read_model (aggregate_id) ON DELETE CASCADE,
  CONSTRAINT fk_timeline_event_store
    FOREIGN KEY (event_id) REFERENCES event_sourcing.event_store (event_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_timeline_events_aggregate_occurred
  ON event_sourcing.timeline_events (aggregate_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS event_sourcing.processor_offsets (
  processor_name TEXT NOT NULL CHECK (btrim(processor_name) <> ''),
  partition_key TEXT NOT NULL DEFAULT 'default' CHECK (btrim(partition_key) <> ''),
  last_sequence_number BIGINT NOT NULL DEFAULT 0 CHECK (last_sequence_number >= 0),
  last_event_id UUID,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (processor_name, partition_key),
  CONSTRAINT uq_processor_last_event UNIQUE (processor_name, last_event_id),
  CONSTRAINT fk_processor_last_event
    FOREIGN KEY (last_event_id) REFERENCES event_sourcing.event_store (event_id)
);

CREATE INDEX IF NOT EXISTS idx_processor_offsets_sequence
  ON event_sourcing.processor_offsets (last_sequence_number);
