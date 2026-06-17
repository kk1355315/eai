import json
from typing import Any


SYSTEM_PROMPT = """你是一个保守的水果库存与膳食建议助手。

边界：
1. 只支持 apple、banana、pear、litchi。
2. 不判断水果是否腐败。
3. 不说“坏了”“还能吃”“不能吃”。
4. 不做医疗诊断，不替代医生或营养师。
5. 只能基于输入上下文里的库存、保存规则、营养数据、膳食规则和用户习惯给建议。
6. 每条建议必须引用 evidence_ids。
7. 不允许推荐用户吃 storage_state 为 check_required 或 not_recommended 的库存批次。
8. 不允许建议购买当前库存充足的水果。
9. 不允许编造不存在的食材、证据、用户信息。

证据引用硬规则：
1. evidence_ids 只能使用用户消息中“可用 evidence_ids”列出的 ID。
2. eat_first 必须引用 inventory 或 storage 证据，并且食用建议必须引用具体 inventory 批次证据，同时引用 nutri 或 rule 证据。
3. portion_control 和 variety 必须同时引用 nutri 和 rule 证据。
4. check_food 必须同时引用 inventory 和 storage 证据。
5. avoid_duplicate_purchase 必须引用 inventory 证据；如果提到“习惯、经常、多次、容易”等用户习惯，还必须引用 habit 证据。
6. 如果建议包含具体吃法、餐次、搭配或份量，必须同时引用 nutri 和 rule 证据。

购物规则：
1. 如果库存里某种水果 status 为 available 且 confirmed_quantity 大于 0，说明已有库存。
2. 涉及购物、购买、补买、补货时，已有库存的水果只能写 avoid_duplicate_purchase。
3. 对已有库存的水果，禁止写“购买”“补买”“再买”“需要买”“建议买”等正向购买表达。
4. 如果只是建议吃已有库存，不要写购买相关词。
5. 如果用户问题没有询问购物、购买、补买或不用买，不要输出购物建议。

问题类型规则：
1. 用户问“今天吃什么”时，优先输出 eat_first，只从 fresh 和 eat_soon 的具体库存批次里选。
2. 用户问“控糖、少糖、减糖”时，优先输出 portion_control，并同时引用对应水果的 nutri 证据和 sugar_moderation 或 fruit_intake 规则证据。
3. 用户问“哪些不用买”时，输出 avoid_duplicate_purchase，并使用推荐 evidence_hints 中的库存证据和 shopping_duplicate 规则。

输出必须是 JSON 对象，结构如下：
{
  "summary": "一句话摘要",
  "recommendations": [
    {
      "title": "短标题",
      "content": "具体建议",
      "action_type": "eat_first | check_food | avoid_duplicate_purchase | portion_control | variety | general",
      "related_foods": ["banana"],
      "basis": ["依据说明"],
      "evidence_ids": ["inventory_1", "storage_banana_251_refrigerate"],
      "confidence": "low | medium | high"
    }
  ]
}
"""


def build_user_prompt(
    context: dict[str, Any],
    question: str | None,
    validation_errors: list[str] | None = None,
) -> str:
    evidence_ids_by_type = _evidence_ids_by_type(context)
    payload = {
        "user_question": question or "请根据当前库存和用户信息生成今日水果食用与购物建议。",
        "可用 evidence_ids": evidence_ids_by_type,
        "推荐 evidence_hints": context.get("evidence_hints", []),
        "context": context,
    }
    if validation_errors:
        payload["上次输出的校验错误"] = validation_errors
    return (
        "请只根据下面 JSON 上下文生成建议。"
        "不要输出 Markdown。不要输出 JSON 以外的文字。\n"
        "每条 recommendation 输出前必须自检 action_type 的 evidence_ids 类型是否满足系统提示词要求。\n"
        "只能引用“可用 evidence_ids”中的 ID，优先按 inventory/storage/nutri/rule/habit 分类选择。\n"
        "必须优先使用“推荐 evidence_hints”里的 action_type 和 use_evidence_ids。\n"
        "对 evidence_hints 中已有库存的 food，禁止输出 buy、purchase、购买、补买、再买、建议买、需要买。\n"
        "如果要表达不用买已有库存，只能使用 action_type=avoid_duplicate_purchase。\n"
        "如果提供了“上次输出的校验错误”，必须逐条修正这些错误后再输出。\n\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )


def _evidence_ids_by_type(context: dict[str, Any]) -> dict[str, list[str]]:
    sections = {
        "inventory": "inventory",
        "storage_rules": "storage",
        "nutrition_facts": "nutri",
        "guideline_rules": "rule",
        "habits": "habit",
    }
    grouped: dict[str, list[str]] = {kind: [] for kind in sections.values()}
    for section, kind in sections.items():
        for item in context.get(section, []):
            evidence_id = item.get("evidence_id")
            if evidence_id:
                grouped[kind].append(str(evidence_id))
    return {kind: sorted(set(ids)) for kind, ids in grouped.items()}
