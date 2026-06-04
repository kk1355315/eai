import {
  createContext,
  type ReactNode,
  useContext,
  useMemo,
  useState,
} from "react";
import type { SupportedFoodLabel } from "../api/types";

export type Language = "en" | "zh";

const translations = {
  en: {
    advice: "Advice",
    allergies: "Allergies",
    askAi: "Ask Advisor",
    askAdvice: "Ask Advisor",
    askAdviceCopy: "Get personalized advice from your current fruit.",
    askAdvicePlaceholder: "Ask about today's fruit, meals, or what to buy next.",
    ate: "Ate",
    avoid: "Avoid",
    backToday: "Back to Today",
    bought: "Bought",
    cameraSaw: "Camera saw",
    check: "Check",
    checkingLatestFruitBatches: "Checking the latest fruit batches.",
    close: "Close",
    confirm: "Confirm",
    confirmChange: "Confirm change",
    confirmedQuantity: "Confirmed quantity",
    confirmInventoryChange: "Confirm inventory change",
    confirmInventoryFirst:
      "Confirm changes in Inventory before relying on today's plan.",
    consumed: "Consumed",
    currentConfirmedStock: "Current confirmed stock is",
    decreaseQuantity: "Decrease quantity",
    dietPreferences: "Diet Preferences",
    discarded: "Discarded",
    eatSmarter: "Eat smarter",
    eatSoon: "Eat soon",
    everyTwoDays: "Every 2 days",
    fallbackGuidance:
      "The request was not fully accepted, so the app is showing fallback guidance from available inventory data.",
    fresh: "Fresh",
    fridge: "Fridge",
    freezer: "Freezer",
    healthGoals: "Health Goals",
    home: "Home",
    household: "Household",
    increaseQuantity: "Increase quantity",
    inventory: "Inventory",
    inventoryDetails: "details",
    inventoryIsOffline: "Inventory is offline",
    inventorySummary: "Inventory summary",
    items: "items",
    keepCurrent: "Keep current",
    kitchenStock: "Kitchen stock",
    languageToggle: "中文",
    lightMeals: "Light meals",
    loadingInventory: "Loading inventory",
    lowSugar: "Low Sugar",
    moreCarefulReasoning: "More careful reasoning",
    needCheck: "Need Check",
    needCheckEmpty: "Nothing is marked for checking.",
    newBatch: "New batch",
    noFruitBatches: "No fruit batches",
    noFruitBatchesCopy:
      "Apple, Banana, Litchi, and Pear will appear here after recognition.",
    noFruitCopy: "Add apple, banana, litchi, or pear to see today's plan.",
    noFruitTitle: "No fruit yet",
    noShoppingAdvice: "No shopping advice",
    noShoppingAdviceCopy:
      "Your apple, banana, litchi, and pear inventory does not need a shopping note right now.",
    none: "None",
    nothingUrgent: "Nothing urgent today",
    nothingUrgentCopy:
      "Your available fruit looks calm. Check the list below for anything that needs confirmation.",
    pantry: "Pantry",
    optionalSearchContext: "Optional search context",
    patchInventory: "Patch inventory",
    pending: "Pending",
    pendingChange: "Pending change",
    pieces: "pieces",
    profile: "Profile",
    profileEmail: "diana.k@gmail.com",
    profileName: "Diana Kemmer",
    priority: "Priority",
    priorityEmpty: "No fruit is ready to prioritize right now.",
    quickFoodEvents: "Quick food events",
    recommended: "Recommended",
    reminders: "Reminders",
    retry: "Retry",
    shoppingAdvice: "Shopping advice",
    sendAdviceRequest: "Send advice request",
    simplePrep: "Simple prep",
    somethingNeedsAttention: "Something needs attention",
    storageLocation: "Storage location",
    loading: "Loading",
    pleaseTryAgain: "Please try again in a moment.",
    today: "Today",
    tossed: "Tossed",
    useToday: "use today",
    unknown: "Unknown",
    waitingConfirmation: "waiting for confirmation",
    weightManagement: "Weight Management",
  },
  zh: {
    advice: "建议",
    allergies: "过敏源",
    askAi: "询问建议",
    askAdvice: "询问建议",
    askAdviceCopy: "根据当前水果获得个性化建议。",
    askAdvicePlaceholder: "询问今日水果、餐食或下一次采购。",
    ate: "已食用",
    avoid: "避免",
    backToday: "返回今日",
    bought: "已购买",
    cameraSaw: "镜头识别到",
    check: "检查",
    checkingLatestFruitBatches: "正在检查最新水果库存。",
    close: "关闭",
    confirm: "确认",
    confirmChange: "确认变动",
    confirmedQuantity: "确认数量",
    confirmInventoryChange: "确认库存变动",
    confirmInventoryFirst: "请先在库存中确认变动，再参考今日计划。",
    consumed: "已食用",
    currentConfirmedStock: "当前确认库存为",
    decreaseQuantity: "减少数量",
    dietPreferences: "饮食偏好",
    discarded: "已丢弃",
    eatSmarter: "吃得更聪明",
    eatSoon: "尽快食用",
    everyTwoDays: "每 2 天",
    fallbackGuidance: "请求未完全通过，当前显示基于可用库存数据的备用建议。",
    fresh: "新鲜",
    fridge: "冷藏",
    freezer: "冷冻",
    healthGoals: "健康目标",
    home: "首页",
    household: "家庭",
    increaseQuantity: "增加数量",
    inventory: "库存",
    inventoryDetails: "详情",
    inventoryIsOffline: "库存暂不可用",
    inventorySummary: "库存概览",
    items: "项",
    keepCurrent: "保持当前",
    kitchenStock: "厨房库存",
    languageToggle: "EN",
    lightMeals: "清淡饮食",
    loadingInventory: "正在加载库存",
    lowSugar: "低糖",
    moreCarefulReasoning: "更谨慎地分析",
    needCheck: "需要检查",
    needCheckEmpty: "暂无需要检查的水果。",
    newBatch: "新批次",
    noFruitBatches: "暂无水果批次",
    noFruitBatchesCopy: "识别到苹果、香蕉、荔枝或梨后会显示在这里。",
    noFruitCopy: "添加苹果、香蕉、荔枝或梨后查看今日计划。",
    noFruitTitle: "暂无水果",
    noShoppingAdvice: "暂无采购建议",
    noShoppingAdviceCopy: "当前苹果、香蕉、荔枝和梨库存暂不需要采购提醒。",
    none: "无",
    nothingUrgent: "今日暂无紧急项",
    nothingUrgentCopy: "当前可用水果状态平稳，请查看下方是否有待确认项目。",
    pantry: "常温",
    optionalSearchContext: "可选搜索背景",
    patchInventory: "更新库存",
    pending: "待确认",
    pendingChange: "待确认变动",
    pieces: "个",
    profile: "资料",
    profileEmail: "diana.k@gmail.com",
    profileName: "Diana Kemmer",
    priority: "优先食用",
    priorityEmpty: "当前没有需要优先安排的水果。",
    quickFoodEvents: "快速记录",
    recommended: "推荐",
    reminders: "提醒",
    retry: "重试",
    shoppingAdvice: "采购建议",
    sendAdviceRequest: "发送建议请求",
    simplePrep: "简单处理",
    somethingNeedsAttention: "有内容需要处理",
    storageLocation: "储存位置",
    loading: "加载中",
    pleaseTryAgain: "请稍后重试。",
    today: "今日",
    tossed: "已丢弃",
    useToday: "今天食用",
    unknown: "未知",
    waitingConfirmation: "待确认",
    weightManagement: "体重管理",
  },
} as const satisfies Record<Language, Record<string, string>>;

export type TranslationKey = keyof (typeof translations)["en"];

const foodNames: Record<Language, Record<SupportedFoodLabel, string>> = {
  en: {
    apple: "Apple",
    banana: "Banana",
    litchi: "Litchi",
    pear: "Pear",
  },
  zh: {
    apple: "苹果",
    banana: "香蕉",
    litchi: "荔枝",
    pear: "梨",
  },
};

type LanguageContextValue = {
  language: Language;
  toggleLanguage: () => void;
  t: (key: TranslationKey) => string;
  foodName: (food: SupportedFoodLabel, fallback?: string) => string;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>("en");

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      toggleLanguage: () => setLanguage((current) => (current === "en" ? "zh" : "en")),
      t: (key) => translations[language][key],
      foodName: (food, fallback) => foodNames[language][food] ?? fallback ?? food,
    }),
    [language],
  );

  return (
    <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
  );
}

export function useLanguage() {
  const value = useContext(LanguageContext);
  if (!value) {
    throw new Error("useLanguage must be used within LanguageProvider");
  }
  return value;
}
