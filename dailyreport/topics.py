"""Heat tiers: major model news, usage changes, then wider AI news."""
import re
from .models import MODEL_NAMES

AI_CONTEXT = re.compile(r'人工智能|大模型|语言模型|生成式|机器学习|深度学习|神经网络|智能体|具身智能|扩散模型|机器人|(?<![A-Za-z0-9_])(?:AI|LLMs?)(?![A-Za-z0-9_])', re.I)
ROUNDUP = re.compile(r'早报|晚报|日报|一周(?:要闻|回顾|盘点)|今日.{0,8}汇总|(?:[；;][^；;]*){2,}')
PROMOTION = re.compile(r'奖池|奖金|有奖|征集|报名|招募|只等.{0,8}你|优惠券|限时优惠')
MODEL_TYPE = re.compile(r'大模型|语言模型|基础模型|foundation model|language model', re.I)
MODEL_RELEASE = re.compile(
    r'(?:发布|推出|开源|上线|上新|release|launch).{0,8}(?:新(?:一代)?(?:大模型|语言模型|基础模型|模型)|new model)'
    r'|(?:新(?:一代)?(?:大模型|语言模型|基础模型|模型)|new model).{0,8}(?:发布|推出|开源|上线|上新|release|launch)',
    re.I,
)
MODEL_ITERATION = re.compile(
    r'(?:模型|model).{0,5}(?:迭代|升级|新版本|版本升级|version upgrade)'
    r'|(?:迭代|升级|version upgrade).{0,5}(?:模型|model)',
    re.I,
)
VERSION_MILESTONE = re.compile(
    r'新版本|版本.{0,4}(?:发布|推出|迭代|升级|更新)|(?:发布|推出|迭代|升级|更新).{0,4}版本'
    r'|new version|version.{0,4}(?:release|launch|upgrade|update)',
    re.I,
)
CAPABILITY_UPGRADE = re.compile(
    r'(?:推理|编程|代码|数学|多模态|视觉|语音|长上下文)(?:能力|性能).{0,4}(?:升级|提升|增强|突破)'
    r'|(?:升级|提升|增强|突破).{0,4}(?:推理|编程|代码|数学|多模态|视觉|语音|长上下文)(?:能力|性能)',
    re.I,
)
NON_MODEL_ARTIFACT = re.compile(r'报告|白皮书|指南|榜单|评测|report|whitepaper|guide', re.I)


def ai_related(text):
    return bool(AI_CONTEXT.search(text) or MODEL_NAMES.search(text))


def editorial_candidate(title):
    """Exclude multi-story roundups and promotional calls from ranked news."""
    return not (ROUNDUP.search(title) or PROMOTION.search(title))


def concrete_news(title, bullets):
    """Conservative content gate, not a claim of factual verification.

    Require an identifiable subject and a concrete action/result in the actual
    summary. A catchy headline or an editorial notice cannot supply evidence.
    """
    text = ' '.join(b for b in bullets if not re.match(
        r'^(?:英文技术博客|官方公告原文|官方版本说明|论文摘要)摘录', b.strip()))
    subject = MODEL_NAMES.search(text) or re.search(
        r'\b[A-Z][A-Za-z0-9.-]{2,}\b|阿里|腾讯|百度|小米|小鹏|字节|讯飞|华为|议会|法院', text)
    action = re.search(
        r'发布|推出|新增|开源|上线|升级|重置|降价|涨价|出货|下载量|日活|'
        r'审厂|零部件定点|合作|通过.{0,12}法案|漏洞|修复|'
        r'训练.{0,15}(?:模型|分类器)|(?:提升|降低|达到|超过).{0,20}\d|'
        r'\b(?:released?|launched?|introduced?|downloads|benchmark|pricing)\b', text, re.I)
    detail = re.search(
        r'功能|支持|用于|帮助|权限|数据|工具|模型|版本|能力|审查|认证|审计|'
        r'量产|分类器|用户|下载量|日活|市场份额|\d|\b(?:model|tool|users|API)\b', text, re.I)
    return bool(subject and action and detail)


