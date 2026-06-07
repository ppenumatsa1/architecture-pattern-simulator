export interface InsuranceSubmissionForm {
  applicantName: string;
  policyType: string;
  coverageAmount: number;
  applicantAge: number;
  annualIncome: number;
  creditScore: number;
  debtToIncome: number;
  latePaymentsLast12Months: number;
  hasBankruptcy: boolean;
  fraudFlag: boolean;
  notes: string;
}

export interface SubmissionResult {
  submissionId: string;
  status: string;
  raw: unknown;
}
