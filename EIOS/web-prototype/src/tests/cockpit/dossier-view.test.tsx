import { describe, expect, it } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';

function Probe() {
  const { state, openChat, showDossier, markChatUnread } = useCockpit();
  return (
    <>
      <span data-testid="view">{state.dossierView}</span>
      <span data-testid="unread">{String(state.chatUnread)}</span>
      <span data-testid="tick">{state.chatFocusTick}</span>
      <button onClick={openChat}>open</button>
      <button onClick={showDossier}>dossier</button>
      <button onClick={markChatUnread}>unread</button>
    </>
  );
}

const renderProbe = () =>
  render(
    <CockpitProvider>
      <Probe />
    </CockpitProvider>,
  );

describe('the dossier column view', () => {
  it('starts on the dossier with nothing unread', () => {
    renderProbe();
    expect(screen.getByTestId('view')).toHaveTextContent('dossier');
    expect(screen.getByTestId('unread')).toHaveTextContent('false');
  });

  it('opens the chat, asks the input to take focus each time, and clears the unread dot', () => {
    renderProbe();
    fireEvent.click(screen.getByText('unread'));
    expect(screen.getByTestId('unread')).toHaveTextContent('true');
    fireEvent.click(screen.getByText('open'));
    expect(screen.getByTestId('view')).toHaveTextContent('chat');
    expect(screen.getByTestId('unread')).toHaveTextContent('false');
    expect(screen.getByTestId('tick')).toHaveTextContent('1');
    fireEvent.click(screen.getByText('open'));
    expect(screen.getByTestId('tick')).toHaveTextContent('2');
  });

  it('goes back to the dossier', () => {
    renderProbe();
    fireEvent.click(screen.getByText('open'));
    fireEvent.click(screen.getByText('dossier'));
    expect(screen.getByTestId('view')).toHaveTextContent('dossier');
  });

  it('marks an answer unread only while the dossier is showing', () => {
    renderProbe();
    fireEvent.click(screen.getByText('open'));
    fireEvent.click(screen.getByText('unread'));
    expect(screen.getByTestId('unread')).toHaveTextContent('false');
  });

  it('Cmd+K opens the chat', () => {
    renderProbe();
    act(() => {
      fireEvent.keyDown(window, { key: 'k', metaKey: true });
    });
    expect(screen.getByTestId('view')).toHaveTextContent('chat');
  });
});
