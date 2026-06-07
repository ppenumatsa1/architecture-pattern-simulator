export interface DataViewResult {
  source: 'api' | 'fallback';
  data: unknown;
  error?: string;
}

export interface DashboardApplication {
  submissionId: string;
  applicantId: string;
  status: string;
  submittedAt: string | null;
  riskScore: number | null;
  riskLevel: string | null;
  payload: Record<string, unknown>;
  raw: unknown;
}
