import { useEffect, useState, type CSSProperties } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { LoadingCard } from "../components/ui/LoadingCard";
import { ErrorCard } from "../components/ui/ErrorCard";
import { EmptyCard } from "../components/ui/EmptyCard";
import {
  ProfileOverview,
  type ProfileEditField,
  type ProfileFormValue,
} from "../components/profile";
import { profileQueryKey, usePatchProfile, useProfile } from "../api/profile";
import type { Profile, ProfilePatch } from "../api/types";
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
  const queryClient = useQueryClient();
  const profileQuery = useProfile();
  const patchProfile = usePatchProfile();
  const profile = profileQuery.data;
  const [formValue, setFormValue] = useState<ProfileFormValue>(emptyFormValue);
  const [activeField, setActiveField] = useState<ProfileEditField | null>(null);

  useEffect(() => {
    if (profile && !activeField) {
      setFormValue(toFormValue(profile));
    }
  }, [activeField, profile]);

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
      <ProfileOverview
        activeField={activeField}
        canSubmit={canSubmit}
        error={error}
        formValue={formValue}
        isSaving={patchProfile.isPending}
        onChange={setFormValue}
        onSubmit={() => {
          if (!activeField) {
            return;
          }

          patchProfile.mutate(toProfilePatch(formValue, activeField), {
            onSuccess: (updatedProfile) => {
              queryClient.setQueryData(profileQueryKey, updatedProfile);
              setFormValue(toFormValue(updatedProfile));
              setActiveField(null);
            },
          });
        }}
        onToggleField={(field) => {
          if (!activeField) {
            setFormValue(toFormValue(profile));
          }
          setActiveField((current) => (current === field ? null : field));
        }}
        profile={profile}
      />
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

function toProfilePatch(
  value: ProfileFormValue,
  activeField: ProfileEditField,
): ProfilePatch {
  switch (activeField) {
    case "goal":
      return { goal: value.goal.trim() };
    case "diet_preference":
      return { diet_preference: value.diet_preference.trim() };
    case "cooking_condition":
      return { cooking_condition: value.cooking_condition.trim() };
    case "avoid_foods":
      return { avoid_foods: value.avoid_foods };
    case "allergies_optional":
      return { allergies_optional: optionalText(value.allergies_optional) };
    case "health_notes_optional":
      return { health_notes_optional: optionalText(value.health_notes_optional) };
  }
}

function optionalText(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

const styles: Record<string, CSSProperties> = {
  stack: {
    display: "grid",
    gap: 21,
    width: "min(100%, 809px)",
  },
};
