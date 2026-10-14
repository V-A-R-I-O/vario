'use client';

import { IntentEditor } from '@/components/admin/IntentEditor';

// Edit an existing intent. Mode (dynamic workflow vs static FAQ) is derived from
// the loaded intent's type inside the editor.
export default function EditIntentPage({ params }: { params: { id: string } }) {
  return <IntentEditor intentId={params.id} />;
}
