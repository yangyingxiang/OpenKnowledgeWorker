import { redirect } from 'next/navigation';

export default async function ProcessPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect(`/processes/${id}/documents`);
}
