import { Header } from "@/components/header/Header";

export default function StoryPermalink({ params }: { params: { ac_code: string } }) {
  return (
    <>
      <Header />
      <main id="main" className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="mb-2 text-2xl font-semibold tracking-tight">Story · {params.ac_code}</h1>
        <p className="text-sm text-muted-foreground">
          Phase 6 wires this page to read from Cloud Storage and render the permalink narrative + cover + audio.
        </p>
      </main>
    </>
  );
}
