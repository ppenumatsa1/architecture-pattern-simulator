import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getModeConfig } from './api/modeConfig';
import {
  fetchApplicationsByMode,
  fetchSubmissionData,
  submitInsuranceApplication,
  subscribeToSubmissionEvents,
} from './api/simulatorApi';
import ArchitectureModeSelector from './components/ArchitectureModeSelector';
import SubmissionsPanel from './components/SubmissionsPanel';
import SubmissionInspector from './components/SubmissionInspector';
import SubmissionForm from './components/SubmissionForm';
import {
  ArchitectureMode,
  DataViewResult,
  DashboardApplication,
  InsuranceSubmissionForm,
  SimulationEvent,
  StreamConnectionState,
} from './types';

const PAGE_SIZE = 10;

function App() {
  const [mode, setMode] = useState<ArchitectureMode>('monolith');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [submissionId, setSubmissionId] = useState<string | null>(null);
  const [submissionRawResult, setSubmissionRawResult] = useState<unknown>(null);
  const [events, setEvents] = useState<SimulationEvent[]>([]);
  const [applications, setApplications] = useState<DashboardApplication[]>([]);
  const [isLoadingApplications, setIsLoadingApplications] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [connectionState, setConnectionState] = useState<StreamConnectionState>('idle');
  const [dataView, setDataView] = useState<DataViewResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const eventsRef = useRef<SimulationEvent[]>([]);
  const submissionRawResultRef = useRef<unknown>(null);
  const activeModeConfig = useMemo(() => getModeConfig(mode), [mode]);

  useEffect(() => {
    eventsRef.current = events;
  }, [events]);

  useEffect(() => {
    submissionRawResultRef.current = submissionRawResult;
  }, [submissionRawResult]);

  const refreshApplications = useCallback(
    async (targetMode: ArchitectureMode = mode) => {
      setIsLoadingApplications(true);
      try {
        const rows = await fetchApplicationsByMode(targetMode, 100);
        setApplications(rows);
      } catch {
        setApplications([]);
      } finally {
        setIsLoadingApplications(false);
      }
    },
    [mode],
  );

  const refreshDataView = useCallback(
    async (targetSubmissionId = submissionId, eventSnapshot?: SimulationEvent[]) => {
      if (!targetSubmissionId) {
        return;
      }

      setIsLoadingData(true);
      try {
        const data = await fetchSubmissionData(
          mode,
          targetSubmissionId,
          eventSnapshot ?? eventsRef.current,
          submissionRawResultRef.current,
        );
        setDataView(data);
      } finally {
        setIsLoadingData(false);
      }
    },
    [mode, submissionId],
  );

  useEffect(() => {
    const timer = setTimeout(() => {
      void refreshApplications(mode);
    }, 0);

    return () => clearTimeout(timer);
  }, [mode, refreshApplications]);

  useEffect(() => {
    if (!submissionId) {
      return;
    }

    const unsubscribe = subscribeToSubmissionEvents(mode, submissionId, {
      onStatusChange: setConnectionState,
      onEvent: (event) => {
        let nextEvents: SimulationEvent[] = [];
        setEvents((previous) => {
          nextEvents = [...previous, event];
          return nextEvents;
        });
        eventsRef.current = nextEvents;
        void refreshDataView(submissionId, nextEvents);
        void refreshApplications(mode);
      },
    });

    return unsubscribe;
  }, [mode, refreshApplications, refreshDataView, submissionId]);

  const handleSubmit = async (payload: InsuranceSubmissionForm) => {
    let createdSubmissionId: string | null = null;
    setIsSubmitting(true);
    setError(null);
    setEvents([]);
    eventsRef.current = [];
    setDataView(null);
    setConnectionState('idle');

    try {
      const result = await submitInsuranceApplication(mode, payload);
      createdSubmissionId = result.submissionId;
      setSubmissionId(result.submissionId);
      setSubmissionRawResult(result.raw);
      submissionRawResultRef.current = result.raw;
      const initialEvent: SimulationEvent = {
        id: `${result.submissionId}-submitted`,
        timestamp: new Date().toISOString(),
        type: 'submitted',
        source: mode,
        message: `Submission accepted with status: ${result.status}`,
        raw: result.raw,
      };
      setEvents([initialEvent]);
      eventsRef.current = [initialEvent];
      void refreshApplications(mode);
    } catch (submitError) {
      const errorMessage = submitError instanceof Error ? submitError.message : 'Submission failed';
      setError(errorMessage);
      return;
    } finally {
      setIsSubmitting(false);
    }

    await refreshDataView(createdSubmissionId ?? undefined);
  };

  const handleModeChange = (nextMode: ArchitectureMode) => {
    setMode(nextMode);
    setCurrentPage(1);
    setSubmissionId(null);
    setSubmissionRawResult(null);
    submissionRawResultRef.current = null;
    setEvents([]);
    eventsRef.current = [];
    setDataView(null);
    setError(null);
    setConnectionState('idle');
  };

  const handleSelectSubmission = (nextSubmissionId: string) => {
    setSubmissionId(nextSubmissionId);
    setSubmissionRawResult(null);
    submissionRawResultRef.current = null;
    setEvents([]);
    eventsRef.current = [];
    setConnectionState('idle');
    void refreshDataView(nextSubmissionId);
  };

  return (
    <main className="sim-shell">
      <header className="sim-header compact-header">
        <h1>Insurance Architecture Pattern Simulator</h1>
        <p>Compare Monolith, Microservices, and Event Sourcing + CQRS</p>
        <ArchitectureModeSelector selectedMode={mode} onModeChange={handleModeChange} />
        <div className="status-inline">
          <span className="status-chip compact">
            Mode: <strong>{activeModeConfig.label}</strong>
          </span>
          <span className="status-chip compact" title={activeModeConfig.submitEndpoint}>
            Endpoint: <strong>{activeModeConfig.submitEndpoint}</strong>
          </span>
          <span className="status-chip compact">
            Stream: <strong>{connectionState}</strong>
          </span>
          <span className="status-chip compact" title={submissionId ?? 'not started'}>
            Submission: <strong>{submissionId ?? 'not started'}</strong>
          </span>
        </div>
        {error ? <p className="error-banner">{error}</p> : null}
      </header>

      <div className="workflow-grid">
        <div className="workflow-left">
          <SubmissionForm mode={mode} isSubmitting={isSubmitting} onSubmit={handleSubmit} />
        </div>

        <div className="workflow-center">
          <SubmissionsPanel
            applications={applications}
            currentPage={currentPage}
            pageSize={PAGE_SIZE}
            isLoading={isLoadingApplications}
            selectedSubmissionId={submissionId}
            onSelectSubmission={handleSelectSubmission}
            onPageChange={setCurrentPage}
            onRefresh={() => refreshApplications(mode)}
          />
        </div>

        <div className="workflow-right">
          <SubmissionInspector
            mode={mode}
            submissionId={submissionId}
            events={events}
            dataView={dataView}
            isLoadingData={isLoadingData}
            onRefreshData={() => refreshDataView()}
          />
        </div>
      </div>
    </main>
  );
}

export default App;
