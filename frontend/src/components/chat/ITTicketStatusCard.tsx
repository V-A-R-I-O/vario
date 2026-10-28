import React from 'react';
import { DataCard, NotFound } from './messages';
import type { BotMessageData, KeyValue } from './types';

export interface ITTicketStatusData {
  ticketId: string;
  status: string;
  category?: string;
  description?: string;
  reporter?: string;
  updatedAt?: string;
}

/** IT ticket-status card built from the shared data-card component (Slice 20). */
export function createITTicketStatusMessage(data: ITTicketStatusData): BotMessageData {
  const rows: KeyValue[] = [
    { label: 'Ticket ID', value: data.ticketId },
    { label: 'Status', value: data.status },
  ];
  if (data.category) rows.push({ label: 'Category', value: data.category });
  if (data.description) rows.push({ label: 'Description', value: data.description });
  if (data.reporter) rows.push({ label: 'Reporter', value: data.reporter });
  if (data.updatedAt) rows.push({ label: 'Last Updated', value: data.updatedAt });

  return { type: 'data_card', title: `IT Ticket ${data.ticketId} Status`, rows };
}

export function createITTicketNotFoundMessage(ticketId?: string): BotMessageData {
  return {
    type: 'not_found',
    text: ticketId
      ? `Ticket ${ticketId} was not found. Please verify the ticket ID and try again.`
      : 'Ticket was not found. Please verify the ticket ID and try again.',
  };
}

export function ITTicketStatusCard({ ticketId, status, category, description, reporter, updatedAt }: ITTicketStatusData) {
  const message = createITTicketStatusMessage({ ticketId, status, category, description, reporter, updatedAt });
  if (message.type !== 'data_card') return null;
  return <DataCard title={message.title} rows={message.rows} />;
}

export function ITTicketNotFoundCard({ ticketId }: { ticketId?: string }) {
  const message = createITTicketNotFoundMessage(ticketId);
  if (message.type !== 'not_found') return null;
  return <NotFound text={message.text} />;
}
