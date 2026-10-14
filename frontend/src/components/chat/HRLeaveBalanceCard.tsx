// HR Leave Balance Card - Composes the shared DataCard component with HR-specific data
// Slice-14: Renders leave balance breakdown (total, casual, sick, earned)
import React from 'react';
import { DataCard } from './messages';
import type { KeyValue, BotMessageData } from './types';

export interface HRLeaveBalanceCardProps {
  total: number;
  casual: number;
  sick: number;
  earned: number;
}

export function HRLeaveBalanceCard({ total, casual, sick, earned }: HRLeaveBalanceCardProps) {
  const rows: KeyValue[] = [
    { label: 'Total Leave', value: `${total} days` },
    { label: 'Casual', value: `${casual} days` },
    { label: 'Sick', value: `${sick} days` },
    { label: 'Earned', value: `${earned} days` },
  ];

  return <DataCard title="Your Leave Balance" rows={rows} />;
}

export function createHRLeaveBalanceMessage(data: HRLeaveBalanceCardProps): BotMessageData {
  const rows: KeyValue[] = [
    { label: 'Total Leave', value: `${data.total} days` },
    { label: 'Casual', value: `${data.casual} days` },
    { label: 'Sick', value: `${data.sick} days` },
    { label: 'Earned', value: `${data.earned} days` },
  ];

  return {
    type: 'data_card',
    title: 'Your Leave Balance',
    rows,
  };
}
