import { Header } from "@/components/header/Header";
import { ChatStream } from "@/components/chat/ChatStream";

export default function Home() {
  return (
    <>
      <Header />
      <main id="main" className="mx-auto w-full max-w-3xl">
        <ChatStream />
      </main>
    </>
  );
}
