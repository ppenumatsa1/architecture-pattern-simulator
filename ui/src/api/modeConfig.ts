import { ArchitectureModeConfig } from '../types';

const modeConfigs: Record<ArchitectureModeConfig['mode'], ArchitectureModeConfig> = {
  monolith: {
    mode: 'monolith',
    label: 'Monolith',
    description: 'Single deployable service handling commands, persistence, and reads.',
    submitEndpoint: '/api/monolith/submissions',
    eventsEndpoint: (submissionId: string) => `/api/monolith/submissions/${submissionId}/events`,
    dataEndpoint: (submissionId: string) => `/api/monolith/submissions/${submissionId}`,
    diagram: {
      title: 'Monolith',
      summary: 'One API, one datastore, one place to debug.',
      nodes: ['UI', 'Monolith API', 'Monolith DB'],
      flow: ['UI -> Monolith API', 'Monolith API -> Monolith DB', 'Monolith API -> UI (events)'],
    },
  },
  microservices: {
    mode: 'microservices',
    label: 'Microservices',
    description: 'Submission, processing, and status handled by separate services.',
    submitEndpoint: '/api/microservices/submissions',
    eventsEndpoint: (submissionId: string) =>
      `/api/microservices/submissions/${submissionId}/events`,
    dataEndpoint: (submissionId: string) => `/api/microservices/submissions/${submissionId}/status`,
    diagram: {
      title: 'Microservices',
      summary:
        'Outbox publishers bridge DB transactions to Redis Streams for reliable async processing.',
      nodes: [
        'UI',
        'Micro Submission API',
        'Micro Outbox Publisher',
        'Redis Streams',
        'Micro Risk Service',
        'Micro Persistence Service',
        'Micro Status API',
        'Status DB',
      ],
      flow: [
        'UI -> Micro Submission API',
        'Submission API -> Outbox row (same DB transaction)',
        'Micro Outbox Publisher -> Redis Streams (submission_requests/risk_results)',
        'Redis Streams -> Micro Risk Service -> Micro Persistence Service',
        'Micro Persistence Service -> Status DB',
        'Micro Status API -> UI (events)',
      ],
    },
  },
  'event-sourcing': {
    mode: 'event-sourcing',
    label: 'Event Sourcing + CQRS',
    description: 'Commands append immutable events; projections serve query models.',
    submitEndpoint: '/api/event-sourcing/commands/create-submission',
    eventsEndpoint: (submissionId: string) =>
      `/api/event-sourcing/submissions/${submissionId}/events`,
    dataEndpoint: (submissionId: string) => `/api/event-sourcing/projections/${submissionId}`,
    diagram: {
      title: 'Event Sourcing + CQRS',
      summary:
        'Command and risk writes use transactional outbox; workers publish and project immutable events.',
      nodes: [
        'UI',
        'CQRS Command API',
        'Event Store',
        'CQRS Outbox Worker',
        'Redis Streams',
        'CQRS Risk Worker',
        'CQRS Projection Worker',
        'CQRS Query API',
      ],
      flow: [
        'UI -> CQRS Command API',
        'Command API -> Event Store + Outbox row',
        'CQRS Outbox Worker -> Redis Streams (domain_events)',
        'Event Store sequence -> CQRS Risk Worker -> Event Store + Outbox',
        'CQRS Projection Worker -> Query read models',
        'CQRS Query API -> UI (events/reads)',
      ],
    },
  },
};

export const architectureModes = Object.values(modeConfigs);

export function getModeConfig(mode: ArchitectureModeConfig['mode']): ArchitectureModeConfig {
  return modeConfigs[mode];
}
