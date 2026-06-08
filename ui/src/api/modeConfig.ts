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
        'Micro Outbox Publisher (submission_requests)',
        'Redis Streams (submission_requests)',
        'Micro Risk Service',
        'Micro Outbox Publisher (risk_results)',
        'Redis Streams (risk_results)',
        'Micro Persistence Service',
        'Micro Status API',
        'Status DB',
      ],
      flow: [
        'UI -> Micro Submission API',
        'Submission API -> Outbox row (same DB transaction)',
        'Micro Outbox Publisher -> Redis Streams (submission_requests)',
        'Redis Streams -> Micro Risk Service -> Outbox row (risk_results)',
        'Micro Outbox Publisher -> Redis Streams (risk_results)',
        'Redis Streams -> Micro Persistence Service',
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
        'Commands and processors append immutable events; projections and query API read from event store-backed models.',
      nodes: [
        'UI',
        'CQRS Command API',
        'Event Store',
        'CQRS Risk Worker',
        'CQRS Projection Worker',
        'CQRS Query API',
      ],
      flow: [
        'UI -> CQRS Command API',
        'Command API -> Event Store',
        'Event Store sequence -> CQRS Risk Worker -> Event Store',
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
