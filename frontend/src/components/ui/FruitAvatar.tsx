import { FRUIT_IMAGE_SRC } from "../../lib/fruitAssets";
import styles from "./FruitAvatar.module.css";

type FruitName = "apple" | "banana" | "litchi" | "pear";

type FruitAvatarProps = {
  fruit: FruitName;
  label?: string;
  size?: "sm" | "md" | "lg";
};

const fruitMeta = {
  apple: { label: "Apple" },
  banana: { label: "Banana" },
  litchi: { label: "Litchi" },
  pear: { label: "Pear" },
} satisfies Record<FruitName, { label: string }>;

export function FruitAvatar({ fruit, label, size = "md" }: FruitAvatarProps) {
  const meta = fruitMeta[fruit];

  return (
    <div
      className={`${styles.avatar} ${styles[fruit]} ${styles[size]}`}
      aria-label={label ?? meta.label}
      role="img"
    >
      <img alt="" className={styles.image} src={FRUIT_IMAGE_SRC[fruit]} />
    </div>
  );
}
