import type { Metadata } from "next";
import PageHeader from "@/components/ui/PageHeader";
import SectionBand from "@/components/ui/SectionBand";
import Explorer from "@/components/explorer/Explorer";

export const metadata: Metadata = {
  title: "Signer explorer",
  description: "Choose a signer and a p99 signing-time budget; see the smallest shortlisted post-quantum signature that fits.",
};

export default function ExplorerPage() {
  return (
    <>
      <PageHeader eyebrow="Interactive" title="How small can your signature be?">
        <p>
          Pick how many signatures a key must support, who signs, and how long a signature may take in the worst case of 100.
          The explorer returns the smallest of the 49 evaluated parameter sets that fits, using the measured signing-work
          distributions and the same selection rule as the paper (§4.5).
        </p>
      </PageHeader>
      <SectionBand className="!pt-0">
        <Explorer />
      </SectionBand>
    </>
  );
}
