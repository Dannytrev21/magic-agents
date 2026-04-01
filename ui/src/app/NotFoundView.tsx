import { Link } from "react-router-dom";

import styles from "@/app/NotFoundView.module.css";

export function NotFoundView() {
  return (
    <div className={styles.root}>
      <section className={styles.panel}>
        <h1 className={styles.title}>Route not found</h1>
        <p className={styles.description}>
          The operator shell is mounted, but this route does not exist in the current workspace.
        </p>
        <Link className={styles.link} to="/">
          Return to workspace
        </Link>
      </section>
    </div>
  );
}
