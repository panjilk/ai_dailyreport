"""Editorial priority: model iterations, usage changes, then wider AI news."""
import re
from .models import MODEL_NAMES

AI_CONTEXT = re.compile(r'人工智能|大模型|语言模型|生成式|机器学习|深度学习|神经网络|智能体|具身智能|扩散模型|机器人|(?<![A-Za-z0-9_])(?:AI|LLMs?)(?![A-Za-z0-9_])', re.I)


def ai_related(text):
    return bool(AI_CONTEXT.search(text) or MODEL_NAMES.search(text))


def news_priority(story):
    title = story.get('title', '')
    if re.search(r'用量|额度|限额|重置|订阅|套餐|定价|价格|收费|免费|降价|涨价|rate.limit|quota|usage|pricing|subscription', title, re.I):
        return 1
    if story.get('content_kind') in ('paper', 'release'):
        return 2
    if re.search(r'政策|监管|法规|法案|政治|选举|融资|收购|投资|营收|财报|裁员|任命|诉讼|禁令|会议|policy|regulat|funding', title, re.I):
        return 2
    if (MODEL_NAMES.search(title) or re.search(r'大模型|语言模型|基础模型|foundation model|language model', title, re.I)) and re.search(
            r'迭代|更新|升级|新版本|新模型|发布|推出|开源|上线|上新|能力|推理|编程|多模态|release|launch|upgrade|new.version', title, re.I):
        return 0
    return 2
