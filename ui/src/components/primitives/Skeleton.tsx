import styles from "@/components/primitives/Skeleton.module.css";

type SkeletonProps = {
  width?: string;
  height?: string;
};

export function Skeleton({ width = "100%", height = "1rem" }: SkeletonProps) {
  return (
    <div
      className={styles.skeleton}
      aria-hidden="true"
      style={{ width, height }}
    />
  );
}
