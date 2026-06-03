import { useEffect, useMemo, useState } from "react";
import type { CSSProperties, PointerEvent } from "react";
import { getInventory, InventoryItem, StorageState } from "./api";
import appleImage from "./assets/fruits/apple.png";
import bananaImage from "./assets/fruits/banana.png";
import litchiImage from "./assets/fruits/litchi.png";
import pearImage from "./assets/fruits/pear.png";

type Tab = "home" | "inventory" | "profile";

type FruitView = {
  id: number;
  label: string;
  name: string;
  image: string;
  quantity: number;
  unit: string;
  state: StorageState;
  daysStored: number | null;
  remainingDays: number | null;
  status: string;
};

type DataStatus = "loading" | "ready" | "empty" | "fallback";

const fruitMeta: Record<string, { name: string; image: string }> = {
  apple: { name: "苹果", image: appleImage },
  banana: { name: "香蕉", image: bananaImage },
  litchi: { name: "荔枝", image: litchiImage },
  pear: { name: "梨", image: pearImage },
};

const fallbackInventory: FruitView[] = [
  {
    id: 1,
    label: "apple",
    name: "苹果",
    image: appleImage,
    quantity: 2,
    unit: "个",
    state: "fresh",
    daysStored: 1,
    remainingDays: 12,
    status: "available",
  },
  {
    id: 2,
    label: "banana",
    name: "香蕉",
    image: bananaImage,
    quantity: 4,
    unit: "根",
    state: "eat_soon",
    daysStored: 3,
    remainingDays: 2,
    status: "available",
  },
  {
    id: 3,
    label: "litchi",
    name: "荔枝",
    image: litchiImage,
    quantity: 8,
    unit: "个",
    state: "fresh",
    daysStored: 2,
    remainingDays: 5,
    status: "available",
  },
  {
    id: 4,
    label: "pear",
    name: "梨",
    image: pearImage,
    quantity: 1,
    unit: "个",
    state: "fresh",
    daysStored: 2,
    remainingDays: 10,
    status: "available",
  },
];

const stateText: Record<string, string> = {
  fresh: "新鲜",
  eat_soon: "优先吃",
  check_required: "待确认",
  not_recommended: "不推荐",
};

function toFruitView(item: InventoryItem): FruitView | null {
  const label = item.food.model_label;
  const meta = fruitMeta[label];
  if (!meta) {
    return null;
  }
  return {
    id: item.id,
    label,
    name: meta.name,
    image: meta.image,
    quantity: item.confirmed_quantity,
    unit: item.unit || "个",
    state: item.storage_state,
    daysStored: item.days_stored,
    remainingDays: item.remaining_days,
    status: item.status,
  };
}

function sortByPriority(items: FruitView[]) {
  const order: Record<string, number> = {
    eat_soon: 0,
    fresh: 1,
    check_required: 2,
    not_recommended: 3,
  };
  return [...items].sort((a, b) => {
    const aOrder = order[String(a.state)] ?? 4;
    const bOrder = order[String(b.state)] ?? 4;
    if (aOrder !== bOrder) return aOrder - bOrder;
    return (a.remainingDays ?? 999) - (b.remainingDays ?? 999);
  });
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("home");
  const [inventory, setInventory] = useState<FruitView[]>(fallbackInventory);
  const [dataStatus, setDataStatus] = useState<DataStatus>("loading");

  useEffect(() => {
    getInventory()
      .then((items) => {
        const fruits = items.map(toFruitView).filter(Boolean) as FruitView[];
        setInventory(fruits);
        setDataStatus(fruits.length > 0 ? "ready" : "empty");
      })
      .catch(() => {
        setInventory(fallbackInventory);
        setDataStatus("fallback");
      });
  }, []);

  useEffect(() => {
    if (dataStatus !== "loading") {
      return;
    }
    const timer = window.setTimeout(() => {
      setInventory(fallbackInventory);
      setDataStatus("fallback");
    }, 1600);
    return () => {
      window.clearTimeout(timer);
    };
  }, [dataStatus]);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
    requestAnimationFrame(() => {
      document.querySelector(".phone")?.scrollTo({ top: 0, behavior: "auto" });
      document.querySelectorAll(".page").forEach((page) => {
        page.scrollTo({ top: 0, behavior: "auto" });
      });
    });
  }, [activeTab]);

  const priority = useMemo(() => sortByPriority(inventory), [inventory]);
  const expiring = priority.filter((item) =>
    item.state === "eat_soon" ||
    item.state === "check_required" ||
    item.state === "not_recommended" ||
    (item.remainingDays !== null && item.remainingDays <= 3),
  );
  const freshCount = inventory.filter((item) => item.state === "fresh").length;

  function handleGlassPointer(event: PointerEvent<HTMLElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    event.currentTarget.style.setProperty("--pointer-x", `${x.toFixed(1)}%`);
    event.currentTarget.style.setProperty("--pointer-y", `${y.toFixed(1)}%`);
  }

  return (
    <main className="shell">
      <section className="phone" onPointerMove={handleGlassPointer}>
        {activeTab === "home" && (
          <HomePage key="home" priority={priority} expiring={expiring} isEmpty={dataStatus === "empty"} />
        )}
        {activeTab === "inventory" && (
          <InventoryPage
            key="inventory"
            items={priority}
            freshCount={freshCount}
            expiringCount={expiring.length}
            isEmpty={dataStatus === "empty"}
          />
        )}
        {activeTab === "profile" && <ProfilePage key="profile" />}
        <BottomNav activeTab={activeTab} onChange={setActiveTab} />
      </section>
    </main>
  );
}

