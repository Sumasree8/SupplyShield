import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskLevelBadge } from './RiskLevelBadge';

describe('RiskLevelBadge', () => {
  it('renders the human label for a known level', () => {
    render(<RiskLevelBadge level="critical" />);
    expect(screen.getByText('Critical')).toBeInTheDocument();
  });

  it('applies the level-specific class', () => {
    render(<RiskLevelBadge level="high" />);
    expect(screen.getByText('High')).toHaveClass('badge--high');
  });

  it('falls back to the raw value for an unknown level', () => {
    render(<RiskLevelBadge level="unknown" />);
    expect(screen.getByText('unknown')).toBeInTheDocument();
  });
});
