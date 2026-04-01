import type { PipelineEvent } from '@/lib/api/types';

export function parseSseChunk(chunk: string): PipelineEvent[] {
  return chunk
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.startsWith('data: '))
    .flatMap((line) => {
      try {
        return [JSON.parse(line.slice(6)) as PipelineEvent];
      } catch {
        return [];
      }
    });
}
