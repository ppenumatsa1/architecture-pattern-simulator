import { SimulationEvent } from '../types';

interface FlowTimelineProps {
  events: SimulationEvent[];
}

function FlowTimeline({ events }: FlowTimelineProps) {
  return (
    <section>
      <h2>Flow Timeline</h2>
      {events.length === 0 ? (
        <p className="timeline-empty">Waiting for events...</p>
      ) : (
        <ol className="timeline-list">
          {events.map((event) => (
            <li key={event.id}>
              <strong>{event.type}</strong> — {event.message}
              <div className="time-stamp">{new Date(event.timestamp).toLocaleTimeString()}</div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export default FlowTimeline;
