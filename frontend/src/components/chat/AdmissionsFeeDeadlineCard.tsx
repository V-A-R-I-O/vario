import React from 'react';
import { DataCard, FaqAnswer } from './messages';
import type { KeyValue, BotMessageData } from './types';

export interface FeeItem {
  item: string;
  amount: string;
}

export interface DeadlineItem {
  milestone: string;
  date: string;
}

export interface AdmissionsFeeDeadlineProps {
  academicYear?: string;
  fees?: FeeItem[];
  deadlines?: DeadlineItem[];
  refundPolicy?: string;
  title?: string;
}

/**
 * Admissions Fee and Deadline Card (slice-26, FR-16).
 * Composes DataCard to present tuition fees, application fees,
 * deposit amounts, and calendar milestones with key/value rows.
 */
export function AdmissionsFeeDeadlineCard({
  academicYear = '2026-2027',
  fees = [],
  deadlines = [],
  refundPolicy,
  title,
}: AdmissionsFeeDeadlineProps) {
  const rows: KeyValue[] = [];

  for (const dl of deadlines) {
    if (dl.milestone && dl.date) {
      rows.push({ label: dl.milestone, value: dl.date });
    }
  }

  for (const f of fees) {
    if (f.item && f.amount) {
      rows.push({ label: f.item, value: f.amount });
    }
  }

  if (rows.length === 0 && refundPolicy) {
    return <FaqAnswer text={`Refund Policy (${academicYear}): ${refundPolicy}`} />;
  }

  let defaultTitle = `Admissions Calendar (${academicYear})`;
  if (fees.length > 0 && deadlines.length === 0) {
    defaultTitle = `Admissions Fee Schedule (${academicYear})`;
  } else if (deadlines.length > 0 && fees.length === 0) {
    defaultTitle = `Admissions Important Deadlines (${academicYear})`;
  }

  return <DataCard title={title || defaultTitle} rows={rows} />;
}

/**
 * Helper to construct BotMessageData for fee/deadline inquiries.
 */
export function createAdmissionsFeeDeadlineMessage(
  props: AdmissionsFeeDeadlineProps & { text?: string }
): BotMessageData {
  const fees = props.fees || [];
  const deadlines = props.deadlines || [];
  const academicYear = props.academicYear || '2026-2027';

  if (fees.length > 0 || deadlines.length > 0) {
    const rows: KeyValue[] = [];
    for (const dl of deadlines) {
      if (dl.milestone && dl.date) {
        rows.push({ label: dl.milestone, value: dl.date });
      }
    }
    for (const f of fees) {
      if (f.item && f.amount) {
        rows.push({ label: f.item, value: f.amount });
      }
    }

    let defaultTitle = `Admissions Calendar (${academicYear})`;
    if (fees.length > 0 && deadlines.length === 0) {
      defaultTitle = `Admissions Fee Schedule (${academicYear})`;
    } else if (deadlines.length > 0 && fees.length === 0) {
      defaultTitle = `Admissions Important Deadlines (${academicYear})`;
    }

    return {
      type: 'data_card',
      title: props.title || defaultTitle,
      rows,
    };
  }

  return {
    type: 'faq_answer',
    text: props.text || (props.refundPolicy ? `Refund Policy: ${props.refundPolicy}` : ''),
  };
}
