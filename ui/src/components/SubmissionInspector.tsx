import { useMemo, useState } from 'react';
import { getModeConfig } from '../api/modeConfig';
import { ArchitectureMode, DataViewResult, SimulationEvent } from '../types';

type InspectorTab = 'activity' | 'data' | 'architecture';

interface SubmissionInspectorProps {
  mode: ArchitectureMode;
  submissionId: string | null;
  events: SimulationEvent[];
  dataView: DataViewResult | null;
  isLoadingData: boolean;
  onRefreshData: () => Promise<void>;
}

function asObject(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function normalizeState(rawState: unknown): string {
  const state = String(rawState ?? 'unknown').toLowerCase();
  if (state === 'under_reveiw') {
    return 'under_review';
  }
  return state;
}

function statusClassName(state: string): string {
  if (state === 'approved') {
    return 'approved';
  }
  if (state === 'rejected') {
    return 'rejected';
  }
  return 'under-review';
}

function prettyStatus(state: string): string {
  return state.replace(/_/g, ' ');
}

function shortId(value: string): string {
  return value.length > 16 ? `${value.slice(0, 15)}...` : value;
}

function prettyActivityTitle(type: string): string {
  const normalized = String(type || 'message').toLowerCase();
  const labels: Record<string, string> = {
    submitted: 'Submission Created',
    accepted: 'Submission Accepted',
    approved: 'Submission Approved',
    rejected: 'Submission Rejected',
    under_review: 'Manual Review Requested',
    submission_received: 'Submission Received',
    submission_stored: 'Submission Stored',
    submission_review_requested: 'Manual Review Requested',
    submission_approved: 'Submission Approved',
    submission_rejected: 'Submission Rejected',
    risk_scoring_started: 'Risk Scoring Started',
    risk_scored: 'Risk Scored',
    projection_updated: 'Projection Updated',
  };

  const key = normalized.replace(/[.\-\s]+/g, '_');
  return labels[key] ?? key.replace(/_/g, ' ').replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function buildActivityLog(events: SimulationEvent[], mode: ArchitectureMode) {
  return events.map((event) => {
    const raw = asObject(event.raw);
    return {
      event: {
        id: event.id,
        timestamp: event.timestamp,
        type: event.type,
        source: event.source,
        message: event.message,
      },
      log: {
        producerService: raw.producerService ?? raw.source ?? mode,
        payload: event.raw,
      },
    };
  });
}

function extractDetails(dataView: DataViewResult | null) {
  const data = asObject(dataView?.data);
  const risk = asObject(data.risk);
  const payload = asObject(data.payload);
  const status = normalizeState(data.status ?? data.state ?? data.submission_status);

  return {
    status,
    riskScore: risk.score ?? data.risk_score ?? null,
    riskLevel: risk.level ?? data.risk_level ?? null,
    applicant: String(data.applicantId ?? data.applicant_id ?? payload.applicant_id ?? 'n/a'),
    policyType: String(payload.policyType ?? payload.policy_type ?? 'n/a'),
    creditScore: payload.creditScore ?? payload.credit_score ?? 'n/a',
    raw: data,
  };
}

function SubmissionInspector({
  mode,
  submissionId,
  events,
  dataView,
  isLoadingData,
  onRefreshData,
}: SubmissionInspectorProps) {
  const [tab, setTab] = useState<InspectorTab>('activity');
  const [activityView, setActivityView] = useState<'pretty' | 'raw'>('pretty');
  const [showActivityJson, setShowActivityJson] = useState(false);
  const [dataViewMode, setDataViewMode] = useState<'pretty' | 'raw'>('pretty');
  const modeConfig = useMemo(() => getModeConfig(mode), [mode]);

  if (!submissionId) {
    return (
      <section className="inspector-panel">
        <h2>Selected Submission</h2>
        <p className="empty-text">
          Select a submission to inspect activity, data, and architecture flow.
        </p>
      </section>
    );
  }

  const details = extractDetails(dataView);
  const activityLog = buildActivityLog(events, mode);

  return (
    <section className="inspector-panel">
      <div className="panel-head">
        <h2>Selected Submission</h2>
        <button type="button" onClick={() => void onRefreshData()} disabled={isLoadingData}>
          {isLoadingData ? 'Refreshing...' : 'Refresh Data'}
        </button>
      </div>

      <div className="selected-meta">
        <div title={submissionId}>{shortId(submissionId)}</div>
        <div className="meta-badges">
          <span className={`state-pill ${statusClassName(details.status)}`}>
            {prettyStatus(details.status)}
          </span>
          <span className="risk-pill">
            Risk {String(details.riskScore ?? '-')} {String(details.riskLevel ?? '')}
          </span>
        </div>
      </div>

      <div className="inspector-tabs" role="tablist" aria-label="Submission inspector tabs">
        {(['activity', 'data', 'architecture'] as InspectorTab[]).map((item) => (
          <button
            key={item}
            type="button"
            className={tab === item ? 'active' : ''}
            onClick={() => setTab(item)}
          >
            {item[0].toUpperCase() + item.slice(1)}
          </button>
        ))}
      </div>

      {tab === 'activity' ? (
        <div className="inspector-body">
          <div className="view-toggle">
            <button
              type="button"
              className={activityView === 'pretty' ? 'active' : ''}
              onClick={() => setActivityView('pretty')}
            >
              Pretty
            </button>
            <button
              type="button"
              className={activityView === 'raw' ? 'active' : ''}
              onClick={() => setActivityView('raw')}
            >
              Raw JSON
            </button>
            {activityView === 'pretty' ? (
              <button
                type="button"
                className={showActivityJson ? 'active' : ''}
                onClick={() => setShowActivityJson((prev) => !prev)}
              >
                {showActivityJson ? 'Hide Payloads' : 'Show Payloads'}
              </button>
            ) : null}
          </div>

          {activityView === 'pretty' ? (
            <div className="timeline-cards">
              {events.length === 0 ? (
                <p className="empty-text">No activity yet.</p>
              ) : (
                events.map((event) => {
                  const raw = asObject(event.raw);
                  const source = String(raw.producerService ?? raw.source ?? event.source ?? mode);
                  return (
                    <article key={event.id} className="event-card">
                      <strong>{prettyActivityTitle(event.type)}</strong>
                      <div className="event-meta">
                        <div>Source: {source}</div>
                        <div>Time: {new Date(event.timestamp).toLocaleTimeString()}</div>
                      </div>
                      {showActivityJson ? (
                        <details className="event-json-toggle">
                          <summary>View JSON</summary>
                          <pre className="json-box inspector-json">
                            {JSON.stringify(
                              activityLog.find((entry) => entry.event.id === event.id),
                              null,
                              2,
                            )}
                          </pre>
                        </details>
                      ) : null}
                    </article>
                  );
                })
              )}
            </div>
          ) : (
            <pre className="json-box inspector-json">{JSON.stringify(activityLog, null, 2)}</pre>
          )}
        </div>
      ) : null}

      {tab === 'data' ? (
        <div className="inspector-body">
          <div className="view-toggle">
            <button
              type="button"
              className={dataViewMode === 'pretty' ? 'active' : ''}
              onClick={() => setDataViewMode('pretty')}
            >
              Pretty
            </button>
            <button
              type="button"
              className={dataViewMode === 'raw' ? 'active' : ''}
              onClick={() => setDataViewMode('raw')}
            >
              Raw JSON
            </button>
          </div>

          {dataViewMode === 'pretty' ? (
            <dl className="kv-grid">
              <div>
                <dt>Status</dt>
                <dd>{prettyStatus(details.status)}</dd>
              </div>
              <div>
                <dt>Risk Score</dt>
                <dd>{String(details.riskScore ?? 'n/a')}</dd>
              </div>
              <div>
                <dt>Risk Level</dt>
                <dd>{String(details.riskLevel ?? 'n/a')}</dd>
              </div>
              <div>
                <dt>Applicant</dt>
                <dd>{details.applicant}</dd>
              </div>
              <div>
                <dt>Policy</dt>
                <dd>{details.policyType}</dd>
              </div>
              <div>
                <dt>Credit Score</dt>
                <dd>{String(details.creditScore)}</dd>
              </div>
            </dl>
          ) : (
            <pre className="json-box inspector-json">{JSON.stringify(details.raw, null, 2)}</pre>
          )}
        </div>
      ) : null}

      {tab === 'architecture' ? (
        <div className="inspector-body">
          <h3>{modeConfig.label} Flow</h3>
          <div className="architecture-stack">
            {modeConfig.diagram.nodes.map((node, index) => (
              <div key={node} className="arch-node-wrap">
                <div className="arch-node">{node}</div>
                {index < modeConfig.diagram.nodes.length - 1 ? (
                  <div className="arch-arrow">↓</div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

export default SubmissionInspector;
