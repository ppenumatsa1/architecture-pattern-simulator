import { request } from './client';
import { getModeConfig } from './modeConfig';
import {
  ArchitectureMode,
  DataViewResult,
  DashboardApplication,
  InsuranceSubmissionForm,
  SimulationEvent,
  StreamConnectionState,
  SubmissionResult,
} from '../types';

interface SubmissionApiResponse {
  submissionId?: string;
  submission_id?: string | number;
  id?: string;
  status?: string;
}

interface StreamCallbacks {
  onStatusChange: (state: StreamConnectionState) => void;
  onEvent: (event: SimulationEvent) => void;
}

function getDashboardEndpoint(mode: ArchitectureMode): string {
  if (mode === 'monolith') {
    return '/api/monolith/submissions';
  }

  if (mode === 'microservices') {
    return '/api/microservices/dashboard/submissions';
  }

  return '/api/event-sourcing/dashboard/submissions';
}

function randomId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `submission-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
}

function buildSubmissionRequestBody(mode: ArchitectureMode, payload: InsuranceSubmissionForm) {
  const submissionPayload = {
    policyType: payload.policyType,
    notes: payload.notes,
    amount: payload.coverageAmount,
    age: payload.applicantAge,
    income: payload.annualIncome,
    creditScore: payload.creditScore,
    debtToIncome: payload.debtToIncome,
    latePaymentsLast12Months: payload.latePaymentsLast12Months,
    hasBankruptcy: payload.hasBankruptcy,
    fraudFlag: payload.fraudFlag,
  };

  if (mode === 'microservices') {
    return {
      applicant_id: payload.applicantName,
      payload: submissionPayload,
    };
  }

  return {
    applicantId: payload.applicantName,
    payload: submissionPayload,
  };
}

function asObject(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function normalizeApplicationRow(raw: unknown): DashboardApplication {
  const obj = asObject(raw);
  const payload = asObject(obj.payload);
  const risk = asObject(obj.risk);

  const submissionId = String(obj.submissionId ?? obj.submission_id ?? obj.id ?? randomId());
  const applicantId = String(
    obj.applicantId ?? obj.applicant_id ?? payload.applicant_id ?? payload.applicantId ?? 'unknown',
  );
  const status = String(obj.status ?? obj.state ?? obj.submission_status ?? 'unknown');

  const submittedAt =
    (obj.submittedAt as string | undefined) ??
    (obj.submitted_at as string | undefined) ??
    (obj.receivedAt as string | undefined) ??
    (obj.received_at as string | undefined) ??
    null;

  const riskScoreRaw = risk.score ?? obj.risk_score;
  const riskScore = typeof riskScoreRaw === 'number' ? riskScoreRaw : Number(riskScoreRaw ?? NaN);
  const riskLevelRaw = risk.level ?? obj.risk_level;

  return {
    submissionId,
    applicantId,
    status,
    submittedAt,
    riskScore: Number.isFinite(riskScore) ? riskScore : null,
    riskLevel: riskLevelRaw ? String(riskLevelRaw) : null,
    payload,
    raw,
  };
}

function normalizeEvent(rawData: string, mode: ArchitectureMode): SimulationEvent {
  let parsed: unknown = rawData;
  let type = 'message';
  let message = rawData;

  try {
    parsed = JSON.parse(rawData) as unknown;
    const obj = asObject(parsed);
    type = String(obj.type ?? obj.eventType ?? obj.event_type ?? obj.status ?? 'message');
    message = String(obj.message ?? obj.detail ?? JSON.stringify(parsed));
  } catch {
    // Keep raw text payload
  }

  return {
    id: randomId(),
    timestamp: new Date().toISOString(),
    type,
    source: mode,
    message,
    raw: parsed,
  };
}

export async function submitInsuranceApplication(
  mode: ArchitectureMode,
  payload: InsuranceSubmissionForm,
): Promise<SubmissionResult> {
  const config = getModeConfig(mode);
  const requestBody = buildSubmissionRequestBody(mode, payload);
  const raw = await request<SubmissionApiResponse>(config.submitEndpoint, {
    method: 'POST',
    body: requestBody,
  });

  return {
    submissionId: String(raw.submissionId ?? raw.submission_id ?? raw.id ?? randomId()),
    status: raw.status ?? 'accepted',
    raw,
  };
}

export function subscribeToSubmissionEvents(
  mode: ArchitectureMode,
  submissionId: string,
  callbacks: StreamCallbacks,
): () => void {
  const config = getModeConfig(mode);
  const url = config.eventsEndpoint(submissionId);
  let source: EventSource | null = null;
  let retries = 0;
  let reconnectTimer: number | undefined;
  let stopped = false;

  const connect = () => {
    if (stopped) {
      return;
    }

    callbacks.onStatusChange(retries === 0 ? 'connecting' : 'reconnecting');
    source = new EventSource(url);

    source.onopen = () => {
      retries = 0;
      callbacks.onStatusChange('connected');
    };

    source.onmessage = (event: MessageEvent<string>) => {
      if (!event.data) {
        return;
      }

      callbacks.onEvent(normalizeEvent(event.data, mode));
    };

    source.onerror = () => {
      callbacks.onStatusChange('error');
      source?.close();

      if (stopped) {
        return;
      }

      retries += 1;
      const delay = Math.min(1000 * 2 ** Math.min(retries, 4), 10000);
      reconnectTimer = window.setTimeout(connect, delay);
    };
  };

  connect();

  return () => {
    stopped = true;
    if (reconnectTimer !== undefined) {
      window.clearTimeout(reconnectTimer);
    }
    source?.close();
    callbacks.onStatusChange('closed');
  };
}

export async function fetchSubmissionData(
  mode: ArchitectureMode,
  submissionId: string,
  events: SimulationEvent[],
  rawSubmissionResult?: unknown,
): Promise<DataViewResult> {
  const config = getModeConfig(mode);

  try {
    const data = await request<unknown>(config.dataEndpoint(submissionId), {
      method: 'GET',
    });
    return { source: 'api', data };
  } catch (error) {
    const latestEvent = events.length > 0 ? events[events.length - 1] : undefined;
    const fallback = {
      submissionId,
      mode,
      latestStatus: latestEvent?.type ?? 'submitted',
      eventCount: events.length,
      recentEvents: events.slice(-5).map((event) => ({
        timestamp: event.timestamp,
        type: event.type,
        message: event.message,
      })),
      submissionResponse: rawSubmissionResult ?? null,
      note: 'Fallback snapshot because data endpoint is not available yet.',
    };

    return {
      source: 'fallback',
      data: fallback,
      error: error instanceof Error ? error.message : 'Unable to load submission data',
    };
  }
}

export async function fetchApplicationsByMode(
  mode: ArchitectureMode,
  limit = 25,
): Promise<DashboardApplication[]> {
  const endpoint = getDashboardEndpoint(mode);
  const raw = await request<unknown>(`${endpoint}?limit=${limit}&offset=0`, {
    method: 'GET',
  });

  const rows = Array.isArray(raw) ? raw : asObject(raw).items;
  if (!Array.isArray(rows)) {
    return [];
  }

  return rows.map((row) => normalizeApplicationRow(row));
}
