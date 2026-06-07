import { fireEvent, render, screen } from '@testing-library/react';
import { vi } from 'vitest';

import ArchitectureModeSelector from '../ArchitectureModeSelector';

describe('ArchitectureModeSelector', () => {
  it('renders all modes and invokes callback when a mode is selected', () => {
    const onModeChange = vi.fn();

    render(<ArchitectureModeSelector selectedMode="monolith" onModeChange={onModeChange} />);

    expect(screen.getByRole('button', { name: /monolith/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /microservices/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /event sourcing \+ cqrs/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /microservices/i }));

    expect(onModeChange).toHaveBeenCalledWith('microservices');
    expect(onModeChange).toHaveBeenCalledTimes(1);
  });
});
