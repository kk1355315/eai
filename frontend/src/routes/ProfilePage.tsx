import { LoadingCard } from "../components/ui/LoadingCard";
import { ProfileOverview } from "../components/profile/ProfileOverview";
import { useProfile } from "../api/profile";
import { previewProfile } from "../lib/previewData";

export default function ProfilePage() {
  const profileQuery = useProfile();
  const isPreviewMode = Boolean(profileQuery.isError && !profileQuery.data);
  const profile = profileQuery.data ?? (isPreviewMode ? previewProfile : undefined);

  if (profileQuery.isLoading && !profile) {
    return <LoadingCard title="Loading profile" />;
  }

  return <ProfileOverview profile={profile ?? previewProfile} />;
}