function HomePage({
  priority,
  expiring,
  isEmpty,
}: {
  priority: FruitView[];
  expiring: FruitView[];
  isEmpty: boolean;
}) {
  const topFruit = priority[0];
  if (isEmpty || topFruit === undefined) {
    return (
      <div className="page">
        <header className="page-header">
          <div>
            <h1>今天</h1>
            <p>冰箱健康系统</p>
          </div>
        </header>

        <section className="hero-panel empty-hero">
          <div className="hero-copy">
            <span>今日推荐水果</span>
            <h2>暂无库存</h2>
            <p>树莓派识别到水果后，这里会自动更新。</p>
          </div>
          <div className="hero-emoji" aria-hidden="true">
            ◌
          </div>
        </section>

        <section className="ask-panel">
          <div className="ask-icon">✦</div>
          <div>
            <h2>问 AI</h2>
            <p>个性化饮食建议</p>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>今天</h1>
          <p>冰箱健康系统</p>
        </div>
      </header>

      <section className="hero-panel">
        <div className="hero-copy">
          <span>今日推荐水果</span>
          <h2>{topFruit.name}</h2>
          <p>{heroDescription(topFruit)}</p>
          <div className="freshness-chip">{itemSummary(topFruit)}</div>
        </div>
        <FruitImage className="hero-visual" item={topFruit} />
      </section>

      <section className="panel">
        <h2>优先</h2>
        <div className="priority-grid">
          {priority.slice(0, 2).map((item) => (
            <FruitMiniCard key={item.id} item={item} />
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>即将到期</h2>
        {expiring.length > 0 ? (
          <div className="expiring-row">
            {expiring.slice(0, 3).map((item) => (
              <div className="expire-item" key={item.id}>
              <FruitImage className="expire-visual" item={item} />
                <strong>{item.name}</strong>
                <span>{remainingText(item)}</span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="暂无临期水果" description="当前库存状态良好。" />
        )}
      </section>

      <section className="ask-panel">
        <div className="ask-icon">✦</div>
        <div>
          <h2>问 AI</h2>
          <p>个性化饮食建议</p>
        </div>
      </section>
    </div>
  );
}

function InventoryPage({
  items,
  freshCount,
  expiringCount,
  isEmpty,
}: {
  items: FruitView[];
  freshCount: number;
  expiringCount: number;
  isEmpty: boolean;
}) {
  const total = items.reduce((sum, item) => sum + item.quantity, 0);

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>库存</h1>
          <p>四种水果</p>
        </div>
      </header>

      <section className="stat-panel">
        <Stat value={total} label="总数" />
        <Stat value={freshCount} label="新鲜" tone="fresh" />
        <Stat value={expiringCount} label="提醒" tone="warn" />
      </section>

      <section className="inventory-list">
        {isEmpty ? (
          <EmptyState title="暂无水果库存" description="树莓派识别入库后会显示在这里。" />
        ) : (
          items.map((item) => <FruitRow key={item.id} item={item} />)
        )}
      </section>
    </div>
  );
}

function ProfilePage() {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>我的</h1>
          <p>个人偏好</p>
        </div>
      </header>

      <section className="profile-card">
        <div className="avatar">我</div>
        <div>
          <h2>用户档案</h2>
          <p>AI 冰箱体验账号</p>
        </div>
      </section>

      <ProfileItem icon="👥" title="家庭成员" tags={["暂未设置"]} />
      <ProfileItem icon="🥗" title="饮食偏好" tags={["后续配置"]} />
      <ProfileItem icon="🛡" title="过敏信息" tags={["后续配置"]} />
      <ProfileItem icon="◎" title="健康目标" tags={["后续配置"]} />
      <ProfileItem icon="🔔" title="提醒频率" tags={["后续配置"]} />
    </div>
  );
}

function FruitMiniCard({ item }: { item: FruitView }) {
  return (
    <div className="mini-card">
      <FruitImage className="mini-visual" item={item} />
      <div>
        <strong>{item.name}</strong>
        <span>{itemSummary(item)}</span>
      </div>
      <i className={`dot ${toneForState(item.state)}`} />
    </div>
  );
}

function FruitRow({ item }: { item: FruitView }) {
  const progress = progressForItem(item);

  return (
    <article className="fruit-row">
      <FruitImage className="fruit-visual" item={item} />
      <div className="fruit-main">
        <strong>{item.name}</strong>
        <span>
          {item.quantity}
          {item.unit} · {item.daysStored ?? 0} 天
        </span>
      </div>
      <div className="freshness-meter" aria-label={`${item.name} 状态`}>
        <span className={toneForState(item.state)} style={{ width: `${progress}%` }} />
      </div>
      <span className={`state-label ${toneForState(item.state)}`}>
        {itemSummary(item)}
      </span>
    </article>
  );
}

function ProfileItem({ icon, title, tags }: { icon: string; title: string; tags: string[] }) {
  return (
    <section className="profile-row">
      <span className="profile-icon">{icon}</span>
      <div>
        <h2>{title}</h2>
        <div className="tag-row">
          {tags.map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

function FruitImage({ className, item }: { className: string; item: FruitView }) {
  return (
    <span className={className}>
      <img alt={item.name} src={item.image} />
    </span>
  );
}

function Stat({ value, label, tone }: { value: number; label: string; tone?: string }) {
  return (
    <div className="stat">
      <strong>{value}</strong>
      <span className={tone}>{label}</span>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <span>{description}</span>
    </div>
  );
}

function BottomNav({ activeTab, onChange }: { activeTab: Tab; onChange: (tab: Tab) => void }) {
  const tabs: Array<{ id: Tab; label: string; icon: string }> = [
    { id: "home", label: "首页", icon: "⌂" },
    { id: "inventory", label: "库存", icon: "▣" },
    { id: "profile", label: "我的", icon: "◉" },
  ];

  return (
    <nav
      className="bottom-nav"
      aria-label="主导航"
      style={{ "--active-index": tabs.findIndex((tab) => tab.id === activeTab) } as CSSProperties}
    >
      <span className="nav-indicator" aria-hidden="true" />
      {tabs.map((tab) => (
        <button
          className={activeTab === tab.id ? "active" : ""}
          key={tab.id}
          onClick={(event) => {
            event.currentTarget.blur();
            onChange(tab.id);
            requestAnimationFrame(() => {
              document.querySelector(".phone")?.scrollTo({ top: 0, behavior: "auto" });
              document.querySelector(".page")?.scrollTo({ top: 0, behavior: "auto" });
            });
          }}
          type="button"
        >
          <span>{tab.icon}</span>
          {tab.label}
        </button>
      ))}
    </nav>
  );
}

function progressForItem(item: FruitView) {
  if (item.state === "check_required" || item.state === "not_recommended") return 18;
  if (item.state === "eat_soon") return 45;
  const remaining = item.remainingDays ?? 7;
  return Math.max(38, Math.min(86, remaining * 7));
}

function remainingText(item: FruitView) {
  if (item.state === "check_required") return "需确认";
  if (item.remainingDays === null || item.remainingDays === undefined) return "待观察";
  return `还剩 ${Math.max(0, item.remainingDays)} 天`;
}

function itemSummary(item: FruitView) {
  if (item.state === "check_required" || item.state === "not_recommended") {
    return stateText[String(item.state)] ?? "需确认";
  }
  if (item.remainingDays !== null && item.remainingDays !== undefined) {
    return item.remainingDays <= 3 ? `还剩 ${Math.max(0, item.remainingDays)} 天` : "新鲜";
  }
  return stateText[String(item.state)] ?? "待观察";
}

function heroDescription(item: FruitView) {
  if (item.state === "check_required") return "请先人工确认状态";
  if (item.remainingDays !== null && item.remainingDays !== undefined) {
    return `还剩 ${Math.max(0, item.remainingDays)} 天，建议优先安排`;
  }
  return "今天优先安排";
}

function toneForState(state: StorageState) {
  if (state === "fresh") return "fresh";
  if (state === "eat_soon") return "warn";
  if (state === "check_required") return "danger";
  if (state === "not_recommended") return "danger";
  return "muted";
}
