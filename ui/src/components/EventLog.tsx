import { SimulationEvent } from '../types';

interface EventLogProps {
  events: SimulationEvent[];
}

function EventLog({ events }: EventLogProps) {
  return (
    <section>
      <h2>Event Log</h2>
      <div className="log-box">
        {events.length === 0
          ? 'No events yet'
          : events
              .map((event) => `[${event.timestamp}] ${event.type} ${JSON.stringify(event.raw)}`)
              .join('\n')}
      </div>
    </section>
  );
}

export default EventLog;
