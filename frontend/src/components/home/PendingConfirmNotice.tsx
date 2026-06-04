import { Bell } from "lucide-react";
import { useLanguage } from "../../lib/language";
import "./home.css";

type PendingConfirmNoticeProps = {
  count: number;
};

export function PendingConfirmNotice({ count }: PendingConfirmNoticeProps) {
  const { language } = useLanguage();

  if (count <= 0) return null;

  return (
    <section className="home-card home-pending-card">
      <span className="home-pending-icon" aria-hidden="true">
        <Bell size={22} strokeWidth={2.2} />
      </span>
      <div>
        <p className="home-pending-title">
          {language === "zh"
            ? `${count} 项需要确认`
            : `${count} items need confirmation`}
        </p>
        <p className="home-pending-copy">
          {language === "zh"
            ? "请先确认库存变动"
            : "Confirm inventory changes first"}
        </p>
      </div>
    </section>
  );
}
