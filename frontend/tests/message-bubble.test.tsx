import { describe, expect, test } from "vitest";
import { render } from "@testing-library/react";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { LanguageProvider } from "@/lib/i18n";
import { TooltipProvider } from "@/components/ui/tooltip";

function wrap(ui: React.ReactNode) {
  return render(
    <LanguageProvider>
      <TooltipProvider delayDuration={0}>{ui}</TooltipProvider>
    </LanguageProvider>,
  );
}

describe("MessageBubble marker dispatch", () => {
  test("renders VoterRecordCard from voter_record marker", () => {
    const { container } = wrap(
      <MessageBubble
        role="assistant"
        text="Found you."
        markers={{
          voter_record: { epic: "ABC1234567", name: "Riya", ac: "KA-151", booth: "KA-151_001" },
        }}
      />,
    );
    expect(container.textContent).toContain("ABC1234567");
    expect(container.textContent).toContain("KA-151");
    expect(container.textContent).toContain("KA-151_001");
  });

  test("renders BoothCard from booth_card marker", () => {
    const { container } = wrap(
      <MessageBubble
        role="assistant"
        text=""
        markers={{
          booth_card: {
            booth_id: "KA-151_001",
            address: "GHPS, Bommanahalli",
            lat: "12.91", lng: "77.62",
            wheelchair: "true", language_assist: "Kannada, Tamil",
            eta_walk: "8 min", eta_transit: "5 min",
          },
        }}
      />,
    );
    expect(container.textContent).toContain("Bommanahalli");
    expect(container.textContent).toContain("8 min");
  });

  test("renders FormPdfCard from pdf_ready marker", () => {
    const { container } = wrap(
      <MessageBubble
        role="assistant"
        text=""
        markers={{
          pdf_ready: { url: "https://example/x.pdf", form_type: "6", filename: "form6.pdf" },
        }}
      />,
    );
    expect(container.textContent).toContain("Form 6");
    expect(container.textContent).toContain("form6.pdf");
  });

  test("plain text bubble has no marker cards", () => {
    const { container } = wrap(<MessageBubble role="assistant" text="Just chatting" />);
    expect(container.querySelectorAll("[role='dialog']")).toHaveLength(0);
  });
});
