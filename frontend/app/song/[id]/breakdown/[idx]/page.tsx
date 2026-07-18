import { redirect } from 'next/navigation';

export default function BreakdownDeepLink({
  params,
}: { params: { id: string; idx: string } }) {
  redirect(`/song/${params.id}#key-lines`);
}
