import { useEffect, useState, type CSSProperties } from "react";
import { LoadingCard } from "../components/ui/LoadingCard";
import { ErrorCard } from "../components/ui/ErrorCard";
import { EmptyCard } from "../components/ui/EmptyCard";
import {
  ProfileForm,
  ProfileOverview,
  type ProfileFormValue,
} from "../components/profile";
import { usePatchProfile, useProfile } from "../api/profile";
import type { Profile } from "../api/types";
import { useLanguage } from "../lib/language";
import { filterSupportedFoodLabels } from "../lib/foods";

const emptyFormValue: ProfileFormValue = {
  goal: "",
  diet_preference: "",
  cooking_condition: "",
  avoid_foods: [],
  allergies_optional: "",
  health_notes_optional: "",
};

export default function ProfilePage() {
  const { t } = useLanguage();
  const profileQuery = useProfile();
  const patchProfile = usePatchProfile();
  const profile = profileQuery.data;
  const [formValue, setFormValue] = useState<ProfileFormValue>(emptyFormValue);

  useEffect(() => {
    if (profile) {
      setFormValue(toFormValue(profile));
    }
  }, [profile]);

  if (profileQuery.isLoading && !profile) {
    return <LoadingCard title="Loading profile" />;
  }

  if (profileQuery.isError) {
    return <ErrorCard onRetry={() => void profileQuery.refetch()} />;
  }

  if (!profile) {
    return <EmptyCard title={t("profile")} description={t("pleaseTryAgain")} />;
  }

  const canSubmit =
    formValue.goal.trim().length > 0 &&
    formValue.diet_preference.trim().length > 0 &&
    formValue.cooking_condition.trim().length > 0;
  const error =
    patchProfile.error instanceof Error ? patchProfile.error.message : null;

  return (
    <div style={styles.stack}>
      <ProfileOverview profile={profile} />
      <section style={styles.formCard} aria-label="Edit profile">
        <ProfileForm
          value={formValue}
          onChange={setFormValue}
          onSubmit={() => {
            patchProfile.mutate(toProfilePatch(formValue));
          }}
          isSaving={patchProfile.isPending}
          canSubmit={canSubmit}
          error={error}
        />
      </section>
    </div>
  );
}

function toFormValue(profile: Profile): ProfileFormValue {
  return {
    goal: profile.goal ?? "",
    diet_preference: profile.diet_preference ?? "",
    cooking_condition: profile.cooking_condition ?? "",
    avoid_foods: filterSupportedFoodLabels(profile.avoid_foods),
    allergies_optional: profile.allergies_optional ?? "",
    health_notes_optional: profile.health_notes_optional ?? "",
  };
}

function toProfilePatch(value: ProfileFormValue) {
  return {
    goal: value.goal.trim(),
    diet_preference: value.diet_preference.trim(),
    cooking_condition: value.cooking_condition.trim(),
    avoid_foods: value.avoid_foods,
    allergies_optional: optionalText(value.allergies_optional),
    health_notes_optional: optionalText(value.health_notes_optional),
  };
}

function optionalText(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

const styles: Record<string, CSSProperties> = {
  stack: {
    display: "grid",
    gap: 21,
  },
  formCard: {
    background: "rgba(255, 255, 255, 0.72)",
    border: "1px solid rgba(255, 255, 255, 0.82)",
    borderRadius: 34,
    boxShadow: "0 18px 46px rgba(74, 103, 139, 0.12)",
    boxSizing: "border-box",
    maxWidth: "100%",
    padding: "18px 40px 36px",
    width: 809,
  },
};
