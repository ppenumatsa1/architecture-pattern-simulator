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
      summary: 'Independently deployable services coordinated through Redis Streams.',
      nodes: [
        'UI',
        'Submission API',
        'Redis Streams',
        'Risk Service',
        'Persistence Service',
        'Status API',
        'Status DB',
      ],
      flow: [
        'UI -> Submission API',
        'Submission API -> Redis Streams (submission_requests)',
        'Redis Streams -> Risk Service',
        'Risk Service -> Redis Streams (risk_results)',
        'Redis Streams -> Persistence Service -> Status DB',
        'Status API -> UI (events)',
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
      summary: 'Event Store is source of truth; Redis Streams transports events to processors.',
      nodes: [
        'UI',
        'Command API',
        'Event Store',
        'Redis Streams',
        'Risk Processor',
        'Projection Processor',
        'Query API',
      ],
      flow: [
        'UI -> Command API',
        'Command API -> Event Store',
        'Command API/Event Store -> Redis Streams (domain_events)',
        'Redis Streams -> Risk Processor / Projection Processor',
        'Projection Processor -> Query API model',
        'Query API -> UI (events/reads)',
      ],
    },
  },
};

export const architectureModes = Object.values(modeConfigs);

export function getModeConfig(mode: ArchitectureModeConfig['mode']): ArchitectureModeConfig {
  return modeConfigs[mode];
}
