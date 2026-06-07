import { FormEvent, useState } from 'react';
import { ArchitectureMode, InsuranceSubmissionForm } from '../types';

interface SubmissionFormProps {
  mode: ArchitectureMode;
  isSubmitting: boolean;
  onSubmit: (payload: InsuranceSubmissionForm) => Promise<void>;
}

const initialForm: InsuranceSubmissionForm = {
  applicantName: '',
  policyType: 'home',
  coverageAmount: 100000,
  applicantAge: 35,
  annualIncome: 75000,
  creditScore: 720,
  debtToIncome: 0.28,
  latePaymentsLast12Months: 0,
  hasBankruptcy: false,
  fraudFlag: false,
  notes: '',
};

function SubmissionForm({ mode, isSubmitting, onSubmit }: SubmissionFormProps) {
  const [form, setForm] = useState<InsuranceSubmissionForm>(initialForm);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await onSubmit(form);
  };

  return (
    <section className="submission-panel">
      <h2>New Submission</h2>
      <form onSubmit={handleSubmit} className="submission-form compact">
        <label>
          Applicant name
          <input
            required
            value={form.applicantName}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, applicantName: event.target.value }))
            }
          />
        </label>

        <label>
          Policy type
          <select
            value={form.policyType}
            onChange={(event) => setForm((prev) => ({ ...prev, policyType: event.target.value }))}
          >
            <option value="home">Home</option>
            <option value="auto">Auto</option>
            <option value="life">Life</option>
          </select>
        </label>

        <div className="form-two-col">
          <label>
            Coverage amount
            <input
              required
              min={1000}
              type="number"
              value={form.coverageAmount}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  coverageAmount: Number(event.target.value) || 0,
                }))
              }
            />
          </label>

          <label>
            Credit score
            <input
              required
              min={300}
              max={850}
              type="number"
              value={form.creditScore}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  creditScore: Number(event.target.value) || 0,
                }))
              }
            />
          </label>
        </div>

        <details className="advanced-fields full">
          <summary>Advanced fields</summary>
          <div className="advanced-grid">
            <label>
              Applicant age
              <input
                required
                min={18}
                type="number"
                value={form.applicantAge}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    applicantAge: Number(event.target.value) || 0,
                  }))
                }
              />
            </label>

            <label>
              Annual income
              <input
                required
                min={0}
                type="number"
                value={form.annualIncome}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    annualIncome: Number(event.target.value) || 0,
                  }))
                }
              />
            </label>

            <label>
              Debt-to-income ratio
              <input
                required
                min={0}
                max={1}
                step={0.01}
                type="number"
                value={form.debtToIncome}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    debtToIncome: Number(event.target.value) || 0,
                  }))
                }
              />
            </label>

            <label>
              Late payments (last 12 months)
              <input
                required
                min={0}
                type="number"
                value={form.latePaymentsLast12Months}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    latePaymentsLast12Months: Number(event.target.value) || 0,
                  }))
                }
              />
            </label>

            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={form.hasBankruptcy}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, hasBankruptcy: event.target.checked }))
                }
              />
              Bankruptcy history
            </label>

            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={form.fraudFlag}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, fraudFlag: event.target.checked }))
                }
              />
              Fraud flag
            </label>

            <label className="full">
              Notes
              <textarea
                value={form.notes}
                onChange={(event) => setForm((prev) => ({ ...prev, notes: event.target.value }))}
                rows={3}
              />
            </label>
          </div>
        </details>

        <button type="submit" disabled={isSubmitting} className="submit-row">
          {isSubmitting ? 'Submitting...' : `Submit (${mode})`}
        </button>
      </form>
    </section>
  );
}

export default SubmissionForm;
