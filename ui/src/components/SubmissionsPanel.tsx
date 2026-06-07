import { DashboardApplication } from '../types';

interface SubmissionsPanelProps {
  applications: DashboardApplication[];
  currentPage: number;
  pageSize: number;
  isLoading: boolean;
  selectedSubmissionId: string | null;
  onSelectSubmission: (submissionId: string) => void;
  onPageChange: (page: number) => void;
  onRefresh: () => Promise<void>;
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

function formatRisk(level: string | null): string {
  if (!level) {
    return 'unknown';
  }
  return level.toLowerCase();
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return 'n/a';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'n/a';
  }

  return date.toLocaleTimeString();
}

function summarizeByStatus(applications: DashboardApplication[]) {
  const summary = {
    total: applications.length,
    approved: 0,
    rejected: 0,
    underReview: 0,
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
    }
  });

  return summary;
}

function shortId(value: string): string {
  return value.length > 9 ? `${value.slice(0, 8)}...` : value;
}

function SubmissionsPanel({
  applications,
  currentPage,
  pageSize,
  isLoading,
  selectedSubmissionId,
  onSelectSubmission,
  onPageChange,
  onRefresh,
}: SubmissionsPanelProps) {
  const summary = summarizeByStatus(applications);
  const totalPages = Math.max(1, Math.ceil(applications.length / pageSize));
  const page = Math.min(Math.max(1, currentPage), totalPages);
  const start = (page - 1) * pageSize;
  const pageRows = applications.slice(start, start + pageSize);

  return (
    <section className="dashboard-panel">
      <div className="panel-head">
        <h2>Submissions</h2>
        <button type="button" onClick={() => void onRefresh()} disabled={isLoading}>
          {isLoading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div className="summary-cards">
        <div className="summary-card">
          <span>Total</span>
          <strong>{summary.total}</strong>
        </div>
        <div className="summary-card">
          <span>Approved</span>
          <strong>{summary.approved}</strong>
        </div>
        <div className="summary-card">
          <span>Under Review</span>
          <strong>{summary.underReview}</strong>
        </div>
        <div className="summary-card">
          <span>Rejected</span>
          <strong>{summary.rejected}</strong>
        </div>
      </div>

      <div className="table-wrap">
        <table className="submissions-table">
          <thead>
            <tr>
              <th>Applicant</th>
              <th>Status</th>
              <th>Risk</th>
              <th>Submitted</th>
              <th>ID</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 ? (
              <tr>
                <td colSpan={5} className="empty-text">
                  No submissions found for this mode.
                </td>
              </tr>
            ) : (
              pageRows.map((application) => {
                const normalizedState = normalizeState(application.status);
                return (
                  <tr
                    key={application.submissionId}
                    className={application.submissionId === selectedSubmissionId ? 'selected' : ''}
                    onClick={() => onSelectSubmission(application.submissionId)}
                  >
                    <td>{application.applicantId}</td>
                    <td>
                      <span className={`state-pill ${stateClassName(normalizedState)}`}>
                        {formatStatus(normalizedState)}
                      </span>
                    </td>
                    <td>
                      <span className={`risk-pill ${formatRisk(application.riskLevel)}`}>
                        {application.riskLevel ?? 'n/a'} {application.riskScore ?? '-'}
                      </span>
                    </td>
                    <td>{formatTimestamp(application.submittedAt)}</td>
                    <td title={application.submissionId}>{shortId(application.submissionId)}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        <span>
          Showing {pageRows.length === 0 ? 0 : start + 1}-{start + pageRows.length} of{' '}
          {applications.length}
        </span>
        <div className="pager">
          <button type="button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
            Prev
          </button>
          <span>Page {page}</span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}

export default SubmissionsPanel;
