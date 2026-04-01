import { useDeferredValue, useState } from "react";

import { Rail } from "@/components/layout/Rail";
import { Badge } from "@/components/primitives/Badge";
import { Button } from "@/components/primitives/Button";
import { EmptyState } from "@/components/primitives/EmptyState";
import { Skeleton } from "@/components/primitives/Skeleton";
import { Text } from "@/components/primitives/Text";
import type { JiraStory, PhaseResponse } from "@/lib/api/contracts";

import { useJiraConfiguredQuery, useJiraStoriesQuery, useStartSessionMutation } from "./hooks";
import styles from "./StoryIntakeRail.module.css";

type StoryIntakeRailProps = {
  selectedStoryKey: string | null;
  onStorySelected: (story: JiraStory) => void;
  onSessionStarted: (response: PhaseResponse) => void;
};

const DEMO_ACCEPTANCE_CRITERIA = [
  {
    index: 0,
    text: "Operators can open a story without losing API compatibility.",
    checked: false,
  },
];

export function StoryIntakeRail({
  selectedStoryKey,
  onStorySelected,
  onSessionStarted,
}: StoryIntakeRailProps) {
  const [searchValue, setSearchValue] = useState("");
  const deferredSearch = useDeferredValue(searchValue);
  const jiraConfigured = useJiraConfiguredQuery();
  const storiesQuery = useJiraStoriesQuery();
  const startSession = useStartSessionMutation();

  const visibleStories = (storiesQuery.data ?? []).filter((story) => {
    const haystack = `${story.key} ${story.summary}`.toLowerCase();
    return haystack.includes(deferredSearch.trim().toLowerCase());
  });

  const canStartDemo = visibleStories.length > 0 && !startSession.isPending;

  function handleStartDemo() {
    const firstStory = visibleStories[0];
    if (!firstStory) {
      return;
    }

    onStorySelected(firstStory);
    startSession.mutate(
      {
        jiraKey: firstStory.key,
        jiraSummary: firstStory.summary,
        acceptanceCriteria: DEMO_ACCEPTANCE_CRITERIA,
      },
      {
        onSuccess: onSessionStarted,
      },
    );
  }

  return (
    <Rail
      ariaLabel="Story intake"
      label="Intake"
      title="Story intake"
      description="Typed Jira intake and session bootstrap live here. Manual entry and resume surfaces land in the next epic."
    >
      <div className={styles.stack}>
        <Text tone="muted">
          Jira {jiraConfigured.data ? "is available" : "will fall back to local entry"} for this
          shell.
        </Text>
        <input
          className={styles.search}
          type="search"
          placeholder="Filter Jira stories"
          value={searchValue}
          onChange={(event) => setSearchValue(event.target.value)}
        />
        <div className={styles.list}>
          {storiesQuery.isPending ? (
            <>
              <Skeleton height="4rem" />
              <Skeleton height="4rem" />
              <Skeleton height="4rem" />
            </>
          ) : storiesQuery.isError ? (
            <EmptyState
              title="Unable to load Jira stories"
              description="The shell stays usable and the API client exposes this failure cleanly."
            />
          ) : visibleStories.length === 0 ? (
            <EmptyState
              title="No stories match this filter"
              description="Adjust the search or use manual entry once the next intake story lands."
            />
          ) : (
            visibleStories.map((story) => (
              <button
                key={story.key}
                type="button"
                className={styles.storyButton}
                data-selected={selectedStoryKey === story.key}
                onClick={() => onStorySelected(story)}
              >
                <div className={styles.meta}>
                  <span className={styles.storyKey}>{story.key}</span>
                  <Badge tone="muted">{story.status}</Badge>
                </div>
                <span className={styles.storySummary}>{story.summary}</span>
              </button>
            ))
          )}
        </div>
        <Button
          variant="secondary"
          isLoading={startSession.isPending}
          onClick={handleStartDemo}
          disabled={!canStartDemo}
        >
          Start demo session
        </Button>
      </div>
    </Rail>
  );
}
