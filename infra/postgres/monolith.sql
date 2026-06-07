CREATE TABLE IF NOT EXISTS monolith.submissions (
  submission_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  applicant_id TEXT NOT NULL CHECK (btrim(applicant_id) <> ''),
  status TEXT NOT NULL DEFAULT 'received' CHECK (status IN ('received', 'under_review', 'approved', 'rejected')),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_monolith_submissions_status_submitted_at
  ON monolith.submissions (status, submitted_at DESC);

CREATE TABLE IF NOT EXISTS monolith.risk_results (
  risk_result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  submission_id BIGINT NOT NULL UNIQUE,
  risk_score NUMERIC(5,2) NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
  risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
  factors JSONB NOT NULL DEFAULT '[]'::jsonb,
  evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_monolith_risk_submission
    FOREIGN KEY (submission_id) REFERENCES monolith.submissions (submission_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_monolith_risk_results_level_evaluated
  ON monolith.risk_results (risk_level, evaluated_at DESC);

CREATE TABLE IF NOT EXISTS monolith.timeline_events (
  timeline_event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  submission_id BIGINT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('submission_received', 'risk_scored', 'manual_review_requested', 'decision_made')),
  event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_monolith_timeline_submission
    FOREIGN KEY (submission_id) REFERENCES monolith.submissions (submission_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_monolith_timeline_submission_occurred
  ON monolith.timeline_events (submission_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_monolith_timeline_event_type_occurred
  ON monolith.timeline_events (event_type, occurred_at DESC);
