import { redirect } from "next/navigation";

export default function V2LocalePage({ params }: { params: { locale: string } }) {
  redirect(`/general/${params.locale}`);
}
