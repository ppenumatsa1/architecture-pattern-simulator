import { DataViewResult, DashboardApplication, SimulationEvent } from '../types';

interface DashboardPanelProps {
  applications: DashboardApplication[];
  isLoadingApplications: boolean;
  events: SimulationEvent[];
  selectedSubmissionId: string | null;
  isLoadingData: boolean;
  dataView: DataViewResult | null;
  onRefreshApplications: () => Promise<void>;
  onSelectSubmission: (submissionId: string) => void;
  onRefreshDataView: () => Promise<void>;
}

function normalizeState(rawState: string | null | undefined): string {
  const state = String(rawState ?? 'unknown').toLowerCase();
  if (state === 'under_reveiw') {
    return 'under_review';
  }
  return state;
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

function formatStatus(state: string): string {
  return state.replace(/_/g, ' ');
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return 'n/a';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'n/a';
  }

  return date.toLocaleString();
}

function summarizeByStatus(applications: DashboardApplication[]) {
  const summary = {
    total: applications.length,
    approved: 0,
    rejected: 0,
    underReview: 0,
    other: 0,
  };

  applications.forEach((application) => {
    const normalized = normalizeState(application.status);
    if (normalized === 'approved') {
      summary.approved += 1;
      return;
    }
    if (normalized === 'rejected') {
      summary.rejected += 1;
      return;
    }
    if (normalized === 'under_review') {
      summary.underReview += 1;
      return;
    }
    summary.other += 1;
  });

  return summary;
}

function DashboardPanel({
  applications,
  isLoadingApplications,
  events,
  selectedSubmissionId,
  isLoadingData,
  dataView,
  onRefreshApplications,
  onSelectSubmission,
  onRefreshDataView,
}: DashboardPanelProps) {
  const summary = summarizeByStatus(applications);

  return (
    <section>
      <h2>Mode Dashboard</h2>
      <div className="dashboard-summary-grid">
        <div className="status-chip">
          Total: <strong>{summary.total}</strong>
        </div>
        <div className="status-chip">
          Under Review: <strong>{summary.underReview}</strong>
        </div>
        <div className="status-chip">
          Approved: <strong>{summary.approved}</strong>
        </div>
        <div className="status-chip">
          Rejected: <strong>{summary.rejected}</strong>
        </div>
      </div>

      <div className="dashboard-toolbar">
        <button
          type="button"
          onClick={() => void onRefreshApplications()}
          disabled={isLoadingApplications}
        >
          {isLoadingApplications ? 'Refreshing list...' : 'Refresh Applications'}
        </button>
        <span>
          {selectedSubmissionId
            ? `Tracking submission ${selectedSubmissionId}`
            : 'Select a submission to stream live updates'}
        </span>
      </div>

      <div className="application-table-wrap">
        <table className="application-table">
          <thead>
            <tr>
              <th>Submission</th>
              <th>Applicant</th>
              <th>Status</th>
              <th>Risk</th>
              <th>Submitted</th>
            </tr>
          </thead>
          <tbody>
            {applications.length === 0 ? (
              <tr>
                <td colSpan={5} className="empty-text">
                  No submissions found for this mode.
                </td>
              </tr>
            ) : (
              applications.map((application) => {
                const normalizedState = normalizeState(application.status);
                return (
                  <tr
                    key={application.submissionId}
                    className={application.submissionId === selectedSubmissionId ? 'selected' : ''}
                    onClick={() => onSelectSubmission(application.submissionId)}
                  >
                    <td>{application.submissionId}</td>
                    <td>{application.applicantId}</td>
                    <td>
                      <span className={`state-pill ${stateClassName(normalizedState)}`}>
                        {formatStatus(normalizedState)}
                      </span>
                    </td>
                    <td>
                      {application.riskScore ?? '-'}{' '}
                      {application.riskLevel ? `(${application.riskLevel})` : ''}
                    </td>
                    <td>{formatTimestamp(application.submittedAt)}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="live-grid">
        <div className="live-card">
          <h3>Live Activity</h3>
          {events.length === 0 ? (
            <p className="timeline-empty">Waiting for events...</p>
          ) : (
            <ol className="timeline-list compact">
              {events.map((event) => (
                <li key={event.id}>
                  <strong>{event.type}</strong> {event.message}
                  <div className="time-stamp">{new Date(event.timestamp).toLocaleTimeString()}</div>
                </li>
              ))}
            </ol>
          )}
          <div className="log-box compact">
            {events.length === 0
              ? 'No events yet'
              : events
                  .map((event) => `[${event.timestamp}] ${event.type} ${JSON.stringify(event.raw)}`)
                  .join('\n')}
          </div>
        </div>

        <div className="live-card">
          <h3>Data Snapshot</h3>
          <button
            type="button"
            onClick={() => void onRefreshDataView()}
            disabled={isLoadingData || !selectedSubmissionId}
          >
            {isLoadingData ? 'Refreshing snapshot...' : 'Refresh Snapshot'}
          </button>
          {!dataView ? (
            <p className="empty-text">No submission selected.</p>
          ) : (
            <>
              <p className="dataview-meta">
                Source: <strong>{dataView.source}</strong>
                {dataView.error ? (
                  <span style={{ color: '#b45309' }}> (fallback reason: {dataView.error})</span>
                ) : null}
              </p>
              <pre className="json-box compact">{JSON.stringify(dataView.data, null, 2)}</pre>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

export default DashboardPanel;
