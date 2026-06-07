import { architectureModes } from '../api/modeConfig';
import { ArchitectureMode } from '../types';

interface ArchitectureModeSelectorProps {
  selectedMode: ArchitectureMode;
  onModeChange: (mode: ArchitectureMode) => void;
}

function ArchitectureModeSelector({ selectedMode, onModeChange }: ArchitectureModeSelectorProps) {
  return (
    <div className="mode-tabs" role="tablist" aria-label="Architecture mode selector">
      {architectureModes.map((mode) => {
        const active = mode.mode === selectedMode;
        return (
          <button
            key={mode.mode}
            type="button"
            onClick={() => onModeChange(mode.mode)}
            className={`mode-tab ${active ? 'active' : ''}`}
          >
            {mode.label}
          </button>
        );
      })}
    </div>
  );
}

export default ArchitectureModeSelector;
