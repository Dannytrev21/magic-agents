import { ArtifactPanel } from "@/components/layout/ArtifactPanel";
import { Rail } from "@/components/layout/Rail";
import { Badge } from "@/components/primitives/Badge";
import { Divider } from "@/components/primitives/Divider";
import { MonoText } from "@/components/primitives/MonoText";
import { Text } from "@/components/primitives/Text";

export function InspectorPreview() {
  return (
    <Rail
      ariaLabel="Evidence inspector"
      label="Inspector"
      title="Evidence inspector"
      description="Artifacts, traceability, and execution viewers slot into this pane without displacing the center workspace."
    >
      <ArtifactPanel title={<Badge tone="muted">Contract surface</Badge>}>
        <Text tone="muted">
          Typed API adapters own the backend boundary, so presentational components never build
          routes by hand.
        </Text>
      </ArtifactPanel>
      <Divider />
      <ArtifactPanel title="Spec reference">
        <MonoText>/specs/DEV-17.yaml</MonoText>
        <Text tone="muted">Mono treatment is reserved for IDs, refs, paths, and code-like content.</Text>
      </ArtifactPanel>
    </Rail>
  );
}
