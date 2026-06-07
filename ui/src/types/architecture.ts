export type ArchitectureMode = 'monolith' | 'microservices' | 'event-sourcing';

export interface ArchitectureDiagramModel {
  title: string;
  summary: string;
  nodes: string[];
  flow: string[];
}

export interface ArchitectureModeConfig {
  mode: ArchitectureMode;
  label: string;
  description: string;
  submitEndpoint: string;
  eventsEndpoint: (submissionId: string) => string;
  dataEndpoint: (submissionId: string) => string;
  diagram: ArchitectureDiagramModel;
}
