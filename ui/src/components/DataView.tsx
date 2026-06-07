import { DataViewResult } from '../types';

interface DataViewProps {
  isLoading: boolean;
  value: DataViewResult | null;
  onRefresh: () => Promise<void>;
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

function prettyState(rawState: unknown): string {
  const normalized = normalizeState(rawState);
  return normalized.replace(/_/g, ' ');
}

function stateClassName(state: string): string {
  if (state === 'approved') {
    return 'approved';
  }
  if (state === 'rejected') {
    return 'rejected';
  }
  return 'under-review';
}

function buildStateReason(data: Record<string, unknown>, normalizedState: string): string {
  if (normalizedState !== 'under_review') {
    return 'Decision is finalized for this submission.';
  }

  const risk = asObject(data.risk);
  const riskLevel = String(risk.level ?? '').toLowerCase();
  if (riskLevel === 'medium' || riskLevel === 'high' || riskLevel === 'critical') {
    return `Manual review is expected for ${riskLevel} risk assessments.`;
  }

  return 'Submission is currently waiting for manual review.';
}

function DataView({ isLoading, value, onRefresh }: DataViewProps) {
  const data = asObject(value?.data);
  const normalizedState = normalizeState(data.state);
  const reason = buildStateReason(data, normalizedState);

  return (
    <section>
      <h2>Data View</h2>
      <button type="button" onClick={() => void onRefresh()} disabled={isLoading}>
        {isLoading ? 'Refreshing...' : 'Refresh Data View'}
      </button>
      {!value ? (
        <p className="empty-text">No submission selected.</p>
      ) : (
        <div>
          <p className="dataview-meta">
            Source: <strong>{value.source}</strong>
            {value.error ? (
              <span style={{ color: '#b45309' }}> (fallback reason: {value.error})</span>
            ) : null}
          </p>

          {'state' in data ? (
            <div className="dataview-status">
              <strong>Status</strong>
              <span className={`state-pill ${stateClassName(normalizedState)}`}>
                {prettyState(data.state)}
              </span>
              <span>{reason}</span>
            </div>
          ) : null}

          <pre className="json-box">{JSON.stringify(value.data, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}

export default DataView;
