export type StreamConnectionState =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error'
  | 'closed';

export interface SimulationEvent {
  id: string;
  timestamp: string;
  type: string;
  source: string;
  message: string;
  raw: unknown;
}