def _has_versioned_model_name(title):
    """Recognize direct versions and named variants explicitly called models."""
    for match in MODEL_NAMES.finditer(title):
        suffix = title[match.end():match.end() + 100]
        if re.match(r'\s*[-–—_/]?\s*(?:v(?:ersion)?\s*)?(?:\d+(?:\.\d+)*|[A-Za-z]\d+(?:\.\d+)*)(?![A-Za-z0-9.])', suffix, re.I):
            return True
        if re.match(
                r'\s+(?:[A-Za-z][A-Za-z-]{0,19}\s+){1,3}(?:v(?:ersion)?\s*)?\d+(?:\.\d+)*(?![A-Za-z0-9.])\s*'
                r'(?:(?:语音转文本|语音识别|语音|多模态|文本|图像|视频|语言|基础|大)?模型'
                r'|(?:(?:speech-to-text|speech|language|foundation)\s+)?model\b)',
                suffix, re.I):
            return True
        if re.match(r'\s+(?:Opus|Fable|Mythos)\s+\d+(?:\.\d+)*(?![A-Za-z0-9.])', suffix, re.I):
            return True
    return False


def _is_model_milestone(title):
    """Reserve the hottest tier for explicit model/version milestones."""
    if NON_MODEL_ARTIFACT.search(title):
        return False
    has_named_model = bool(MODEL_NAMES.search(title))
    has_model_type = bool(MODEL_TYPE.search(title))
    if not (has_named_model or has_model_type):
        return False
    if MODEL_RELEASE.search(title) or MODEL_ITERATION.search(title):
        return True
    if has_named_model and VERSION_MILESTONE.search(title):
        return True
    versioned_model = _has_versioned_model_name(title)
    release_verb = re.search(r'发布|推出|开源|上线|上新|release|launch', title, re.I)
    if versioned_model and release_verb:
        return True
    return bool(CAPABILITY_UPGRADE.search(title) and (versioned_model or has_model_type))


def news_priority(story):
    title = story.get('title', '')
    if _is_model_milestone(title):
        return 0
    if re.search(r'用量|额度|限额|重置|订阅|套餐|定价|价格|收费|免费|降价|涨价|rate.limit|quota|usage|pricing|subscription', title, re.I):
        return 1
    if ai_related(title) and re.search(
            r'发布|推出|上线|开放|接入|升级|突破|安全|风险|漏洞|示警|警示|警告|预警|监管|法案|禁令|架构|release|launch|security|safety|regulat|\bwarn(?:s|ing)?\b', title, re.I):
        return 1
    if story.get('content_kind') in ('paper', 'release'):
        return 2
    return 2


def playback_priority(story):
    """Put news about a named model family before wider AI coverage."""
    title = story.get('title', '')
    match = MODEL_NAMES.search(title)
    if not match and story.get('source_title'):
        title = story['source_title']
        match = MODEL_NAMES.search(title)
    if match:
        preceding = title[:match.start()]
        # A comparison target does not make the story news about that model.
        comparison_only = bool(re.search(r'(?:超过|超越|对比|相比|比|outpac(?:e|ing)|versus|\bvs\.?\b)\s*$', preceding, re.I))
        model_focused = not comparison_only and (
            _is_model_milestone(title) or
            bool(re.search(r'模型|大模型|推理|编程|多模态|语音|视频|智能体|Agent|发布|推出|新增|升级|更新|功能|能力|API|开源|上线|用量|额度', title, re.I)) or
            (match.start() <= 2 and bool(re.search(r'AI|人工智能|成果|产品|研究|安全', title[match.end():], re.I)))
        )
    else:
        model_focused = False
    return (0 if model_focused else 1,
            0 if story.get('category') == '模型发布' else 1,
            news_priority(story))
