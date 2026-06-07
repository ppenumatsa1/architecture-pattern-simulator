import { getModeConfig } from '../api/modeConfig';
import { ArchitectureMode, SimulationEvent, StreamConnectionState } from '../types';

interface ArchitectureDiagramProps {
  mode: ArchitectureMode;
  events: SimulationEvent[];
  connectionState: StreamConnectionState;
}

function inferActiveFlowIndex(mode: ArchitectureMode, events: SimulationEvent[]): number {
  if (!Array.isArray(events) || events.length === 0) {
    return 0;
  }

  const latestType = events[events.length - 1].type.toLowerCase();

  if (mode === 'monolith') {
    if (
      latestType.includes('decision') ||
      latestType.includes('approved') ||
      latestType.includes('rejected') ||
      latestType.includes('manual_review_requested')
    ) {
      return 2;
    }
    if (latestType.includes('risk') || latestType.includes('review')) {
      return 1;
    }
    return 0;
  }

  if (mode === 'microservices') {
    if (
      latestType.includes('decision') ||
      latestType.includes('approved') ||
      latestType.includes('rejected') ||
      latestType.includes('manual_review_requested')
    ) {
      return 7;
    }
    if (latestType.includes('review') || latestType.includes('risk')) {
      return 5;
    }
    if (latestType.includes('submission')) {
      return 3;
    }
    return 0;
  }

  if (latestType.includes('approved') || latestType.includes('rejected')) {
    return 7;
  }
  if (latestType.includes('review')) {
    return 7;
  }
  if (latestType.includes('projection')) {
    return 6;
  }
  if (latestType.includes('risk')) {
    return 5;
  }
  if (latestType.includes('submission') || latestType.includes('created')) {
    return 3;
  }
  return 0;
}

function ArchitectureDiagram({ mode, events, connectionState }: ArchitectureDiagramProps) {
  const config = getModeConfig(mode);
  const activeIndex = inferActiveFlowIndex(mode, events);

  return (
    <section>
      <h2>Architecture Flow</h2>
      <p>{config.diagram.summary}</p>
      <div className="flow-meta-row">
        <span className="state-pill under-review">Stream {connectionState}</span>
        <span>Live node highlights advance as new events arrive.</span>
      </div>
      <div className="flow-chart" role="list" aria-label="Architecture flow chart">
        {config.diagram.nodes.map((node, index) => (
          <div key={node} className="flow-step" role="listitem">
            <div className={`flow-node ${index <= activeIndex ? 'active' : ''}`}>{node}</div>
            {index < config.diagram.nodes.length - 1 ? <div className="flow-connector" /> : null}
          </div>
        ))}
      </div>
      <div className="diagram-wrap">
        <div className="flow-legend">
          {config.diagram.flow.map((step, index) => (
            <div key={step} className={`flow-legend-item ${index <= activeIndex ? 'active' : ''}`}>
              {step}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default ArchitectureDiagram;
