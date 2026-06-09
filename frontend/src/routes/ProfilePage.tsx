import { LoadingCard } from "../components/ui/LoadingCard";
import { ErrorCard } from "../components/ui/ErrorCard";
import { EmptyCard } from "../components/ui/EmptyCard";
import { ProfileOverview } from "../components/profile/ProfileOverview";
import { useProfile } from "../api/profile";
import { useLanguage } from "../lib/language";

export default function ProfilePage() {
  const { t } = useLanguage();
  const profileQuery = useProfile();
  const profile = profileQuery.data;

  if (profileQuery.isLoading && !profile) {
    return <LoadingCard title="Loading profile" />;
  }

  if (profileQuery.isError) {
    return <ErrorCard onRetry={() => void profileQuery.refetch()} />;
  }

  if (!profile) {
    return <EmptyCard title={t("profile")} description={t("pleaseTryAgain")} />;
  }

  return <ProfileOverview profile={profile} />;
}
